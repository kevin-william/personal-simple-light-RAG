# T06 - Índice persistente com busca por cosseno

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Código implementado; validação externa registrada em docs/validation.md
> **Progresso:** código entregue; critérios externos conforme relatório
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** Codex
> **Dependências:** [T01](t01-configuracao.md), [T05](t05-embeddings.md)
> **Commit único:** `feat(search): add persistent cosine vector store`

## 1. Por que

Estabelecer busca vetorial verificável e impedir mistura de configurações incompatíveis.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

Trecho literal da seção **### 3.5. ChromaDB e cosseno**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.5. ChromaDB e cosseno

- Utilizar cliente persistente e configurar explicitamente a coleção para cosseno pela API da versão fixada do ChromaDB.
- Fornecer os embeddings BGE-M3 calculados pela aplicação tanto na ingestão quanto nas consultas, evitando uma função de embeddings padrão diferente.
- Guardar texto, vetor e metadados: documento, origem, página/linhas, posição, versão e configuração de processamento.
- Exibir distância cosseno ou similaridade `1 - distância` com rótulo correto. Similaridade não é probabilidade nem confiança da resposta.
- Eventual limiar de relevância deve ser calibrado com documentos de teste; não assumir um número universal.
- Operações: adicionar/atualizar, buscar versões ativas, listar fontes, excluir origem/documento e resetar a coleção.
````
<!-- PLAN_EXCERPT_END -->

Trecho literal da seção **### 4.1. Testes automatizados**:

<!-- PLAN_EXCERPT_START -->
````text
### 4.1. Testes automatizados

- Extração de TXT, Markdown e PDF com texto, incluindo metadados e PDF sem texto.
- Divisão: integridade, limites declarados, overlap e entradas longas.
- Embeddings: mesma configuração para documentos/perguntas, normalização e rejeição de incompatibilidades.
- ChromaDB real em diretório temporário: cosseno, ordenação, persistência, CRUD e filtragem de versões ativas.
- Reimportação idempotente, atualização sem chunks antigos, arquivos homônimos, aliases e remoção.
- Falhas simuladas antes/depois da ativação e recuperação após reinício sem perda da versão anterior.
- Download interrompido/arquivo inválido e reutilização do cache válido.
- Memória: somente última mensagem completa, resumo limitado e ausência de histórico completo na requisição de embeddings.
- Resolução contextual: continuações, mudança de assunto, ambiguidade e saída estruturada inválida.
- Orçamento de tokens, template oficial e validação de citações.
````
<!-- PLAN_EXCERPT_END -->

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/rag/vectorstore.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_vectorstore.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Criar cliente persistente com métrica cosseno pela API da versão fixada. Desabilitar embeddings implícitos do Chroma e fornecer vetores calculados.
2. Armazenar texto, posição, versão de conteúdo/processamento e metadados de origem. Persistir fingerprint e rejeitar reabertura/gravação incompatível.
3. Expor add/query/delete/list e retorno de distância com similaridade `1 - distância`. Definir interface para restrições de versões ativas; o catálogo consumidor chega em T08.
4. Não adicionar limiar universal nem tratar similaridade como confiança. Manter as operações úteis/testáveis sem catálogo por meio de restrições explícitas de consulta.

## 5. Testes no mesmo commit

- Integração com Chroma real e vetores determinísticos normalizados: ordenação por cosseno e transformação distância/similaridade.
- Reabrir diretório temporário confirma persistência; CRUD funciona.
- Fingerprint divergente é rejeitado e a função padrão do Chroma não é usada.
- Restrições por versão excluem candidatos e retornam menos que k quando não há resultados.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_vectorstore.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Vetores sintéticos provam métrica e persistência, não relevância semântica do BGE-M3.
- Fora de escopo: ativação de versões e transação coordenada, pertencentes a T08/T09.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Coleção persistente usa cosseno explicitamente.
- [ ] Configuração incompatível não é misturada no índice.
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
