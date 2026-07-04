"""Módulo para reconstruir documentos completos a partir de páginas."""
from typing import List

from jsonl_reader import DocumentPage
from typing import List, Tuple, Dict

class DocumentReconstructor:
    """Reconstrói o texto completo do documento a partir de páginas."""
    
    def reconstruct(self, pages: List[DocumentPage]) -> Tuple[str, Dict[int, int]]:
        """Reconstrói o texto do documento preservando a ordem das páginas.
        
        Args:
            pages: Lista de instâncias de DocumentPage ordenadas por número de página.
        
        Returns:
            Tupla de (full_text, page_offset_map) onde page_offset_map
            mapeia números de página para deslocamentos de caracteres no texto completo.
        """
        if not pages:
            return "", {}
        
        full_text_parts = []
        page_offset_map = {}
        current_offset = 0
        
        for page in pages:
            # Registra a posição inicial desta página
            page_offset_map[page.page] = current_offset
            
            # Adiciona o texto da página
            full_text_parts.append(page.text)
            
            # Atualiza o deslocamento (adiciona o comprimento do texto + nova linha para separação)
            current_offset += len(page.text)
            
            # Adiciona nova linha entre páginas se não for a última página
            if page != pages[-1]:
                full_text_parts.append("\n")
                current_offset += 1
        
        full_text = "".join(full_text_parts)
        
        return full_text, page_offset_map