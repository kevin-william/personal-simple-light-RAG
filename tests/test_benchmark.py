from scripts.benchmark import record
from src.rag.pipeline import Answer
import json


def test_private_text_is_opt_in():
    answer = Answer(text='private secret',warnings=['private data in validation error'],metrics={'peak_rss_bytes':None})
    safe = record('private question',answer,['secret'])
    assert 'private' not in json.dumps(safe)
    assert safe['expected_phrases_present'] is True
    assert safe['grounding_review']=='pending human review'
    assert record('question',answer,include_text=True)['answer']=='private secret'
