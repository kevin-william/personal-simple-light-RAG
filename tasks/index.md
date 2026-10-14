# Índice de tarefas atômicas

Plano: [implementation_plan.md](../implementation_plan.md)

**Skill aplicada:** `decompose-plan-atomic-tasks`, lida no caminho indicado pelo usuário. Decomposição da versão integral do plano, preservando suas decisões; não inicia implementação nem cria commits.

## Regra de atomicidade e convenções

Cada tarefa corresponde a exatamente um commit, contendo código de produção, testes automatizados do comportamento introduzido e documentação de uso afetada. Não há tarefa futura somente de testes para corrigir cobertura adiada. T17 acrescenta instrumentação e runner de produção, além de seus testes.

Na inspeção, a pasta continha apenas o plano. Não havia Git, AGENTS.md, README, código nem convenções de testes. Todos os caminhos de implementação/testes são propostos; as mensagens usam Conventional Commits como escolha deste plano. Inicializar Git não faz parte desta entrega. Reavaliar instruções existentes ao começar cada tarefa.

## Ordem e commits

| Ordem | Tarefa | Dependências | Commit único | Status |
|---|---|---|---|---|
| 1 | [T01 — Configuração validada e entrada executável](t01-configuracao.md) | — | `feat(config): add validated settings and application entry point` | Código entregue; validação local aprovada |
| 2 | [T02 — Preparação reproduzível CUDA e CPU com diagnóstico](t02-instalacao-perfis.md) | T01 | `feat(setup): add CUDA and CPU installation profiles` | Código entregue; validação local aprovada |
| 3 | [T03 — Downloads verificáveis, cache e preparação offline](t03-download-modelos.md) | T01, T02 | `feat(models): add verified model downloads and offline cache` | Código entregue; validação local aprovada |
| 4 | [T04 — Extração e divisão com rastreabilidade de fontes](t04-extracao-chunks.md) | T01, T02 | `feat(ingestion): add document extraction and bounded chunks` | Código entregue; validação local aprovada |
| 5 | [T05 — BGE-M3 normalizado para documentos e perguntas](t05-embeddings.md) | T02, T03, T04 | `feat(embeddings): add consistent normalized BGE-M3 encoding` | Código entregue; validação local aprovada |
| 6 | [T06 — Índice persistente com busca por cosseno](t06-chroma-cosseno.md) | T01, T05 | `feat(search): add persistent cosine vector store` | Código entregue; validação local aprovada |
| 7 | [T07 — Catálogo transacional de origens, conteúdo e versões](t07-catalogo.md) | T01 | `feat(catalog): add source identities and version lifecycle` | Código entregue; validação local aprovada |
| 8 | [T08 — Importação inicial e reimportação idempotente](t08-ingestao-idempotente.md) | T04, T05, T06, T07 | `feat(ingestion): add idempotent document imports and aliases` | Código entregue; validação local aprovada |
| 9 | [T09 — Atualização segura e recuperação de ingestão](t09-atualizacao-recuperacao.md) | T08 | `feat(ingestion): add safe version updates and crash recovery` | Código entregue; validação local aprovada |
| 10 | [T10 — Exclusão por identidade e reset recuperável](t10-exclusao.md) | T09 | `feat(documents): add identity-based deletion and index reset` | Código entregue; validação local aprovada |
| 11 | [T11 — Inferência Phi com template oficial e política de memória](t11-runtime-phi.md) | T02, T03, T05 | `feat(llm): add Phi inference and model memory lifecycle` | Código entregue; validação local aprovada |
| 12 | [T12 — Última mensagem e resumo incremental pela LLM](t12-memoria-enxuta.md) | T10, T11 | `feat(memory): add compact LLM-generated conversation state` | Código entregue; validação local aprovada |
| 13 | [T13 — Perguntas independentes e contexto mínimo pela LLM](t13-resolucao-contextual.md) | T12 | `feat(context): add LLM-based follow-up resolution` | Código entregue; validação local aprovada |
| 14 | [T14 — Resposta RAG com orçamento de tokens e citações](t14-pipeline-rag.md) | T06, T09, T10, T11, T13 | `feat(rag): add grounded response pipeline with token budgets` | Código entregue; validação local aprovada |
| 15 | [T15 — Menu e interface de gerenciamento de documentos](t15-ui-documentos.md) | T02, T03, T09, T10 | `feat(cli): add document management menu and diagnostics` | Código entregue; validação local aprovada |
| 16 | [T16 — Chat interativo com streaming, memória e fontes](t16-ui-chat.md) | T14, T15 | `feat(chat): add interactive streaming RAG conversation` | Código entregue; validação local aprovada |
| 17 | [T17 — Métricas por etapa e avaliação reproduzível](t17-metricas-avaliacao.md) | T16 | `feat(metrics): add RAG timing instrumentation and benchmark runner` | Código entregue; validação local aprovada |

## Cadeia de dependências

Implementar na ordem numérica para uma sequência linear válida. As arestas abaixo são pré-requisitos reais; a ordem não exige delegação ou execução paralela.

```text
T01: raiz
T02: T01
T03: T01, T02
T04: T01, T02
T05: T02, T03, T04
T06: T01, T05
T07: T01
T08: T04, T05, T06, T07
T09: T08
T10: T09
T11: T02, T03, T05
T12: T10, T11
T13: T12
T14: T06, T09, T10, T11, T13
T15: T02, T03, T09, T10
T16: T14, T15
T17: T16
```

T08 entrega ingestão inicial útil e trata falhas iniciais; recusa arquivos alterados até T09, que acrescenta atualização segura e recuperação completa. T15 entrega gerenciamento de documentos antes de habilitar chat em T16. Reverter uma tarefa não quebra seus predecessores; consumidores posteriores precisam ser revertidos primeiro.

## Cobertura e fronteiras de responsabilidade

| Plano | Tarefas responsáveis | Fronteira |
|---|---|---|
| 1. Arquitetura / 2. Decisões | T01–T17 | Estrutura distribuída pelas funcionalidades; decisões preservadas nos trechos literais. |
| 3.1 Instalação, hardware e memória | T02 / T11 / T17 | Preparação / ciclo de modelos / medições reais. |
| 3.2 Configuração e downloads | T01 / T03 | Configuração e caminhos / cache e integridade. |
| 3.3 Extração, divisão e embeddings | T04 / T05 | Extração e caracteres / tokenização BGE e vetores. |
| 3.4 Duplicação, atualização e falhas | T07 / T08 / T09 / T10 / T12 / T15 | Catálogo / importação / atualização e recovery / exclusão / invalidação da memória / interface. |
| 3.5 ChromaDB e cosseno | T06 / T08 / T10 / T14 | Índice / versões ativas / exclusão / consumo na resposta. |
| 3.6 Memória e resolução dinâmica | T12 / T13 / T14 | Estado / resolução / orquestração. |
| 3.7 Template, orçamento e resposta | T11 / T14 / T16 | Runtime e tokens / orçamento e citações / apresentação. |
| 3.8 Interfaces | T01 / T02 / T15 / T16 | Entrada mínima / preparação / documentos / chat. |
| 4.1 Testes automatizados | T01–T17 | Cada comportamento é testado na tarefa que o introduz; não há commit posterior só de testes. |
| 4.2 Instalação e ponta a ponta | T02 / T03 / T05 / T09 / T10 / T11 / T14 / T16 / T17 | Gates reais distribuídos; avaliação final e registros em T17. |
| 4.3 Desempenho e requisitos | T17 | Instrumentação, runner e medições CPU/CUDA. |
| 5. Referências técnicas | T02 / T03 / T05 / T06 / T11 | Consultar documentação primária ao fixar artefatos e APIs; links são referências, não requisitos adicionais. |

Trechos de uma mesma seção podem aparecer em várias tarefas para preservar contexto literal. A coluna de fronteira determina quem implementa cada mudança; a repetição do trecho não duplica a responsabilidade.

## Gates externos

- T02: existência de wheels compatíveis e instalação limpa Windows CPU/CUDA sem compilador; matriz de versões e driver realmente validada.
- T03: revisões imutáveis reais, downloads/licenças e espaço em disco; não inventar hashes.
- T05/T11: modelos reais e hardware CPU/NVIDIA para validar embeddings, template, offload e ciclo de memória.
- T14/T16/T17: corpus autorizado com respostas/fontes esperadas, avaliação de fundamentação e fluxos reais nos dois perfis.
- T17: RAM/VRAM, latências e requisitos publicados só depois de medições; campos indisponíveis não viram zero.
- Testes simulados não aprovam gates de instalação, qualidade ou hardware. Registrar evidência, pendência ou bloqueio. Não iniciar funcionalidades dependentes sem resolver o gate necessário.
- Fora de escopo global: OCR, formatos adicionais, busca híbrida/reranker, outras GPUs, serviço remoto/multiusuário, múltiplos escritores e troca de quantização/modelo.

## Validação da documentação

O verificador literal foi copiado da skill sem alterações para permitir repetir a checagem localmente:

```powershell
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Links relativos, dependências, 17 arquivos de tarefa, mensagens únicas, ordem e oito critérios por tarefa também devem ser conferidos. Links da raiz do índice são relativos a `tasks/`; arquivos citados em tabelas são propostas, não links para arquivos já existentes.

## Progresso agregado

- **Tarefas com código entregue:** 17/17 — 100%.
- **Critérios registrados:** 134/136; T02/T17 preservam um critério externo pendente.
- **Validação local:** 57 testes automatizados; modelos reais CPU/CUDA; benchmarks no README.
- **Gates externos:** Windows limpo, outros hardwares/corpus e requisitos mínimos certificados, conforme [relatório](../docs/validation.md).
- **Commits:** um por tarefa, mais baseline de documentação e correções de validação real.
- **Git:** repositório local inicializado; nada publicado ou enviado a remoto.
- **Decomposição:** relatório original [decomposition_validation.json](../decomposition_validation.json) descreve a etapa anterior, não o estado da implementação.

Os caminhos antes propostos agora existem no repositório. A validação atual
está em [docs/validation.md](../docs/validation.md). Ignorados intencionalmente:
`models/`, `data/`, `work/`, `.venv*`, `.env` e caches. Documentação de tarefas,
testes, código e relatórios observados são versionados.
