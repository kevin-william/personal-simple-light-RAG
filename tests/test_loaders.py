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


def test_pdf_text_and_page_metadata(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=100,height=100)
    font = DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    content = DecodedStreamObject()
    content.set_data(b'BT /F1 12 Tf 10 80 Td (OAuth2 setup) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(content)
    path = tmp_path/'text.pdf'
    writer.write(path)
    doc = load_file(path)[0]
    assert 'OAuth2 setup' in doc.text
    assert doc.metadata['page']==1 and doc.metadata['total_pages']==1
