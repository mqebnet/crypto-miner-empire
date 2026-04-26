# ============================================================
#  config.py — Configuración central
# ============================================================
import os
from dotenv import load_dotenv
load_dotenv()

# ── TELEGRAM ────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
ADMIN_IDS  = [int(x) for x in os.getenv("ADMIN_IDS","0").split(",") if x.strip().isdigit()]
WEBAPP_URL = os.getenv("WEBAPP_URL","").strip().rstrip("/")
BOT_USERNAME = os.getenv("BOT_USERNAME","CryptoMinerEmpireBot")

# ── ECONOMÍA ────────────────────────────────────────────────
COINS_PER_EURO   = 1000
MIN_WITHDRAWAL   = 1000   # 1000 monedas = 1€
WITHDRAW_COOLDOWN_DAYS = 7

# ── ANUNCIOS ────────────────────────────────────────────────
# Objetivo: usuario llega a 1000 monedas en 5-7 días
# 20 ads/día × 7 coins avg = 140 coins/día → ~7 días ✅
ADS_PER_DAY_MAX   = 20
ADS_PER_HOUR_MAX  = 5
AD_COOLDOWN_SEC   = 45    # 45s entre anuncios
AD_MIN_WATCH_SEC  = 30    # 30s mínimo viendo el anuncio
CAPTCHA_EVERY_N   = 3     # captcha cada 3 anuncios

# Redes de anuncios por tipo de usuario
AD_NETWORKS = {
    "new":     {"url": "https://omg10.com/4/10905573",          "name": "Monetag"},
    "active":  {"url": "https://narilyhukelpfulin.com?QH1Uz=1254352", "name": "Admaven"},
    "premium": {"url": "https://www.profitablecpmratenetwork.com/d6fa6mkuf?key=97ddc968a7d79a314ebb856e7338e28a", "name": "Adsterra"},
    "offer":   {"url": "https://checkmyapp.store/cl/i/m53nrm",  "name": "OGAds"},
}

# Recompensas por tipo
AD_REWARDS = {
    "new":     (4, 6),
    "active":  (5, 8),
    "premium": (7, 12),
}

# Bonus por tiempo de visionado
AD_TIME_BONUS = {30: 0, 60: 1, 90: 2, 120: 3}

# ── MINERÍA PASIVA (complemento mínimo) ─────────────────────
# Max ~8 coins/día con nivel 1 — no se puede retirar sin ver ads
MINE_LEVELS = {
    1: {"name_es":"GPU Básica",    "name_en":"Basic GPU",     "cps":0.0001,  "cost":0},
    2: {"name_es":"GPU Gamer",     "name_en":"Gamer GPU",     "cps":0.0003,  "cost":200},
    3: {"name_es":"Granja Minera", "name_en":"Mining Farm",   "cps":0.0008,  "cost":800},
    4: {"name_es":"Data Center",   "name_en":"Data Center",   "cps":0.002,   "cost":3000},
    5: {"name_es":"Super Cluster", "name_en":"Super Cluster", "cps":0.005,   "cost":10000},
}
MINE_MAX_IDLE_H = 8

# ── RACHAS ──────────────────────────────────────────────────
STREAK_BONUS_PER_DAY = 0.03
STREAK_MAX_BONUS     = 0.30
STREAK_MIN_ADS       = 3

DAILY_REWARDS = {1:20, 2:30, 3:50, 4:70, 5:100, 6:130, 7:200}

# ── MISIONES ────────────────────────────────────────────────
MISSIONS = [
    {"id":"ads_5",    "type":"ads",     "req":5,  "reward":50,  "es":"Ver 5 anuncios",          "en":"Watch 5 ads"},
    {"id":"ads_20",   "type":"ads",     "req":20, "reward":100, "es":"Ver 20 anuncios",         "en":"Watch 20 ads"},
    {"id":"upgrade",  "type":"upgrade", "req":1,  "reward":80,  "es":"Mejorar tu mina",         "en":"Upgrade mine"},
    {"id":"invite_1", "type":"referral","req":1,  "reward":100, "es":"Invitar 1 amigo",         "en":"Invite 1 friend"},
    {"id":"streak_3", "type":"streak",  "req":3,  "reward":150, "es":"Racha de 3 días",         "en":"3-day streak"},
    {"id":"streak_7", "type":"streak",  "req":7,  "reward":300, "es":"Racha de 7 días",         "en":"7-day streak"},
    {"id":"withdraw", "type":"withdraw","req":1,  "reward":200, "es":"Primer retiro",           "en":"First withdrawal"},
    {"id":"ads_100",  "type":"ads",     "req":100,"reward":500, "es":"Ver 100 anuncios total",  "en":"Watch 100 ads total"},
]

# ── REFERIDOS ───────────────────────────────────────────────
REFERRAL_BONUS       = 50
REFERRAL_PASSIVE_PCT = 0.03

# ── BOOSTS ──────────────────────────────────────────────────
BOOST_X2_MINS = 10

# ── PAGOS ───────────────────────────────────────────────────
PAYMENT_METHODS = {
    "paypal": {"name":"PayPal","emoji":"💳","min_eur":1.0,
               "note_es":"Email de PayPal verificado","note_en":"Verified PayPal email"},
    "usdt":   {"name":"Telegram Wallet (USDT)","emoji":"💎","min_eur":1.0,
               "note_es":"@username de Telegram Wallet","note_en":"Telegram Wallet @username"},
}

# ── SEGURIDAD ────────────────────────────────────────────────
RISK_BLOCK = 7
RISK_BAN   = 9
SUSPICIOUS_ADS_2H = 15

# ── TEMPORADA ────────────────────────────────────────────────
SEASON_DURATION_DAYS = 30
