from .loaders import Document


def split_documents(documents, size=800, overlap=150):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Limites de chunk/overlap inválidos.')
    result = []
    for doc in documents:
        start = 0
        while start < len(doc.text):
            end = min(start + size, len(doc.text))
            if end < len(doc.text):
                # Preserve complete paragraphs/lines/sentences when this still advances.
                for separator in ('\n\n', '\n', '. ', ' '):
                    point = doc.text.rfind(separator, start + max(overlap + 1, size // 2), end)
                    if point >= 0:
                        end = point + len(separator)
                        break
            text = doc.text[start:end]
            meta = dict(doc.metadata, offset=start, end_offset=end, position=len(result))
            if 'line_start' in meta:
                base = doc.metadata['line_start']
                meta['line_start'] = base + doc.text.count('\n', 0, start)
                meta['line_end'] = base + doc.text.count('\n', 0, max(start, end - 1))
                headings = [line for line in doc.text[:start].splitlines() if line.startswith('#')]
                if headings:
                    meta['heading'] = headings[-1]
            if text.strip():
                result.append(Document(text, meta))
            if end == len(doc.text):
                break
            start = end - overlap
    return result
