# T08 - Importação inicial e reimportação idempotente

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Implementada; validação local aprovada
> **Progresso:** 100% do código; validação externa conforme relatório
> **Início:** 14/10/2026 | **Fim previsto:** - | **Fim real do código:** 14/10/2026
> **Responsável:** Codex
> **Dependências:** [T04](t04-extracao-chunks.md), [T05](t05-embeddings.md), [T06](t06-chroma-cosseno.md), [T07](t07-catalogo.md)
> **Commit único:** `feat(ingestion): add idempotent document imports and aliases`

## 1. Por que

Permitir alimentar uma base utilizável sem duplicar o mesmo arquivo ou recalcular conteúdo já indexado.

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
| Teste proposto | `tests/test_ingestion.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Orquestrar hash, extração, chunks, embeddings e gravação por arquivo, com IDs determinísticos e ativação apenas após conferir completude.
2. Reimportação inalterada é no-op; outra origem de conteúdo idêntico associa alias sem duplicar vetores. Homônimos diferentes são indexados independentemente.
3. Garantir rollback/limpeza de falha na importação inicial e reconciliação mínima de pending sem origem ativa após reinício; nunca expor versões incompletas.
4. Oferecer consulta de versões ativas com filtragem e expansão de candidatos até obter k ou esgotar o índice.
5. Até T09, detectar arquivo modificado e recusar atualização com mensagem explícita, preservando conteúdo ativo. Documentar essa fronteira temporária; não deixar código de atualização quebrado.

## 5. Testes no mesmo commit

- Catálogo SQLite e Chroma reais, encoder substituído por vetores determinísticos: primeira importação, no-op e alias sem duplicação.
- Falha em encode/gravação e interrupção inicial não deixam chunks consultáveis; reexecução é idempotente.
- Busca repõe candidatos inativos até k quando há ativos suficientes.
- Arquivo alterado é detectado e mantém versão antiga nesta etapa.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_ingestion.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Fora de escopo: substituição de versão já ativa, exclusão e UI.
- Fixtures e encoder simulado validam orquestração; avaliação semântica depende de T14/T17.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [x] Reimportações e aliases não geram vetores duplicados.
- [x] Consultas retornam somente conteúdo ativo completo.
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
