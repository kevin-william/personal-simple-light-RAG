from types import SimpleNamespace
from src.rag.query_resolver import QueryResolver
import pytest


def test_dynamic_context_and_invalid_retry():
    result = {'standalone_query':'Como configurar OAuth2 no produto X?', 'relevant_context':'OAuth2 do produto X',
              'needs_retrieval':True,'clarification_needed':None}
    class Fake:
        calls = 0
        def structured(self,messages,*args,**kwargs):
            self.calls += 1
            self.input = messages
            return {'needs_retrieval':'true'} if self.calls == 1 else result
    llm = Fake()
    memory = SimpleNamespace(last_message={'role':'assistant','content':'OAuth2 no X. Outros passos...'},summary='X',references=[{}])
    resolved = QueryResolver(llm).resolve('e como configuro isso?',memory)
    assert llm.calls == 2
    assert 'Outros passos' not in resolved.standalone_query
    assert resolved.needs_retrieval


def test_ambiguity_and_failure_bound():
    memory = SimpleNamespace(last_message=None,summary='',references=[])
    llm = SimpleNamespace(structured=lambda *args,**kwargs: {'standalone_query':'qual?', 'relevant_context':'',
                  'needs_retrieval':False,'clarification_needed':'Qual produto?'})
    r = QueryResolver(llm).resolve('qual?',memory)
    assert r.clarification_needed == 'Qual produto?' and r.needs_retrieval
    llm.structured = lambda *args,**kwargs: {}
    with pytest.raises(ValueError,match='reparo'):
        QueryResolver(llm).resolve('qual?',memory)
