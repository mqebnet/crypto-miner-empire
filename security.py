import os, time, hmac, hashlib, json, re, functools
from collections import defaultdict
from urllib.parse import unquote
from flask import request, jsonify, g
from config import BOT_TOKEN

# ── 1. VERIFICACIÓN TELEGRAM ─────────────────────────────────
def verify_init_data(init_data: str) -> dict | None:
    if not init_data: return None
    try:
        parsed = {}
        for part in init_data.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                parsed[k] = unquote(v)
        received = parsed.pop("hash", "")
        if not received: return None
        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > 86400: return None
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, received): return None
        return json.loads(parsed.get("user", "{}"))
    except: return None

# ── 2. RATE LIMITING ─────────────────────────────────────────
_rl = defaultdict(list)
LIMITS = {
    "default":          (60, 60),
    "/api/ad/open":     (6, 60),
    "/api/ad/claim":    (6, 60),
    "/api/withdraw":    (3, 3600),
}

def check_rate_limit(uid, endpoint):
    limit, window = LIMITS.get(endpoint, LIMITS["default"])
    now = time.time()
    key = f"{uid}:{endpoint}"
    _rl[key] = [t for t in _rl[key] if now - t < window]
    if len(_rl[key]) >= limit: return False
    _rl[key].append(now)
    return True

# ── 3. CORS ──────────────────────────────────────────────────
ALLOWED_ORIGINS = {
    "https://web.telegram.org",
    "https://k.web.telegram.org",
    "https://z.web.telegram.org",
    "https://webk.telegram.org",
}

def apply_cors(response):
    origin = request.headers.get("Origin","")
    if origin in ALLOWED_ORIGINS or os.getenv("DEV_MODE")=="true":
        response.headers["Access-Control-Allow-Origin"]  = origin or "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Telegram-Init-Data"
    return response

# ── 4. SECURITY HEADERS ──────────────────────────────────────
def apply_headers(response):
    response.headers["X-Frame-Options"]           = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
    response.headers["Server"]                    = "CME/2.0"
    return response

# ── 5. INPUT VALIDATION ──────────────────────────────────────
def validate_email(e):
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', e)) and len(e)<=254

def validate_tg_username(u):
    return bool(re.match(r'^@[a-zA-Z][a-zA-Z0-9_]{4,31}$', u))

def sanitize(s, max_len=500):
    if not isinstance(s, str): return ""
    return re.sub(r'[\x00-\x1f\x7f-\x9f]','',s)[:max_len].strip()

def validate_payment(method, detail):
    if method == "paypal":
        return (True,"") if validate_email(detail) else (False,"Email inválido")
    if method == "usdt":
        return (True,"") if validate_tg_username(detail) else (False,"Username inválido (necesita @)")
    return False, "Método no válido"

# ── 6. SECURE ENDPOINT DECORATOR ────────────────────────────
def secure(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data","")
        if not init_data and os.getenv("DEV_MODE")=="true":
            dev = request.headers.get("X-Dev-User-Id")
            if dev: g.uid = int(dev); return f(*args, **kwargs)
        user_data = verify_init_data(init_data)
        if not user_data:
            return jsonify({"error":"unauthorized"}), 401
        uid = user_data.get("id")
        if not uid:
            return jsonify({"error":"unauthorized"}), 401
        if not check_rate_limit(uid, request.path):
            return jsonify({"error":"rate_limited"}), 429
        g.uid = uid
        return f(*args, **kwargs)
    return wrapper
