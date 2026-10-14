import warnings


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
        messages = [{'role':'system','content':
            'Atualize uma memória de conversa MUITO enxuta. Preserve só assunto, entidades, restrições e decisões. '
            'Não copie documentos nem listas de fontes. Não responda à pergunta. '
            'Retorne apenas o resumo das mensagens antigas e da pergunta atual; a nova resposta ficará separada.'},
            {'role':'user','content':f'Resumo anterior:\n{self.summary}\nÚltima mensagem antiga:\n{previous}\nPergunta atual:\n{question}'}]
        try:
            summary = self.llm.complete(messages,max_tokens=self.max_tokens)
            if self.llm.tokens(summary) > self.max_tokens:
                raise ValueError('Resumo excedeu o limite.')
            self.summary = summary
        except (ValueError,RuntimeError) as error:
            warnings.warn(f'Resumo não atualizado: {error}. Nenhum histórico completo foi acumulado.',stacklevel=2)
        self.last_message = {'role':'assistant','content':answer}
        self.references = list(references)
        self.generation = generation
