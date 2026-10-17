# Resultado da otimização do fluxo RAG

Validação local em 17/10/2026, branch `codex/otimizacao-fluxo-rag`.

O fluxo foi simplificado para consultas independentes: pergunta atual, busca documental e uma única geração. Phi permanece na GPU e BGE-M3 na CPU, sem trocas de modelo entre perguntas. Histórico visual não participa da inferência.

## Ambiente e método

- GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU, 6144 MiB de VRAM; RAM total aproximada: 15.7 GiB.
- Modelos e revisões preservados; contexto 4096, resposta até 512 tokens, batch/microbatch 128, temperatura 0,1 e seed inicial 42.
- Runtime: torch 2.6.0+cu124, llama-cpp-python 0.3.36, sentence-transformers 5.1.1, chromadb 1.0.20, textual 8.0.0, rich 14.2.0.
- Corpus: README atualizado do próprio projeto, em uma base exclusiva em `work/optimization-benchmark/`; a base original `data/` foi preservada.
- Uma execução com modelos frios e cinco aquecidas em cada um dos quatro caminhos, sequencialmente, sem outro modelo residente na GPU. O cache de arquivos do Windows não foi limpo.
- Os quatro caminhos usaram o mesmo prompt, confirmado por um único SHA256: `a9598fdc4d9db504ff7c6e2034c31e626db255567df4437496139e601f2484c5`.
- Rich e Textual foram executados com renderização em um pseudoterminal Windows, com entrada automatizada. Isso inclui a escrita no terminal, mas não mede a percepção na janela/corpus originais do usuário.

## Medianas das cinco execuções aquecidas

| Caminho | Decode nativo | Entrega estimada | Primeiro texto no fluxo | Tempo total |
|---|---:|---:|---:|---:|
| Motor direto | 35.05 tokens/s | 34.23 tokens/s | 0.042 s | 10.31 s |
| Pipeline RAG | 34.99 tokens/s | 34.07 tokens/s | 0.181 s | 10.66 s |
| Chat do menu (Rich) | 35.05 tokens/s | 34.12 tokens/s | 0.157 s | 10.60 s |
| TUI (Textual) | 35.02 tokens/s | 33.90 tokens/s | 0.185 s | 10.46 s |

O primeiro update de texto do widget da TUI ocorreu em mediana após **0.262 s**, incluindo o agrupamento visual de até aproximadamente 100 ms. A métrica do primeiro texto do fluxo é coletada antes desse agrupamento.

Cada consulta aquecida fez **uma chamada ao Phi e zero cargas/descargas**. Os dois chats ficaram dentro da margem de 10% definida para a duração da resposta em relação ao pipeline; o decode ficou acima de 99% da referência direta, superando o critério de 80%. As diferenças pequenas entre caminhos incluem variação de execução e de geração, sem demonstrarem aceleração pela interface.

Na primeira execução, o tempo total foi de 21.87 s no pipeline, incluindo carga e verificação dos pesos. Esses custos de inicialização continuam existindo.

## Validação funcional

- 88 testes funcionais aprovados, incluindo independência entre consultas, fontes vazias, concorrência, cancelamento, falha de encerramento, coalescimento visual e recuperação da interface após ingestão bem-sucedida ou falha.
- Teste de pesos reais no perfil misto aprovado: embeddings normalizados e Phi com offload efetivo, mantendo BGE-M3 residente em CPU.
- Teste de pesos reais no perfil CPU explícito aprovado, usando o mesmo ambiente CUDA instalado e zero camadas offloaded. Isso não certifica uma máquina sem GPU nem o wheel CPU separado.
- Três consultas reais ao README aprovadas: instalação CPU e listagem retornaram os comandos esperados com citações; pergunta sobre telefone ausente foi recusada. Cada consulta fez uma geração, sem resumo. Os textos foram inspecionados pelo agente, sem avaliação humana formal.
- `pip check`, compilação dos módulos e verificador das 17 tarefas históricas aprovados.
- A instalação local foi restaurada e o conflito preexistente entre o Rich fixado e o Textual foi resolvido: Rich 14.2.0 e Textual 8.0.0. Os wheels locais CUDA são reutilizáveis; o wheel llama.cpp tem SHA256 conferido.

## Evidências e reprodução

Relatório completo: [work/optimization-benchmark/report.json](work/optimization-benchmark/report.json). Os relatórios detalhados e as bases de medição permanecem locais e ignorados pelo Git.

Casos documentais: [work/optimization-quality/report.json](work/optimization-quality/report.json). A pergunta sem resposta nesses casos ainda tinha candidatos documentais e precisou de uma geração para recusar; zero chamadas aplica-se a buscas sem candidatos, como seleção de fontes vazia.

```powershell
.venv/Scripts/python -m pytest -m "not integration_models" --basetemp work/pytest-optimization-check -q
.venv/Scripts/python -m pytest tests/test_models_integration.py --models --model-profile mixed -q
.venv/Scripts/python scripts/benchmark_flow.py --corpus scripts/benchmark_corpus.json --data-dir work/optimization-recheck --output work/optimization-recheck/report.json --runs 5 --terminal
```

O benchmark exige uma base isolada e inicia pelo caminho `plain` para capturar o prompt de referência. Sem `--terminal`, as interfaces são medidas com saída em buffer/driver headless. O manifesto público `scripts/benchmark_corpus.json` está versionado e aponta para o README do projeto. O benchmark convencional em `scripts/benchmark.py` também aceita um manifesto fornecido pelo usuário.

As observações antigas de aproximadamente 6 tokens/s no RAG são uma referência histórica. A pergunta, o prompt e o README mudaram nesta etapa; não constituem um ensaio pareado para afirmar um multiplicador exato de ganho. Também não houve reprodução da sessão específica em que o usuário percebeu aproximadamente 1 token/s, nem certificação de instalação em Windows limpo ou de qualidade em outros corpora.
