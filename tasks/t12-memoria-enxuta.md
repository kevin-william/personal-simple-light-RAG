# T12 - Última mensagem e resumo incremental pela LLM

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Implementada; validação local aprovada
> **Progresso:** 100% do código; validação externa conforme relatório
> **Início:** 14/10/2026 | **Fim previsto:** - | **Fim real do código:** 14/10/2026
> **Responsável:** Codex
> **Dependências:** [T10](t10-exclusao.md), [T11](t11-runtime-phi.md)
> **Commit único:** `feat(memory): add compact LLM-generated conversation state`

## 1. Por que

Preservar continuidade sem manter rodadas completas ocultas nem transformar conversa em evidência documental.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

Trecho literal da seção **### 3.6. Memória enxuta e resolução dinâmica pela LLM**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.6. Memória enxuta e resolução dinâmica pela LLM

- Estado persistente da conversa em memória: **última mensagem completa**, seu papel, resumo enxuto das mensagens anteriores e referências válidas a fontes. A pergunta atual entra transitoriamente no processamento.
- Ao concluir uma resposta, incorporar mensagens anteriores ao resumo pela LLM e manter somente a nova última mensagem completa. Não preservar uma rodada inteira como histórico adicional oculto.
- Resumo incremental limitado por tokens: assunto, entidades, restrições e decisões necessárias. Não guardar listas extensas de chunks nem copiar o histórico. Resumo de conversa não é evidência documental.
- Antes de cada busca, a LLM recebe a pergunta atual, a última mensagem e o resumo. Deve produzir saída estruturada validada com `standalone_query`, `relevant_context`, `needs_retrieval` e `clarification_needed`.
- `relevant_context` contém somente o fragmento da mensagem/resumo que resolve a referência atual. O embedder recebe a pergunta independente, que incorpora apenas as entidades/restrições necessárias, nunca todo o contexto anterior.
- Exemplo: após uma resposta sobre autenticação OAuth2 do produto X, “e como configuro isso?” vira “Como configurar a autenticação OAuth2 no produto X?”. Não incorporar à busca os demais assuntos ou todos os passos da resposta anterior.
- Templates auxiliares para perguntas triviais, como “explique melhor”, “resuma isso”, “qual deles?” e “e no Windows?”, podem orientar a LLM. A LLM deve validar sua pertinência ao contexto; não aplicar substituições cegas por palavras-chave.
- Se houver ambiguidade real, pedir uma clarificação curta. Não inventar o referente. Saída inválida deve ter tentativa limitada de reparo e tratamento explícito da falha.
- Uma transformação puramente conversacional pode dispensar nova busca quando baseada em conteúdo já disponível e fontes ainda válidas; novas afirmações factuais sobre documentos exigem recuperação.
- Consolidar resumo e resolução em uma chamada quando viável e semanticamente equivalente, medindo o custo. Chamadas adicionais à LLM têm impacto em latência; não prometer ganho de desempenho sem benchmark.
````
<!-- PLAN_EXCERPT_END -->

Trecho literal da seção **### 3.8. Interfaces**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.8. Interfaces

- Menu: iniciar chat; adicionar/atualizar arquivo ou pasta; listar documentos/estatísticas; remover/resetar; ver configuração/hardware; sair.
- Ingestão: aceitar caminhos absolutos/relativos, mostrar arquivos encontrados, progresso e relatório de falhas por arquivo.
- Chat: `/clear` limpa última mensagem e resumo; `/sources` controla detalhes; `/exit` retorna ao menu.
- Status: mostrar backend efetivo de cada modelo, versão, revisão, memória quando disponível e situação do índice.
- Preparação e execução por comandos documentados, com configuração padrão pronta para CUDA e alternativa CPU clara.
````
<!-- PLAN_EXCERPT_END -->

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/rag/memory.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_memory.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Definir estado com última mensagem, papel, resumo enxuto e referências de fontes/versionamento, com limite de tokens do resumo.
2. Após resposta, resumir incrementalmente mensagens que deixam de ser a última, incluindo a pergunta atual, e reter apenas a nova mensagem completa.
3. Resumo preserva entidades, restrições e decisões; não copiar chunks ou histórico inteiro. Tratar falha de resumo de maneira explícita sem acumular mensagens ocultas.
4. Consumir geração/eventos do catálogo para invalidar referências após exclusão/atualização. Expor clear que remove resumo e última mensagem.

## 5. Testes no mesmo commit

- Mais de cinco rodadas deixam exatamente uma mensagem completa; verificar estado e payloads.
- LLM simulada verifica resumo incremental e limite tokenizado; falha não acumula histórico escondido.
- Limpar memória esvazia estado; mudança de geração invalida fontes antigas.
- Teste opt-in de resumo real verifica concisão e preservação de entidades em exemplos fixos, sem substituir avaliação humana.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_memory.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Fora de escopo: persistir conversas no disco e usar resumo como fonte documental.
- Texto de resposta e pergunta atuais existem transitoriamente; não devem permanecer em buffer histórico após concluir o ciclo.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [x] Estado mantém somente a última mensagem completa e resumo limitado.
- [x] Referências obsoletas são invalidadas.
- [x] Código e configuração desta tarefa implementados e executáveis.
- [x] Testes deste comportamento incluídos e aprovados no mesmo commit.
- [x] Documentação diretamente afetada atualizada.
- [x] Excertos e links validados; dependências anteriores concluídas.
- [x] Gates externos têm evidência ou bloqueio explícito, sem dados fabricados.
- [x] Um commit criado com a mensagem prevista, quando houver repositório Git.

---

## Progresso final da implementação

| Item | Status |
|---|---|
| Implementação | Implementada |
| Testes | Automatizados aprovados; modelos reais conforme relatório |
| Documentação de uso | Atualizada |
| Validação real/gates | Local aprovada; pendências externas no relatório |
| Commit | Commit desta tarefa |

**Progresso geral:** código 100%; gates externos conforme [validação](../docs/validation.md).
**Critérios concluídos:** 8/8
**Evidências de execução:** pytest focado, compileall e verificador literal aprovados neste commit. Validações de hardware/modelos em [docs/validation.md](../docs/validation.md); skips não são aprovação.
