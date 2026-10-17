# Plano de otimização do fluxo RAG

Atualizado em 17/10/2026.

Branch: `codex/otimizacao-fluxo-rag`, criada a partir de `main`, commit `dc79284`.
Estado: implementado e validado em 17/10/2026. Evidências e limites em [optimization_results.md](optimization_results.md).

Este documento substitui as propostas de implementação do diagnóstico anterior. As medições de `performance_correction_plan.md` continuam como referência histórica.

## 1. Resultado esperado e decisões

- Perfil padrão: Phi-4-mini Q8_0 em CUDA/VRAM e BGE-M3 em CPU/RAM, em modo residente.
- Consultas independentes: nenhuma pergunta, resposta, referência ou resumo anterior participa da próxima busca ou geração.
- Prompt da resposta: instruções de sistema existentes, trechos documentais recuperados para a consulta atual e a pergunta atual. Não criar nesta etapa uma interface nova para cadastrar system prompts.
- Exatamente uma chamada de geração ao Phi por consulta respondida com documentos. Busca sem resultados pode responder sem chamar o Phi.
- Sem CUDA ou sem recursos para carregar o Phi no perfil escolhido: informar o problema e orientar `--profile cpu`. Não trocar o backend silenciosamente.
- Manter os modelos, suas revisões, a quantização, os limites de contexto/resposta e a base documental atual. Não é necessária reindexação por trocar o dispositivo do BGE-M3.
- Adotar nesta etapa a remoção da memória do fluxo de execução, sem adicionar um modo conversacional opcional. Essa é a interpretação escolhida para a orientação do usuário de buscar sem guardar contexto.
- Mensagens antigas podem permanecer visíveis na TUI. O histórico visual nunca será enviado ao modelo. A última resposta/fontes poderá ser mantida exclusivamente para exibição.

Fluxo resultante:

```text
Pergunta atual
  -> validar entrada e fontes selecionadas
  -> BGE-M3 na CPU: calcular embedding da pergunta
  -> Chroma: recuperar trechos documentais ativos
  -> montar e validar o orçamento do prompt
  -> Phi na GPU: gerar uma resposta em streaming
  -> finalizar citações e métricas
  -> aguardar outra consulta, preservando os dois modelos carregados
```

## 2. Passo a passo de implementação

### Passo 1 — preservar a referência e registrar as decisões

- Trabalhar na branch já criada; preservar os documentos originais e a base `data/`.
- Na conferência de 17/10, o executável `.venv/Scripts/python.exe` não estava presente. Antes de medir a referência, recriar o ambiente pelo instalador existente com `-Profile cuda -SkipModels`, aproveitando os pesos e caches locais. Não registrar testes como executados até o ambiente estar disponível.
- Incorporar este plano e o diagnóstico histórico à branch, sem versionar pesos, bases de teste ou relatórios com conteúdo privado.
- Preservar os resultados da auditoria em `work/performance-audit/` para comparação. Os cerca de 30–35 tokens/s dos motores isolados e 6 tokens/s do RAG anterior são referências observadas, não metas universais.
- Fazer commits separados para configuração/residência, fluxo independente, concorrência/interfaces e validação/documentação. Nenhum push ou merge faz parte desta etapa.

### Passo 2 — definir o perfil misto e sua seleção

Ponto principal: `src/config.py`.

- Alterar o padrão de embeddings para CPU, mantendo LLM CUDA, `N_GPU_LAYERS=-1` e `MEMORY_MODE=resident`.
- Adicionar `--profile mixed`, que seleciona explicitamente LLM CUDA, embeddings CPU e residência. Manter `--profile cpu` com ambos em CPU e zero camadas na GPU; manter `--profile cuda` como escolha explícita do comportamento legado com ambos em CUDA.
- Perfis explícitos definem os dispositivos; os demais limites continuam configuráveis. Preservar offload parcial positivo configurado em perfis GPU; normalizar zero herdado do perfil CPU para -1 ao selecionar um perfil GPU.
- Sem argumento de perfil, respeitar a configuração explícita por ambiente/arquivo e os novos valores padrão. Preservar a seleção CPU de ambientes instalados como CPU; um marcador antigo CUDA não deve forçar embeddings CUDA quando o usuário não pediu esse perfil.
- Fazer o instalador usar `mixed` por padrão, instalando as mesmas dependências CUDA necessárias ao Phi, e gravar o perfil. Atualizar exemplo de configuração, diagnóstico, status e benchmark para reconhecer `mixed`.
- Status deve apresentar os dispositivos efetivos e a ausência de memória conversacional, sem carregar modelos. Diagnóstico do perfil misto deve exigir suporte CUDA do runtime da LLM, sem exigir embeddings CUDA.

### Passo 3 — corrigir residência e decisões de memória

Ponto principal: `src/models/lifecycle.py`.

- Reutilizar qualquer modelo já carregado. Não carregar antecipadamente no menu, na listagem de documentos ou no status.
- No modo residente, não descarregar o outro modelo automaticamente quando os dispositivos forem diferentes. No perfil misto, carga do BGE em RAM não pode expulsar o Phi da VRAM, nem o inverso.
- Para dispositivos compartilhados, preservar a política legada de residência/expulsão; manter alternância como opção explícita fora do perfil misto.
- Tratar o tamanho dos pesos mais 1 GiB como heurística do comportamento legado, sem usá-lo para garantir que o perfil misto cabe. O carregamento real também aloca contexto e buffers.
- Em falha de memória, liberar recursos parciais da carga que falhou e apresentar erro com componente/dispositivo e orientação. Não mudar backend nem expulsar silenciosamente o modelo do outro dispositivo para tentar novamente.
- Registrar eventos de carga/descarga, duração, componente, dispositivo e motivo, distinguindo encerramento de expulsão por memória.
- Ao encerrar a aplicação, liberar ambos. Depois do aquecimento, uma sequência de consultas não deve gerar cargas ou descargas adicionais no perfil misto.

### Passo 4 — simplificar a consulta para uma única geração

Ponto principal: `src/rag/pipeline.py`.

- Validar pergunta vazia antes de carregar modelos. Usar a pergunta atual, sem reescrita pela LLM, como entrada do BGE-M3.
- Remover `QueryResolver` e `ConversationMemory` da construção e execução do pipeline: nenhuma resolução, resumo, reparo de JSON ou referência herdada entre consultas.
- Manter os módulos legados fora do caminho de execução nesta etapa; não criar uma opção para reativá-los. Adaptar os testes integrados ao contrato independente.
- Simplificar a montagem do prompt para sistema + evidências + pergunta. Remover blocos de contexto conversacional e interpretação contextual; manter escape de tokens especiais, contagem com o template Phi, reserva da resposta e redução segura de trechos.
- Buscar sempre nos documentos para consultas válidas. Frases como “resuma isso” não acessam respostas anteriores nem acionam transformação de histórico.
- Manter filtros de fontes, validação de citações, recusa por ausência de evidência e avisos de truncamento. Lista vazia de fontes significa nenhuma fonte; não convertê-la em busca na base inteira.
- Sem resultados, retornar a mensagem de ausência de evidências sem geração nem resumo. Não apresentar texto produzido pela aplicação como tokens gerados pelo Phi.
- Manter `Answer.resolved_query` igual à pergunta efetivamente consultada e `Answer.summary` vazio para compatibilidade dos relatórios; remover a dependência do benchmark de `pipeline.memory`.
- `clear_memory()` permanece como alias de limpeza do último resultado/fontes; ajustar o texto de `/clear` para refletir isso. A sincronização com alterações do catálogo continua invalidando fontes exibidas.
- Retirar limites de resumo/resolução da configuração e da documentação de uso; configurações antigas no `.env` seguem ignoradas pelo tratamento existente de campos extras.

### Passo 5 — impedir operações concorrentes no mesmo runtime

- Adicionar uma trava reentrante compartilhada pela aplicação, usada por consultas, ingestão, exclusão e reset. Aquisição não bloqueante: outra operação em andamento gera uma mensagem clara e nenhuma modificação parcial.
- Manter a trava durante todo o consumo do streaming e liberá-la em `finally`, inclusive em cancelamento ou erro. A reentrância permite ingestão de pasta chamando ingestão de arquivos na mesma thread.
- Na TUI, desabilitar ações de escrita durante uma resposta e envio de consultas durante ingestão; restaurar os controles em todos os caminhos de saída. O bloqueio central também protege os caminhos que não usam a TUI.
- Fechar o gerador de resposta em `finally` nos dois chats, preservando o texto parcial em caso de cancelamento.

### Passo 6 — medir e apresentar o streaming corretamente

- Exibir separadamente: tempo até o primeiro texto, duração da resposta, tempo total e decode nativo. Não contar eventos de streaming como tokens.
- Medir o intervalo do primeiro ao último fragmento e os intervalos entre entregas; uma taxa por retokenização deve ser identificada como estimativa, não confundida com decode nativo.
- Quando houver apenas mensagem da aplicação ou contadores nativos indisponíveis, mostrar a taxa nativa como indisponível. Preservar ausência de medição de VRAM como ausência, sem substituir por zero.
- Registrar quantidade de chamadas ao Phi, cargas/descargas e tempos de embedding, busca, preparação e geração. O novo fluxo não deve registrar fases de resolução ou resumo.
- Atualizar a TUI a cada 100 ms usando o texto acumulado mais recente e no máximo uma atualização pendente. Eliminar a espera de um callback de desenho por fragmento.
- No chat Rich, limitar reconstrução de Markdown a 100 ms e fazer atualização final completa. Conclusão, falha e cancelamento sempre devem descarregar o buffer visual restante.

### Passo 7 — validar e documentar o novo comportamento

- Executar a suíte funcional com os testes adaptados ao fluxo independente, seguida dos testes com pesos reais na base isolada.
- Medir separadamente motor direto, pipeline, chat do menu e TUI, usando os mesmos prompts documentais e limites. Fazer uma execução fria e pelo menos cinco consultas aquecidas por caminho, sequencialmente, sem outro modelo ocupando a GPU de teste.
- Registrar contadores nativos e intervalos efetivos de entrega. Nas interfaces automatizadas, documentar que o desenho físico do terminal fica fora da medição; conferir também uma execução em terminal real antes de afirmar que o ritmo percebido foi corrigido.
- Comparar medianas e dispersão. Meta local: decode do RAG aquecido de pelo menos 80% da referência direta com prompt equivalente, sem recargas; diferença mediana de duração da resposta com e sem UI de até 10%.
- Atualizar instruções de instalação, perfis, uso sem histórico, limitações e resultados. Os 34 tokens/s anteriores são uma referência experimental; publicar os valores efetivamente medidos após a alteração.

## 3. Testes e critérios de aceite

1. **Configuração:** padrão misto, CPU explícita, CUDA explícita, precedência de configuração, perfis instalados e status sem carga de pesos.
2. **Residência:** testar as duas ordens de carga no perfil misto. Carregar um modelo não chama `unload()` do outro; após aquecer, cinco consultas usam as mesmas instâncias. Erro de memória não troca dispositivos.
3. **Independência:** enviar pergunta A e depois B; embedding e prompt de B não contêm A, sua resposta, resumo ou fontes anteriores. Repetir com mudança de assunto e “resuma isso”.
4. **Chamadas:** uma geração Phi para consulta com documentos; zero para ausência de evidências. Nenhuma chamada estruturada auxiliar, inclusive em falha ou cancelamento.
5. **RAG:** preservar orçamento, escape de marcadores, fontes ativas, aliases, seleção vazia, citações, documentos atualizados/removidos e resposta truncada.
6. **Concorrência:** tentar ingestão, exclusão ou nova consulta durante streaming. Confirmar recusa antes de executar e recuperação normal depois de cancelar ou falhar.
7. **Interfaces/métricas:** fragmentos com vários tokens, mensagens sem LLM, métricas nativas ausentes, atualização final, texto parcial e liberação de controles. Confirmar que o histórico visual não é reenviado.
8. **Medição real:** cumprir residência e metas relativas descritas no passo 7 no computador da auditoria, registrando qualquer diferença de ambiente. Não generalizar resultados para todas as GPUs.

## 4. Limites desta etapa

- Nenhuma alteração de modelo, quantização, revisão dos embeddings, estratégia de divisão ou índice; nenhuma migração para Ollama.
- Não implementar seleção automática de CPU por falha de CUDA, histórico opcional, novos editores de system prompt, ajuste de Flash Attention ou otimização de filtros do Chroma nesta branch.
- Não prometer resolver especificamente o relato de aproximadamente 1 token/s sem reproduzir a pergunta, o corpus e o terminal correspondentes. O critério é medir e corrigir o novo fluxo e registrar seus resultados.
- Implementação e documentação registradas nesta branch. Sem push ou merge; base documental original preservada.
