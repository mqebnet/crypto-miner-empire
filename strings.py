S = {
"welcome_new":{"es":"⛏️ *CRYPTO MINER EMPIRE*\n━━━━━━━━━━━━━━━━\n\n🎮 *¡Bienvenido!*\n\n⚡ Ve anuncios → gana monedas\n⛏️ Tu mina produce sola\n💸 1.000 monedas = *1€ real*\n\n✅ *Verificado · Paga · Serio*\n\n👇 Pulsa el botón para jugar","en":"⛏️ *CRYPTO MINER EMPIRE*\n━━━━━━━━━━━━━━━━\n\n🎮 *Welcome!*\n\n⚡ Watch ads → earn coins\n⛏️ Your mine produces passively\n💸 1,000 coins = *€1 real money*\n\n✅ *Verified · Pays · Serious*\n\n👇 Tap the button to play"},
"welcome_back":{"es":"👋 *¡De vuelta, {name}!*\n\n⛏️ Tu mina ha estado trabajando.\n💰 Monedas: *{coins:.0f} 🪙*","en":"👋 *Welcome back, {name}!*\n\n⛏️ Your mine has been working.\n💰 Coins: *{coins:.0f} 🪙*"},
"app_btn":{"es":"⚡ ABRIR CRYPTO MINER EMPIRE","en":"⚡ OPEN CRYPTO MINER EMPIRE"},
"admin_stats":{"es":"📊 *ADMIN*\n━━━━━━━━━━━━\n👤 Usuarios: *{total_users}*\n🆕 Hoy: *{new_today}*\n📅 Activos: *{active_today}*\n💸 Pendientes: *{pending_wd}*\n💶 Pagado: *{paid_eur:.2f}€*\n📺 Ads 24h: *{ads_24h}*\n⚠️ Sospechosos: *{suspicious}*\n🚫 Baneados: *{banned}*\n\n_/pending /user /suspicious /economy /ban_","en":"📊 *ADMIN*\n━━━━━━━━━━━━\n👤 Users: *{total_users}*\n🆕 Today: *{new_today}*\n📅 Active: *{active_today}*\n💸 Pending: *{pending_wd}*\n💶 Paid: *€{paid_eur:.2f}*\n📺 Ads 24h: *{ads_24h}*\n⚠️ Suspicious: *{suspicious}*\n🚫 Banned: *{banned}*\n\n_/pending /user /suspicious /economy /ban_"},
}

def t(key, lang, **kw):
    entry = S.get(key, {})
    text  = entry.get(lang) or entry.get("es", f"[{key}]") if isinstance(entry,dict) else entry
    try: return text.format(**kw) if kw else text
    except: return text
