import warnings
import json
from pydantic import BaseModel,Field,ConfigDict


class MemorySelection(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True)
    fragments: list[str] = Field(max_length=3)


class ConversationMemory:
    def __init__(self, llm, max_tokens=192):
        self.llm, self.max_tokens = llm, max_tokens
        self.clear()

    def clear(self):
        self.last_message = None
        self.summary = ''
        self.references = []
        self.generation = None

    def sync(self, generation):
        if self.generation is not None and generation != self.generation:
            self.clear()
        self.generation = generation

    def remember(self, question, answer, references, generation):
        self.sync(generation)
        previous = self.last_message['content'] if self.last_message else ''
        sources = [self.summary,previous,question]
        instructions = ('Você seleciona uma memória EXTRATIVA, não responde perguntas. '
            'Retorne JSON {"fragments":["trecho literal"]}, no máximo 3 fragmentos curtos e 35 palavras no total. '
            'Cada fragmento deve existir literalmente em UM dos textos de entrada. '
            'Selecione só assunto, entidades, restrições e decisões relevantes. '
            'Não invente comandos ou fatos, não reescreva, não complete respostas. '
            'Para pergunta sem resposta, guarde somente um trecho da própria pergunta. '
            'É permitido retornar fragments vazio quando não houver informação útil.')
        messages = [{'role':'system','content':instructions},{'role':'user','content':json.dumps(
            {'previous_summary':self.summary,'previous_last_message':previous,'question_to_remember':question},ensure_ascii=False)}]
        try:
            summary = None
            for attempt in range(2):
                try:
                    data = self.llm.structured(messages,MemorySelection.model_json_schema(),max_tokens=self.max_tokens)
                    selection = MemorySelection.model_validate(data)
                    fragments = [f for f in selection.fragments if f.strip()]
                    if any(not any(fragment in source for source in sources) for fragment in fragments):
                        raise ValueError('Memória contém fragmento inventado, não literal.')
                    summary = ' | '.join(fragments)
                    if self.llm.tokens(summary)>self.max_tokens or len(summary.split())>35:
                        raise ValueError('Seleção da memória excedeu o limite.')
                    break
                except (ValueError,RuntimeError):
                    if attempt:
                        raise
                    messages[0]['content'] = instructions+' Repare: use fragmentos menores e copie literalmente; não invente texto.'
            self.summary = summary
        except (ValueError,RuntimeError) as error:
            warnings.warn(f'Resumo não atualizado: {error}. Nenhum histórico completo foi acumulado.',stacklevel=2)
        self.last_message = {'role':'assistant','content':answer}
        self.references = list(references)
        self.generation = generation
