| Integrante | Função |
|-----------|--------|
| [Ismael Diogenys](#ismael-diogenys--chunking-e-otimização-de-chunking) | Chunking e Otimização de chunking|
| [Brayan Vanz de Oliveira](#brayan-vanz-de-oliveira--) | Pipeline de RAG (orquestração, recuperação e geração de respostas) |
| [Maria Camila](#maria-camila--) | |
| [Guilherme de Almeida Gama](#guilherme-de-almeida-gama--) |Ingestão e Detecção de respostas insatisfatórias|
| [Carlos Alberto](#carlos-alberto--) | |
| [Thiago de Sousa Carvalho](#thiago-de-sousa-carvalho--) | |




# Ismael Diogenys — Chunking e otimização de chunking

Durante o projeto, fui responsável pelo projeto e implementação da estratégia de chunking utilizada para os Protocolos Clínicos e Diretrizes Terapêuticas (PCDTs), bem como pela avaliação e otimização contínua dessa estratégia. O objetivo principal foi construir chunks que preservassem a estrutura lógica dos documentos e maximizassem a qualidade da recuperação de informação em um sistema Retrieval-Augmented Generation (RAG).

A estratégia adotada foi baseada na estrutura hierárquica dos PCDTs, utilizando seções e subseções como unidades fundamentais de chunking. Para isso, desenvolvi um pipeline capaz de reconstruir os documentos a partir do JSONL, identificar automaticamente a hierarquia de seções por meio da numeração oficial dos documentos, consolidar essa estrutura e gerar chunks semanticamente coerentes. Além disso, implementei uma estratégia de merge para evitar chunks excessivamente pequenos, preservando o contexto clínico sem fragmentar informações relevantes.

Outra contribuição importante foi o desenvolvimento de uma etapa de enriquecimento semântico das seções antes da geração dos chunks finais. Nessa etapa, são extraídos automaticamente os principais conceitos presentes em cada seção por meio de técnicas de extração de candidatos, ranqueamento local e filtragem baseada em IDF calculado sobre todo o corpus. O resultado é um conjunto de entidades semânticas (`semantic_entities`) associado a cada chunk, permitindo enriquecer posteriormente a representação utilizada na recuperação de informação.

A avaliação ocorreu de forma iterativa durante todo o desenvolvimento. Diversos casos de erro foram identificados e corrigidos, principalmente relacionados à detecção incorreta de seções, ao tratamento de enumerações presentes no corpo do texto e à reconstrução dos limites das seções. Um dos problemas mais críticos encontrados foi a interrupção prematura do conteúdo da primeira seção de alguns documentos, ocasionando perda de contexto e geração de chunks inconsistentes. A investigação do pipeline permitiu localizar a origem do problema e corrigir a lógica responsável pela delimitação das seções antes da geração dos chunks.

Além da validação estrutural, também realizei avaliações qualitativas sobre o potencial de recuperação dos chunks produzidos. A principal preocupação foi garantir que cada chunk fosse suficientemente informativo para responder, de forma isolada, ao maior número possível de perguntas clínicas, mantendo ao mesmo tempo um tamanho adequado e uma forte coerência semântica.

Com mais tempo, eu expandiria a etapa de avaliação utilizando métricas quantitativas específicas para Retrieval-Augmented Generation, como Recall@k, MRR (Mean Reciprocal Rank) e nDCG, comparando diferentes estratégias de chunking sobre um conjunto padronizado de perguntas clínicas. Também investigaria estratégias híbridas de chunking, combinando a estrutura hierárquica dos documentos com informações semânticas extraídas automaticamente do texto. Em um contexto clínico, considero que uma RAG pode ser considerada "boa o suficiente" quando demonstra, de forma consistente, alta capacidade de recuperar os trechos corretos para diferentes tipos de consultas, preservando o contexto necessário para apoiar respostas confiáveis e reduzindo significativamente a ocorrência de omissões ou recuperações irrelevantes.

Para mais detalhes sobre minhas contribuições, acessar [README.md](academic/src/chunking/README.md).

# Guilherme de Almeida Gama — Insgestão e Detecção de respostas insatisfatórias

Fiquei responsável pela implementação da ingestão de documentos, que foi dividida em duas partes, a parte de scraping, responsável por baixar os documentos que serão utilizados como base de conhecimento para o RAG e armazena-los no diretório academic/data/raw , e a parte de ingestion, responsável por percorrer todos os arquivos em data/raw e extrair o texto página por página e os metadados associados (source, page e type) para posteriormente salva-los em um arquivo JSONL usado na parte de chunking. Também fiquei responsável pela detecção das respostas insatisfatórias, categorizando em tipos de falhas, causas prováveis, gravidade do erro e ações corretivas

Para mais detalhes sobre minhas contribuições, acessar [README.md](academic/src/ingestion/README.md).
# Brayan Vanz de Oliveira — Pipeline de RAG (orquestração, recuperação e geração de respostas)
 
Durante o projeto, fui responsável pelo pacote `academic/src/rag/`, isto é, por toda a etapa de consulta do sistema: a partir da base vetorial já construída (índice FAISS e metadados dos chunks de PCDT, gerados pelo módulo de embedding), implementei o pipeline completo que recebe a pergunta do usuário, recupera os trechos relevantes e gera uma resposta em português ancorada exclusivamente nesses trechos.
 
O pipeline foi estruturado em etapas modulares e independentes — decomposição da pergunta, recuperação, geração e auto-reflexão —, cada uma isolada em seu próprio módulo (`decomposition.py`, `retrieval.py`, `generation.py`, `reflection.py`) e orquestradas em `pipeline.py`. Optei por decompor perguntas compostas em sub-perguntas objetivas antes da busca, já que perguntas que misturam múltiplos aspectos (por exemplo, critérios diagnósticos e tratamento de uma mesma doença) tendem a recuperar chunks mais relevantes quando cada aspecto é buscado separadamente na base vetorial. Os resultados das sub-perguntas são mesclados com deduplicação por `chunk_id` e limitados a um número máximo de chunks, para não estourar a janela de contexto do LLM.
 
Uma parte importante do meu trabalho foi implementar uma etapa de **auto-reflexão**: depois de gerar a resposta, uma segunda passada do LLM avalia criticamente se os documentos recuperados são relevantes, se a resposta está de fato fundamentada no contexto (sem alucinação) e se ela é completa. Quando essa avaliação indica que uma nova busca provavelmente ajudaria, o pipeline tenta novamente com uma consulta sugerida pelo próprio modelo, respeitando um número máximo de tentativas — o que reduz respostas mal fundamentadas sem custar buscas repetidas desnecessárias (evitei, por exemplo, refazer a mesma consulta quando o modelo não sugere nada de fato diferente, já que a temperatura baixa tornaria o resultado praticamente idêntico).
 
Também dediquei bastante atenção à confiabilidade das saídas estruturadas do LLM: como a decomposição e a auto-reflexão dependem de respostas em JSON válido, e modelos menores rodando localmente via Ollama nem sempre retornam esse JSON de forma limpa, desenvolvi um utilitário genérico (`structured_output.py`) que extrai o bloco JSON da saída bruta, trata o caso em que o modelo "ecoa" o próprio schema em vez de preencher uma instância dele, e tenta uma correção explícita antes de recorrer a um valor padrão seguro. Essa camada evitou que falhas pontuais de formatação do LLM quebrassem o pipeline inteiro, e foi um dos pontos que mais precisou de iteração durante os testes, já que os padrões de erro variavam conforme o modelo e o tamanho do prompt.

Com mais tempo, eu investiria em avaliação quantitativa do pipeline como um todo — não só da recuperação isoladamente, mas da cadeia completa (decomposição + recuperação + geração + reflexão) —, usando um conjunto padronizado de perguntas clínicas com respostas de referência para medir taxa de acerto, fidelidade ao contexto (faithfulness) e frequência de vereditos de baixa confiança. Também exploraria um reranqueamento dos chunks recuperados antes da geração (hoje a ordem é apenas a da recuperação por similaridade) e um cache para consultas repetidas, já que cada pergunta hoje dispara ao menos duas chamadas ao LLM (geração e reflexão), além das chamadas de decomposição. Em um contexto clínico, considero que uma RAG pode ser considerada "boa o suficiente" quando ela é tão criteriosa em admitir o que não sabe quanto em responder o que sabe — ou seja, quando a taxa de respostas fundamentadas é alta, mas principalmente quando os casos em que o contexto é insuficiente são sinalizados de forma confiável e transparente ao usuário, em vez de mascarados por uma resposta genérica ou parcialmente inventada.
 
Para mais detalhes sobre minhas contribuições, acessar [README.md](academic/src/rag/README.md).
