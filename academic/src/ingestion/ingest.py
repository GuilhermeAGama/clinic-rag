import json
from pathlib import Path
import re
import unicodedata

from langchain_community.document_loaders import PyPDFLoader

DATASETS = [
    {
        "type": "PCDT",
        "input": Path(__file__).resolve().parents[2] / "data" / "raw" / "pdfs" / "PCDT",
        "output": Path(__file__).resolve().parents[2] / "data" / "processed" / "pcdt.jsonl"
    },
    {
        "type": "BULA",
        "input": Path(__file__).resolve().parents[2] / "data" / "raw" / "pdfs" / "bulas",
        "output": Path(__file__).resolve().parents[2] / "data" / "processed" / "bulas.jsonl"
    }
]

RAW_FOLDER = Path(__file__).resolve().parents[2] / "data" / "raw" / "pdfs" / "bulas"
OUTPUT_FILE = Path(__file__).resolve().parents[2] / "data" / "processed" / "bulas.jsonl"

PCDT_SECTION_HEADERS = [
    "ANEXO",
    "ANEXOS",
    "APENDICE",
    "APENDICES",
    "FLUXOGRAMA",
    "FLUXOGRAMAS",
    "COLABORADORES",
    "AGRADECIMENTOS"
]

PCDT_REFERENCE_HEADERS = [
    "REFERENCIAS",
    "REFERÊNCIAS",
    "REFERENCIAS BIBLIOGRAFICAS",
    "REFERÊNCIAS BIBLIOGRÁFICAS",
    "BIBLIOGRAFIA"
]

def ingest_directory(raw_folder: Path, output_file: Path, document_type: str) -> None:
    """Seleciona todos os arquivos PDF em um diretório e os processa usando as funções auxiliares para gerar um arquivo JSONL de saída."""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("", encoding="utf-8")

    pdfs = list(raw_folder.glob("*.pdf"))

    print(f"Encontrados {len(pdfs)} PDFs em {raw_folder.name}.\n")

    with output_file.open("a", encoding="utf-8") as f:

        for pdf in pdfs:

            print(f"Lendo {pdf.name}")

            try:
                loader = PyPDFLoader(str(pdf))
                pages = loader.load()

            except Exception as e:
                print(f"Erro em {pdf.name}")
                print(e)
                continue

            
            #document_type = infer_document_type(pages)

            document = []

            for page in pages:
                document.append({
                    "page": page.metadata["page"] + 1,
                    "text": normalize_text(page.page_content)
                })

            document = remove_references(document)

            for page in document:

                if not page["text"]:
                    continue

                record = {
                    "text": page["text"],
                    "source": pdf.name,
                    "page": page["page"],
                    "type": document_type
                }

                f.write(json.dumps(record, ensure_ascii=False))
                f.write("\n")

    print(f"\nIngestão de {raw_folder.name} concluída!")

def normalize_text(text: str) -> str:
    """Remove excesso de espaços, acentos e cedilha. recebe uma string e retorna uma string limpa."""

    text = text.replace("\x00", " ")

    # Remove acentos e cedilha
    #text = unicodedata.normalize("NFD", text)
    #text = "".join(
    #    c for c in text
    #    if unicodedata.category(c) != "Mn"
    #)

    # Remove excesso de espaços
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def is_reference_header(line: str) -> bool:
    """Detecta cabeçalhos que indicam o início da seção de referências. Recebe uma string e retorna um bool."""
    return re.fullmatch(
        r"\s*(\d+\s*\.?)?\s*(REFERENCIAS|REFERÊNCIAS)(\s+BIBLIOGRAFICAS)?\s*",
        line,
        flags=re.IGNORECASE
    ) is not None


def is_section_header(line: str) -> bool:
    """Detecta cabeçalhos que encerram a seção de referências. Recebe uma string e retorna um bool"""
    line = line.strip().upper()

    return any(
        line.startswith(header)
        for header in PCDT_SECTION_HEADERS
    )


def remove_references(document):
    """Remove apenas a seção REFERÊNCIAS, preservando anexos, apêndices e demais seções posteriores. 
    Recebe uma lista de dicionários representando as páginas do documento e retorna a lista com as referências removidas."""

    inside_references = False

    for page in document:

        cleaned_lines = []

        for line in page["text"].splitlines():

            # Encontrou o início da seção REFERÊNCIAS
            if not inside_references and is_reference_header(line):
                inside_references = True
                continue

            # Encontrou uma nova seção
            if inside_references and is_section_header(line):
                inside_references = False

            if not inside_references:
                cleaned_lines.append(line)

        page["text"] = "\n".join(cleaned_lines).strip()

    return document


# main

for dataset in DATASETS:
    ingest_directory(
        dataset["input"],
        dataset["output"],
        dataset["type"]
    )
