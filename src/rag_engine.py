"""
rag_engine.py  –  Motor RAG com suporte a filtro por modelo de hardware.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from openai import OpenAI

from config.settings import (
    VECTORDB_DIR, LM_STUDIO_BASE_URL, LM_STUDIO_MODEL, LM_STUDIO_API_KEY,
    TOP_K_RESULTS, SIMILARITY_THRESH, MAX_TOKENS, TEMPERATURE,
)

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

SYSTEM_PROMPT = """Você é um assistente técnico especializado em diagnóstico de falhas em hardware de computadores.

Seu papel é ajudar técnicos e usuários a identificar e resolver problemas de hardware com base em:
- Sintomas descritos pelo usuário
- Documentação técnica oficial dos fabricantes (manuais, troubleshooting guides)
- Seu conhecimento técnico especializado

## Diretrizes de comportamento

1. **Diagnóstico guiado**: Faça perguntas objetivas para afunilar o problema antes de dar o diagnóstico final.
2. **Base nos manuais**: Sempre que o contexto técnico estiver disponível, cite a fonte (ex: "Conforme o manual da MSI B550...").
3. **Estrutura clara**: Organize suas respostas com seções bem definidas (Diagnóstico, Possíveis Causas, Testes Sugeridos).
4. **Tom profissional e acessível**: Use linguagem técnica, mas explique termos complexos para iniciantes.
5. **Honestidade**: Se não tiver certeza, diga claramente e sugira buscar suporte especializado.
6. **Foco no hardware**: Não responda perguntas fora do escopo de diagnóstico do equipamento selecionado.

Responda sempre em português brasileiro."""


class RAGEngine:

    def __init__(self):
        self._embeddings  = None
        self._vectorstore = None
        self._llm_client  = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        print("🔧 Inicializando RAG Engine…")

        self._embeddings = HuggingFaceEmbeddings(
            model_name    = EMBED_MODEL,
            model_kwargs  = {"device": "cpu"},
            encode_kwargs = {"normalize_embeddings": True},
        )

        if not Path(VECTORDB_DIR).exists():
            raise FileNotFoundError(
                f"Banco vetorial não encontrado em '{VECTORDB_DIR}'. "
                "Execute 'python ingest.py' primeiro."
            )

        self._vectorstore = Chroma(
            persist_directory  = VECTORDB_DIR,
            embedding_function = self._embeddings,
            collection_name    = "hardware_manuals",
        )

        self._llm_client = OpenAI(
            base_url = LM_STUDIO_BASE_URL,
            api_key  = LM_STUDIO_API_KEY,
        )

        self._initialized = True
        count = self._vectorstore._collection.count()
        print(f"✅ RAG Engine pronto  ({count} vetores no banco).")

    # ── Recuperação com filtro opcional ─────────────────────────────────────

    def retrieve(
        self,
        query: str,
        filtro_palavras: list[str] | None = None,
    ) -> Tuple[List[Document], List[float]]:
        """
        Busca trechos relevantes. Se filtro_palavras for fornecido,
        reordena os resultados priorizando chunks que mencionam
        as palavras-chave do modelo selecionado.
        """
        # Busca mais resultados quando há filtro para ter margem de reordenação
        k = TOP_K_RESULTS * 3 if filtro_palavras else TOP_K_RESULTS

        results = self._vectorstore.similarity_search_with_relevance_scores(query, k=k)
        filtered = [(doc, score) for doc, score in results if score >= SIMILARITY_THRESH]

        if not filtered:
            return [], []

        # Reordena: chunks que batem com o filtro do modelo ficam no topo
        if filtro_palavras:
            palavras = [p.lower() for p in filtro_palavras]

            def score_filtro(item):
                doc, sim = item
                texto = (doc.page_content + doc.metadata.get("source_file", "")).lower()
                hits  = sum(1 for p in palavras if p in texto)
                return (hits, sim)   # ordena por hits desc, depois por similaridade

            filtered.sort(key=score_filtro, reverse=True)
            filtered = filtered[:TOP_K_RESULTS]

        docs, scores = zip(*filtered)
        return list(docs), list(scores)

    # ── Prompt ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_context(docs, scores) -> str:
        if not docs:
            return ""
        parts = ["## Trechos relevantes dos manuais técnicos\n"]
        for i, (doc, score) in enumerate(zip(docs, scores), 1):
            source = doc.metadata.get("source_file", "desconhecido")
            page   = doc.metadata.get("page", "?")
            parts.append(
                f"### Fonte {i}: {source}  (pág. {page}  |  relevância: {score:.0%})\n"
                f"{doc.page_content.strip()}\n"
            )
        return "\n".join(parts)

    @staticmethod
    def _build_messages(context, history, user_message, modelo_desc) -> list[dict]:
        system = SYSTEM_PROMPT
        if modelo_desc:
            system += (
                f"\n\n## Equipamento selecionado pelo usuário\n"
                f"**{modelo_desc}**\n"
                f"Foque o diagnóstico exclusivamente neste equipamento. "
                f"Se o usuário perguntar sobre outro hardware não suportado, "
                f"redirecione gentilmente para o equipamento selecionado."
            )

        messages = [{"role": "system", "content": system}]
        if context:
            messages.append({"role": "system", "content": f"Use quando relevante:\n\n{context}"})
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    # ── Geração ──────────────────────────────────────────────────────────────

    def generate(
        self,
        user_message: str,
        history: list[dict] | None = None,
        filtro_rag: list[str] | None = None,
        modelo_desc: str | None = None,
    ) -> dict:
        self.initialize()

        if history is None:
            history = []

        docs, scores = self.retrieve(user_message, filtro_palavras=filtro_rag)
        context      = self._build_context(docs, scores)
        messages     = self._build_messages(context, history, user_message, modelo_desc)

        response = self._llm_client.chat.completions.create(
            model       = LM_STUDIO_MODEL,
            messages    = messages,
            max_tokens  = MAX_TOKENS,
            temperature = TEMPERATURE,
        )

        answer  = response.choices[0].message.content.strip()
        sources = list({doc.metadata.get("source_file", "desconhecido") for doc in docs})

        return {
            "answer":      answer,
            "sources":     sources,
            "has_context": bool(docs),
        }
