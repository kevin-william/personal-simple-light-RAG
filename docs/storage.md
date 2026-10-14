# Consistência da base

SQLite mantém origens, aliases, versões e geração. ChromaDB mantém os vetores
e trechos. Eles não formam uma transação única: uma versão em preparação só
fica visível após conferir que todos os trechos existem e ativar seu ponteiro.

Falhas antes de ativação preservam a versão antiga. Preparações interrompidas
são limpas para reimportação, e limpeza de versões órfãs é repetível. O teste
de regressão inclui um subprocesso que encerra com `os._exit(23)` após gravar
uma versão pending nos bancos reais, sem fechar conexões normalmente.

Arquivos idênticos compartilham conteúdo vetorial. Excluir uma origem não
remove os demais aliases. Consultas e referências exigem versão e origem
ativas; referências a aliases excluídos são rejeitadas.

Reset exige confirmação e pode limpar uma coleção com fingerprint antigo
incompatível com a configuração atual. Ele remove visibilidade no catálogo
antes de recriar a coleção; modelos e documentos originais são preservados.

A aplicação usa lock de runtime: apenas uma instância por base. Não há
suporte declarado a múltiplos escritores ou serviço distribuído.
