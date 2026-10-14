from src.rag.loaders import Document
from src.rag.splitter import split_documents
import pytest


def test_coverage_overlap_and_metadata():
    text = '\n# A\n' + ('Unicode é.\n' * 200)
    chunks = split_documents([Document(text, {'source':'doc.md', 'line_start':1})], 80, 15)
    covered = set()
    for chunk in chunks:
        a,b = chunk.metadata['offset'],chunk.metadata['end_offset']
        assert chunk.text == text[a:b]
        assert len(chunk.text) <= 80
        assert chunk.metadata['line_start'] == 1 + text[:a].count('\n')
        covered.update(range(a,b))
    assert covered == set(range(len(text)))


def test_split_boundaries():
    with pytest.raises(ValueError):
        split_documents([], 20, 20)
    assert not split_documents([Document('', {})])
