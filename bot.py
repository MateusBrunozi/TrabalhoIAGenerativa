import logging
import sys
from pathlib import Path

from telegram import (
    Update, BotCommand,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from telegram.constants import ChatAction, ParseMode

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import TELEGRAM_BOT_TOKEN, VECTORDB_DIR
from src.rag_engine import RAGEngine
from src.session_manager import SessionManager
from src.hardware_catalog import (
    CATALOG, get_marcas, get_modelos, get_modelo_info, get_filtro_rag, get_genericos_marca,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format   = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt  = "%Y-%m-%d %H:%M:%S",
    level    = logging.INFO,
    handlers = [logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)
logger = logging.getLogger("hardware_bot")

rag     = RAGEngine()
session = SessionManager()


# ════════════════════════════════════════════════════════════════════════════
#  Teclados inline
# ════════════════════════════════════════════════════════════════════════════

def teclado_marcas() -> InlineKeyboardMarkup:
    """Uma linha por marca."""
    botoes = [
        [InlineKeyboardButton(label, callback_data=f"marca:{chave}")]
        for chave, label in get_marcas()
    ]
    return InlineKeyboardMarkup(botoes)


def teclado_modelos(marca: str) -> InlineKeyboardMarkup:
    """Grade de modelos da marca (2 por linha) + botão Voltar.
    Usa índice numérico no callback_data para não estourar o limite de 64 bytes do Telegram.
    """
    modelos = get_modelos(marca)
    linhas  = []
    for i in range(0, len(modelos), 2):
        par = modelos[i : i + 2]
        linhas.append([
            InlineKeyboardButton(label, callback_data=f"md:{i+j}")
            for j, (chave, label) in enumerate(par)
        ])
    linhas.append([InlineKeyboardButton("⬅️ Voltar às marcas", callback_data="voltar:marcas")])
    return InlineKeyboardMarkup(linhas)


def teclado_confirmacao(idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar", callback_data=f"ok:{idx}"),
        InlineKeyboardButton("🔄 Escolher outro", callback_data="voltar:marcas"),
    ]])


# ════════════════════════════════════════════════════════════════════════════
#  Comandos
# ════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session.clear(chat_id)
    user = update.effective_user

    await update.message.reply_text(
        f"👋 Olá, {user.first_name}!\n\n"
        "🔧 Assistente de Diagnóstico de Hardware\n\n"
        "Selecione a marca do equipamento para começar:",
        reply_markup  = teclado_marcas(),
    )


async def cmd_novo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session.clear(chat_id)

    await update.message.reply_text(
        "Nova sessão iniciada. Selecione a marca do equipamento:",
        reply_markup = teclado_marcas(),
    )


async def cmd_ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos\n\n"
        "/start  – Apresentação\n"
        "/novo   – Reinicia e escolhe novo equipamento\n"
        "/ajuda  – Esta mensagem\n"
        "/status – Status do sistema\n\n"
        "Dicas para um bom diagnóstico:\n"
        "• Descreva os sintomas com detalhes\n"
        "• Mencione LEDs acesos, beeps ou códigos\n"
        "• Responda as perguntas de retorno do bot",
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    s = session.get_or_create(chat_id)

    try:
        rag.initialize()
        count     = rag._vectorstore._collection.count()
        db_status = f"✅ Online ({count:,} vetores)"
    except Exception as e:
        db_status = f"❌ Erro: {e}"

    hw = s.modelo_desc if s.modelo_desc else "Nenhum selecionado"

    await update.message.reply_text(
        "📊 Status do Sistema\n\n"
        f"🗄️ Base de conhecimento: {db_status}\n"
        f"🖥️ Equipamento ativo: {hw}\n"
        f"💬 Mensagens na sessão: {len(s.historico)}\n"
        f"🤖 Modelo: Gemma 3 12B (LM Studio)",
    )


# ════════════════════════════════════════════════════════════════════════════
#  Callbacks dos botões inline
# ════════════════════════════════════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = query.message.chat_id
    data    = query.data

    await query.answer()   # remove o "loading" do botão

    # ── Seleção de marca ────────────────────────────────────────────────────
    if data.startswith("marca:"):
        marca = data.split(":", 1)[1]
        if marca not in CATALOG:
            await query.edit_message_text("❌ Marca inválida. Use /novo para recomeçar.")
            return

        session.set_marca(chat_id, marca)
        info = CATALOG[marca]
        tipo = "🖥️ Placa-mãe desktop" if info["tipo"] == "desktop" else "💻 Notebook"

        await query.edit_message_text(
            f"{info['emoji']} {info['label']}  |  {tipo}\n\nAgora selecione o modelo do equipamento:",
            reply_markup = teclado_modelos(marca),
        )

    # ── Seleção de modelo (por índice numérico) ─────────────────────────────
    elif data.startswith("md:"):
        idx = int(data.split(":", 1)[1])
        s   = session.get_or_create(chat_id)

        if not s.marca:
            await query.edit_message_text("❌ Selecione a marca primeiro. Use /novo.")
            return

        modelos = get_modelos(s.marca)
        if idx >= len(modelos):
            await query.edit_message_text("❌ Modelo inválido. Use /novo para recomeçar.")
            return

        modelo_chave, _ = modelos[idx]
        info_modelo      = get_modelo_info(s.marca, modelo_chave)
        marca_info       = CATALOG[s.marca]

        # Salva o índice temporariamente na sessão para usar na confirmação
        s.modelo = modelo_chave

        await query.edit_message_text(
            f"🔍 Confirmar equipamento?\n\n"
            f"{marca_info['emoji']} {info_modelo['desc']}\n\n"
            f"Este assistente irá focar o diagnóstico neste modelo.",
            reply_markup = teclado_confirmacao(idx),
        )

    # ── Confirmação ─────────────────────────────────────────────────────────
    elif data.startswith("ok:"):
        idx = int(data.split(":", 1)[1])
        s   = session.get_or_create(chat_id)

        if not s.marca:
            await query.edit_message_text("❌ Erro na seleção. Use /novo.")
            return

        modelos     = get_modelos(s.marca)
        if idx >= len(modelos):
            await query.edit_message_text("❌ Erro na seleção. Use /novo.")
            return

        modelo_chave, _ = modelos[idx]
        info_modelo      = get_modelo_info(s.marca, modelo_chave)
        filtro           = get_filtro_rag(s.marca, modelo_chave)
        marca_info       = CATALOG[s.marca]

        session.set_modelo(chat_id, modelo_chave, info_modelo["desc"], filtro)

        await query.edit_message_text(
            f"✅ Equipamento selecionado!\n\n"
            f"{marca_info['emoji']} {info_modelo['desc']}\n\n"
            f"Agora descreva o problema em linguagem natural.\n\n"
            f"Exemplo: \"O computador não liga e há um LED vermelho na placa-mãe.\"",
        )

    # ── Voltar às marcas ────────────────────────────────────────────────────
    elif data.startswith("voltar:marcas"):
        session.clear(chat_id)
        await query.edit_message_text(
            "Selecione a marca do equipamento:",
            reply_markup = teclado_marcas(),
        )


# ════════════════════════════════════════════════════════════════════════════
#  Mensagens de texto (diagnóstico)
# ════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id   = update.effective_chat.id
    user_text = update.message.text.strip()
    s         = session.get_or_create(chat_id)

    if not user_text:
        return

    # ── Bloqueia se hardware ainda não selecionado ──────────────────────────
    if s.estado != "ativo":
        await update.message.reply_text(
            "⚠️ Selecione o equipamento antes de começar.\n\n"
            "Use os botões abaixo para escolher a marca:",
            reply_markup = teclado_marcas(),
        )
        session.clear(chat_id)   # reseta para garantir estado limpo
        return

    logger.info("[%d] %s | %s | %.80s…",
                chat_id, s.marca, s.modelo, user_text)

    await ctx.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    history = session.get_history(chat_id)

    try:
        result = rag.generate(
            user_message    = user_text,
            history         = history,
            filtro_rag      = s.filtro_rag,
            genericos_marca = get_genericos_marca(s.marca),
            modelo_desc     = s.modelo_desc,
        )

        answer      = result["answer"]
        sources     = result["sources"]
        has_context = result["has_context"]
        blocked     = result.get("blocked", False)

        camada = result.get("camada", "nenhum")

        footer = ""
        if blocked:
            footer = ""  # mensagem de bloqueio já é autoexplicativa
        elif has_context and sources:
            srcs   = "\n".join(f"  • {src}" for src in sources)
            
            # Checa qual foi a camada utilizada para ajustar o texto do rodapé
            if camada == "especifico":
                footer = f"\n\n📚 Fontes consultadas (manual específico):\n{srcs}"
            elif camada == "generico":
                footer = f"\n\nℹ️ Manual específico não detalhou esse sintoma. Usei manuais genéricos da marca:\n{srcs}"
            elif camada == "misto":
                footer = f"\n\n📚 Fontes consultadas (manuais específicos e genéricos combinados):\n{srcs}"
            else:
                footer = f"\n\n📚 Fontes consultadas:\n{srcs}"
                
        else:
            footer = (
                f"\n\n⚠️ Nenhum manual (específico ou genérico) "
                f"foi encontrado para este sintoma. "
                f"Resposta baseada apenas no conhecimento geral do modelo."
            )

        # Não salva no histórico se foi bloqueado por escopo (evita poluir contexto)
        if not blocked:
            session.add_message(chat_id, "user",      user_text)
            session.add_message(chat_id, "assistant", answer)

        full_response = answer

        # Envia a resposta da IA dividida em blocos de até 4000 caracteres
        while len(full_response) > 0:
            if len(full_response) <= 4000:
                chunk = full_response
                full_response = ""
            else:
                # Tenta quebrar na última quebra de linha antes do limite
                cut_index = full_response.rfind('\n', 0, 4000)
                if cut_index == -1:
                    cut_index = full_response.rfind(' ', 0, 4000)
                if cut_index == -1:
                    cut_index = 4000
                
                chunk = full_response[:cut_index]
                full_response = full_response[cut_index:].lstrip()

            await update.message.reply_text(chunk)

        # Envia o rodapé (footer) como uma mensagem final separada
        if footer:
            await update.message.reply_text(footer.strip())

    except ConnectionError:
        await update.message.reply_text(
            "❌ LM Studio inacessível.\n\n"
            "Verifique se o servidor local está ativo na porta 1234 "
            "com o modelo carregado.",
        )
    except Exception as e:
        logger.exception("Erro no chat %d", chat_id)
        await update.message.reply_text(
            f"❌ Erro inesperado.\n\n{type(e).__name__}: {e}\n\n"
            "Use /novo para reiniciar a sessão.",
        )


# ════════════════════════════════════════════════════════════════════════════
#  Inicialização
# ════════════════════════════════════════════════════════════════════════════

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start",  "Iniciar / apresentação"),
        BotCommand("novo",   "Escolher novo equipamento"),
        BotCommand("ajuda",  "Lista de comandos"),
        BotCommand("status", "Status do sistema"),
    ])
    try:
        rag.initialize()
    except FileNotFoundError as e:
        logger.warning("⚠️  %s  – Execute 'python ingest.py'.", e)


def main():
    if TELEGRAM_BOT_TOKEN == "SEU_TOKEN_AQUI":
        print("❌  Configure o TELEGRAM_BOT_TOKEN em config/settings.py")
        sys.exit(1)

    print("🚀 Iniciando Assistente de Hardware via RAG…")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("novo",   cmd_novo))
    app.add_handler(CommandHandler("ajuda",  cmd_ajuda))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot em execução. Aguardando mensagens…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
