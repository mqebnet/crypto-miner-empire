# ============================================================
#  services/bot_handlers.py — Solo comandos admin del bot
#  Todo el juego está en la webapp
# ============================================================
import time
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS
import core.database as db

router = Router()

def is_admin(uid): return uid in ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id): return
    stats = db.get_stats()
    from core.strings import t
    await msg.answer(t("admin_stats","es",**stats), parse_mode="Markdown")

@router.message(Command("pending"))
async def cmd_pending(msg: Message):
    if not is_admin(msg.from_user.id): return
    from core.keyboards import admin_wd_keyboard
    wds = db.get_pending_withdrawals()
    if not wds: return await msg.answer("✅ Sin retiros pendientes.")
    for w in wds:
        name = w["first_name"] or w["username"] or str(w["user_id"])
        method_raw = w["method"] or ""
        detail = method_raw.split(":",1)[1] if ":" in method_raw else "—"
        method_name = method_raw.split(":",1)[0] if ":" in method_raw else method_raw
        await msg.answer(
            f"💸 *Retiro #{w['id']}*\n"
            f"👤 {name} (`{w['user_id']}`)\n"
            f"💶 *{w['amount_eur']:.2f}€*\n"
            f"💳 {method_name}: `{detail}`",
            parse_mode="Markdown",
            reply_markup=admin_wd_keyboard(w["id"]))

@router.message(Command("user"))
async def cmd_user(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: return await msg.answer("Uso: /user <user_id>")
    try:
        uid = int(parts[1])
        u   = db.get_user(uid)
        if not u: return await msg.answer("❌ No encontrado.")
        with db.db() as c:
            ads1h = c.execute("SELECT COUNT(*) FROM ad_log WHERE user_id=? AND timestamp>?",
                              (uid, time.time()-3600)).fetchone()[0]
            total_wd = c.execute("SELECT COALESCE(SUM(amount_eur),0) FROM withdrawals WHERE user_id=? AND status='paid'",
                                 (uid,)).fetchone()[0]
        await msg.answer(
            f"👤 *{uid}* — {u['first_name']}\n"
            f"💰 {u['coins']:.1f}🪙 · Tipo: {u['user_type']}\n"
            f"⛏️ Mina Nv.{u['mine_level']} · Racha {u['streak']}d\n"
            f"📺 Ads hoy: {u['ads_today']} · Última hora: {ads1h}\n"
            f"📊 Total ads: {u['total_ads']} · Retirado: {total_wd:.2f}€\n"
            f"⚠️ Risk: {u['risk_score']}/10 · Susp: {'Sí' if u['is_suspicious'] else 'No'}\n"
            f"🚫 Baneado: {'Sí' if u['is_banned'] else 'No'}",
            parse_mode="Markdown")
    except ValueError:
        await msg.answer("ID inválido.")

@router.message(Command("suspicious"))
async def cmd_suspicious(msg: Message):
    if not is_admin(msg.from_user.id): return
    with db.db() as c:
        users = c.execute("SELECT user_id,first_name,risk_score FROM users WHERE is_suspicious=1 AND is_banned=0 ORDER BY risk_score DESC LIMIT 20").fetchall()
    if not users: return await msg.answer("✅ Sin sospechosos.")
    text = "⚠️ *Sospechosos:*\n\n"
    for u in users:
        text += f"• `{u['user_id']}` {u['first_name']} — *{u['risk_score']}/10*\n"
    await msg.answer(text, parse_mode="Markdown")

@router.message(Command("economy"))
async def cmd_economy(msg: Message):
    if not is_admin(msg.from_user.id): return
    s = db.get_stats()
    est_revenue = s["ads_24h"] * 0.008
    await msg.answer(
        f"📈 *ECONOMÍA*\n━━━━━━━━━━━━\n"
        f"📺 Ads 24h: *{s['ads_24h']}*\n"
        f"💰 Ingreso est. 24h: *{est_revenue:.2f}€*\n"
        f"💶 Total pagado: *{s['paid_eur']:.2f}€*",
        parse_mode="Markdown")

@router.message(Command("ban"))
async def cmd_ban(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: return await msg.answer("Uso: /ban <id>")
    try:
        uid = int(parts[1])
        db.update_user(uid, is_banned=1, ban_reason="Manual")
        await msg.answer(f"🚫 `{uid}` baneado.", parse_mode="Markdown")
    except: await msg.answer("ID inválido.")

@router.message(Command("unban"))
async def cmd_unban(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: return await msg.answer("Uso: /unban <id>")
    try:
        uid = int(parts[1])
        db.update_user(uid, is_banned=0, is_suspicious=0, risk_score=0, ban_reason="")
        await msg.answer(f"✅ `{uid}` desbaneado.", parse_mode="Markdown")
    except: await msg.answer("ID inválido.")

from aiogram.types import CallbackQuery
from aiogram import F as AiF

@router.callback_query(AiF.data.startswith("adm_pay:"))
async def cb_pay(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer()
    wid = int(cb.data.split(":")[1])
    db.process_withdrawal(wid, "paid", "Pagado")
    await cb.message.edit_text(f"✅ Retiro #{wid} *pagado*.", parse_mode="Markdown")
    await cb.answer("✅")

@router.callback_query(AiF.data.startswith("adm_rej:"))
async def cb_rej(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer()
    wid = int(cb.data.split(":")[1])
    db.process_withdrawal(wid, "rejected", "Rechazado")
    await cb.message.edit_text(f"❌ Retiro #{wid} *rechazado*.", parse_mode="Markdown")
    await cb.answer("❌")
