import pytest
from src.rag.loaders import load_file, discover, clean_text


def test_unicode_lines_and_discovery(tmp_path):
    path = tmp_path / 'doc.md'
    path.write_text('\n# Título\nConfiguração\n', encoding='utf-8')
    assert load_file(path)[0].metadata['line_start'] == 1
    assert discover(tmp_path) == [path]
    assert clean_text('e\u0301\r\n') == 'é'
    path.write_bytes(b'\xff')
    with pytest.raises(UnicodeError):
        load_file(path)
    with pytest.raises(FileNotFoundError):
        discover(tmp_path / 'missing')


def test_pdf_without_text(tmp_path):
    from pypdf import PdfWriter
    path = tmp_path / 'scan.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(path)
    with pytest.warns(UserWarning), pytest.raises(ValueError, match='OCR'):
        load_file(path)
