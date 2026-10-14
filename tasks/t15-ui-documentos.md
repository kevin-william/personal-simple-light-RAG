# T15 - Menu e interface de gerenciamento de documentos

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Implementada; validação local aprovada
> **Progresso:** 100% do código; validação externa conforme relatório
> **Início:** 14/10/2026 | **Fim previsto:** - | **Fim real do código:** 14/10/2026
> **Responsável:** Codex
> **Dependências:** [T02](t02-instalacao-perfis.md), [T03](t03-download-modelos.md), [T09](t09-atualizacao-recuperacao.md), [T10](t10-exclusao.md)
> **Commit único:** `feat(cli): add document management menu and diagnostics`

## 1. Por que

Entregar uma interface completa para alimentar e manter o RAG sem exigir edição manual do índice.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

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

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/ui/__init__.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/ui/console.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/ui/menu.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/ui/ingestion.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `main.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_document_ui.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Implementar menu Rich/prompt_toolkit com ingestão, listagem, exclusão/reset e status; opção chat só será habilitada em T16.
2. Aceitar arquivo/pasta e caminhos absolutos/relativos, mostrar resumo, progresso e resultados por arquivo.
3. Selecionar exclusão por identidade/origem e pedir confirmação para reset. Cancelamento não altera a base.
4. Status mostra perfil configurado, backend verificado quando disponível, revisões e índice; listagem/menu não carregam modelos.
5. Documentar preparação CUDA padrão, alternativa CPU e operações com exemplos executáveis.

## 5. Testes no mesmo commit

- Testes de entrada/saída simulada: menus, caminhos com espaços/acentos, cancelamento e confirmações.
- Integração com catálogo/índice temporários testa ingestão, listagem e remoção pela UI.
- Relatório apresenta added/updated/skipped/failed e não esconde erros individuais.
- Menu/status/listagem não inicializam LLM/embedder.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_document_ui.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Fora de escopo: chat em streaming, interface web e OCR.
- Não mostrar funcionalidades indisponíveis como operacionais.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [x] Usuário gerencia arquivos pelo menu sem editar dados internos.
- [x] Reset é confirmado e status descreve execução efetiva com precisão.
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
