# T04 - Extração e divisão com rastreabilidade de fontes

> **Instruções do projeto:** nenhuma AGENTS.md ou convenção local foi encontrada na inspeção inicial; conferir novamente antes de implementar. [Plano vigente](../implementation_plan.md).
> **Status:** Código implementado; validação externa registrada em docs/validation.md
> **Progresso:** código entregue; critérios externos conforme relatório
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** Codex
> **Dependências:** [T01](t01-configuracao.md), [T02](t02-instalacao-perfis.md)
> **Commit único:** `feat(ingestion): add document extraction and bounded chunks`

## 1. Por que

Transformar arquivos em trechos rastreáveis antes de gastar recursos com embeddings.

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
| Código/configuração propostos | `src/rag/__init__.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/loaders.py` | Criar ou modificar conforme os predecessores |
| Código/configuração propostos | `src/rag/splitter.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_loaders.py` | Criar ou modificar conforme os predecessores |
| Teste proposto | `tests/test_splitter.py` | Criar ou modificar conforme os predecessores |
| Documentação | `README.md` | Criar ou modificar conforme os predecessores |

**Fato verificado:** inicialmente existe somente `implementation_plan.md`, sem código, testes, README ou repositório Git. Os caminhos acima são propostas de implementação; conferir os arquivos criados pelos predecessores antes de alterá-los. Usar funções pytest; nenhuma classe de teste existente foi presumida.

## 4. Como implementar

1. Extrair PDF por página e TXT/Markdown em UTF-8, preservando página/linhas, caminho e cabeçalhos aplicáveis.
2. Descobrir arquivos/pastas recursivamente, com resultado ou erro por arquivo. Identificar PDF vazio e páginas sem texto; informar necessidade de OCR.
3. Dividir recursivamente em caracteres com overlap explícito e preservar origem do trecho. Isolar processamento comum do texto para uso nas consultas de T05.
4. Não truncar nem perder texto silenciosamente. Disponibilizar redivisão de trechos para o limite tokenizado que T05 verificará.

## 5. Testes no mesmo commit

- Fixtures sintéticas TXT/MD/PDF com texto e PDF sem texto; conferir página/linha e relatório.
- UTF-8 inválido, caminho inexistente e erro de leitura não geram documento falso.
- Parágrafos longos, Unicode, vazio e limites/overlap preservam o conteúdo e os metadados.
- Comparar processamento comum de duas entradas iguais sem prefixos específicos por papel.

Testes simulados validam contratos e ramos de erro. Testes de persistência usam os bancos reais em diretórios temporários. Testes com modelos/rede/hardware são opt-in (`integration_models`), devem ser declarados no pytest e têm gates externos: uma execução com skip não constitui aprovação desses gates.

## 6. Comandos de validação

Executar da raiz do projeto, no ambiente virtual do perfil preparado. Estes comandos são **previstos para a implementação**, não foram executados como testes de produção durante a decomposição.

```powershell
python -m pytest tests/test_loaders.py tests/test_splitter.py -q
python -m pytest -m "not integration_models" -q
python -m compileall -q src main.py
python scripts/verify_plan_excerpts.py tasks --plan implementation_plan.md
```

Quando houver cenários opt-in nesta tarefa, executar também os arquivos focados com `-m integration_models` no ambiente real correspondente e guardar o resultado. Gates manuais, como Windows limpo ou avaliação de fundamentação, devem ter registro separado.

## 7. Gates e fora de escopo

- Fixtures são evidência de extração, não de qualidade RAG em documentação real.
- Fora de escopo: OCR, DOCX, reranker e segmentação por outro modelo.

- Não iniciar dependências posteriores para fazer esta tarefa passar; código e testes desta tarefa devem funcionar junto aos predecessores concluídos.
- Atualizar somente documentação diretamente afetada e preservar alterações alheias.

## 8. Critérios de aceitação

- [ ] Chunks respeitam limites em caracteres e mantêm localização.
- [ ] PDF sem texto gera aviso ou falha explícita.
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
