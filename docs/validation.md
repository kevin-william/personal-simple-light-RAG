# Validação da implementação — 14/10/2026

Código das 17 tarefas implementado e registrado em commits locais, seguido
de correções encontradas na validação real. O repositório é local; não houve push.

## Ambiente observado

Windows 11, Python 3.12.6 x64, Intel64 Family 6 Model 186 Stepping 2,
16 GB de RAM (16.895.991.808 bytes reportados), NVIDIA GeForce RTX 3050
Laptop com 6 GB de VRAM, driver 617.14. Isso não é uma certificação de
instalação em Windows limpo nem um requisito mínimo universal.

| Perfil | PyTorch | llama-cpp-python | Execução observada |
|---|---|---|---|
| CUDA principal | 2.6.0+cu124 | 0.3.36, wheel upstream CUDA 12.4 | BGE-M3 em CUDA; Phi com 33/33 camadas offloaded |
| CPU opcional | 2.6.0+cpu | 0.3.19, wheel upstream CPU | BGE-M3 em CPU; Phi com zero camadas offloaded |

## Verificação executada

- **57 testes automatizados aprovados**, incluindo ChromaDB e SQLite reais,
  normalização/processamento, aliases, atualização, exclusão, reset incompatível,
  recuperação de processo encerrado abruptamente, orçamento, contexto e UI.
- Teste opt-in com **pesos reais em CPU e CUDA** aprovado em ambos os perfis:
  embeddings de 1024 dimensões normalizados, cache offline, geração Phi,
  tokens oficiais e liberação alternada dos modelos.
- `compileall`, `pip check`, comando `light-rag --status` e verificador literal
  das 17 tarefas aprovados. 36 excertos do plano permanecem rastreáveis.
- `setup.ps1 -SkipModels` executado com sucesso no perfil CUDA deste computador,
  incluindo registro do comando instalado e diagnóstico dos dois backends.
- GGUF e BGE-M3 baixados nas revisões fixadas, com tamanho/SHA256 verificados;
  GGUF `Phi-4-mini-instruct.Q8_0.gguf` e BGE-M3 `pytorch_model.bin` nesta revisão.
- Avaliação ponta a ponta do README: comando de preparação CPU, continuação
  sobre listar documentos e pergunta sobre telefone ausente. Respostas e
  fontes inspecionadas por Codex; os casos positivos correspondem aos comandos
  documentados e o caso negativo foi recusado. Não houve avaliação humana.

## Amostras observadas

Corpus: README deste projeto. Contexto **2048**, resposta até **192 tokens**;
essas amostras não medem a configuração completa padrão de 4096/512.
O teste nativo separado utilizou o contexto padrão de 4096.

| Perfil | Respostas | TTFT (s, intervalo) | Decode nativo (tokens/s, intervalo) | Pico RSS amostrado (GiB) |
|---|---:|---:|---:|---:|
| CPU, residente | 3 | 43.09–48.31 | 10.14–12.04 | 5.65 |
| CUDA, alternado | 6 | 10.18–27.87 | 28.21–32.87 | 6.37 |

TTFT inclui resolução, embeddings, busca e prefill. Decode nativo separa
prefill de decodificação; tempos inclusivos por fase não devem ser somados.
VRAM por processo é indisponível no WDDM deste ambiente e aparece como null;
não foi fabricado pico de VRAM. CPU/CUDA usam modos de memória diferentes,
portanto as amostras não constituem comparação controlada de backends.

Relatórios detalhados: [CPU](observed/cpu.json), [CUDA](observed/cuda.json).
Eles contêm texto apenas da documentação deste próprio projeto, mediante
`--include-text`. Por padrão, benchmark oculta texto e detalhes de erro privados.

## Ajustes derivados dos testes

- Wheel CUDA antigo 0.3.4 não reconhecia o pre-tokenizer gpt-4o: substituído
  pelo upstream 0.3.36, fixado por URL/SHA256, sem compilação C++.
- DLLs de runtime são encontradas no PyTorch; BGE-M3 aceita seus pesos BIN.
- Limites de strings enormes na gramática JSON foram removidos da gramática
  nativa, mantendo tipos, mínimos pequenos e limites completos no Pydantic.
- Resumo extrativo pela LLM rejeita fragmentos inventados; enum dinâmico faz
  o resolvedor copiar a pergunta atual antes de produzir a consulta independente.
- Pergunta original permanece no fim do prompt. Comandos de status não são
  tratados como instalação; documentação explica instalação/listagem claramente.
- Resposta inteira em código inline literal pode receber citação automática
  por correspondência exata; esse vínculo não prova pertinência semântica.
- Painel de fontes e memória são invalidados ao mudar a geração do catálogo.

## Gates externos ainda pendentes

- Instalação em **Windows limpo**, sem dependências previamente presentes.
- Validação em hardware CPU sem GPU física e em outras GPUs/quantidades de RAM.
- Avaliação humana e corpus real de documentação do usuário; recuperação e
  qualidade não são garantidas por um corpus pequeno do próprio projeto.
- Calibração de relevância e publicação de requisitos mínimos/recomendados
  certificados. Não há promessa de ausência absoluta de alucinações.

Código entregue; esses gates precisam de ambientes/dados adicionais antes
de prometer compatibilidade universal ou requisitos mínimos de hardware.
