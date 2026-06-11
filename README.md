## 📋 Sobre o Trabalho

Este trabalho implementa um **chatbot inteligente via Telegram** capaz de auxiliar técnicos e usuários no diagnóstico de falhas em hardware de computadores, combinando **IA Generativa** com **Arquitetura RAG** *(Retrieval-Augmented Generation)*.

O sistema interpreta sintomas descritos em linguagem natural, consulta automaticamente uma base de conhecimento formada por manuais técnicos oficiais dos fabricantes, e gera diagnósticos contextualizados com possíveis causas e testes sugeridos.

---

## 🎯 Problema Abordado

O diagnóstico de hardware é um processo que:

- Exige conhecimento técnico especializado
- Depende fortemente da experiência do técnico
- Possui documentação extensa e dispersa entre fabricantes
- Gera diagnósticos incorretos com frequência, causando troca desnecessária de peças

**Pergunta central:** Como utilizar IA generativa para auxiliar no diagnóstico de falhas em hardware de forma contextualizada e confiável?

---

## 💡 Solução

Um chatbot no Telegram com fluxo guiado de seleção de equipamento e diagnóstico assistido por IA, onde:

1. O usuário seleciona a **marca** e o **modelo** do equipamento via botões interativos
2. Descreve o problema em linguagem natural
3. O sistema recupera trechos relevantes dos manuais técnicos do fabricante via busca vetorial
4. O modelo de linguagem gera um diagnóstico contextualizado, com causas prováveis e testes sugeridos
5. O bot pode fazer perguntas de retorno para afunilar o problema

---

## 🏗️ Arquitetura

```
Usuário (Telegram)
       │
       ▼
   bot.py                        ← Interface Telegram + fluxo de seleção
       │
       ▼
 rag_engine.py                   ← Motor RAG
   ├── ChromaDB                  ← Busca vetorial nos manuais
   │     └── paraphrase-multilingual-MiniLM-L12-v2   (embeddings)
   └── LM Studio API             ← Gemma 3 12B (execução local)
```

**Fluxo de uma mensagem:**

```
Mensagem do usuário
      │
      ▼
Conversão em embedding (vetor numérico)
      │
      ▼
Busca por similaridade no ChromaDB
(recupera os N trechos mais relevantes dos manuais)
      │
      ▼
Injeção do contexto no prompt + histórico da conversa
      │
      ▼
Gemma 3 12B gera o diagnóstico
      │
      ▼
Resposta enviada ao usuário com fontes consultadas
```

---

## 🖥️ Hardware Suportado

| Categoria | Fabricantes | Plataformas |
|-----------|-------------|-------------|
| Placas-mãe Desktop | ASUS, MSI, Gigabyte | AMD AM4 (A520, B450, B550, X570) / Intel LGA1700 (Z690, Z790) |
| Notebooks | Dell | Inspiron |

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Versão | Função |
|---|---|---|
| Python | 3.11 | Backend principal |
| python-telegram-bot | 21.6 | Interface do chatbot |
| LangChain | 0.3.7 | Orquestração RAG |
| ChromaDB | 0.5.18 | Banco vetorial persistente |
| sentence-transformers | 3.2.1 | Modelo de embeddings multilíngue (local) |
| LM Studio | — | Execução local do LLM |
| Gemma 3 12B | — | Modelo de linguagem principal |
| pypdf | 4.3.1 | Extração de texto dos manuais PDF |

---

## 📁 Estrutura do Projeto

```
hardware-rag-bot/
├── bot.py                    ← Ponto de entrada — bot do Telegram
├── ingest.py                 ← Indexação dos PDFs no banco vetorial
├── requirements.txt          ← Dependências Python
├── config/
│   └── settings.py           ← Configurações (token, modelo, parâmetros RAG)
├── src/
│   ├── rag_engine.py         ← Motor RAG (recuperação + geração)
│   ├── session_manager.py    ← Gerenciamento de sessões por usuário
│   └── hardware_catalog.py   ← Catálogo de marcas e modelos suportados
├── data/
│   └── manuals/              ← PDFs dos manuais técnicos (não versionados)
└── vectordb/                 ← Banco vetorial gerado (não versionado)
```

---

## 🚀 Como Executar

### Pré-requisitos

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) com Gemma 3 12B
- Token de bot do Telegram via [@BotFather](https://t.me/BotFather)

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/hardware-rag-bot.git
cd hardware-rag-bot

# 2. Crie e ative o ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Instale as dependências
pip install -r requirements.txt
```

### Configuração

Edite `config/settings.py`:

```python
TELEGRAM_BOT_TOKEN = "seu_token_aqui"
LM_STUDIO_MODEL    = "nome-exato-do-modelo-no-lm-studio"
```

### Execução

```bash
# Apenas na primeira vez (ou ao adicionar novos manuais)
python ingest.py

# Iniciar o bot (LM Studio deve estar ativo com servidor local na porta 1234)
python bot.py
```

---

## 📱 Demonstração do Fluxo

```
/start
  └─► Seleção de marca:  🔵 ASUS  |  🔴 MSI  |  🟠 Gigabyte  |  💻 Dell
        └─► Seleção de modelo:  MAG B550 Tomahawk  |  MAG B550M Mortar  |  ...
              └─► Confirmação do equipamento
                    └─► Chat de diagnóstico livre com contexto dos manuais
```

---

## ⚙️ Parâmetros RAG Configuráveis

| Parâmetro | Descrição | Padrão |
|---|---|---|
| `CHUNK_SIZE` | Tamanho dos trechos indexados (caracteres) | 1000 |
| `CHUNK_OVERLAP` | Sobreposição entre trechos | 200 |
| `TOP_K_RESULTS` | Trechos recuperados por consulta | 5 |
| `SIMILARITY_THRESH` | Limiar mínimo de relevância (0–1) | 0.3 |
| `TEMPERATURE` | Criatividade do modelo (0 = mais preciso) | 0.2 |
| `MAX_HISTORY` | Mensagens mantidas por sessão | 10 |

---

