from src.rag.memory import ConversationMemory
import pytest


class Summarizer:
    def complete(self,messages,**kwargs):
        self.input = messages
        return 'OAuth2 do produto X.'
    def tokens(self,text):
        return len(text.split())


def test_one_message_and_bounded_summary():
    llm = Summarizer()
    memory = ConversationMemory(llm)
    for i in range(8):
        memory.remember(f'q{i}',f'a{i}',[{'version':'v1'}],1)
    assert memory.last_message == {'role':'assistant','content':'a7'}
    assert memory.summary == 'OAuth2 do produto X.'
    assert 'a6' in llm.input[1]['content'] and 'a5' not in llm.input[1]['content']
    memory.sync(2)
    assert memory.last_message is None and not memory.references and not memory.summary


def test_summary_failure_does_not_accumulate_history():
    llm = Summarizer()
    memory = ConversationMemory(llm)
    llm.complete = lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError('failed'))
    with pytest.warns(UserWarning):
        memory.remember('q','new answer',[],1)
    assert memory.last_message['content'] == 'new answer'
    assert memory.summary == ''
    memory.clear()
    assert not memory.last_message
