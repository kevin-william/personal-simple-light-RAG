# Benchmarks e avaliação

```powershell
.venv/Scripts/python scripts/benchmark.py --corpus docs/evaluation.json --data-dir work/benchmark-cuda --profile cuda --mode alternating --runs 2 --output work/benchmark-cuda.json
.venv/Scripts/python scripts/benchmark.py --corpus docs/evaluation.json --data-dir work/benchmark-cpu --profile cpu --mode resident --runs 2 --output work/benchmark-cpu.json
```

Manifesto: `documents` contém caminhos relativos ao JSON; `questions` contém
perguntas e `expected_substrings` opcionais. Revise o corpus antes de executar.
O exemplo usa documentação do próprio projeto. Fixtures sintéticas dos testes
não demonstram qualidade em documentos externos. Fundamentação, recusas,
continuações e citações precisam de revisão humana, além de correspondência
de frases. O runner grava versões, configuração, hashes, índices das perguntas
e tempos. Textos privados ficam fora do relatório por padrão; `--include-text`
os registra explicitamente apenas no arquivo local solicitado.

TTFT é a latência percebida: começa antes da resolução e termina no primeiro
fragmento exibido. Tempo total inclui resumo após a resposta. Tokens/s mede
geração; phases são tempos inclusivos (podem conter carregamento), portanto
não se deve somar fases aninhadas para obter tempo total. RSS máximo é amostrado
a cada 100 ms e em fronteiras de fase; pode não capturar picos muito breves.
VRAM por processo é medida ao fim via NVIDIA; WDDM pode informar N/A. Isso é
`null`, não zero, e não é apresentado como pico de VRAM.

Compare frio/quente, modos residente/alternado, lotes e offload parcial usando
configurações separadas. Não publique requisitos mínimos/recomendados nem
metas numéricas sem medições no hardware correspondente. Evidências atuais
ficam em [validation.md](validation.md).
