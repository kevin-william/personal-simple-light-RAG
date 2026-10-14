# T05 - BGE-M3 normalizado para documentos e perguntas

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Código implementado; validação externa registrada em docs/validation.md
> **Progresso:** código entregue; critérios externos conforme relatório
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** Codex
> **Dependências:** [T02](t02-instalacao-perfis.md), [T03](t03-download-modelos.md), [T04](t04-extracao-chunks.md)
> **Commit único:** `feat(embeddings): add consistent normalized BGE-M3 encoding`

## 1. Por que

Fornecer um contrato único de vetores válido para cosseno, com execução CUDA ou CPU explícita.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

Trecho literal da seção **### 3.3. Extração, divisão e embeddings**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.3. Extração, divisão e embeddings

- PDF: preservar arquivo, página e total de páginas. Detectar páginas sem texto e registrar avisos; não indexar silenciosamente um PDF vazio.
- TXT/Markdown: leitura UTF-8, preservando caminho, intervalo de linhas e cabeçalhos quando possível. Informar falhas de codificação e leitura.
- Divisão recursiva por parágrafos, linhas e frases, respeitando os limites em **caracteres** declarados na configuração. Não descrever esse procedimento como segmentação semântica por modelo.
- Validar que cada trecho cabe no limite de entrada configurado do BGE-M3; dividir novamente em vez de truncar silenciosamente.
- Centralizar limpeza e normalização do texto. Não aplicar prefixos ou instruções distintos aos embeddings de perguntas e documentos.
- Gerar embeddings com `normalize_embeddings=True`, verificando dimensão, valores finitos e vetores válidos.
- Registrar a configuração de embeddings e de divisão no índice. Mudanças incompatíveis exigem nova indexação; não misturar embeddings de configurações diferentes.
````
<!-- PLAN_EXCERPT_END -->

Trecho literal da seção **## 2. Decisões técnicas**:

<!-- PLAN_EXCERPT_START -->
````text
## 2. Decisões técnicas

1. **Linguagem e runtime:** Python com `llama-cpp-python`, carregando o GGUF no processo da aplicação. GPU NVIDIA/CUDA é o padrão; CPU é opcional.
2. **LLM:** repositório `unsloth/Phi-4-mini-instruct-GGUF`, arquivo **`Phi-4-mini-instruct.Q8_0.gguf`**. Fixar uma revisão validada do repositório antes do lançamento.
3. **Embeddings:** `BAAI/bge-m3` via `sentence-transformers`/PyTorch. CUDA padrão e CPU opcional. Usar embeddings densos com normalização L2.
4. **Busca:** ChromaDB persistente com métrica **cosseno explicitamente configurada**. Mesmo modelo, revisão, normalização e processamento de texto para documentos e perguntas.
5. **Formatos:** PDF com texto extraível, TXT e Markdown. Detectar PDFs sem texto e informar que precisam de OCR; OCR não faz parte do MVP.
6. **Interfaces:** Rich e `prompt_toolkit`, com chat e gerenciamento de documentos separados no menu. Fontes detalhadas acessíveis por comando.
7. **Memória:** manter somente a última mensagem completa do diálogo; as anteriores são incorporadas pela LLM a um resumo muito enxuto. Não manter uma janela com cinco rodadas completas.
8. **Continuações:** a LLM deve interpretar o contexto, resolver referências e produzir uma pergunta independente e um fragmento contextual mínimo. Nunca enviar todo o histórico ao embedder.
9. **Distribuição:** preparação automatizada, versões fixadas e pacotes pré-compilados validados. O usuário não deve precisar compilar C++ no caminho de instalação suportado.
````
<!-- PLAN_EXCERPT_END -->

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/models/embeddings.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/splitter.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_embeddings.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Carregar SentenceTransformer pela revisão/cache configurados somente quando necessário; permitir liberação explícita.
2. Usar limpeza comum e `normalize_embeddings=True` para perguntas e documentos, sem instruções/prefixos divergentes.
3. Checar limite real de tokens antes de encode: redividir documentos longos e rejeitar pergunta excessiva com mensagem clara, evitando truncamento silencioso.
4. Validar dimensão, norma, valores finitos e vetores não nulos. Gerar fingerprint da configuração/revisão/divisão para o índice e lotes configuráveis com erro de memória acionável.

## 5. Testes no mesmo commit

- Encoder simulado prova identidade do processamento, normalização, batching e escolha de dispositivo.
- Rejeitar vetores inválidos e verificar redivisão por limite tokenizado.
- Teste opt-in com BGE-M3 real: dimensão/norma esperadas, cache offline e execução CPU.
- Teste opt-in em NVIDIA verifica dispositivo CUDA real e não apenas disponibilidade de torch.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_embeddings.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Gate externo: cache real dos modelos e hardware NVIDIA para validar aceleração.
- Fora de escopo: embeddings esparsos, ColBERT e alternância conjunta da LLM, tratada em T11.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Mesmo contrato gera os embeddings de documentos e perguntas.
- [ ] Nenhuma entrada longa é truncada silenciosamente.
- [x] Código e configuração desta tarefa implementados e executáveis.
- [x] Testes deste comportamento incluídos e aprovados no mesmo commit.
- [x] Documentação diretamente afetada atualizada.
- [x] Excertos e links validados; dependências anteriores concluídas.
- [ ] Gates externos têm evidência ou bloqueio explícito, sem dados fabricados.
- [x] Um commit criado com a mensagem prevista, quando houver repositório Git.

---

## Progresso final da implementação

| Item | Status |
|---|---|
| Implementação | Implementada |
| Testes | Automatizados aprovados; modelos reais conforme relatório |
| Documentação de uso | Atualizada |
| Validação real/gates | Pendente |
| Commit | Commit desta tarefa |

**Progresso geral:** código entregue; gates reais pendentes/conforme relatório
**Critérios concluídos:** 5/8 (gates reais avaliados no relatório)
**Evidências de execução:** pytest focado, compileall e verificador literal aprovados neste commit. Validações de hardware/modelos em `docs/validation.md`; skips não são aprovação.
