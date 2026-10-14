# T02 - Preparação reproduzível CUDA e CPU com diagnóstico

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Implementada; gate externo pendente
> **Progresso:** 100% do código; validação externa conforme relatório
> **Início:** 14/10/2026 | **Fim previsto:** - | **Fim real do código:** 14/10/2026
> **Responsável:** Codex
> **Dependências:** [T01](t01-configuracao.md)
> **Commit único:** `feat(setup): add CUDA and CPU installation profiles`

## 1. Por que

Permitir uma instalação sem compilador C++ e explicitar qual backend foi instalado, mantendo NVIDIA como caminho principal.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

Trecho literal da seção **### 3.1. Instalação, hardware e memória**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.1. Instalação, hardware e memória

- Dependências comuns: `sentence-transformers`, `chromadb`, `pypdf`, `rich`, `prompt_toolkit`, `huggingface_hub` e `pydantic-settings`; `torch` e `llama-cpp-python` instalados conforme o perfil.
- Oferecer preparação CUDA como padrão e preparação CPU explícita. Fixar e documentar a combinação validada de Python, biblioteca, wheel, PyTorch, CUDA e driver.
- Verificar suporte CUDA de PyTorch e do backend llama.cpp separadamente: detectar uma GPU não prova que ambas as bibliotecas têm aceleração habilitada.
- Em CUDA, usar `n_gpu_layers=-1` como padrão. Permitir offload parcial configurável quando necessário.
- Em CPU, usar `n_gpu_layers=0` e embeddings em CPU. Se CUDA estiver indisponível no perfil padrão, apresentar diagnóstico e instrução para selecionar CPU, sem fingir que houve aceleração.
- Carregar a LLM apenas quando necessária e reutilizá-la durante o chat. O menu e a listagem de documentos não precisam carregar os modelos.
- Indexação em lotes configuráveis. No chat, definir política para manter ambos os modelos carregados quando houver memória suficiente ou executá-los alternadamente em modo econômico.
- Em falta de memória, reduzir lotes ou recomendar offload parcial/perfil CPU conforme o caso. Não trocar silenciosamente o modelo, a quantização ou o backend.
- Medir RAM e VRAM reais antes de publicar requisitos mínimos. GPU NVIDIA é recomendada, mas a execução CPU deve passar pelos testes funcionais.
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
| Código/configuração propostos | `scripts/setup.ps1` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/models/__init__.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/models/hardware.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `requirements.txt` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `pyproject.toml` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `main.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_setup_profiles.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Selecionar e fixar versões compatíveis de Python, wheels de llama-cpp-python, torch e demais dependências após verificar os artefatos oficiais. Documentar a matriz efetivamente validada.
2. Implementar preparação padrão CUDA e parâmetro `-Profile cpu`, com ambiente virtual local e resolução binária sem fallback silencioso para compilação.
3. Expor diagnóstico de PyTorch e do suporte compilado de llama.cpp separadamente. Distinguir suporte compilado, dispositivo disponível e offload efetivo, que só será confirmado em T11.
4. Mensagens de CUDA indisponível orientam escolha explícita de CPU. Atualizar status sem downloads de modelos e documentar driver e versões requeridos.

## 5. Testes no mesmo commit

- Seleção padrão CUDA e seleção explícita CPU geram comandos corretos e nenhuma compilação automática.
- Falhas de dependência, wheel ausente e driver indisponível têm diagnóstico; não alterar o perfil silenciosamente.
- PyTorch com CUDA e llama.cpp sem CUDA, e o inverso, são detectados separadamente.
- Teste real de instalação mínima dos dois perfis em Windows limpo; mocks de sondagens são apenas testes de ramificação.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_setup_profiles.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Gate externo: Windows limpo, rede e artefatos binários compatíveis; validar NVIDIA/driver em hardware real para aprovar o perfil CUDA.
- Não afirmar compatibilidade ou aceleração real com base apenas nos testes simulados.
- Fora de escopo: compilar C++, suportar outras GPUs e carregar os modelos completos.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [x] Instalação dos dois perfis é documentada e não exige compilador.
- [ ] Matriz de versões é fixada e registros dos gates reais são anexados.
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
**Critérios concluídos:** 7/8
**Evidências de execução:** pytest focado, compileall e verificador literal aprovados neste commit. Validações de hardware/modelos em [docs/validation.md](../docs/validation.md); skips não são aprovação.
