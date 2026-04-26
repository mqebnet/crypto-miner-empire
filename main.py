"""
CRYPTO MINER EMPIRE v3
Flask (web) + Bot via webhook — sin polling, sin conflictos
"""
import asyncio, logging, os, sys
from flask import Flask, send_file, jsonify, request, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ── ENV ──────────────────────────────────────────────────────
PORT       = int(os.environ.get("PORT", 8080))
BOT_TOKEN  = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.getenv("WEBAPP_URL","").strip().rstrip("/")
WEBHOOK    = f"{WEBAPP_URL}/bot{BOT_TOKEN}" if WEBAPP_URL else ""

# ── FLASK APP ────────────────────────────────────────────────
app = Flask(__name__)

# Register API blueprint
from webapp.api import api
app.register_blueprint(api)

# Security headers on all responses
from webapp.security import apply_cors, apply_headers
@app.after_request
def security(r):
    return apply_headers(apply_cors(r))

@app.before_request
def preflight():
    if request.method == "OPTIONS":
        return Response(status=200)

# ── STATIC ───────────────────────────────────────────────────
INDEX = os.path.join(os.path.dirname(__file__), "webapp", "static", "index.html")

@app.route("/")
def index():
    if os.path.exists(INDEX):
        log.info(f"✅ Serving index.html")
        return send_file(INDEX)
    return ("<html><head>"
            "<script src='https://telegram.org/js/telegram-web-app.js'></script>"
            "</head><body style='background:#06090F;color:#fff;display:flex;"
            "align-items:center;justify-content:center;height:100vh;font-family:sans-serif'>"
            "<h1>⛏️ Crypto Miner Empire</h1></body></html>")

@app.route("/health")
def health():
    return jsonify({"status":"ok","webhook":bool(WEBHOOK)})

# ── WEBHOOK ENDPOINT ─────────────────────────────────────────
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Update, Message, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo, BotCommand, MenuButtonWebApp
)
from aiogram.filters import CommandStart
from services.bot_handlers import router as admin_router

bot = Bot(token=BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp  = Dispatcher(storage=MemoryStorage())
dp.include_router(admin_router)

@dp.message(CommandStart())
async def start(msg: Message):
    from core.database import get_user, create_user
    from core.lang import detect_lang
    from core.strings import t

    uid      = msg.from_user.id
    name     = msg.from_user.first_name or "Miner"
    lang     = detect_lang(msg.from_user.language_code)
    uname    = msg.from_user.username or ""
    existing = get_user(uid)

    # Extraer referido
    ref_by = None
    parts  = msg.text.split()
    if len(parts) > 1:
        try:
            r = int(parts[1].replace("ref_",""))
            if r != uid: ref_by = r
        except: pass

    if not existing:
        create_user(uid, uname, name, lang, ref_by)
        from config import REFERRAL_BONUS
        from core.database import add_coins, update_user, get_user as gu
        if ref_by:
            ref_u = gu(ref_by)
            if ref_u and not ref_u["is_banned"]:
                add_coins(ref_by, REFERRAL_BONUS)
                update_user(ref_by, referrals_count=ref_u["referrals_count"]+1)
                try:
                    rl = ref_u["lang"]
                    await msg.bot.send_message(ref_by,
                        f"👥 *{'¡Nuevo referido!' if rl=='es' else 'New referral!'}*\n"
                        f"+{REFERRAL_BONUS} 🪙", parse_mode="Markdown")
                except: pass

    u = get_user(uid)
    coins = u["coins"] if u else 0
    await msg.answer(
        t("welcome_new" if not existing else "welcome_back",
          lang, name=name, coins=coins)
    )

    # Botón de la app
    if WEBAPP_URL:
        await msg.answer(
            "👇 *Toca para entrar al juego:*",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=t("app_btn", lang),
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]])
        )

@app.route(f"/bot{BOT_TOKEN}", methods=["POST"])
def webhook():
    data   = request.get_json(force=True, silent=True)
    if not data: return "", 400
    update = Update.model_validate(data, context={"bot": bot})
    asyncio.run(dp.feed_update(bot, update))
    return "", 200

# ── STARTUP ──────────────────────────────────────────────────
async def setup():
    from core.database import init_db
    init_db()

    # Eliminar webhook anterior y configurar nuevo
    await bot.delete_webhook(drop_pending_updates=True)

    if WEBHOOK:
        await bot.set_webhook(WEBHOOK, drop_pending_updates=True)
        log.info(f"✅ Webhook: {WEBHOOK[:60]}...")

        # Configurar menú button → abre la app automáticamente
        if WEBAPP_URL:
            try:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="⚡ Abrir App",
                        web_app=WebAppInfo(url=WEBAPP_URL)
                    )
                )
                await bot.set_my_commands([
                    BotCommand(command="start", description="Abrir el juego"),
                ])
                log.info("✅ Menu button configurado — la app se abre automáticamente")
            except Exception as e:
                log.warning(f"⚠️ Menu button: {e}")
    else:
        log.warning("⚠️ WEBAPP_URL no configurada — webhook no activo")

# ── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"🔗 WEBAPP_URL = {WEBAPP_URL or '(no configurada)'}")
    log.info(f"📁 index.html = {'✅ encontrado' if os.path.exists(INDEX) else '❌ NO encontrado'}")

    asyncio.run(setup())

    log.info(f"🌐 Flask en :{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
