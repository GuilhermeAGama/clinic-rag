# `rag/` — Pacote de resposta a perguntas sobre os PCDT

Este pacote implementa o pipeline de **Retrieval-Augmented Generation (RAG)** que responde, em português, perguntas dos usuários com base nos **Protocolos Clínicos e Diretrizes Terapêuticas (PCDT)** do Ministério da Saúde.

Ele **não constrói** sua própria base vetorial: consome os artefatos já gerados pelos módulos `ingestion`, `chunking` e `embedding` do projeto — em particular o índice FAISS e os metadados dos chunks produzidos por `embedding/create_vector_db.py`. O pacote `rag` cuida exclusivamente da etapa de **consulta**: dado um índice já pronto, ele decompõe a pergunta, recupera os trechos relevantes, gera uma resposta ancorada nesses trechos e avalia criticamente essa resposta antes de devolvê-la ao usuário.

## Visão geral do fluxo

```
pergunta do usuário
    -> decomposição em sub-perguntas               (decomposition.py)
    -> recuperação (FAISS) por sub-pergunta
       + deduplicação e formatação do contexto      (retrieval.py, vector_store.py)
    -> geração da resposta, ancorada no contexto     (generation.py)
    -> auto-reflexão (documentos relevantes?
       resposta fundamentada e completa?)            (reflection.py)
    -> se necessário e dentro do limite de tentativas,
       nova busca + nova geração                     (pipeline.py)
    -> resposta final, com metadados de transparência
       (fontes, sub-perguntas, resultado da reflexão)
```

Esse fluxo é o padrão de **RAG com auto-correção (self-reflective RAG)**: em vez de gerar uma única resposta "às cegas", o sistema critica seu próprio resultado e, se identificar que uma nova busca provavelmente ajudaria, tenta novamente — dentro de um limite de tentativas — antes de responder ao usuário.

## Estrutura do pacote

| Módulo | Responsabilidade |
|---|---|
| `__init__.py` | Ponto de entrada público do pacote (`answer_question`, `build_pipeline`). |
| `config.py` | Configuração central: caminhos, nomes de modelo e parâmetros do pipeline. |
| `llm.py` | Fábrica do LLM (`ChatOllama`) usado em todas as etapas. |
| `vector_store.py` | Carregamento do índice FAISS + metadados e o retriever sobre eles. |
| `prompts.py` | Todos os prompts (em português) usados no pipeline. |
| `decomposition.py` | Decomposição da pergunta original em sub-perguntas. |
| `retrieval.py` | Recuperação por sub-pergunta, deduplicação e formatação do contexto. |
| `generation.py` | Geração da resposta final ancorada no contexto. |
| `reflection.py` | Auto-reflexão crítica sobre documentos e resposta gerados. |
| `structured_output.py` | Utilitário genérico para obter JSON estruturado e válido de um LLM local. |
| `pipeline.py` | Orquestração de todas as etapas acima; ponto central do pacote. |
| `cli.py` | Interface de linha de comando simples para testar o pipeline interativamente. |

A seguir, cada módulo é detalhado.

---

## `config.py`

Centraliza toda a configuração do pacote, para que caminhos, nomes de modelo e parâmetros fiquem definidos em um único lugar e sejam importados (`from rag import config`) pelos demais módulos.

Principais constantes:

- **Caminhos de dados**: `CHUNKS_PATH`, `VECTOR_STORE_INDEX_PATH` (`index.faiss`) e `VECTOR_STORE_METADATA_PATH` (`metadata.jsonl`), todos relativos a `academic/data/`.
- **Modelos**: `EMBEDDING_MODEL_NAME` (`bge-m3`, padrão) e `LLM_MODEL_NAME` (`qwen3.5:4b`, padrão), servidos via Ollama (`OLLAMA_BASE_URL`).
- **Parâmetros do LLM**: `LLM_TEMPERATURE` (0.2), `LLM_NUM_CTX` (janela de contexto, padrão 8192) e `LLM_NUM_PREDICT` (tokens máximos gerados, padrão 2048).
- **Parâmetros de recuperação**: `RETRIEVAL_TOP_K` (chunks recuperados por sub-pergunta, padrão 5), `MAX_CONTEXT_CHUNKS` (limite de chunks únicos enviados ao LLM, padrão 5) e `MAX_SUBQUESTIONS` (máximo de sub-perguntas geradas, padrão 4).
- **Controle de novas tentativas**: `MAX_REFLECTION_RETRIES` (quantas vezes o pipeline pode buscar de novo após a auto-reflexão apontar um problema, padrão 1).

Todos os parâmetros numéricos podem ser sobrescritos por variáveis de ambiente (ex.: `RETRIEVAL_TOP_K=8`), sem necessidade de alterar código. O módulo também garante que `academic/src` esteja no `sys.path`, permitindo importar o pacote a partir de diferentes pontos de entrada (ex.: `cli.py`, notebooks, testes).

---

## `llm.py`

Fábrica única do LLM usado por todo o pipeline (`get_llm`), evitando que cada módulo instancie o `ChatOllama` com parâmetros divergentes.

```python
def get_llm(model_name: str | None = None, temperature: float | None = None) -> ChatOllama
```

Retorna uma instância de `ChatOllama` configurada com o modelo e o `base_url` definidos em `config.py`, `reasoning=False` e os limites `num_ctx`/`num_predict` também vindos da configuração. `model_name` e `temperature` podem ser sobrescritos pontualmente (útil em testes), mas em uso normal a temperatura deve permanecer baixa para manter respostas determinísticas e fiéis aos documentos recuperados.

---

## `vector_store.py`

Responsável por **carregar** (não construir) a base vetorial FAISS gerada por `embedding/create_vector_db.py`, e por expor um retriever LangChain sobre ela.

- **`get_embeddings()`**: instancia `OllamaEmbeddings` com o modelo `bge-m3`, usado para vetorizar a pergunta do usuário no momento da busca (os chunks já foram vetorizados na etapa de embedding, fora deste pacote).
- **`load_vector_store(index_path, metadata_path)`**: lê o índice FAISS (`faiss.read_index`) e os metadados dos chunks (`metadata.jsonl`, um JSON por linha). Se os arquivos não existirem, levanta `FileNotFoundError` com instrução de como gerá-los (`python -m embedding.create_vector_db`). Também emite um aviso caso o número de vetores do índice não bata com o número de registros de metadados — sinal de que os artefatos podem vir de execuções diferentes.
- **`FaissChunkRetriever`**: um `BaseRetriever` do LangChain construído sobre o índice FAISS bruto (`IndexFlatIP`, com vetores normalizados — produto interno equivale a similaridade de cosseno). Em `_get_relevant_documents`, vetoriza a query, normaliza (`faiss.normalize_L2`), busca os `k` vizinhos mais próximos e monta `Document`s do LangChain com metadados ricos: `chunk_id`, `source`, `section_number`, `section_titles`, `page_start`/`page_end`, `document_type` e o score de similaridade.
- **`get_retriever(vector_store, k, embeddings)`**: função de conveniência que monta um `FaissChunkRetriever` a partir do dicionário retornado por `load_vector_store`.

---

## `prompts.py`

Concentra **todos** os prompts do pipeline (em português do Brasil), como `ChatPromptTemplate` do LangChain, separados por etapa:

- **`ANSWER_PROMPT`**: prompt de geração da resposta final. O prompt de sistema (`ANSWER_SYSTEM_PROMPT`) estabelece regras rígidas: responder sempre em português, usar **exclusivamente** o contexto fornecido (sem conhecimento médico geral do modelo), admitir explicitamente quando a informação não está disponível, não fazer recomendações clínicas não respaldadas pelo contexto, e deixar claro que a resposta não substitui julgamento clínico profissional.
- **`DECOMPOSITION_PROMPT`**: pede ao LLM que decomponha a pergunta original em até `MAX_SUBQUESTIONS` sub-perguntas objetivas e autossuficientes (ex.: critérios diagnósticos, tratamento medicamentoso, acompanhamento etc.), retornando **apenas** um JSON válido no formato descrito por `format_instructions`.
- **`REFLECTION_PROMPT`**: pede ao LLM que avalie criticamente, com base apenas no que foi fornecido (pergunta, contexto e resposta gerada), se os documentos são relevantes, se a resposta está fundamentada e se é completa — também retornando apenas um JSON estruturado.

Manter os prompts isolados em um único módulo facilita ajustes e revisão, sem tocar na lógica dos demais componentes.

---

## `decomposition.py`

Implementa a etapa de **query decomposition**: perguntas compostas (ex.: *"Quais os critérios diagnósticos e o tratamento de primeira linha para a Doença de Gaucher?"*) tendem a recuperar documentos melhores quando quebradas em sub-perguntas mais objetivas, buscadas separadamente na base vetorial.

- **`SubQuestions`** (modelo Pydantic): lista de 1 a `MAX_SUBQUESTIONS` sub-perguntas.
- **`decompose_question(llm, question, max_subquestions)`**: invoca o LLM via `invoke_structured` (ver `structured_output.py`) usando `DECOMPOSITION_PROMPT`. Se a pergunta já for simples, o próprio prompt instrui o modelo a retorná-la como única sub-pergunta. Em caso de falha na saída estruturada, o `default` usado é `SubQuestions(sub_questions=[question])` — ou seja, a pergunta original nunca deixa de ser coberta. A função também filtra strings vazias e trunca a lista em `max_subquestions` como salvaguarda adicional, sempre retornando pelo menos uma sub-pergunta.

---

## `retrieval.py`

Cuida da recuperação de chunks relevantes para o conjunto de sub-perguntas e da formatação do contexto enviado ao LLM.

- **`retrieve_for_subquestions(retriever, sub_questions, max_context_chunks)`**: para cada sub-pergunta, chama `retriever.invoke(...)` e mescla os resultados, removendo duplicatas por `chunk_id` (ou pelo conteúdo do chunk, como fallback) — já que sub-perguntas diferentes podem recuperar o mesmo trecho. Falhas de recuperação em uma sub-pergunta são logadas e não interrompem as demais. O resultado final é limitado a `max_context_chunks` chunks únicos, para controlar o tamanho do contexto enviado ao LLM.
- **`format_documents_for_prompt(documents, max_chars_per_chunk=2000)`**: formata os documentos recuperados em blocos de texto legíveis (`[Trecho N] Fonte: ... | Seção: ...`), identificando claramente a origem de cada trecho — o que também permite ao LLM citar a fonte na resposta. Cada trecho é truncado em `max_chars_per_chunk` caracteres: como alguns chunks de PCDT são bem maiores que a média, sem esse limite um único trecho grande poderia consumir sozinho boa parte da janela de contexto (`num_ctx`) do LLM, causando respostas cortadas — especialmente em modelos menores. Se nenhum documento for encontrado, retorna uma mensagem padrão indicando isso.

---

## `generation.py`

Implementa a geração da resposta final, estritamente ancorada no contexto recuperado.

- **`generate_answer(llm, question, context_text)`**: monta a cadeia `ANSWER_PROMPT | llm`, invoca com a pergunta e o contexto já formatado (por `format_documents_for_prompt`), e retorna o texto da resposta (`result.content`), sem processamento adicional — toda a lógica de "responder só com base no contexto" está no prompt de sistema, não neste módulo.

---

## `reflection.py`

Implementa a etapa de **auto-reflexão (self-reflection)**: uma segunda passada do LLM, agora no papel de revisor crítico, que avalia a qualidade da recuperação e da resposta geradas nas etapas anteriores.

- **`ReflectionResult`** (modelo Pydantic): contém `documentos_relevantes` (bool), `resposta_fundamentada` (bool — uma resposta que corretamente diz "não sei" também conta como fundamentada), `resposta_completa` (bool), `veredito` e `justificativa`. O campo `veredito` é um `Literal` com três valores possíveis:
  - `"satisfatorio"` — está tudo certo;
  - `"contexto_insuficiente"` — os documentos não bastam, mas a resposta já reflete isso honestamente (não adianta buscar de novo);
  - `"necessita_nova_busca"` — uma nova recuperação com outra consulta provavelmente ajudaria.

  Quando o veredito é `"necessita_nova_busca"`, o campo opcional `consulta_sugerida` traz uma nova consulta de busca sugerida pelo próprio LLM.

- **`reflect_on_answer(llm, question, context_text, answer)`**: invoca `REFLECTION_PROMPT` via `invoke_structured`. Se a auto-reflexão falhar (ex.: o LLM não retorna um JSON válido mesmo após a tentativa de correção), o `default` usado é conservador — marca a resposta como **não** fundamentada/completa e veredito `"necessita_nova_busca"` — priorizando sinalizar baixa confiança em vez de assumir sucesso silenciosamente.

---

## `structured_output.py`

Utilitário genérico (usado tanto por `decomposition.py` quanto por `reflection.py`) para obter **saídas estruturadas em JSON** de um LLM local via Ollama de forma robusta, já que modelos menores nem sempre retornam JSON perfeitamente formatado.

- **`invoke_structured(llm, prompt, pydantic_model, prompt_variables, default)`**: monta um `PydanticOutputParser` para o `pydantic_model` desejado, vincula o schema JSON ao LLM (`llm.bind(format=schema)`) e invoca a cadeia `prompt | structured_llm`. Antes de fazer o parsing, aplica duas camadas de tolerância a erros:
  - **`_extract_json_block`**: extrai o maior bloco `{...}` da saída bruta do modelo, tolerando texto extra antes/depois do JSON.
  - **`_unwrap_schema_echo`**: alguns modelos pequenos "ecoam" o JSON Schema (com as chaves `properties`/`required`) em vez de gerar uma instância dele; essa função detecta esse padrão e extrai os valores reais de dentro de `properties`.

  Se o parsing ainda assim falhar, a função faz **uma segunda tentativa**, enviando ao LLM um prompt de correção explícito pedindo para reenviar apenas o JSON no formato esperado. Se a segunda tentativa também falhar, o erro é logado e a função retorna o valor de `default` fornecido pelo chamador — garantindo que uma saída malformada do LLM nunca derrube o pipeline.

---

## `pipeline.py`

Módulo central de orquestração: conecta todas as etapas acima em um fluxo único, com suporte a novas tentativas guiadas pela auto-reflexão.

- **`RAGComponents`** (`dataclass`): agrupa `llm` e `retriever` já inicializados, para serem reutilizados entre chamadas (evita recarregar o índice FAISS e o LLM a cada pergunta).
- **`build_pipeline(index_path, metadata_path, top_k)`**: carrega a base vetorial (`load_vector_store`), monta o retriever (`get_retriever`) e instancia o LLM (`get_llm`), retornando um `RAGComponents` pronto para uso repetido.
- **`_sources_from_documents(documents)`** (privada): extrai, de uma lista de `Document`, uma lista deduplicada de fontes (`source` + `section`, concatenando os títulos de seção) para exibição ao usuário.
- **`_run_single_attempt(components, question, search_query)`** (privada): executa **uma** passada completa do pipeline — decomposição, recuperação, geração e reflexão — usando `search_query` (ou a própria pergunta) como base para a decomposição/recuperação. É reutilizada tanto na primeira tentativa quanto nas tentativas subsequentes.
- **`answer_question(question, components=None, max_retries=config.MAX_REFLECTION_RETRIES)`**: função pública principal do pacote.
  1. Valida que a pergunta não é vazia.
  2. Se `components` não for informado, chama `build_pipeline()` sob demanda (útil para uso pontual, mas ineficiente em loops — a documentação da própria função recomenda reutilizar componentes via `build_pipeline`).
  3. Executa a primeira tentativa (`_run_single_attempt`).
  4. Enquanto o veredito da auto-reflexão for `"necessita_nova_busca"` e o número de tentativas não tiver excedido `max_retries`: verifica se a `consulta_sugerida` é de fato diferente da última consulta usada — como a temperatura é baixa, repetir exatamente a mesma consulta produziria (na prática) o mesmo resultado, então o pipeline só tenta de novo se houver uma consulta genuinamente nova; caso contrário, encerra o laço e marca a resposta como baixa confiança.
  5. Retorna um dicionário com `answer`, `question`, `sub_questions`, `sources` (via `_sources_from_documents`), `reflection` (o `ReflectionResult` serializado com `model_dump()`), `low_confidence` (`True` se o veredito final não for `"satisfatorio"`) e `attempts` (quantas passadas foram executadas).

Esse desenho dá ao usuário final não só a resposta, mas **metadados de transparência**: quais sub-perguntas foram usadas, quais fontes embasaram a resposta, e um sinal explícito de quando o sistema não está confiante no resultado — importante em um domínio clínico, onde uma resposta com baixa confiança deve ser tratada com mais cautela do que uma resposta plenamente fundamentada.

---

## `cli.py`

Interface de linha de comando simples para testar o pipeline interativamente, sem precisar de uma API ou front-end.

Uso:

```bash
cd academic/src
python -m rag.cli
```

O `main()` inicializa o pipeline uma única vez (`build_pipeline()`) e entra em um loop que lê perguntas do terminal, chama `answer_question(question, components=components)` reutilizando os mesmos componentes, e imprime a resposta formatada (`_print_result`) — incluindo a lista de fontes consultadas e um aviso visível (`⚠️`) quando `low_confidence` é `True`. Digitar `sair`, `exit` ou `quit` (ou `Ctrl+C`/EOF) encerra o programa.

---

## `__init__.py`

Expõe a API pública do pacote:

```python
from rag import answer_question

resultado = answer_question("Qual o tratamento de primeira linha para X?")
print(resultado["answer"])
```

Reexporta apenas `answer_question` e `build_pipeline` (`__all__`), mantendo os demais módulos como detalhes internos de implementação, acessíveis via import explícito (`from rag.retrieval import ...`) quando necessário.

---

## Como usar o pacote

**Pré-requisito**: a base vetorial já deve ter sido construída (`python -m embedding.create_vector_db`), gerando `index.faiss` e `metadata.jsonl` em `academic/data/embeddings/`.

**Uso pontual:**

```python
from rag import answer_question

resultado = answer_question("Quais os critérios diagnósticos da Doença de Gaucher?")
print(resultado["answer"])
print(resultado["sources"])
```

**Uso em loop (reaproveitando LLM e índice já carregados):**

```python
from rag import build_pipeline, answer_question

components = build_pipeline()
for pergunta in perguntas:
    resultado = answer_question(pergunta, components=components)
    ...
```

**Via linha de comando:**

```bash
cd academic/src
python -m rag.cli
```

## Configuração via variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `EMBEDDING_MODEL_NAME` | `bge-m3` | Modelo de embeddings (Ollama). |
| `LLM_MODEL_NAME` | `qwen3.5:4b` | Modelo de linguagem (Ollama). |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Endereço do servidor Ollama. |
| `LLM_NUM_CTX` | `8192` | Janela de contexto do LLM. |
| `LLM_NUM_PREDICT` | `2048` | Máximo de tokens gerados por resposta. |
| `RETRIEVAL_TOP_K` | `5` | Chunks recuperados por sub-pergunta. |
| `MAX_CONTEXT_CHUNKS` | `5` | Máximo de chunks únicos usados como contexto. |
| `MAX_SUBQUESTIONS` | `4` | Máximo de sub-perguntas geradas na decomposição. |
| `MAX_REFLECTION_RETRIES` | `1` | Máximo de novas tentativas guiadas pela auto-reflexão. |