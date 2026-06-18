"""
rag_engine.py  –  Motor RAG com filtro RÍGIDO por modelo + fallback
                  para manuais genéricos da marca (Q-LED, POST codes,
                  troubleshooting) quando o manual específico não
                  cobre o sintoma perguntado.
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

SYSTEM_PROMPT = """Você é o DiagnosticAI, um assistente técnico especializado EXCLUSIVAMENTE em diagnóstico de falhas em hardware.

## Diretrizes de Comportamento
1. **Base nos Manuais:** A prioridade absoluta é a informação dos manuais técnicos fornecidos no contexto. Sempre cite a fonte (ex: "Conforme o manual da placa-mãe...").
2. **Concisão e Veracidade:** Nunca invente causas ou testes que não façam sentido lógico. Se o manual não cobrir o problema e você não tiver certeza, seja honesto.
3. **Segurança e Limites:** Avise o usuário imediatamente se uma falha for grave, apresentar risco elétrico ou exigir ferramentas de um técnico especializado.
4. **Vocabulário Adaptável:** Explique os problemas de forma acessível, mas sem perder a precisão técnica.
5. **Foco Estrito:** O escopo é estritamente diagnóstico de hardware. Se o usuário pedir para escrever códigos de programação, fazer cálculos, gerar textos criativos ou falar de assuntos gerais, RECUSE IMEDIATAMENTE. Responda APENAS: "Este assunto está fora do meu escopo. Sou programado exclusivamente para ajudar no diagnóstico de falhas físicas de hardware."

## Estrutura da Resposta
Sempre que aplicável à dúvida do usuário, organize sua resposta de forma clara, utilizando estas seções (omita as que não fizerem sentido para o contexto atual):

🔍 **Diagnóstico Inicial:**
Breve análise técnica do sintoma relatado.

⚠️ **Possíveis Causas:**
Liste as causas lógicas, da mais para a menos provável.

🧪 **Testes Sugeridos:**
Passos práticos e seguros que o usuário pode realizar para isolar o defeito.

💡 **Próximos Passos:**
Recomendações finais. 
MUITO IMPORTANTE: Termine a resposta SEMPRE com uma pergunta objetiva para afunilar o diagnóstico (Ex: "Já realizou algum desses testes? Posso refinar o diagnóstico." ou "Qual exatamente é o comportamento quando você liga?").

Responda sempre em português brasileiro."""

PALAVRAS_HARDWARE = {
    "placa", "mãe", "motherboard", "cpu", "processador", "ram", "memória",
    "memoria", "led", "post", "bios", "uefi", "fonte", "ssd", "hd", "disco",
    "ventoinha", "cooler", "temperatura", "trava", "reinicia", "desliga",
    "não liga", "nao liga", "tela azul", "bsod", "bipe", "beep", "video",
    "vídeo", "monitor", "gpu", "placa de vídeo", "bateria", "carregador",
    "carrega", "notebook", "laptop", "slot", "soquete", "socket", "cmos",
    "drivers", "driver", "superaquec", "lentidão", "lentidao",
    "boot", "inicializa", "liga", "energia", "fan", "dissipador",
}

PALAVRAS_FORA_ESCOPO = {
    "windows", "instalar", "jogo", "joguinho", "receita", "piada", 
    "poema", "filme", "música", "musica", "namorada", "namorado", 
    "política", "politica", "religião", "religiao", "futebol", 
    "programar", "programação", "programacao", "código", "codigo", 
    "python", "java", "javascript", "html", "css", "c++", "sql", 
    "script", "calculadora", "matemática"
}


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
            collection_metadata={"hnsw:space": "cosine"}
        )

        self._llm_client = OpenAI(
            base_url = LM_STUDIO_BASE_URL,
            api_key  = LM_STUDIO_API_KEY,
        )

        self._initialized = True
        count = self._vectorstore._collection.count()
        print(f"✅ RAG Engine pronto  ({count} vetores no banco).")

    # ── Verificação de escopo ────────────────────────────────────────────────

    @staticmethod
    def is_fora_de_escopo(texto: str) -> bool:
        texto_lower = texto.lower()
        tem_termo_fora = any(p in texto_lower for p in PALAVRAS_FORA_ESCOPO)
        tem_termo_hw   = any(p in texto_lower for p in PALAVRAS_HARDWARE)
        return tem_termo_fora and not tem_termo_hw

    # ── Recuperação em duas camadas: modelo específico + genéricos da marca ─

    def _buscar_por_arquivo(
        self,
        resultados: list[tuple[Document, float]],
        palavras: list[str],
        modo: str = "all",
    ) -> list[tuple[Document, float]]:
        """
        Filtra resultados cujo nome de arquivo bate com as palavras-chave.
        modo="all"  → TODAS as palavras devem aparecer no nome (manual específico)
        modo="any"  → BASTA UMA palavra aparecer no nome (manuais genéricos)
        """
        palavras = [p.lower() for p in palavras]

        def bate(doc: Document) -> bool:
            fonte = doc.metadata.get("source_file", "").lower()
            if modo == "all":
                return all(p in fonte for p in palavras)
            return any(p in fonte for p in palavras)

        return [(doc, score) for doc, score in resultados if bate(doc)]

    def retrieve(
        self,
        query: str,
        filtro_palavras: list[str] | None = None,
        genericos_marca: list[str] | None = None,
    ) -> Tuple[List[Document], List[float], str]:
        
        print(f"\n🔍 Buscando por: '{query}'")
        
        docs_encontrados = []
        scores_encontrados = []
        camada_final = "nenhum"

        # ── 1ª camada: manual específico do modelo ────────
        if filtro_palavras:
            nome_esperado = "_".join(p.upper() for p in filtro_palavras) + ".pdf"
            try:
                results_especificos = self._vectorstore.similarity_search_with_relevance_scores(
                    query, 
                    k=TOP_K_RESULTS,
                    filter={"source_file": nome_esperado}
                )
                
                especificos = [(d, s) for d, s in results_especificos if s >= 0.05]
                if especificos:
                    docs, scores = zip(*especificos)
                    docs_encontrados.extend(docs)
                    scores_encontrados.extend(scores)
                    print(f"✅ Encontrado no manual específico: {nome_esperado}")
                    camada_final = "especifico"
            except Exception as e:
                print(f"Aviso na busca específica: {e}")

        # ── 2ª camada: manuais genéricos da marca ────────────────────────────
        if genericos_marca:
            k = max(TOP_K_RESULTS * 10, 50)
            results_gerais = self._vectorstore.similarity_search_with_relevance_scores(query, k=k)
            
            genericos = self._buscar_por_arquivo(results_gerais, genericos_marca, modo="any")
            genericos_validos = [(d, s) for d, s in genericos if s >= 0.01]
            
            if genericos_validos:
                genericos_validos = sorted(genericos_validos, key=lambda x: x[1], reverse=True)[:TOP_K_RESULTS]
                docs, scores = zip(*genericos_validos)
                docs_encontrados.extend(docs)
                scores_encontrados.extend(scores)
                print(f"✅ Encontrado em manuais genéricos")
                
                # Se já tinha achado no específico, a camada vira "misto" para o bot saber
                if camada_final == "especifico":
                    camada_final = "misto"
                else:
                    camada_final = "generico"

        # ── Combina os resultados ───────────────────────────────────────────
        if docs_encontrados:
            # Junta tudo, remove possíveis duplicatas de texto e ordena pelos melhores scores
            resultados_unicos = {}
            for doc, score in zip(docs_encontrados, scores_encontrados):
                if doc.page_content not in resultados_unicos or score > resultados_unicos[doc.page_content][1]:
                    resultados_unicos[doc.page_content] = (doc, score)
            
            misto_ordenado = sorted(resultados_unicos.values(), key=lambda x: x[1], reverse=True)
            
            # Pegamos o dobro de documentos do limite normal para garantir que o contexto seja rico (específico + genérico)
            misto_ordenado = misto_ordenado[:TOP_K_RESULTS * 2] 
            
            docs_finais, scores_finais = zip(*misto_ordenado)
            return list(docs_finais), list(scores_finais), camada_final

        print("⚠️ Nenhum trecho alcançou os critérios mínimos.")
        return [], [], "nenhum"
    
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
                f"Foque o diagnóstico exclusivamente neste equipamento."
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
        genericos_marca: list[str] | None = None,
        modelo_desc: str | None = None,
    ) -> dict:
        self.initialize()

        if history is None:
            history = []

        # ── Bloqueio de escopo (antes de gastar tokens com o LLM) ──────────
        if self.is_fora_de_escopo(user_message):
            return {
                "answer": (
                    "Esse assunto está fora do escopo deste assistente. "
                    "Eu posso ajudar apenas com diagnóstico de falhas no "
                    f"equipamento selecionado{f' ({modelo_desc})' if modelo_desc else ''}.\n\n"
                    "Descreva um sintoma ou problema técnico do hardware."
                ),
                "sources": [],
                "has_context": False,
                "camada": "bloqueado",
                "blocked": True,
            }

        docs, scores, camada = self.retrieve(
            user_message,
            filtro_palavras = filtro_rag,
            genericos_marca = genericos_marca,
        )
        context  = self._build_context(docs, scores)
        messages = self._build_messages(context, history, user_message, modelo_desc)

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
            "camada":      camada,
            "blocked":     False,
        }
