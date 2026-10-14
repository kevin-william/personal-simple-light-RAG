# T13 - Perguntas independentes e contexto mínimo pela LLM

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Código implementado; validação externa registrada em docs/validation.md
> **Progresso:** código entregue; critérios externos conforme relatório
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** Codex
> **Dependências:** [T12](t12-memoria-enxuta.md)
> **Commit único:** `feat(context): add LLM-based follow-up resolution`

## 1. Por que

Recuperar documentos relevantes para continuações sem embutir todo o histórico na consulta vetorial.

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

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/rag/query_resolver.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_query_resolver.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Enviar pergunta atual, última mensagem e resumo à LLM para resolver referências, com schema standalone_query/relevant_context/needs_retrieval/clarification_needed.
2. Validar tipos, tamanho e coerência, com tentativa de reparo limitada. Ambiguidade real produz clarificação, não referente inventado.
3. Adicionar templates auxiliares para explique melhor/resuma isso/qual deles/e no Windows, cuja pertinência é decidida pela LLM.
4. Definir saída para transformação conversacional apenas quando o conteúdo e as fontes ainda são válidos. Novas afirmações documentais exigem busca.
5. Usar somente standalone_query para embeddings; consolidar resumo e resolução somente se equivalência for demonstrada, mantendo inicialmente etapas explícitas.

## 5. Testes no mesmo commit

- Caso OAuth2 do produto X produz consulta independente sem copiar passos/assuntos irrelevantes.
- Mudança de assunto, ambiguidade, saída inválida e limite de reparos têm resultados explícitos.
- Templates não substituem palavras cegamente e versões de fontes inválidas impedem dispensar busca.
- Testes simulados validam contrato; casos opt-in com LLM real avaliam resolução semântica e registram falhas.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_query_resolver.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Fora de escopo: prometer que o modelo nunca erra e enviar histórico completo ao embedder.
- Consolidação de chamadas é otimização opcional condicionada a evidência, não requisito bloqueante.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Resolvedor retorna schema válido ou erro/clarificação controlados.
- [ ] Consulta vetorial recebe apenas pergunta independente.
- [x] Código e configuração desta tarefa implementados e executáveis.
- [x] Testes deste comportamento incluídos e aprovados no mesmo commit.
- [x] Documentação diretamente afetada atualizada.
- [x] Excertos e links validados; dependências anteriores concluídas.
- [ ] Gates externos têm evidência ou bloqueio explícito, sem dados fabricados.
- [x] Um commit criado com a mensagem prevista, quando houver repositório Git.

---

## Progresso final da implementação

| Item | Status |
|---|---|
| Implementação | Implementada |
| Testes | Automatizados aprovados; modelos reais conforme relatório |
| Documentação de uso | Atualizada |
| Validação real/gates | Pendente |
| Commit | Commit desta tarefa |

**Progresso geral:** código entregue; gates reais pendentes/conforme relatório
**Critérios concluídos:** 5/8 (gates reais avaliados no relatório)
**Evidências de execução:** pytest focado, compileall e verificador literal aprovados neste commit. Validações de hardware/modelos em `docs/validation.md`; skips não são aprovação.
