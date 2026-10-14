# T07 - Catálogo transacional de origens, conteúdo e versões

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [T01](t01-configuracao.md)
> **Commit único:** `feat(catalog): add source identities and version lifecycle`

## 1. Por que

Separar identidade da origem e identidade do conteúdo para deduplicação, aliases e ativação transacional.

Uma tarefa corresponde a um único commit com código, testes e documentação diretamente afetada. Os predecessores continuam funcionais se esta tarefa for revertida; funcionalidades consumidoras posteriores devem ser revertidas antes de suas dependências.

## 2. Referencia exata no plano

Plano: [implementation_plan.md](../implementation_plan.md)

Trecho literal da seção **### 3.4. Duplicação, atualização e falhas**:

<!-- PLAN_EXCERPT_START -->
````text
### 3.4. Duplicação, atualização e falhas

- Atribuir `document_id` estável, associando-o ao caminho canônico de origem. Preservar nome amigável separadamente; arquivos de mesmo nome em pastas diferentes são distintos.
- Calcular hash do conteúdo. Reimportar a mesma origem sem alterações deve ser idempotente e não gerar embeddings ou chunks duplicados.
- Reconhecer conteúdo idêntico em caminhos diferentes e reutilizar a versão vetorial, mantendo os aliases de origem no catálogo. Remover um alias não deve apagar conteúdo ainda associado a outra origem.
- Arquivo alterado: criar nova versão em preparação, extrair e gerar todos os embeddings antes de substituir a versão ativa. Usar IDs de chunk determinísticos por documento/conteúdo, versão de processamento e posição.
- Manter catálogo SQLite com estados `pending`, `active` e `failed`, hashes, versões, origens e erros. ChromaDB e catálogo não constituem uma transação única: implementar recuperação explícita.
- Gravar a nova versão no ChromaDB, confirmar completude e só então ativá-la em uma transação do catálogo. Consultas devem aceitar apenas versões ativas, filtrando candidatas e buscando mais resultados quando necessário.
- Após ativação, remover chunks obsoletos sem afetar outras origens. Falha na limpeza deve ser recuperável no próximo início.
- Se leitura, extração, embeddings ou gravação falharem, preservar a versão ativa anterior. Identificar versões incompletas no próximo início e limpar ou retomar de maneira idempotente.
- Processar diretórios por arquivo e apresentar resumo de adicionados, atualizados, ignorados e falhos. Uma falha individual não deve invalidar os demais arquivos.
- Exclusão por `document_id` ou identificador de origem, nunca apenas por nome. Reset exige confirmação explícita na interface.
- Após excluir/atualizar documentos, invalidar referências de memória a evidências antigas e exigir nova recuperação antes de responder sobre esses conteúdos.
````
<!-- PLAN_EXCERPT_END -->

## 3. Arquivos e ações

| Tipo | Arquivo | Ação |
|---|---|---|
| Código/configuração propostos | `src/rag/catalog.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_catalog.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Implementar catálogo SQLite com migração inicial, IDs estáveis de origem por caminho canônico e entidade de conteúdo compartilhada por hash/fingerprint.
2. Origens com conteúdo igual apontam à mesma versão vetorial; fontes homônimas em diretórios diferentes continuam distintas. Esse modelo concilia document_id estável e compartilhamento do conteúdo.
3. Estados pending/active/failed com erros e contagem esperada de chunks. Expor transações de ativação e operações de aliases sem excluir conteúdo ainda referenciado.
4. Registrar geração do catálogo para consumidores invalidarem evidências após alterações. Não apresentar SQLite+Chroma como uma transação única.

## 5. Testes no mesmo commit

- SQLite real: IDs estáveis, caminhos homônimos, hashes, aliases e reabertura.
- Rollback de ativação preserva versão anterior e transições inválidas são rejeitadas.
- Remover alias mantém referências restantes; geração muda apenas em alterações relevantes.
- Separar testes do catálogo de coordenação com Chroma.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_catalog.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Escolha de implementação: entidade de conteúdo compartilhada e geração do catálogo; não são nomes de campos previamente existentes.
- Fora de escopo: extração, gravação de vetores e recuperação entre bancos.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Catálogo representa origens distintas e conteúdo compartilhado.
- [ ] Ativação tem rollback e invariantes testados.
- [ ] Código e configuração desta tarefa implementados e executáveis.
- [ ] Testes deste comportamento incluídos e aprovados no mesmo commit.
- [ ] Documentação diretamente afetada atualizada.
- [ ] Excertos e links validados; dependências anteriores concluídas.
- [ ] Gates externos têm evidência ou bloqueio explícito, sem dados fabricados.
- [ ] Um commit criado com a mensagem prevista, quando houver repositório Git.

---

## Progresso final da implementação

| Item | Status |
|---|---|
| Implementação | Não iniciada |
| Testes | Não iniciados |
| Documentação de uso | Não iniciada |
| Validação real/gates | Pendente |
| Commit | Pendente |

**Progresso geral:** 0%
**Critérios concluídos:** 0/8
**Evidências de execução:** nenhuma; esta entrega decompõe o plano e não implementa a aplicação.
