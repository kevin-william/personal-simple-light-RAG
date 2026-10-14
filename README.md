# Personal Simple Light RAG

Chat CLI local em Python: Phi-4-mini Q8_0, BGE-M3 e ChromaDB.
GPU NVIDIA/CUDA é o padrão recomendado. CPU é uma opção explícita.

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

Python 3.12 x64; PyTorch 2.6.0 (cu124 ou CPU), llama-cpp-python 0.3.36
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

Inferência direta com `llama-cpp-python`. Mensagens estruturadas passam por
formatter oficial Phi (`<|system|>`, `<|user|>`, `<|assistant|>`, `<|end|>`),
com contagem pelo mesmo serializer, sem ChatML nem duplicação de tokens.
Marcadores especiais presentes em texto de usuário/documentos são escapados.
`MEMORY_MODE=alternating` libera um modelo antes de carregar o outro; é útil
para pouca VRAM. `N_GPU_LAYERS` permite offload parcial explícito.
No modo residente, uma estimativa conservadora compara tamanho dos pesos
e reserva de 1 GiB à memória disponível antes de carregar o segundo modelo;
o primeiro pode ser liberado automaticamente. É uma heurística, não garantia
de memória suficiente nem troca de modelo/backend.
Status de offload efetivo vem do log nativo quando disponível; não é inferido
do parâmetro solicitado. Nenhum modelo é carregado pelo menu/listagem.
`LLM_BATCH_SIZE=128` reduz a memória temporária de prefill; pode ser ajustado
explicitamente para comparar desempenho. As DLLs CUDA do PyTorch são usadas
no processo Windows, sem exigir instalação de compilador C++/CUDA Toolkit.

## Conversa

Memória mantém apenas a última mensagem completa e um resumo extrativo enxuto
selecionado pela LLM (até 3 fragmentos/35 palavras e o limite de tokens).
Fragmentos devem existir literalmente na conversa: comandos inventados são
rejeitados com uma tentativa de reparo. Atualização/exclusão invalida essa memória.
A LLM resolve continuações em uma pergunta independente e contexto mínimo;
somente a pergunta independente vai ao BGE-M3. Ambiguidades pedem clarificação.
Templates de perguntas triviais orientam a LLM, sem substituições por palavras-chave.
Saída JSON inválida recebe no máximo uma tentativa de reparo.

O pipeline reserva tokens para resposta e conta o template oficial no orçamento.
Entradas essenciais excessivas são recusadas; chunks podem ser reduzidos e
o painel mostra o trecho efetivamente fornecido. Citações válidas apontam para
esses trechos; IDs inválidos geram aviso. IDs corretos
não garantem que o texto sustenta cada afirmação. Respostas interrompidas não
atualizam memória. Perguntas sem evidência recebem uma recusa explícita.
Quando a resposta inteira é um comando em código inline copiado literalmente
de um trecho fornecido, a aplicação acrescenta sua referência se o modelo a
omitiu. Isso comprova a localização do texto, não sua pertinência à pergunta.

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

Ou escolha Chat no menu. `/clear` limpa a última mensagem e resumo;
`/sources` alterna detalhes de fontes; `/exit` volta ao menu. Ctrl+C cancela
uma resposta sem salvar a resposta parcial na memória. Base vazia pede ingestão.
O perfil CPU escolhido pelo instalador fica registrado na venv; em instalações
manuais selecione `--profile cpu`. Sem seleção CPU, CUDA continua padrão.

## Testes e benchmarks

```powershell
.venv/Scripts/python -m pytest -m "not integration_models" --basetemp work/pytest -q
.venv/Scripts/python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Testes de modelos reais são opt-in (`--models --model-profile cpu` ou `cuda`).
Benchmarks por fase e avaliação estão em [docs/benchmarks.md](docs/benchmarks.md).
Resultados observados e gates pendentes: [docs/validation.md](docs/validation.md).
