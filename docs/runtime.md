# Runtime validado

Python 3.12 x64, PyTorch 2.6.0+cu124 e llama-cpp-python 0.3.36 CUDA 12.4
compõem o perfil NVIDIA. O wheel upstream moderno usa `py3-none-win_amd64`;
procurar somente wheels `cp312` encontra versões antigas. 0.3.4 não reconhece
o pre-tokenizer `gpt-4o` do GGUF escolhido e não é suportado neste projeto.

O perfil CPU usa PyTorch 2.6.0+cpu e llama-cpp-python 0.3.19 CPU.
Os perfis são explícitos, sem troca silenciosa de backend ou compilação C++.
O instalador aplica `requirements-lock.txt` às dependências comuns.

- [Wheel CUDA upstream fixado](https://github.com/abetlen/llama-cpp-python/releases/tag/v0.3.36-cu124).
- SHA256 do asset Windows: `7086b98420cf9cca5e3f14181edc4332038bfb0a0e380370a693806bb527911f`.
- `Phi-4-mini-instruct.Q8_0.gguf`: revisão `78eb92a46fc37e6b524df991ed9aca9bc6aa7b80`.
- BGE-M3: revisão `5617a9f61b028005a4858fdac845db406aefb181`, com `pytorch_model.bin` nesta revisão.

Manifestos de cache validam estrutura, tamanho e SHA256. Corrupção tem erro
acionável e pode ser corrigida por `--prepare`. Após cache completo, carregar
modelos não acessa a rede. Os pesos BIN oficiais são usados com PyTorch 2.6.

As DLLs de runtime do PyTorch são registradas somente no processo Windows;
nenhum PATH de usuário/sistema ou arquivo de plugin é alterado. Os tokens
oficiais do Phi são validados antes de inferir. Offload é observado pelo log
nativo; o parâmetro solicitado não é tratado como prova de aceleração.

`LLM_BATCH_SIZE=128` limita memória temporária. O modo alternado libera um
modelo antes do outro; o residente pode liberar o outro modelo se o tamanho
dos pesos mais reserva de 1 GiB ultrapassar a memória livre. Essa estimativa
não substitui medição nem garante que toda alocação terá sucesso.
