# ============================================================
#  core/database.py
# ============================================================
import sqlite3, time, json
from contextlib import contextmanager
from datetime import date
from config import *

DB_PATH = "miner.db"

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id           INTEGER PRIMARY KEY,
            username          TEXT DEFAULT '',
            first_name        TEXT DEFAULT '',
            lang              TEXT DEFAULT 'es',
            coins             REAL DEFAULT 0,
            mine_level        INTEGER DEFAULT 1,
            last_collect      REAL DEFAULT 0,
            ads_today         INTEGER DEFAULT 0,
            ads_reset_date    TEXT DEFAULT '',
            ads_hour_count    INTEGER DEFAULT 0,
            ads_hour_start    REAL DEFAULT 0,
            last_ad_time      REAL DEFAULT 0,
            last_ad_open      REAL DEFAULT 0,
            total_ads         INTEGER DEFAULT 0,
            streak            INTEGER DEFAULT 0,
            streak_ads_today  INTEGER DEFAULT 0,
            last_streak_date  TEXT DEFAULT '',
            daily_day         INTEGER DEFAULT 0,
            last_daily_date   TEXT DEFAULT '',
            boost_type        TEXT DEFAULT '',
            boost_until       REAL DEFAULT 0,
            total_earned      REAL DEFAULT 0,
            season_coins      REAL DEFAULT 0,
            referral_by       INTEGER DEFAULT NULL,
            referrals_count   INTEGER DEFAULT 0,
            completed_missions TEXT DEFAULT '[]',
            risk_score        INTEGER DEFAULT 0,
            fast_clicks       INTEGER DEFAULT 0,
            is_suspicious     INTEGER DEFAULT 0,
            is_banned         INTEGER DEFAULT 0,
            ban_reason        TEXT DEFAULT '',
            user_type         TEXT DEFAULT 'new',
            created_at        REAL DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS withdrawals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            amount_coins  REAL NOT NULL,
            amount_eur    REAL NOT NULL,
            method        TEXT DEFAULT 'paypal',
            status        TEXT DEFAULT 'pending',
            requested_at  REAL DEFAULT (unixepoch()),
            processed_at  REAL,
            admin_note    TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS ad_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            coins      REAL NOT NULL,
            watch_secs REAL DEFAULT 0,
            timestamp  REAL DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS referral_earnings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            from_user   INTEGER NOT NULL,
            coins       REAL NOT NULL,
            timestamp   REAL DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS action_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            action    TEXT NOT NULL,
            detail    TEXT DEFAULT '',
            timestamp REAL DEFAULT (unixepoch())
        );
        CREATE INDEX IF NOT EXISTS idx_ad_log_user ON ad_log(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_wd_status ON withdrawals(status);
        """)
    print("✅ Base de datos inicializada")

def get_user(uid):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def create_user(uid, username, first_name, lang, referral_by=None):
    with db() as c:
        c.execute("""INSERT OR IGNORE INTO users
            (user_id,username,first_name,lang,referral_by,last_collect)
            VALUES (?,?,?,?,?,?)""",
            (uid, username or '', first_name or '', lang, referral_by, time.time()))

def update_user(uid, **kw):
    if not kw: return
    cols = ", ".join(f"{k}=?" for k in kw)
    with db() as c:
        c.execute(f"UPDATE users SET {cols} WHERE user_id=?", [*kw.values(), uid])

def add_coins(uid, amount):
    with db() as c:
        c.execute("""UPDATE users SET coins=coins+?,
            total_earned=total_earned+?, season_coins=season_coins+?
            WHERE user_id=?""", (amount, amount, amount, uid))

def deduct_coins(uid, amount) -> bool:
    with db() as c:
        r = c.execute("UPDATE users SET coins=coins-? WHERE user_id=? AND coins>=?",
                      (amount, uid, amount))
        return r.rowcount > 0

def reset_daily_if_needed(uid):
    u = get_user(uid)
    today = str(date.today())
    if u and u["ads_reset_date"] != today:
        update_user(uid, ads_today=0, ads_reset_date=today,
                    ads_hour_count=0, ads_hour_start=time.time(),
                    streak_ads_today=0)
        return True
    return False

def collect_passive(uid) -> float:
    u = get_user(uid)
    if not u: return 0.0
    now     = time.time()
    elapsed = min(now - u["last_collect"], MINE_MAX_IDLE_H * 3600)
    ld      = MINE_LEVELS.get(u["mine_level"], MINE_LEVELS[1])
    sb      = min(u["streak"] * STREAK_BONUS_PER_DAY, STREAK_MAX_BONUS)
    cps     = ld["cps"] * (1 + sb)
    if u["boost_until"] > now and u["boost_type"] == "x2":
        cps *= 2
    earned = elapsed * cps
    with db() as c:
        c.execute("""UPDATE users SET coins=coins+?,
            total_earned=total_earned+?, season_coins=season_coins+?,
            last_collect=? WHERE user_id=?""",
            (earned, earned, earned, now, uid))
    return earned

def record_ad_open(uid):
    update_user(uid, last_ad_open=time.time())

def can_watch_ad(uid):
    reset_daily_if_needed(uid)
    u = get_user(uid)
    if not u: return False, "not_found"
    if u["is_banned"]: return False, "banned"
    if u["ads_today"] >= ADS_PER_DAY_MAX: return False, "daily_limit"
    now = time.time()
    elapsed = now - u["last_ad_time"]
    if elapsed < AD_COOLDOWN_SEC:
        return False, f"cooldown:{int(AD_COOLDOWN_SEC - elapsed)}"
    if now - u["ads_hour_start"] > 3600:
        update_user(uid, ads_hour_count=0, ads_hour_start=now)
        u = get_user(uid)
    if u["ads_hour_count"] >= ADS_PER_HOUR_MAX:
        remaining = int(3600 - (now - u["ads_hour_start"]))
        return False, f"hour_limit:{remaining}"
    return True, ""

def register_ad_watch(uid) -> tuple:
    import random
    u   = get_user(uid)
    now = time.time()
    watch_secs = now - (u["last_ad_open"] or now)

    bonus = 0
    for threshold, b in sorted(AD_TIME_BONUS.items()):
        if watch_secs >= threshold: bonus = b

    lo, hi = AD_REWARDS.get(u["user_type"], AD_REWARDS["new"])
    coins = random.randint(lo, hi) + bonus

    if u["boost_until"] > now and u["boost_type"] == "x2":
        coins *= 2

    today = str(date.today())
    streak = u["streak"]
    if u["last_streak_date"] != today:
        yesterday = str(date.fromordinal(date.today().toordinal()-1))
        streak = (streak + 1) if u["last_streak_date"] == yesterday else 1
        update_user(uid, streak=streak, last_streak_date=today)

    update_user(uid,
        ads_today=u["ads_today"]+1,
        ads_hour_count=u["ads_hour_count"]+1,
        last_ad_time=now,
        streak_ads_today=u["streak_ads_today"]+1,
        total_ads=u["total_ads"]+1)

    add_coins(uid, coins)

    with db() as c:
        c.execute("INSERT INTO ad_log (user_id,coins,watch_secs) VALUES (?,?,?)",
                  (uid, coins, watch_secs))

    # Referral passive
    if u["referral_by"]:
        rc = coins * REFERRAL_PASSIVE_PCT
        add_coins(u["referral_by"], rc)
        with db() as c:
            c.execute("INSERT INTO referral_earnings (referrer_id,from_user,coins) VALUES (?,?,?)",
                      (u["referral_by"], uid, rc))

    # Update user type
    total = u["total_ads"] + 1
    if total > 100 or u["total_earned"] > 1000:
        update_user(uid, user_type="premium")
    elif total > 20:
        update_user(uid, user_type="active")

    # Risk check
    _check_risk(uid, u["ads_today"]+1, watch_secs)

    log_action(uid, "ad_watch", f"coins={coins} secs={watch_secs:.1f}")
    return coins, watch_secs

def _check_risk(uid, ads_today, watch_secs):
    score = 0
    if watch_secs < 3: score += 2
    if ads_today >= SUSPICIOUS_ADS_2H: score += 3
    with db() as c:
        fast = c.execute("SELECT COUNT(*) FROM ad_log WHERE user_id=? AND watch_secs<3",
                         (uid,)).fetchone()[0]
        if fast > 5: score += 2
    u = get_user(uid)
    new_score = min(10, (u["risk_score"] or 0) + score)
    if new_score >= RISK_BAN and not u["is_banned"]:
        update_user(uid, risk_score=new_score, is_banned=1, ban_reason="auto-ban risk")
        log_action(uid, "auto_ban", f"score={new_score}")
    elif new_score >= RISK_BLOCK:
        update_user(uid, risk_score=new_score, is_suspicious=1)
    elif score > 0:
        update_user(uid, risk_score=new_score)

def request_withdrawal(uid, method="paypal"):
    u = get_user(uid)
    if not u: return False, "not_found", 0
    if u["is_banned"]: return False, "banned", 0
    if u["is_suspicious"]: return False, "suspicious", 0
    if u["coins"] < MIN_WITHDRAWAL: return False, "insufficient", 0
    with db() as c:
        last = c.execute("""SELECT requested_at FROM withdrawals
            WHERE user_id=? AND status IN ('pending','paid')
            ORDER BY requested_at DESC LIMIT 1""", (uid,)).fetchone()
    if last:
        days = (time.time() - last["requested_at"]) / 86400
        if days < WITHDRAW_COOLDOWN_DAYS:
            return False, f"cooldown:{int(WITHDRAW_COOLDOWN_DAYS-days)+1}", 0
    coins = float(u["coins"])
    eur   = round(coins / COINS_PER_EURO, 2)
    with db() as c:
        c.execute("UPDATE users SET coins=0 WHERE user_id=?", (uid,))
        c.execute("INSERT INTO withdrawals (user_id,amount_coins,amount_eur,method) VALUES (?,?,?,?)",
                  (uid, coins, eur, method))
    log_action(uid, "withdrawal", f"eur={eur} method={method}")
    return True, "ok", eur

def check_missions(uid, mission_type, value):
    u = get_user(uid)
    done = json.loads(u["completed_missions"] or "[]")
    rewarded = []
    for m in MISSIONS:
        if m["id"] in done or m["type"] != mission_type: continue
        if value >= m["req"]:
            done.append(m["id"])
            add_coins(uid, m["reward"])
            rewarded.append(m)
    if rewarded:
        update_user(uid, completed_missions=json.dumps(done))
    return rewarded

def get_missions(uid):
    u = get_user(uid)
    done = json.loads(u["completed_missions"] or "[]")
    return [{**m, "done": m["id"] in done} for m in MISSIONS]

def get_top(limit=10):
    with db() as c:
        return c.execute("""SELECT user_id,first_name,username,season_coins
            FROM users WHERE is_banned=0 ORDER BY season_coins DESC LIMIT ?""",
            (limit,)).fetchall()

def get_stats():
    today = str(date.today())
    with db() as c:
        return {
            "total_users":  c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "new_today":    c.execute("SELECT COUNT(*) FROM users WHERE date(created_at,'unixepoch')=?", (today,)).fetchone()[0],
            "active_today": c.execute("SELECT COUNT(*) FROM users WHERE ads_reset_date=?", (today,)).fetchone()[0],
            "pending_wd":   c.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'").fetchone()[0],
            "paid_eur":     c.execute("SELECT COALESCE(SUM(amount_eur),0) FROM withdrawals WHERE status='paid'").fetchone()[0],
            "suspicious":   c.execute("SELECT COUNT(*) FROM users WHERE is_suspicious=1 AND is_banned=0").fetchone()[0],
            "banned":       c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0],
            "ads_24h":      c.execute("SELECT COUNT(*) FROM ad_log WHERE timestamp>?", (time.time()-86400,)).fetchone()[0],
        }

def get_pending_withdrawals():
    with db() as c:
        return c.execute("""SELECT w.*,u.first_name,u.username FROM withdrawals w
            JOIN users u ON w.user_id=u.user_id
            WHERE w.status='pending' ORDER BY w.requested_at ASC""").fetchall()

def process_withdrawal(wid, status, note=""):
    with db() as c:
        c.execute("UPDATE withdrawals SET status=?,processed_at=?,admin_note=? WHERE id=?",
                  (status, time.time(), note, wid))

def log_action(uid, action, detail=""):
    with db() as c:
        c.execute("INSERT INTO action_log (user_id,action,detail) VALUES (?,?,?)",
                  (uid, action, detail))
