# T09 - Atualização segura e recuperação de ingestão

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [T08](t08-ingestao-idempotente.md)
> **Commit único:** `feat(ingestion): add safe version updates and crash recovery`

## 1. Por que

Substituir conteúdo sem perder a versão válida e sobreviver a interrupções entre dois armazenamentos independentes.

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

Trecho literal da seção **### 4.2. Testes de instalação e ponta a ponta**:

<!-- PLAN_EXCERPT_START -->
````text
### 4.2. Testes de instalação e ponta a ponta

1. Instalação limpa no Windows com GPU NVIDIA pelo caminho padrão, usando pacotes pré-compilados e sem compilador C++.
2. Instalação limpa no Windows sem CUDA/GPU pelo perfil CPU, também sem compilador C++.
3. Confirmar backend efetivo: CUDA de PyTorch e offload da LLM separadamente; diagnósticos claros quando indisponíveis.
4. Baixar/carregar `Phi-4-mini-instruct.Q8_0.gguf` e BGE-M3; reiniciar e reutilizar cache. Confirmar uso offline após preparação.
5. Importar documentos, consultar, reiniciar e consultar novamente com índice persistido.
6. Reimportar sem duplicar, atualizar conteúdo, remover origem e verificar que chunks obsoletos não aparecem na busca ou em respostas novas.
7. Interromper ingestão e confirmar recuperação, preservando a versão ativa anterior.
8. Usar conjunto fixo de perguntas com respostas conhecidas, perguntas sem resposta, continuações, ambiguidades e mudanças de assunto. Medir correção, fundamentação, citações e recusas; não prometer ausência absoluta de alucinações.
9. Testar PDFs sem texto, caminhos inválidos, falta de disco, erros de rede e falta de memória com mensagens acionáveis.
````
<!-- PLAN_EXCERPT_END -->

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/rag/ingestion.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/catalog.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/vectorstore.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_ingestion_updates.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_recovery.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Gerar nova versão completa em preparação antes de trocar o ponteiro ativo no catálogo; não alterar a versão compartilhada por outros aliases.
2. Após ativação, limpar vetores órfãos de versões antigas, preservando conteúdos referenciados por outras origens.
3. Implementar reconciliação idempotente ao iniciar, incluindo falhas antes/depois da ativação e durante limpeza. Especificar limpeza/reindexação de preparação interrompida como política inicial.
4. Processar pastas por arquivo com relatório added/updated/skipped/failed e isolamento de erros. Emitir mudança de geração para invalidar referências de memória em T12/T14.

## 5. Testes no mesmo commit

- Integração real SQLite+Chroma: atualização troca texto ativo e não mantém chunks antigos na busca.
- Falhas em extração, encode, staging, ativação e limpeza preservam versão correta.
- Reinício entre cada etapa e recuperação repetida não duplicam dados nem apagam versões válidas.
- Atualizar uma origem com alias não altera conteúdo da outra; falha de um arquivo não aborta a pasta.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_ingestion_updates.py tests/test_recovery.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Não há atomicidade global SQLite+Chroma; a garantia vem do protocolo de ativação e reconciliação.
- Fora de escopo: ingestão concorrente entre múltiplos processos e serviço remoto. Documentar suporte a um escritor local.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Atualização preserva a versão anterior até ativar a nova.
- [ ] Recuperação repetida mantém catálogo e índice consistentes.
- [ ] Código e configuração desta tarefa implementados e executáveis.
- [ ] Testes deste comportamento incluídos e aprovados no mesmo commit.
- [ ] Documentação diretamente afetada atualizada.
- [ ] Excertos e links validados; dependências anteriores concluídas.
- [ ] Gates externos têm evidência ou bloqueio explícito, sem dados fabricados.
- [ ] Um commit criado com a mensagem prevista, quando houver repositório Git.

---

## Progresso final da implementação

| Item | Status |
|---|---|
| Implementação | Não iniciada |
| Testes | Não iniciados |
| Documentação de uso | Não iniciada |
| Validação real/gates | Pendente |
| Commit | Pendente |

**Progresso geral:** 0%
**Critérios concluídos:** 0/8
**Evidências de execução:** nenhuma; esta entrega decompõe o plano e não implementa a aplicação.
