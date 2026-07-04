"""Módulo para ler e agrupar documentos JSONL."""
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Union, Optional, Dict, List
from dataclasses import dataclass

@dataclass
class DocumentPage:
    """Representa uma única página de um documento."""
    text: str
    source: str
    page: int
    doc_type: str


class JSONLReader:
    """Lê e agrupa documentos JSONL por fonte."""
    
    def __init__(self, jsonl_path: Union[str, Path]):
        """Inicializa o leitor JSONL.
        
        Args:
            jsonl_path: Caminho para o arquivo JSONL.
        """
        self.jsonl_path = Path(jsonl_path)
    
    def read_lines(self) -> Iterator[DocumentPage]:
        """Lê todas as linhas do arquivo JSONL.
        
        Yields:
            Instâncias de DocumentPage para cada linha.
        """
        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                yield DocumentPage(
                    text=data['text'],
                    source=data['source'],
                    page=data['page'],
                    doc_type=data['type']
                )
    
    def group_by_source(self, max_sources: Optional[int] = None) -> Dict[str, List[DocumentPage]]:
        """Agrupa páginas de documentos por fonte.
        
        Args:
            max_sources: Número máximo de fontes para processar. 
                        Se None ou <= 0, processa todas as fontes.
        
        Returns:
            Dicionário mapeando fonte para lista de páginas.
        """
        groups = defaultdict(list)
        
        for page in self.read_lines():
            groups[page.source].append(page)
        
        # Ordena páginas dentro de cada fonte por número de página
        for source in groups:
            groups[source].sort(key=lambda x: x.page)
        
        # Aplica limite max_sources
        if max_sources is not None and max_sources > 0:
            sources = sorted(groups.keys())[:max_sources]
            return {s: groups[s] for s in sources}
        
        return dict(groups)