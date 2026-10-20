# Personal Simple Light RAG

Chat CLI local em Python com suporte às famílias **Phi** e **Qwen**, embeddings densos e ChromaDB.
O motor de inferência é 100% autônomo e embutido (`llama-cpp-python`).
O padrão para máquinas com GPU NVIDIA é misto (LLM em CUDA e embeddings em CPU);
para computadores sem placa de vídeo, há suporte otimizado para inferência puramente em CPU.

## Desempenho em CPU e Escolha de Modelos

Ao executar LLMs em CPU, o principal limitador de velocidade na geração de texto (*decode*) é a **largura de banda da memória RAM**. Como cada token gerado exige que a CPU leia a totalidade dos pesos do modelo da RAM:

$$\text{Velocidade Máxima (tokens/s)} \approx \frac{\text{Largura de Banda da RAM (GB/s)}}{\text{Tamanho do Modelo (GB)}}$$

Em máquinas com apenas 1 pente de memória DDR4 (Single-Channel, ~18–20 GB/s de vazão real), um modelo de 4 GB atinge no máximo ~4,5 a 4,9 tokens/s. No Ollama, a métrica de ~30 a 35 tokens/s frequentemente observada refere-se à taxa de **leitura do prompt** (*prompt eval*), e não à taxa de escrita (*decode*), que é idêntica nos dois motores.

Para acelerar expressivamente a inferência em CPU, utilize quantizações **Q4_K_M** ou modelos mais compactos:

### Modelos de LLM Homologados

| Modelo | Arquivo GGUF / Quantização | Tamanho em RAM | Velocidade Estimada em CPU (Single-Channel) | Indicação de Uso |
|---|---|---|---|---|
| **Phi-4-mini** (Padrão CPU) | `Phi-4-mini-instruct-Q4_K_M.gguf` | **~2,5 GB** | **~8 a 9 tokens/s** (2x mais rápido) | **Recomendado para CPU**: equilíbrio ideal de velocidade e alta inteligência. |
| **Qwen 2.5 3B** | `qwen2.5-3b-instruct-q4_k_m.gguf` | **~2,1 GB** | **~10 tokens/s** | Excelente em português e raciocínio, muito rápido em CPU. |
| **Qwen 2.5 1.5B** | `qwen2.5-1.5b-instruct-q4_k_m.gguf` | **~1,1 GB** | **~18 a 20 tokens/s** | Ultra-leve; ideal para CPUs mais modestas ou notebooks com pouca RAM. |
| **Phi-4-mini Q8** (Padrão GPU) | `Phi-4-mini-instruct.Q8_0.gguf` | **~4,1 GB** | ~4,5 tokens/s (CPU) / ~35 tokens/s (CUDA) | Máxima fidelidade; ideal quando há placa de vídeo NVIDIA disponível. |

### Modelos de Embeddings

| Modelo Hugging Face | Dimensão | Tamanho em RAM | Indicação |
|---|---|---|---|
| **`BAAI/bge-m3`** (Padrão) | 1024 | ~2,2 GB | Multilíngue denso, alta precisão semântica para documentos complexos. |
| **`paraphrase-multilingual-MiniLM-L12-v2`** | 384 | ~470 MB | Multilíngue leve; economiza ~1,7 GB de RAM em relação ao BGE-M3. |
| **`all-MiniLM-L6-v2`** | 384 | ~90 MB | Ultra-leve em RAM; ideal para buscas rápidas e documentos em inglês. |

> [!WARNING]
> Ao alterar o modelo de embeddings no `.env` (por exemplo, de 1024 para 384 dimensões), a coleção de vetores anterior torna-se incompatível. O sistema detecta isso automaticamente via `fingerprint`. Para reindexar com o novo modelo, use `.venv/Scripts/python main.py --reset --yes` ou aponte para um novo diretório com `--data-dir`.

### Como trocar de modelo no `.env`

1. Abra o arquivo `.env` (ou copie `.env.example` para `.env`).
2. Descomente o modelo desejado (por exemplo, Phi Q4 ou Qwen 2.5 3B).
3. Execute a preparação para baixar os pesos validados:
   ```powershell
   .venv/Scripts/python main.py --prepare
   ```
4. Inicie o chat normalmente:
   ```powershell
   .venv/Scripts/python main.py --profile cpu
   ```

### Otimização de Threads na CPU

Por padrão, o projeto detecta automaticamente a quantidade de **núcleos físicos da CPU** (ex: 6 núcleos em uma Ryzen 5 5655GE) para alocar `n_threads`. Isso evita a perda de até 21% de desempenho causada pela disputa de threads lógicas (HyperThreading/SMT). Você pode sobrescrever manualmente definindo `LLM_THREADS=6` no `.env`.

---

## Configuração e Inicialização

Python 3.12 x64. A entrada não carrega modelos para mostrar configuração:

```powershell
python main.py --status
python main.py --profile cpu --status
```

Copie `.env.example` para `.env` para personalizar os limites. Caminhos são
relativos à raiz da aplicação, não ao diretório atual do terminal.

## Preparação Windows

Para instalar as dependências e preparar o projeto para execução sem GPU,
use `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Profile cpu`.
Esse instalador cria o ambiente Python, instala os pacotes CPU e baixa os modelos.
O comando `--status` somente exibe configuração; não instala nem prepara pacotes.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
# Alternativa explícita, sem GPU:
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Profile cpu
```

## Modelos

`python main.py --prepare` baixa as revisões imutáveis configuradas de ambos
os modelos, valida tamanho e SHA256 (incluindo SHA remoto quando fornecido)
e publica manifestos somente após sucesso. `--prepare --offline` verifica
cache sem rede. Carregamento também verifica integridade. Pesos ficam em
`models/llm` e `models/embeddings`; downloads interrompidos podem ser repetidos.

## Documentos suportados

PDF com camada de texto, TXT e Markdown UTF-8. PDFs sem texto geram aviso
de OCR e não são indexados vazios. Trechos preservam páginas ou linhas;
divisão recursiva usa caracteres e overlap, sem truncamento silencioso.

## Inferência e memória de hardware

Inferência direta com `llama-cpp-python`. O template oficial (Phi ou ChatML para Qwen)
e a contagem pelo mesmo serializer são preservados; marcadores especiais de documentos e
perguntas são escapados.

O perfil misto usa **Phi em CUDA e BGE-M3 em CPU**, em modo residente.
Sem CUDA ou memória suficiente, use `--profile cpu` para escolher CPU explicitamente.

```powershell
.venv/Scripts/python main.py --profile mixed --tui
.venv/Scripts/python main.py --profile cpu
# Legado: ambos os modelos na GPU, selecionado explicitamente:
.venv/Scripts/python main.py --profile cuda
```

## Consultas independentes

Cada consulta usa somente a pergunta atual, as instruções de sistema e os
trechos documentais recuperados para essa pergunta. A LLM é chamada uma única vez para produzir a resposta.
Não há reescrita de consulta, resumo ou reutilização de respostas anteriores.
O histórico visual da TUI não participa das buscas nem dos prompts.

## Gerenciar documentos

Para ver, visualizar ou listar todos os documentos já indexados, execute
`.venv/Scripts/python main.py --list` ou escolha **3. Listar documentos** no menu.

```powershell
.venv/Scripts/python main.py
.venv/Scripts/python main.py --add "C:\documentos"
.venv/Scripts/python main.py --list
.venv/Scripts/python main.py --delete ID_ORIGEM --yes
.venv/Scripts/python main.py --reset --yes
```

## Chat

```powershell
.venv/Scripts/python main.py --ask "Como configurar autenticação?" --sources
```

Ou escolha Chat no menu. `/clear` limpa o último resultado e suas fontes;
`/sources` alterna detalhes de fontes; `/exit` volta ao menu. Ctrl+C cancela
uma resposta e libera o runtime.

## Testes e benchmarks

```powershell
.venv/Scripts/python -m pytest -m "not integration_models" --basetemp work/pytest -q
```
