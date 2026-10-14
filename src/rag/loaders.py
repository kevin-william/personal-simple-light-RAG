from dataclasses import dataclass
from pathlib import Path
import unicodedata
import warnings


def clean_text(text):
    return unicodedata.normalize('NFC', text.replace('\r\n', '\n').replace('\r', '\n')).strip()


@dataclass
class Document:
    text: str
    metadata: dict


def discover(path):
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f'Caminho não encontrado: {path}')
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob('*') if p.is_file() and p.suffix.lower() in {'.txt', '.md', '.pdf'})


def load_file(path):
    path = Path(path).resolve()
    meta = {'source': str(path), 'name': path.name}
    if path.suffix.lower() == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(path)
        docs = []
        for i, page in enumerate(reader.pages, 1):
            text = clean_text(page.extract_text() or '')
            if text:
                docs.append(Document(text, dict(meta, page=i, total_pages=len(reader.pages))))
            else:
                warnings.warn(f'{path.name}, página {i}: sem texto extraível; pode exigir OCR.', stacklevel=2)
    elif path.suffix.lower() in {'.txt', '.md'}:
        raw = path.read_text(encoding='utf-8-sig')
        # Keep original leading newlines for exact line references.
        text = unicodedata.normalize('NFC', raw.replace('\r\n', '\n').replace('\r', '\n'))
        docs = [Document(text, dict(meta, line_start=1))] if text.strip() else []
    else:
        raise ValueError(f'Formato não suportado: {path.suffix}. Use PDF, TXT ou MD.')
    if not docs:
        raise ValueError(f'{path.name}: sem texto indexável; PDFs digitalizados exigem OCR.')
    return docs
