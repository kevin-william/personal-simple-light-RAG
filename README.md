# Personal Simple Light RAG

Chat CLI local em Python: Phi-4-mini Q8_0, BGE-M3 e ChromaDB.
O padrão é misto: Phi na GPU NVIDIA/CUDA e BGE-M3 na CPU/RAM, ambos residentes.
CPU para ambos é uma opção explícita; consultas não guardam contexto conversacional.

## Configuração

Python 3.12 x64. A entrada não carrega modelos para mostrar configuração:

```powershell
python main.py --status
python main.py --profile cpu --status
```

Copie `.env.example` para `.env` para personalizar os limites. Caminhos são
relativos à raiz da aplicação, não ao diretório atual do terminal.

O plano e as tarefas estão em [implementation_plan.md](implementation_plan.md)
e [tasks/index.md](tasks/index.md). Documentos de origem nunca são apagados.

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

Python 3.12 x64; PyTorch 2.6.0 (cu124 no perfil misto/CUDA ou CPU), llama-cpp-python 0.3.36
(wheel CUDA 12.4 `py3-none-win_amd64`) ou 0.3.19 (wheel CPU). Perfis usam versões diferentes
porque os índices oficiais oferecem wheels Windows distintos. Driver NVIDIA
deve suportar CUDA 12.4; o diagnóstico testa os backends separadamente.
Não há fallback para compilar C++. Instalação não altera Python global.
`-SkipModels` instala sem baixar pesos. `--diagnose` verifica backends sem pesos.
O wheel CUDA é fixado por URL e SHA256 do release upstream. Versões antigas
como 0.3.4 não reconhecem o pre-tokenizer `gpt-4o` deste GGUF.

## Modelos

`python main.py --prepare` baixa as revisões imutáveis configuradas de ambos
os modelos, valida tamanho e SHA256 (incluindo SHA remoto quando fornecido)
e publica manifestos somente após sucesso. `--prepare --offline` verifica
cache sem rede. Carregamento também verifica integridade. Pesos ficam em
`models/llm` e `models/embeddings`; downloads interrompidos podem ser repetidos.
Os dois repositórios publicam licença MIT. Use `--status` para ver as revisões.

## Documentos suportados

PDF com camada de texto, TXT e Markdown UTF-8. PDFs sem texto geram aviso
de OCR e não são indexados vazios. Trechos preservam páginas ou linhas;
divisão recursiva usa caracteres e overlap, sem truncamento silencioso.

BGE-M3 usa normalização L2 e o mesmo processamento para perguntas/documentos.
O limite de entrada é validado por tokens; documentos longos são redivididos.
ChromaDB persiste vetores com cosseno explícito, sem usar encoder padrão.
Similaridade `1 - distância` não é probabilidade ou confiança da resposta.
Mudanças de revisão/divisão/processamento exigem uma nova base ou reset.
O catálogo SQLite separa identidade de origem e conteúdo compartilhado e
registra versões pending/active/failed e uma geração para invalidar memória.

Importação usa hash de conteúdo e IDs determinísticos. Reimportar conteúdo
inalterado não recalcula embeddings; arquivos idênticos compartilham vetores
e mantêm aliases de origem. Apenas versões completas/ativas entram na busca.
Há suporte a um escritor local por vez; execução multiprocesso é fora de escopo.

Atualizações são preparadas antes de trocar o ponteiro ativo no SQLite.
Erros preservam a versão anterior. Ao iniciar, preparações incompletas são
limpas para reimportação idempotente; limpeza pós-ativação pode ser repetida.
Arquivos com conteúdo compartilhado não perdem aliases por uma atualização.

Exclusão usa ID estável de origem, não nome de arquivo. Remover um alias
preserva os demais; reset exige confirmação explícita. Arquivos originais
não são removidos. A visibilidade é retirada antes da limpeza recuperável.

## Inferência e memória de hardware

Inferência direta com `llama-cpp-python`. O template oficial Phi e a contagem
pelo mesmo serializer são preservados; marcadores especiais de documentos e
perguntas são escapados.

O perfil padrão usa **Phi em CUDA e BGE-M3 em CPU**, em modo residente.
Depois da primeira consulta, ambos permanecem carregados em seus dispositivos.
Carregar o modelo da CPU não descarrega o da GPU, nem o inverso.
Sem CUDA ou memória suficiente, a aplicação apresenta erro; não troca o
backend silenciosamente. Use `--profile cpu` para escolher CPU explicitamente.

```powershell
.venv/Scripts/python main.py --profile mixed --tui
.venv/Scripts/python main.py --profile cpu
# Legado: ambos os modelos na GPU, selecionado explicitamente:
.venv/Scripts/python main.py --profile cuda
```

Sem `--profile`, configurações explícitas do ambiente e `.env` são respeitadas,
e os novos padrões selecionam o perfil misto. Um ambiente instalado como CPU
continua selecionando CPU. O perfil `mixed` explícito força residência e os
dispositivos mistos; o perfil `cuda` mantém o comportamento legado.

Em dispositivos compartilhados, o modo residente pode liberar o outro modelo
quando a estimativa de pesos mais 1 GiB ultrapassa a memória livre. Essa
heurística não garante que cache de contexto e buffers caibam.
`MEMORY_MODE=alternating` continua disponível em configurações legadas.
Offload efetivo é observado pelo log nativo, sem inferi-lo do parâmetro pedido.
`N_GPU_LAYERS` permite offload parcial explícito. `LLM_BATCH_SIZE=128` limita
os lotes de prefill; as DLLs CUDA vêm do PyTorch, sem compilador C++ adicional.

## Consultas independentes

Cada consulta usa somente a pergunta atual, as instruções de sistema e os
trechos documentais recuperados para essa pergunta. O BGE-M3 recebe diretamente
a pergunta; o Phi é chamado uma única vez para produzir a resposta.
Não há reescrita de consulta, resumo ou reutilização de respostas anteriores.
O histórico visual da TUI não participa das buscas nem dos prompts.
Escreva perguntas completas: “resuma isso” não acessa a resposta anterior.

O pipeline reserva tokens para resposta e conta o template oficial no orçamento.
Entradas essenciais excessivas são recusadas; trechos podem ser reduzidos e
o painel mostra o texto efetivamente fornecido. Citações válidas apontam para
esses trechos; IDs inválidos geram aviso, e um ID correto por si só não prova
que uma afirmação é sustentada. Sem resultados, a aplicação responde sem
chamar o Phi. Respostas canceladas preservam o texto parcial e liberam o runtime.

Uma resposta inteira em código inline pode receber citação automática quando
copiada literalmente de um trecho fornecido. Isso comprova sua localização,
não sua pertinência à pergunta.

Consultas, ingestão, exclusão e reset são serializados no mesmo runtime.
Uma tentativa concorrente recebe aviso antes de alterar dados ou modelos.
Na TUI, ações incompatíveis ficam desabilitadas; Esc cancela a resposta.
A seleção “Nenhuma” pesquisa em zero fontes, sem recorrer à base inteira.

Os chats agrupam atualizações visuais a cada 100 ms e apresentam separadamente
espera pelo primeiro texto, tempo de resposta, duração total, decode nativo e
entrega estimada. Fragmentos de streaming não são contados como tokens.
Taxa nativa ausente aparece como indisponível. O benchmark registra fases,
chamadas ao Phi e eventos de carga/descarga; VRAM indisponível não vira zero.

## Gerenciar documentos

Para ver, visualizar ou listar todos os documentos já indexados, execute
`.venv/Scripts/python main.py --list` ou escolha **3. Listar documentos** no menu.
Essa listagem mostra ID de origem, caminho e quantidade de trechos por arquivo.

```powershell
.venv/Scripts/python main.py
.venv/Scripts/python main.py --add "C:\documentos"
.venv/Scripts/python main.py --list
.venv/Scripts/python main.py --delete ID_ORIGEM --yes
.venv/Scripts/python main.py --reset --yes
```

O menu oferece confirmação de exclusão/reset e relatório por arquivo.
`--data-dir CAMINHO` seleciona outra base. A base tem um lock de runtime
para impedir duas instâncias de manipularem o mesmo armazenamento.

## Chat

```powershell
.venv/Scripts/python main.py --ask "Como configurar autenticação?" --sources
```

Ou escolha Chat no menu. `/clear` limpa o último resultado e suas fontes;
`/sources` alterna detalhes de fontes; `/exit` volta ao menu. Ctrl+C cancela
uma resposta e libera o runtime. Base vazia pede ingestão.
O perfil CPU escolhido pelo instalador fica registrado na venv; em instalações
manuais selecione `--profile cpu`. Sem seleção CPU, o perfil misto é o padrão.

## Testes e benchmarks

```powershell
.venv/Scripts/python -m pytest -m "not integration_models" --basetemp work/pytest -q
.venv/Scripts/python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Testes de modelos reais são opt-in (`--models --model-profile mixed`, `cpu` ou `cuda`).
Benchmarks por fase e avaliação estão em [docs/benchmarks.md](docs/benchmarks.md).
Diagnóstico histórico e gates pendentes: [docs/validation.md](docs/validation.md).

O plano desta etapa está em [optimization_flow_plan.md](optimization_flow_plan.md).
Resultados medidos e limites: [optimization_results.md](optimization_results.md).

Comparação reproduzível de motor, pipeline e chats (base exclusiva):

```powershell
.venv/Scripts/python scripts/benchmark_flow.py --corpus scripts/benchmark_corpus.json --data-dir work/benchmark-flow --output work/benchmark-flow/report.json --runs 5 --terminal
```

São uma execução fria e cinco aquecidas por caminho. O argumento `--terminal`
inclui renderização no terminal atual; sem ele, usa buffer/driver headless.
O manifesto de exemplo está versionado e usa somente este README.
