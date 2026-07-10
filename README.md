# 🏥 ClinicRAG

> 🤖 Um sistema de RAG (Retrieval-Augmented Generation) para consulta inteligente de Protocolos Clínicos e Diretrizes Terapêuticas (PCDT) do Ministério da Saúde.

🌐 *Read this in [English](./README.md)*

---

## 📖 Sobre o projeto

O **ClinicRAG** é um projeto desenvolvido como desafio do programa de internship em construção de agentes de IA (AI Agentic Builder), em parceria com a **Compass**. O objetivo é aplicar, na prática, todo o ciclo de construção de um sistema de RAG — desde a coleta de dados brutos até uma interface funcional de consulta — utilizando **LLMs rodando localmente via Ollama**, com foco em arquitetura limpa, reprodutibilidade e documentação.

O sistema coleta automaticamente os PDFs de **Protocolos Clínicos e Diretrizes Terapêuticas (PCDT)** disponibilizados publicamente pelo governo brasileiro, processa esse conteúdo, e permite que um usuário faça perguntas em linguagem natural sobre os protocolos, recebendo respostas fundamentadas diretamente nos documentos oficiais.

## 🎯 Objetivo

- 🛠️ Construir um pipeline de RAG completo e funcional, do zero, com boas práticas de engenharia.
- 📚 Aprofundar o entendimento de toda a stack de LLM/IA, da fundamentação teórica até a produção.
- 🧩 Explorar arquitetura modular, containerização e reprodutibilidade via Docker.
- 🎨 Contribuir com diferenciais criativos únicos de cada membro da squad (como modelagem 3D aplicada a interfaces).

## 🧪 Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| 🐍 Linguagem | Python 3.10+ |
| 📥 Coleta de dados | `requests`, `BeautifulSoup4`, `pypdf` |
| 🧠 Orquestração do RAG | `LangChain` |
| 🔍 Embeddings & LLM | `Ollama` (execução local) |
| 🗂️ Base vetorial | `ChromaDB` |
| 💻 Interface | `Streamlit` |
| 🐳 Ambiente | Docker + NVIDIA Container Toolkit (GPU) |

## 🚀 Como executar

O projeto inteiro roda dentro de um container Docker, com Jupyter Lab e Streamlit já configurados.

```bash
cd docker/scripts
bash setup.sh
```

Isso vai construir a imagem, subir o container em segundo plano, e deixar disponíveis:

- 📓 Jupyter Lab → [`http://localhost:8888`](http://localhost:8888)
- 📊 Streamlit → [`http://localhost:8501`](http://localhost:8501)

## 🗂️ Estrutura de pastas

```
clinic-rag/
├── academic/                          👉 projeto principal do desafio
│   ├── data/                          👉 dados em cada estágio do pipeline
│   │   ├── raw/                       📄 PDFs brutos baixados
│   │   ├── processed/                 📄 texto normalizado (JSONL por página)
│   │   ├── chunks/                    ✂️ texto já cortado para embeddings
│   │   └── embeddings/                🔢 vetores gerados
│   ├── eval/                          🧪 avaliação do RAG (LLM as judge)
│   ├── src/                           💻 código-fonte do pipeline
│   │   ├── ingestion/                 📥 coleta e ingestão dos PDFs
│   │   ├── chunking/                  ✂️ divisão do texto em pedaços
│   │   └── embedding/                 🔢 geração de embeddings
│   ├── .env.example                   🔐 modelo de variáveis de ambiente
│   ├── requirements.txt               📦 dependências Python
│   └── README.md                      📘 documentação específica do projeto
├── docker/                            🐳 infraestrutura e automação
│   └── scripts/                       ⚙️ setup.sh e entrypoint.sh
├── CONTRIBUICOES.md                   👥 quem fez o quê + reflexão da squad
└── README.md                          📘 este arquivo
```

Clique nos links abaixo para navegar direto:

- [`academic/`](./academic) — pasta principal do desafio
- [`academic/data/`](./academic/data) — dados brutos, processados, chunks e embeddings
- [`academic/eval/`](./academic/eval) — testes e avaliação do RAG
- [`academic/src/`](./academic/src) — todo o código-fonte do pipeline
- [`academic/requirements.txt`](./academic/requirements.txt) — dependências do projeto
- [`docker/`](./docker) — Dockerfile, docker-compose e scripts de automação
- [`CONTRIBUICOES.md`](./CONTRIBUICOES.md) — contribuição individual de cada membro

## 👥 Equipe

| Membro | Papel |
|---|---|
| 🧭 **Carlos Alberto da Silva Neto** | Líder da Sprint |
| 👨‍💻 Ismael Diógenys dos Santos Correia | Membro da squad |
| 👨‍💻 Brayan Vanz de Oliveira | Membro da squad |
| 👩‍💻 Maria Camila Gonçalves Guimarães | Membro da squad |
| 👨‍💻 Guilherme de Almeida Gama | Membro da squad |
| 👨‍💻 Thiago de Sousa Carvalho | Membro da squad |

📄 Detalhes de contribuição individual estão documentados em [`CONTRIBUICOES.md`](./CONTRIBUICOES.md).

## Acervo Utilizado

O sistema utiliza como base de conhecimento os **Protocolos Clínicos e Diretrizes Terapêuticas (PCDT)** disponibilizados oficialmente pelo **Ministério da Saúde**. Os documentos foram obtidos a partir do portal público de PCDTs (https://www.gov.br/saude/pt-br/assuntos/pcdt), que reúne protocolos organizados por condição clínica e atualizados periodicamente conforme novas evidências científicas e normativas do SUS.

Os PCDTs são documentos normativos que estabelecem critérios para diagnóstico, tratamento, acompanhamento e monitoramento de doenças no âmbito do Sistema Único de Saúde (SUS). Eles definem, entre outros aspectos:

- critérios diagnósticos;
- critérios de inclusão e exclusão de pacientes;
- medicamentos recomendados;
- posologias;
- exames necessários;
- mecanismos de monitoramento clínico;
- critérios para avaliação dos resultados terapêuticos.

As recomendações presentes nesses documentos são fundamentadas em evidências científicas e consideram aspectos de eficácia, segurança, efetividade e custo-efetividade das tecnologias incorporadas ao SUS.

> **Importante:** os PCDTs **não substituem o julgamento clínico do profissional de saúde** e **não devem ser utilizados como ferramenta de diagnóstico clínico**. Seu propósito é padronizar a assistência prestada no SUS, definindo critérios técnicos e administrativos para diagnóstico, tratamento e acompanhamento dos pacientes.

### Tipos de perguntas suportadas

Considerando a natureza dos PCDTs, o sistema foi projetado para responder perguntas fundamentadas exclusivamente nas informações presentes nesses documentos. As principais categorias de consultas são:

#### 1. Elegibilidade e acesso (Quem?)

Perguntas destinadas a identificar quais pacientes têm direito ao tratamento pelo SUS, incluindo critérios de inclusão, critérios de exclusão, contraindicações e requisitos clínicos ou laboratoriais para acesso às terapias.

**Exemplos:**

- Quem pode receber determinado medicamento pelo SUS?
- Quais são os critérios de exclusão do protocolo?
- Em quais situações o tratamento é contraindicado?

#### 2. Conduta terapêutica e linha de cuidado (O que fazer?)

Perguntas relacionadas ao fluxo terapêutico recomendado pelo protocolo, incluindo primeira, segunda e terceira linhas de tratamento, posologias padronizadas, intervenções não farmacológicas e alternativas diante de falha terapêutica.

**Exemplos:**

- Qual é o tratamento de primeira linha?
- Qual medicamento deve ser utilizado após falha terapêutica?
- Qual a dose recomendada para adultos?

#### 3. Resolução diagnóstica (Como comprovar?)

Perguntas sobre os requisitos necessários para confirmação diagnóstica antes do início da terapia, incluindo exames laboratoriais, exames de imagem, critérios clínicos, escalas e códigos CID-10 previstos pelo protocolo.

**Exemplos:**

- Quais exames são necessários para confirmar o diagnóstico?
- Qual CID-10 é utilizado para esta condição?
- Quais critérios laboratoriais são exigidos?

#### 4. Monitoramento, segurança e desfechos (Até quando?)

Perguntas relacionadas ao acompanhamento longitudinal do paciente, monitoramento de efeitos adversos, exames periódicos, critérios de resposta terapêutica e condições que determinam a continuidade ou interrupção do tratamento.

**Exemplos:**

- Com que frequência o paciente deve ser reavaliado?
- Quais exames devem ser realizados durante o tratamento?
- Em quais situações o tratamento deve ser suspenso?

## Aplicação no Contexto da Saúde

Os PCDTs são documentos extensos e altamente estruturados, tornando a localização manual de informações um processo demorado. Um sistema **Retrieval-Augmented Generation (RAG)** permite consultar esse acervo em linguagem natural, recuperando apenas os trechos relevantes para responder às perguntas do usuário.

Essa abordagem pode auxiliar profissionais de saúde e gestores na consulta rápida aos protocolos oficiais do Ministério da Saúde, reduzindo o tempo gasto na busca por informações como critérios de elegibilidade, exames necessários, linhas terapêuticas, posologias e recomendações de monitoramento.

Como as respostas são fundamentadas exclusivamente no conteúdo dos PCDTs e acompanhadas da referência ao documento-fonte, o sistema oferece maior transparência e confiabilidade durante a consulta às diretrizes oficiais.