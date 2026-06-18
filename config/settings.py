# ============================================================
#  Configurações do Assistente de Hardware via RAG
# ============================================================

# --- Telegram ---
TELEGRAM_BOT_TOKEN = ""  

# --- LM Studio (Gemma 3 12B rodando localmente) ---
LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
LM_STUDIO_MODEL    = "gemma-3-12b"       
LM_STUDIO_API_KEY  = "lm-studio"         # qualquer string; LM Studio não valida

# --- RAG ---
CHUNK_SIZE        = 1000   # tamanho dos chunks de texto
CHUNK_OVERLAP     = 200    # sobreposição entre chunks
TOP_K_RESULTS     = 5      # quantos trechos recuperar por consulta
SIMILARITY_THRESH = 0.2    # limiar mínimo de similaridade (0-1)

# --- Caminhos ---
MANUALS_DIR  = "data/manuals"   # coloque seus PDFs aqui
VECTORDB_DIR = "vectordb"      

# --- LLM ---
MAX_TOKENS   = 1024
TEMPERATURE  = 0.2  

# --- Bot ---
MAX_HISTORY  = 10    # mensagens mantidas por sessão (memória do bot)
