from pydantic import BaseModel, Field, ConfigDict,field_validator
import json


class Resolution(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    standalone_query: str = Field(min_length=1,max_length=1600)
    relevant_context: str = Field(max_length=800)
    needs_retrieval: bool
    clarification_needed: str | None = Field(default=None,max_length=300)

    @field_validator('clarification_needed')
    @classmethod
    def clarification_is_a_question(cls,value):
        if value is not None and value.strip().lower() in {'false','true','null','none'}:
            raise ValueError('clarification_needed deve ser null ou uma pergunta de esclarecimento, nunca "false"/"true".')
        return value


class QueryResolver:
    def __init__(self,llm,max_tokens=256):
        self.llm,self.max_tokens = llm,max_tokens

    def resolve(self,question,memory):
        if not question.strip():
            raise ValueError('Pergunta vazia.')
        system = ('Resolva a referência da pergunta usando só o contexto pertinente. Retorne JSON compacto no schema. '
            'standalone_query é uma pergunta independente, nunca histórico ou passos anteriores completos. '
            'relevant_context contém só entidades/restrições essenciais, sem inventar fatos. '
            'Se houver dois referentes plausíveis, clarification_needed deve pedir esclarecimento. '
            'needs_retrieval só pode ser false para transformação do texto já disponível, sem novos fatos. '
            'Exemplos auxiliares a interpretar, não regras automáticas: "resuma isso", "explique melhor", "qual deles?", "e no Windows?". '
            'Após falar de OAuth2 do produto X, "como configuro isso?" vira "Como configurar OAuth2 no produto X?". '
            'Nova pergunta sem relação deve ignorar o assunto anterior.')
        system += (' Exemplo de resposta JSON: {"standalone_query":"Como configurar OAuth2 no produto X?",'
                   '"relevant_context":"OAuth2 do produto X","needs_retrieval":true,"clarification_needed":null}. '
                   'clarification_needed deve ser null para toda pergunta clara, mesmo se a resposta puder faltar nos documentos. '
                   'Nunca use a string "false" como esclarecimento. needs_retrieval é true por padrão para perguntas factuais novas. '
                   'Para "como vejo documentos indexados?", preserve o objetivo de listar/visualizar documentos, sem substituir pela pergunta anterior.')
        system += ' Primeiro copie current_question exatamente; depois resolva SOMENTE essa pergunta atual, não perguntas do resumo.'
        messages = [{'role':'system','content':system},{'role':'user','content':json.dumps(
            {'summary_of_older_messages':memory.summary,'previous_last_message':memory.last_message,
             'current_question_to_resolve':question},ensure_ascii=False)}]
        schema = Resolution.model_json_schema()
        schema['properties'] = {'current_question':{'type':'string','enum':[question]},**schema['properties']}
        schema['required'] = ['current_question',*schema.get('required',[])]
        errors = []
        for attempt in range(2):
            try:
                data = self.llm.structured(messages,schema,max_tokens=self.max_tokens)
                if data.pop('current_question',None) != question:
                    raise ValueError('current_question deve corresponder à pergunta atual, não ao histórico.')
                resolved = Resolution.model_validate(data)
                if not resolved.standalone_query.strip():
                    raise ValueError('Consulta independente vazia.')
                if resolved.clarification_needed is not None and not resolved.clarification_needed.strip():
                    resolved.clarification_needed = None
                if not memory.last_message:
                    resolved.needs_retrieval = True
                return resolved
            except (ValueError,RuntimeError) as error:
                errors.append(str(error))
                messages[0]['content'] = system + ' Repare a saída: retorne todos os campos com tipos corretos e sem campos adicionais. Erro: '+str(error)[:300]
        raise ValueError('Não foi possível resolver a pergunta após uma tentativa de reparo. '+errors[-1])
