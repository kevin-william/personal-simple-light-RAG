from src.rag.memory import ConversationMemory
import pytest
import json


class Summarizer:
    def structured(self,messages,*args,**kwargs):
        self.input = messages
        return {'fragments':[json.loads(messages[1]['content'])['question_to_remember']]}
    def tokens(self,text):
        return len(text.split())


def test_one_message_and_bounded_summary():
    llm = Summarizer()
    memory = ConversationMemory(llm)
    for i in range(8):
        memory.remember(f'q{i}',f'a{i}',[{'version':'v1'}],1)
    assert memory.last_message == {'role':'assistant','content':'a7'}
    assert memory.summary == 'q7'
    assert 'a6' in llm.input[1]['content'] and 'a5' not in llm.input[1]['content']
    memory.sync(2)
    assert memory.last_message is None and not memory.references and not memory.summary


def test_summary_failure_does_not_accumulate_history():
    llm = Summarizer()
    memory = ConversationMemory(llm)
    llm.structured = lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError('failed'))
    with pytest.warns(UserWarning):
        memory.remember('q','new answer',[],1)
    assert memory.last_message['content'] == 'new answer'
    assert memory.summary == ''
    memory.clear()
    assert not memory.last_message


def test_invented_memory_is_rejected():
    llm = Summarizer()
    llm.structured = lambda *a,**k:{'fragments':['Mesquite -no-gpu']}
    memory = ConversationMemory(llm)
    with pytest.warns(UserWarning,match='inventado'):
        memory.remember('Qual comando CPU?','Use setup.ps1 -Profile cpu',[],1)
    assert memory.summary==''
