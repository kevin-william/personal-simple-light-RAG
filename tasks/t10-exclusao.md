# T10 - Exclusão por identidade e reset recuperável

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Código implementado; validação externa registrada em docs/validation.md
> **Progresso:** código entregue; critérios externos conforme relatório
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** Codex
> **Dependências:** [T09](t09-atualizacao-recuperacao.md)
> **Commit único:** `feat(documents): add identity-based deletion and index reset`

## 1. Por que

Remover documentos corretos sem confundir homônimos, perder aliases restantes ou consultar conteúdo excluído.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

Trecho literal da seção **### 3.4. Duplicação, atualização e falhas**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.4. Duplicação, atualização e falhas

- Atribuir `document_id` estável, associando-o ao caminho canônico de origem. Preservar nome amigável separadamente; arquivos de mesmo nome em pastas diferentes são distintos.
- Calcular hash do conteúdo. Reimportar a mesma origem sem alterações deve ser idempotente e não gerar embeddings ou chunks duplicados.
- Reconhecer conteúdo idêntico em caminhos diferentes e reutilizar a versão vetorial, mantendo os aliases de origem no catálogo. Remover um alias não deve apagar conteúdo ainda associado a outra origem.
- Arquivo alterado: criar nova versão em preparação, extrair e gerar todos os embeddings antes de substituir a versão ativa. Usar IDs de chunk determinísticos por documento/conteúdo, versão de processamento e posição.
- Manter catálogo SQLite com estados `pending`, `active` e `failed`, hashes, versões, origens e erros. ChromaDB e catálogo não constituem uma transação única: implementar recuperação explícita.
- Gravar a nova versão no ChromaDB, confirmar completude e só então ativá-la em uma transação do catálogo. Consultas devem aceitar apenas versões ativas, filtrando candidatas e buscando mais resultados quando necessário.
- Após ativação, remover chunks obsoletos sem afetar outras origens. Falha na limpeza deve ser recuperável no próximo início.
- Se leitura, extração, embeddings ou gravação falharem, preservar a versão ativa anterior. Identificar versões incompletas no próximo início e limpar ou retomar de maneira idempotente.
- Processar diretórios por arquivo e apresentar resumo de adicionados, atualizados, ignorados e falhos. Uma falha individual não deve invalidar os demais arquivos.
- Exclusão por `document_id` ou identificador de origem, nunca apenas por nome. Reset exige confirmação explícita na interface.
- Após excluir/atualizar documentos, invalidar referências de memória a evidências antigas e exigir nova recuperação antes de responder sobre esses conteúdos.
````
<!-- PLAN_EXCERPT_END -->

Trecho literal da seção **### 3.5. ChromaDB e cosseno**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.5. ChromaDB e cosseno

- Utilizar cliente persistente e configurar explicitamente a coleção para cosseno pela API da versão fixada do ChromaDB.
- Fornecer os embeddings BGE-M3 calculados pela aplicação tanto na ingestão quanto nas consultas, evitando uma função de embeddings padrão diferente.
- Guardar texto, vetor e metadados: documento, origem, página/linhas, posição, versão e configuração de processamento.
- Exibir distância cosseno ou similaridade `1 - distância` com rótulo correto. Similaridade não é probabilidade nem confiança da resposta.
- Eventual limiar de relevância deve ser calibrado com documentos de teste; não assumir um número universal.
- Operações: adicionar/atualizar, buscar versões ativas, listar fontes, excluir origem/documento e resetar a coleção.
````
<!-- PLAN_EXCERPT_END -->

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/rag/ingestion.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/catalog.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/vectorstore.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_document_deletion.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Expor remoção por identificador de origem/documento, desativando referência no catálogo antes da limpeza de vetores não compartilhados.
2. Manter conteúdo compartilhado enquanto houver alias ativo. Registrar falhas de limpeza para a reconciliação existente.
3. Implementar reset com autorização explícita no contrato de chamada; a confirmação visual será feita em T15. Recusa não muda dados.
4. Incrementar geração e emitir evento de invalidação; T12/T14 consumirão esse contrato sem exigir mudanças futuras nesta operação.

## 5. Testes no mesmo commit

- Exclusão de homônimo correto, alias compartilhado e última origem com bancos reais.
- Exclusão/reset sem confirmação não alteram dados; repetir remoção é seguro.
- Erro de limpeza e reinício não tornam conteúdo excluído consultável.
- Evento/geração invalidam a identidade antiga; sem alegar que memória ainda inexistente foi testada.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_document_deletion.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Fora de escopo: apagar arquivos originais do usuário e confirmação de interface.
- Preservar origens não selecionadas e a infraestrutura de recuperação de T09.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Fontes excluídas não aparecem na busca ativa.
- [ ] Reset exige confirmação e falhas de limpeza são recuperáveis.
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
