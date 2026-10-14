# T17 - Métricas por etapa e avaliação reproduzível

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Código implementado; validação externa registrada em docs/validation.md
> **Progresso:** código entregue; critérios externos conforme relatório
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** Codex
> **Dependências:** [T16](t16-ui-chat.md)
> **Commit único:** `feat(metrics): add RAG timing instrumentation and benchmark runner`

## 1. Por que

Adicionar instrumentação de produção e uma avaliação rastreável para publicar requisitos baseados em medições, com testes neste mesmo commit.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

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

Trecho literal da seção **### 4.3. Desempenho e publicação de requisitos**:

<!-- PLAN_EXCERPT_START -->
````text
### 4.3. Desempenho e publicação de requisitos

- Medir em perfis CUDA e CPU: RAM/VRAM máxima, carregamento dos modelos, tempo de indexação por tamanho de corpus, tempo até primeiro token e tokens por segundo.
- Separar latência de resolução contextual, embeddings, busca, processamento do prompt, geração e resumo. Distinguir início frio de uso com modelos carregados.
- Testar residentes versus carregamento alternado, tamanhos de lote e offload parcial.
- Registrar hardware, versões, contexto, tamanho do corpus e configurações dos benchmarks.
- Publicar requisitos mínimos e recomendados, com tempos observados. Definir metas numéricas a partir da medição, antes do lançamento, sem tratar tamanho do GGUF como consumo total de memória.
````
<!-- PLAN_EXCERPT_END -->

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/metrics.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/pipeline.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/models/lifecycle.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/ingestion.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `scripts/benchmark.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_metrics.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_benchmark.py` | Criar ou modificar conforme os predecessores |
| Documentação | `docs/benchmarks.md` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Instrumentar carregamento, resumo, resolução, embeddings, busca, prompt e geração; registrar TTFT, tokens/s, RAM/VRAM e indexação.
2. Separar frio/quente e medir residente/alternado, batch e offload parcial nos perfis CPU/CUDA; documentar definição de TTFT percebido pelo usuário.
3. Implementar runner com manifestos de corpus/configuração/hardware/versões e exportação JSON. Não registrar conteúdos privados nos logs por padrão.
4. Usar fixtures sintéticas identificadas para regressão e conjunto real autorizado com respostas/fontes esperadas para qualidade. Registrar correção, fundamentação, citações, recusas e falhas contextuais.
5. Publicar apenas resultados observados, requisitos mínimos/recomendados e metas escolhidas após medição. Campo indisponível, especialmente VRAM, é null/indisponível, nunca zero fabricado.

## 5. Testes no mesmo commit

- Relógio/coletores simulados verificam fases, TTFT, unidades, divisão por zero e falha de coleta.
- Runner gera schema válido com versões/configuração e distingue indisponível de zero.
- Instrumentação não altera a resposta nem expõe documentos nos logs padrão.
- Execuções reais do corpus nos dois perfis, com comparação de modos e relatório; testes anteriores já pertencem aos respectivos commits e não são adiados para esta tarefa.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_metrics.py tests/test_benchmark.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Gate externo: disponibilidade de NVIDIA, máquina CPU e corpus autorizado; não fabricar resultados nem aprovar requisitos mínimos sem medições.
- Fora de escopo: trocar quantização/modelo e implementar otimizações não justificadas pelos resultados.
- Esta não é tarefa somente de testes: acrescenta instrumentação e runner executáveis com seus próprios testes.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Métricas por fase e relatórios são reproduzíveis.
- [ ] Requisitos publicados têm evidência real e pendências permanecem explícitas.
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
