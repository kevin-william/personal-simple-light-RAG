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

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
# Alternativa explícita, sem GPU:
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Profile cpu
```

Python 3.12 x64; PyTorch 2.6.0 (cu124 ou CPU), llama-cpp-python 0.3.4
(wheel CUDA 12.4) ou 0.3.19 (wheel CPU). Perfis usam versões diferentes
porque os índices oficiais oferecem wheels Windows distintos. Driver NVIDIA
deve suportar CUDA 12.4; o diagnóstico testa os backends separadamente.
Não há fallback para compilar C++. Instalação não altera Python global.
`-SkipModels` instala sem baixar pesos. `--diagnose` verifica backends sem pesos.
O comando de preparação de modelos será acrescentado na próxima tarefa.

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
Status de offload efetivo vem do log nativo quando disponível; não é inferido
do parâmetro solicitado. Nenhum modelo é carregado pelo menu/listagem.

## Conversa

Memória mantém apenas a última mensagem completa e um resumo enxuto gerado
pela LLM, limitado por tokens. Atualização/exclusão da base invalida essa memória.
A LLM resolve continuações em uma pergunta independente e contexto mínimo;
somente a pergunta independente vai ao BGE-M3. Ambiguidades pedem clarificação.
Templates de perguntas triviais orientam a LLM, sem substituições por palavras-chave.
Saída JSON inválida recebe no máximo uma tentativa de reparo.

O pipeline reserva tokens para resposta e conta o template oficial no orçamento.
Entradas essenciais excessivas são recusadas; chunks podem ser reduzidos e
o painel mostra o trecho efetivamente fornecido. Citações válidas apontam para
esses trechos; IDs inválidos ou ausência de citações geram aviso. IDs corretos
não garantem que o texto sustenta cada afirmação. Respostas interrompidas não
atualizam memória. Perguntas sem evidência recebem uma recusa explícita.
