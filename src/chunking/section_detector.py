"""Módulo para detecção de seções em documentos."""
import re
from typing import List, Optional, Dict

from section_structure import Section


class SectionDetector:
    """Detecta seções em documentos reconstruídos.
    
    Padrão de seção:
    - Começa com nova linha
    - Seguido de enumeração (ex: "1.", "2.1", "3.4.2.1")
    - Seguido de espaço
    - Seguido de título
    - Seguido de nova linha
    - Então o conteúdo começa
    
    Exemplos:
    - \\n2. Diagnóstico\\n
    - \\n2.1 Diagnóstico Clínico\\n
    - \\n3.4.2 Tratamento Farmacológico\\n
    """
    
    # Padrão para enumeração de seção: um ou mais números separados por pontos, opcionalmente terminando com ponto
    # Exemplos: 1., 2.1, 3.4.2, 5.2.3.1
    ENUMERATION_PATTERN = r'\n(\d+(?:\.\d+)*\.?)\s+([^\n]+)\n'
    
    def __init__(self):
        """Inicializa o detector de seções."""
        self.pattern = re.compile(self.ENUMERATION_PATTERN)
    
    def detect_sections(
        self,
        full_text: str,
        source: str,
        page_offset_map: Dict[int, int]
    ) -> List[Section]:
        """Detecta todas as seções no documento usando validação hierárquica.
        
        Args:
            full_text: O texto completo do documento reconstruído.
            source: O identificador da fonte do documento.
            page_offset_map: Mapa de números de página para deslocamentos de caracteres.
        
        Returns:
            Lista de instâncias de Section detectadas.
        """
        sections = []
        
        # Encontrar todos os candidatos de seção usando regex
        matches = list(self.pattern.finditer(full_text))
        
        # Máquina de estados: rastrear última seção válida
        last_valid_components = None
        first_section_found = False
        
        for idx, match in enumerate(matches):
            numbering = match.group(1)
            title = match.group(2)
            
            # VERIFICAÇÃO DE PRIORIDADE: Parar processamento se esta for uma seção de referências
            if self._is_reference_section(title):
                break
            
            # Analisar numeração em componentes
            candidate_components = self._parse_numbering(numbering)
            
            # Validar transição hierárquica
            is_valid = False
            
            if not first_section_found:
                # Verificar se esta é uma primeira seção válida (1. ou 1.1)
                if self._is_first_valid_section(candidate_components):
                    is_valid = True
                    first_section_found = True
                    last_valid_components = candidate_components
            else:
                # Verificar se esta é uma transição válida da última seção
                if self._is_valid_transition(last_valid_components, candidate_components):
                    is_valid = True
                    last_valid_components = candidate_components
            
            # Aceitar apenas se for hierarquicamente válido
            if is_valid:
                # Calcular nível hierárquico
                level = len(candidate_components)
                
                # Determinar limites da seção
                start_pos = match.start()
                end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
                
                # Extrair conteúdo (incluindo a linha de cabeçalho da seção)
                content = full_text[start_pos:end_pos]
                
                # Determinar intervalo de páginas
                start_page = self._find_page_for_offset(start_pos, page_offset_map)
                end_page = self._find_page_for_offset(end_pos - 1, page_offset_map)
                
                section = Section(
                    source=source,
                    section_order=len(sections) + 1,
                    numbering=numbering,
                    level=level,
                    title=title,
                    content=content,
                    start_page=start_page,
                    end_page=end_page
                )
                
                sections.append(section)

        return sections
    
    def _calculate_level(self, numbering: str) -> int:
        """Calcula nível hierárquico a partir da numeração.
        
        Args:
            numbering: Numeração da seção (ex: "1.", "2.1", "3.4.2").
        
        Returns:
            Nível hierárquico (número de componentes numéricos).
        """
        # Remover ponto final se presente
        cleaned = numbering.rstrip('.')
        # Dividir por pontos e contar componentes
        components = cleaned.split('.')
        return len(components)
    
    def _find_page_for_offset(
        self,
        offset: int,
        page_offset_map: Dict[int, int]
    ) -> Optional[int]:
        """Encontra qual página contém um determinado deslocamento de caractere.
        
        Args:
            offset: Deslocamento de caractere no texto completo.
            page_offset_map: Mapa de números de página para deslocamentos de caracteres.
        
        Returns:
            Número da página contendo o deslocamento, ou None se não encontrado.
        """
        if not page_offset_map:
            return None
        
        # Encontrar a página com o maior deslocamento <= deslocamento alvo
        pages = sorted(page_offset_map.keys())
        target_page = None
        
        for page in pages:
            if page_offset_map[page] <= offset:
                target_page = page
            else:
                break
        
        return target_page

    def _parse_numbering(self, numbering: str) -> List[int]:
        """Analisa numeração de seção em componentes numéricos.
        
        Args:
            numbering: Numeração da seção (ex: "1.", "2.1", "3.4.2").
        
        Returns:
            Lista de componentes inteiros (ex: [1], [2, 1], [3, 4, 2]).
        """
        # Remover ponto final se presente
        cleaned = numbering.rstrip('.')
        # Dividir por pontos e converter para inteiros
        return [int(comp) for comp in cleaned.split('.')]
    
    def _is_first_valid_section(self, components: List[int]) -> bool:
        """Verifica se esta é uma primeira seção válida (1. ou 1.1).
        
        Args:
            components: Componentes numéricos analisados.
        
        Returns:
            True se esta for uma primeira seção válida.
        """
        # Primeiras seções válidas: 1. ou 1.1
        if len(components) == 1 and components[0] == 1:
            return True
        if len(components) == 2 and components[0] == 1 and components[1] == 1:
            return True
        return False
    
    def _is_valid_transition(self, current: List[int], candidate: List[int]) -> bool:
        """Valida se o candidato é uma transição hierárquica válida a partir do atual.
        
        Args:
            current: Componentes da última seção válida.
            candidate: Componentes da seção candidata.
        
        Returns:
            True se o candidato for uma transição válida a partir do atual.
        """
        # Regra 1: Incrementar último componente (A.B.C.(D+1))
        if len(candidate) == len(current):
            # Verificar se todos os componentes exceto o último são iguais
            if candidate[:-1] == current[:-1]:
                # Verificar se o último componente é exatamente +1
                if candidate[-1] == current[-1] + 1:
                    return True
        
        # Regra 2: Criar nova subseção (A.B.C.D.1)
        if len(candidate) == len(current) + 1:
            # Verificar se o candidato começa com o atual e termina com 1
            if candidate[:-1] == current and candidate[-1] == 1:
                return True
        
        # Regra 3: Subir para ancestral e continuar sequência
        # Verificar se o candidato é um prefixo do atual (ancestral)
        for depth in range(len(current) - 1, 0, -1):
            ancestor = current[:depth]
            if candidate == ancestor:
                # Isso está voltando ao ancestral sem incrementar - inválido
                continue
            if len(candidate) == depth:
                # Verificar se todos os componentes exceto o último correspondem ao ancestral
                if candidate[:-1] == ancestor[:-1]:
                    # Verificar se o último componente é exatamente +1
                    if candidate[-1] == ancestor[-1] + 1:
                        return True
        
        # Regra 4: Primeiro subtítulo do próximo capítulo ((A+1).1)
        if len(current) == 1 and len(candidate) == 2:
            if candidate[0] == current[0] + 1 and candidate[1] == 1:
                return True
        
        return False

    def _is_reference_section(self, title: str) -> bool:
        """Verifica se o título indica uma seção de referências.
        
        Args:
            title: Título da seção para verificar.
        
        Returns:
            True se o título indicar uma seção de referências.
        """
        # Normalizar título: minúsculas, remover espaços, remover acentos
        normalized = title.lower().strip()
        
        # Remover acentos comuns
        accents_map = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i',
            'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u',
            'ç': 'c'
        }
        
        for accented, plain in accents_map.items():
            normalized = normalized.replace(accented, plain)
        
        # Verificar indicadores de referência
        reference_indicators = [
            'referencia',
            'referencias',
            'referência',
            'referências',
            'referencias bibliograficas',
            'referências bibliográficas'
        ]
        
        return normalized in reference_indicators