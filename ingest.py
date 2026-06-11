"""
ingest.py  –  Indexa todos os PDFs de data/manuals/ no ChromaDB.
Execute uma vez (ou sempre que adicionar novos manuais):
    python ingest.py
"""

import os
import sys
import time
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent))
from config.settings import (
    MANUALS_DIR, VECTORDB_DIR, CHUNK_SIZE, CHUNK_OVERLAP
)

# ─── Modelo de embeddings local (não precisa de GPU) ────────────────────────
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def load_pdfs(directory: str) -> list:
    """Carrega todos os PDFs de um diretório."""
    docs = []
    pdf_files = list(Path(directory).glob("**/*.pdf"))

    if not pdf_files:
        print(f"⚠️  Nenhum PDF encontrado em '{directory}'")
        return docs

    print(f"📂  {len(pdf_files)} PDF(s) encontrado(s).\n")

    for pdf_path in pdf_files:
        print(f"  📄  Carregando: {pdf_path.name}")
        try:
            loader = PyPDFLoader(str(pdf_path))
            pages  = loader.load()

            # Injeta metadados úteis em cada página
            for page in pages:
                page.metadata["source_file"] = pdf_path.name
                page.metadata["source_dir"]  = str(pdf_path.parent)

            docs.extend(pages)
            print(f"       ✅  {len(pages)} página(s) carregadas.")
        except Exception as e:
            print(f"       ❌  Erro ao carregar {pdf_path.name}: {e}")

    return docs


def split_documents(docs: list) -> list:
    """Divide documentos em chunks para indexação."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP,
        separators    = ["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"\n✂️   {len(chunks)} chunks gerados.")
    return chunks


def build_vectorstore(chunks: list) -> Chroma:
    """Cria / atualiza o banco vetorial ChromaDB."""
    print(f"\n🧠  Carregando modelo de embeddings: {EMBED_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name      = EMBED_MODEL,
        model_kwargs    = {"device": "cpu"},
        encode_kwargs   = {"normalize_embeddings": True},
    )

    print(f"💾  Salvando embeddings em '{VECTORDB_DIR}' …")
    start = time.time()

    vectorstore = Chroma.from_documents(
        documents          = chunks,
        embedding          = embeddings,
        persist_directory  = VECTORDB_DIR,
        collection_name    = "hardware_manuals",
    )

    elapsed = time.time() - start
    print(f"✅  Banco vetorial criado em {elapsed:.1f}s  "
          f"({len(chunks)} vetores armazenados).")
    return vectorstore


def main():
    print("=" * 60)
    print("  Indexador de Manuais – Assistente de Hardware RAG")
    print("=" * 60)

    # 1. Carrega PDFs
    docs = load_pdfs(MANUALS_DIR)
    if not docs:
        sys.exit(1)

    # 2. Divide em chunks
    chunks = split_documents(docs)

    # 3. Gera embeddings e salva no ChromaDB
    build_vectorstore(chunks)

    print("\n🎉  Ingestão concluída! Execute 'python bot.py' para iniciar o bot.")


if __name__ == "__main__":
    main()
