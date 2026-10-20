# Diagnóstico e plano de correção de desempenho

> Plano de execução atualizado: [optimization_flow_plan.md](optimization_flow_plan.md), de 17/10/2026. As propostas abaixo são históricas; o fluxo aprovado passa a usar consultas independentes, sem resolução contextual ou resumo, e perfil misto como padrão.

Data: 15/10/2026. Escopo: inspeção do código e medições locais; nenhuma correção de runtime aplicada.

## Conclusão

A diferença percebida reúne dois problemas identificados: a interface calcula incorretamente a taxa de tokens e o fluxo completo apresenta custos reais de inferência e troca de modelos. O usuário corrigiu a identificação do modelo no Ollama: ambos usam Phi-4-mini-instruct Q8; diferença de família de modelo foi descartada como explicação.

- Ollama confirmado no servidor local: `hf.co/unsloth/Phi-4-mini-instruct-GGUF:Q8_0`. O SHA256 do blob é idêntico ao manifesto do GGUF do projeto: `26188c6050d525376a88b04514c236c5e28a36730f1e936f2a00314212b7ba42`.
- Projeto: `unsloth/Phi-4-mini-instruct-GGUF`, arquivo `Phi-4-mini-instruct.Q8_0.gguf`.
- Hardware verificado: RTX 3050 Laptop, 6 GiB de VRAM. Ambiente principal: CUDA disponível, PyTorch 2.6.0+cu124 e llama-cpp-python 0.3.36.
- O Phi sozinho atingiu aproximadamente 35 tokens/s neste computador, com 33/33 camadas na GPU.
- No fluxo RAG com as configurações padrão, o decode caiu para aproximadamente 6 tokens/s, e a política de memória descarregou e recarregou os modelos em todas as perguntas medidas.
- Em um experimento sem alterar arquivos de configuração, Phi em CUDA e BGE-M3 em CPU recuperaram aproximadamente 34 tokens/s na continuação; o turno caiu de 33,18 s para 6,18 s.

O mesmo GGUF do Phi, com um prompt documental de aproximadamente mil tokens e sem carregar BGE-M3, também atingiu cerca de 33 tokens/s. Portanto, o tamanho do prompt testado não explica sozinho a queda observada no fluxo completo.

## Estrutura e caminho crítico

```text
main.py / src/cli.py
  -> Application: monta modelos, armazenamento e ciclo de vida
  -> UI: chat.py (Rich) ou tui.py (Textual)
  -> Pipeline.stream
       1. QueryResolver -> LLM estruturada: interpretar a pergunta
       2. Embedder -> BGE-M3: vetor da consulta
       3. Ingestor -> catálogo SQLite + VectorStore/Chroma: buscar evidências
       4. Pipeline.budget -> contar tokens e selecionar trechos
       5. LLM.stream -> gerar resposta visível
       6. ConversationMemory -> LLM estruturada: selecionar resumo
       7. Metrics.finish -> fechar métricas e coletar VRAM
```

Uma pergunta com resposta documental normalmente usa três chamadas sequenciais à LLM. Resolução e resumo aceitam uma tentativa adicional cada: o total pode chegar a cinco chamadas. ModelLifecycle pode inserir descarregamentos e carregamentos entre essas etapas. A interface só libera a próxima pergunta depois de consumir todo o fluxo, inclusive o resumo.

## Evidências medidas nesta auditoria

As execuções reais usaram os modelos existentes e apenas o README como corpus. A base original `data/` foi preservada; a base de teste está em `work/performance-audit/rag-default/`.

| Cenário | Decode nativo | Espera pelo primeiro texto | Tempo observado |
|---|---:|---:|---:|
| Phi direto, prompt curto, primeira execução | 34,95 tokens/s | 9,59 s | 13,27 s para 128 tokens retokenizados |
| Phi direto, prompt curto, segunda execução | 35,36 tokens/s | 0,04 s | 3,67 s para 128 tokens retokenizados |
| Phi direto, prompt documental, primeira execução após carregar | 33,07 tokens/s | não coletada | 1,64 s de geração, fora o carregamento |
| RAG padrão, primeira pergunta | 6,05 tokens/s | 36,67 s | 42,86 s |
| RAG padrão, continuação | 6,47 tokens/s | 22,11 s | 33,18 s |
| RAG com Phi CUDA e BGE-M3 CPU, primeira pergunta | 31,81 tokens/s | 23,36 s | 25,24 s |
| RAG com Phi CUDA e BGE-M3 CPU, continuação | 34,07 tokens/s | 3,55 s | 6,18 s |

Na continuação do RAG padrão:

- Resolução: 8,94 s.
- Embedding da consulta: 4,52 s, dos quais 4,50 s foram carregamento do BGE-M3.
- Busca: 0,0033 s.
- Preparação do prompt: 4,24 s, incluindo 4,22 s de carregamento da LLM.
- Geração visível, incluindo processamento do prompt: 12,01 s.
- Resumo após a resposta: 3,39 s.

Essas fases são inclusivas: carregamentos também aparecem dentro das fases que os provocam. Não somar indiscriminadamente os contadores.

Relatórios locais:

- `work/performance-audit/direct-llm.json`.
- `work/performance-audit/direct-rag-prompt.json`.
- `work/performance-audit/rag-default.json`, incluindo eventos reais de carga e descarga.
- `work/performance-audit/rag-mixed-device.json`, com os dispositivos separados apenas por parâmetros na execução de teste.

No perfil misto, a continuação gastou 0,125 s no embedding, 0,0042 s na busca, 0,017 s na preparação do prompt, 2,82 s na resolução, 2,04 s na geração e 1,11 s no resumo. Não houve recarregamento nessa continuação. A primeira pergunta ainda expulsou a LLM uma vez ao carregar embeddings em CPU, evidenciando que a política de RAM/VRAM também precisa ser corrigida. A inicialização dos cenários difere: o teste padrão indexou o README antes das perguntas, e o misto reutilizou essa base isolada. A comparação mais útil é a continuação aquecida; os tempos frios não constituem um ensaio pareado.

As amostras diretas têm condições diferentes de aquecimento e reutilização de prefixo. Servem para isolar a capacidade de decode e os custos do fluxo, não para publicar uma comparação controlada entre Ollama e llama.cpp. Duas perguntas não constituem avaliação estatística.

## Verificação adicional do ritmo de streaming

O usuário esclareceu que a lentidão é visível tanto no chat do menu quanto na TUI. Esse relato deve ser tratado como um problema de entrega de texto, independentemente do erro do indicador. Os testes iniciais desta auditoria não abriram as interfaces nem executaram Ollama; a comparação direta abaixo foi feita posteriormente.

Foram executadas duas gerações de 128 tokens em cada motor, com o mesmo prompt serializado, o mesmo GGUF confirmado por hash, contexto 4096, temperatura 0,1 e seed 42. O Ollama foi descarregado antes de executar o projeto, e `ollama ps` confirmou que não havia modelo residente disputando a GPU.

| Motor isolado | Decode nativo, duas execuções | Intervalo mediano entre fragmentos | Maior intervalo |
|---|---:|---:|---:|
| Ollama | 30,43 e 30,39 tokens/s | 32,9 ms | 37,2 ms |
| LLM do projeto, sem RAG | 35,13 e 34,94 tokens/s | 28,0–28,1 ms | 60,2 ms na primeira execução; 31,7 ms na segunda |

Demais parâmetros internos dos motores não foram igualados; o ensaio verifica capacidade e ritmo de streaming, não estabelece equivalência completa de configuração. Relatórios: `work/performance-audit/streaming-ollama.json` e `streaming-direct.json`.

Uma pergunta documental mais longa, sobre memória, resolução contextual e citações, gerou 331 tokens no pipeline completo sem UI. Nas duas execuções:

- Decode nativo: 6,00 e 5,71 tokens/s.
- Intervalo do primeiro ao último fragmento: 55,07 e 57,78 s, excluindo espera inicial e resumo.
- Intervalo mediano entre fragmentos: 162 e 174 ms; máximos de 194 e 201 ms.
- Espera inicial: 32,28 e 30,36 s; duração total: 92,31 e 93,44 s.
- Tempo agregado de espera pelo consumidor do gerador: aproximadamente 0,2 ms. Essa perda ocorre mesmo sem desenho da interface.

O problema de desempenho real foi reproduzido; o ritmo específico de pouco mais de 1 token/s relatado pelo usuário ainda não foi reproduzido nesse ensaio. Não atribuir a percepção de lentidão apenas ao indicador. Relatório: `work/performance-audit/streaming-plain.json`.

A mesma pergunta e os mesmos 331 tokens de resposta foram medidos nos componentes reais dos dois chats:

| Caminho | Decode nativo | Primeiro ao último fragmento | Espera acumulada pelo consumidor |
|---|---:|---:|---:|
| Pipeline sem UI, duas execuções | 6,00 e 5,71 tokens/s | 55,07 e 57,78 s | aproximadamente 0,2 ms por execução |
| Chat do menu, Rich Live + Markdown | 6,01 tokens/s | 55,04 s | 0,15 s |
| TUI Textual, workers e widgets reais | 6,33 tokens/s | 53,32 s | 1,16 s |

Na TUI, o intervalo do primeiro ao último update do widget de texto foi também 53,32 s, com maior espera individual pelo consumidor de 7,8 ms. O ritmo de entrega estimado a partir dos 330 tokens seguintes ao primeiro é cerca de 6,19 tokens/s. Assim, neste corpus e nesta sessão curta, o maior atraso já existe antes das interfaces, e o custo adicional de atualização da TUI não explica uma queda para 1 token/s.

Limites: o chat Rich escreveu em buffer de memória, e a TUI usou o driver headless do Textual a 140×50. O desenho físico na janela de terminal do usuário não foi medido. O histórico longo e o corpus/pergunta exatos usados pelo usuário não foram reproduzidos. A TUI precisou executar fora da restrição de sockets para o loop de eventos do Python no Windows; o bloqueio inicial ocorreu no ambiente de teste antes de abrir a interface, não demonstrou um defeito da aplicação e não integra os tempos da tabela.

Relatórios adicionais: `work/performance-audit/streaming-rich.json` e `streaming-tui.json`. O roteiro reproduzível está em `work/performance-audit/streaming_probe.py`. Nenhum arquivo de configuração ou código de produção foi alterado por esses ensaios.

## Gargalos e problemas identificados

### 1. Indicador de tokens/s incorreto — confirmado

Em `src/ui/tui.py:459–489`, `token_count` conta eventos de streaming e `elapsed` inclui a consulta inteira. Um evento pode conter vários tokens, parte de um token textual ou até texto produzido pela aplicação, como uma citação acrescentada.

Nos dois testes RAG, a mesma fórmula da TUI daria 0,44 e 1,51 “tokens/s”, embora o decode nativo fosse 6,05 e 6,47. Esses testes consumiram o pipeline sem abrir a TUI: a fórmula foi reproduzida, mas o custo de renderização não foi medido.

O pipeline já expõe `metrics.llama_native.decode_tokens_per_second`. Já `metrics.tokens_per_second` inclui o processamento do prompt e usa a retokenização do texto final; também não equivale exatamente ao decode do motor.

### 2. Troca de modelos mesmo em modo residente — confirmada

`src/models/lifecycle.py:7–39` descarrega o outro modelo quando a memória livre fica abaixo do tamanho dos pesos de destino mais 1 GiB. O nome `resident` não garante residência.

Os pesos em disco ocupam aproximadamente 3,80 GiB para Phi e 2,12 GiB para BGE-M3: cerca de 5,92 GiB no total. Isso não é uma medição de VRAM, mas já indica orçamento inadequado para manter ambos na GPU de 6 GiB, considerando cache, buffers e outros usos.

O teste registrou explicitamente o ciclo LLM -> embeddings -> LLM a cada pergunta. Na continuação, apenas recarregar ambos consumiu cerca de 8,7 s. A geração no processo completo também ficou mais lenta que nos testes sem BGE-M3. Separar os dispositivos restaurou o decode no ensaio misto, fortalecendo a hipótese de pressão/interação de memória dos runtimes na GPU. A origem exata da queda, como eventual uso de memória compartilhada pelo Windows, não foi medida e não está comprovada. Offload de 33/33 camadas, sozinho, não comprova desempenho adequado.

### 3. Chamadas auxiliares em toda pergunta — confirmado

`src/rag/query_resolver.py` sempre chama a LLM, inclusive sem histórico. O schema exige repetir a pergunta original e gerar a pergunta independente, aumentando saída e trabalho de validação.

`src/rag/memory.py` sempre tenta produzir um resumo após a resposta. O custo afeta o encerramento do turno e a liberação do campo de entrada. É preciso manter a resolução de referências e a memória extrativa ao otimizar esse caminho.

### 4. Interface impõe espera a cada fragmento — mecanismo e custo medidos em teste automatizado

`src/ui/tui.py:463–468` reconstrói a resposta inteira e chama `call_from_thread` a cada fragmento. Na versão instalada do Textual, esse método espera o callback terminar. A geração espera a UI antes de pedir o próximo fragmento.

O teste automatizado mediu 1,16 s de espera acumulada pelo consumidor na TUI, contra aproximadamente 52,1 s de decode nativo. O chat Rich acrescentou cerca de 0,15 s. São custos reais, mas secundários no cenário medido; o terminal físico e uma sessão longa ainda precisam de medição. A queda principal foi reproduzida no pipeline sem interface. O monitor de hardware usa NVML a cada dois segundos; não há evidência para tratá-lo como gargalo principal.

### 5. Carregamento frio e parametrização — custos secundários

A primeira carga valida SHA256 de vários GiB em `ModelCache.verify(full=True)`. Os objetos evitam repetir o hash completo nas recargas da mesma sessão. Não atribuir o custo recorrente de toda pergunta ao hash.

`LLM_BATCH_SIZE=128` controla tanto batch quanto microbatch; Flash Attention não é configurado e está desabilitado por padrão na versão instalada. Ajustar esses parâmetros exige medir memória, prefill e decode; não é correção comprovada para uma queda de dez vezes.

### 6. Busca vetorial com filtro posterior — risco de escala

`src/rag/vectorstore.py` consulta a coleção inteira e filtra versões em Python, duplicando o número de candidatos até preencher top-k. Com poucas fontes selecionadas em uma base grande, isso pode repetir buscas e trazer muitos textos descartados.

No corpus medido a busca quente levou cerca de 3 ms. Não é o gargalo dominante atual.

## Plano de execução, em ordem

### Etapa 1 — corrigir a observabilidade

Arquivos: `src/ui/tui.py`, `src/metrics.py`, `src/models/llm.py`, `scripts/benchmark.py`.

- Exibir separadamente decode nativo, espera pelo primeiro texto, duração da resposta e tempo total do turno.
- Medir também o ritmo de entrega entre primeiro e último fragmento e os intervalos de atualização do texto. O decode nativo exclui esperas do consumidor e não substitui a medida percebida durante o streaming.
- Usar contagens nativas para a taxa do motor; quando indisponíveis, sinalizar a ausência ou a aproximação, sem contar eventos como tokens.
- Distinguir fim da resposta de fim do resumo. Mostrar a fase atual durante a espera.
- Registrar por chamada: finalidade, tokens de entrada/saída, prefill, decode, reparos, cargas/descargas e motivo de expulsão.
- Registrar RAM e VRAM em fronteiras de fase; VRAM indisponível deve continuar como indisponível.

Aceite: a UI e o relatório usam a mesma definição de decode; testes cobrem fragmentos que não correspondem um a um a tokens e respostas produzidas pela aplicação.

### Etapa 2 — eliminar recarregamentos no perfil deste computador

Arquivos: `src/config.py`, `src/models/lifecycle.py`, `src/models/embeddings.py`, `src/cli.py`, `.env.example`.

- Formalizar primeiro Phi em CUDA e BGE-M3 em CPU, ambos residentes. O ensaio local já mediu embedding quente em CPU de aproximadamente 125 ms e recuperação do decode; repetir em uma conversa maior antes de definir o padrão. Preserva modelos e índice.
- Tornar explícito um perfil misto. Atualmente `load_settings('cuda')` força também embeddings CUDA: alterar só `EMBEDDING_DEVICE` no ambiente pode ser sobrescrito pelo argumento de perfil.
- Corrigir a política para considerar os dispositivos dos dois modelos, evitando expulsar um modelo de GPU apenas para liberar RAM, ou o inverso, quando isso não resolver o recurso limitado.
- Contabilizar cache/buffers e distinguir residência desejada de residência observada. Explicar expulsões na telemetria.
- Serializar ingestão e inferência no mesmo runtime; a TUI hoje permite iniciar ingestão durante uma resposta, compartilhando modelos e ciclo de vida.
- Se o perfil misto não atender, comparar alternativas isoladamente: menor precisão dos embeddings, quantização menor da LLM ou offload parcial. Mudança de embeddings/precisão exige avaliar consistência dos vetores e necessidade de reindexação.

Aceite: após aquecer, cinco perguntas seguidas sem recarregar modelos nem mudar silenciosamente o backend, com menor tempo até o primeiro texto e decode próximo da referência direta para prompts equivalentes.

### Etapa 3 — reduzir o trabalho auxiliar preservando a conversa

Arquivos: `src/rag/query_resolver.py`, `src/rag/memory.py`, `src/rag/pipeline.py`.

- Criar caminho direto para a primeira pergunta sem memória conversacional, com política explícita para ambiguidades. Manter o resolvedor nas continuações que dependem do histórico.
- Medir quantas vezes o reparo ocorre antes de simplificar schema ou remover a cópia obrigatória da pergunta; essa cópia foi introduzida para evitar responder ao assunto anterior.
- Evitar resumo sem conteúdo útil a compactar. Avaliar resumo sob demanda, guardando um estado pendente estritamente limitado e preservando a invalidação pela geração do catálogo.
- Não colocar o resumo em outra thread usando simultaneamente a mesma instância nativa da LLM. Adiar uma chamada só desloca sua latência se ela continuar necessária no turno seguinte.

Aceite: reduzir chamadas no primeiro turno e o custo agregado de uma conversa, mantendo testes de continuação, mudança de assunto, ambiguidade, resumo literal, transformação e cancelamento.

### Etapa 4 — desacoplar streaming e desenho da interface

Arquivos: `src/ui/tui.py`, `src/ui/chat.py`.

- Acumular fragmentos em buffer e atualizar o texto em intervalos de 50–100 ms, sem esperar um callback por fragmento.
- Limitar mensagens pendentes para evitar apenas transferir a lentidão para uma fila crescente.
- Fazer atualização final completa, preservar cancelamento e fechar o gerador em `finally`.

Aceite: comparação com e sem interface usando o mesmo prompt mostra diferença pequena, com texto final e citações completos. Meta inicial de engenharia: diferença mediana de até 10%, a confirmar no hardware.

### Etapa 5 — otimizar parâmetros e recuperação com medição

Arquivos: `src/config.py`, `src/models/llm.py`, `src/rag/vectorstore.py`, `src/rag/ingestion.py`.

- Comparar batch/microbatch 128, 256 e 512 e Flash Attention, uma mudança por vez, verificando suporte do GGUF/runtime e margem de memória.
- Manter contexto de 4096 na referência. Reduzir contexto só como experimento separado e documentar a perda de capacidade.
- Aplicar o filtro de versões/fontes elegíveis no Chroma antes da busca; preservar versões ativas, aliases e IDs de origem.
- Reutilizar contagens de tokens quando houver benefício medido; não remover a validação de orçamento.

Aceite: cada parâmetro adotado melhora a medição pertinente sem falta de memória, perda de citações ou inclusão de versões invisíveis. A busca filtrada deve ter teste com muitas fontes irrelevantes.

### Etapa 6 — comparar com Ollama de forma controlada

- Usar o mesmo modelo, quantização, template, contexto, prompt e limite de geração nos dois motores; separar cargas frias de execuções aquecidas.
- Manter o Phi atual em ambos. A igualdade dos artefatos por hash já foi confirmada; registrar também os parâmetros internos efetivos para ampliar a comparação inicial de duas execuções por motor.
- No Ollama, calcular decode por `eval_count / (eval_duration / 1e9)` e registrar `prompt_eval_duration` e `load_duration` separadamente.
- Medir motor direto, pipeline sem UI e pipeline com UI. Usar cinco ou mais execuções aquecidas por cenário e relatar mediana e dispersão.
- Incluir perguntas novas, continuações, ausência de evidência e filtros de fontes. Verificar a qualidade das respostas ao lado dos tempos.

Não há justificativa, com os dados atuais, para migrar obrigatoriamente ao Ollama: o Phi no motor local já demonstrou aproximadamente 35 tokens/s sozinho e 34 tokens/s no ensaio RAG com os dispositivos separados. O Ollama também foi medido diretamente nesta auditoria, em aproximadamente 30 tokens/s. Falta ampliar as amostras e comparar o mesmo prompt documental com os parâmetros internos de execução registrados.

## Critério de conclusão

O trabalho estará concluído quando o painel apresentar métricas corretas, o perfil escolhido parar de recarregar modelos em consultas aquecidas, o custo de cada chamada estiver visível e a conversa passar nos testes de contexto e fontes. Ganhos de velocidade devem ser demonstrados por medições comparáveis; não basta elevar o número exibido.

Referências externas consultadas: [API de geração do Ollama](https://docs.ollama.com/api/generate) e [API do llama-cpp-python](https://llama-cpp-python.readthedocs.io/en/latest/api-reference/). Os padrões e comportamentos específicos da versão instalada foram também conferidos no código local.
