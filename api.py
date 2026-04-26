# ============================================================
#  webapp/api.py — API endpoints para la Mini App
# ============================================================
import time
from flask import Blueprint, request, jsonify, g
from webapp.security import secure, sanitize, validate_payment
from security.risk_engine import get_ad_link, can_withdraw
import core.database as db
from config import *

api = Blueprint("api", __name__)

@api.after_request
def after(response):
    from webapp.security import apply_cors, apply_headers
    return apply_headers(apply_cors(response))

@api.route("/api/user", methods=["GET"])
@secure
def api_user():
    uid = g.uid
    collected = db.collect_passive(uid)
    u = db.get_user(uid)
    if not u: return jsonify({"error":"not_found"}), 404
    lvl  = u["mine_level"]
    ld   = MINE_LEVELS.get(lvl, MINE_LEVELS[1])
    sb   = min(u["streak"] * STREAK_BONUS_PER_DAY, STREAK_MAX_BONUS)
    rcps = ld["cps"] * (1 + sb)
    now  = time.time()
    boost_active = u["boost_until"] > now
    return jsonify({
        "user_id":      uid,
        "first_name":   u["first_name"],
        "coins":        round(u["coins"], 2),
        "coins_eur":    round(u["coins"] / COINS_PER_EURO, 4),
        "mine_level":   lvl,
        "mine_name":    ld[f"name_es"],
        "mine_rcps":    round(rcps, 6),
        "streak":       u["streak"],
        "streak_bonus": round(sb * 100, 1),
        "ads_today":    u["ads_today"],
        "ads_max":      ADS_PER_DAY_MAX,
        "ads_hour":     u["ads_hour_count"],
        "ads_hour_max": ADS_PER_HOUR_MAX,
        "total_ads":    u["total_ads"],
        "total_earned": round(u["total_earned"], 2),
        "referrals":    u["referrals_count"],
        "user_type":    u["user_type"],
        "boost_active": boost_active,
        "boost_type":   u["boost_type"] if boost_active else "",
        "boost_mins":   max(0, int((u["boost_until"]-now)/60)) if boost_active else 0,
        "can_withdraw": u["coins"] >= MIN_WITHDRAWAL and not u["is_suspicious"],
        "season_coins": round(u["season_coins"], 1),
        "just_collected": round(collected, 4),
    })

@api.route("/api/missions", methods=["GET"])
@secure
def api_missions():
    missions = db.get_missions(g.uid)
    return jsonify({"missions": [
        {"id":m["id"],"desc":m["es"],"reward":m["reward"],"done":m["done"],"type":m["type"]}
        for m in missions
    ]})

@api.route("/api/ranking", methods=["GET"])
@secure
def api_ranking():
    uid = g.uid
    top = db.get_top(10)
    u   = db.get_user(uid)
    return jsonify({
        "ranking": [{"pos":i+1,"name":r["first_name"] or "Miner",
                     "coins":round(r["season_coins"],1),"is_me":r["user_id"]==uid}
                    for i,r in enumerate(top)],
        "my_coins": round(u["season_coins"],1) if u else 0,
    })

@api.route("/api/ad/open", methods=["POST"])
@secure
def api_ad_open():
    uid = g.uid
    u   = db.get_user(uid)
    if not u: return jsonify({"error":"not_found"}), 404
    if u["is_banned"]: return jsonify({"error":"banned"}), 403
    can, reason = db.can_watch_ad(uid)
    if not can:
        if reason.startswith("cooldown:"):
            s = int(reason.split(":")[1])
            return jsonify({"error":"cooldown","seconds":s}), 400
        if reason.startswith("hour_limit:"):
            s = int(reason.split(":")[1])
            return jsonify({"error":"hour_limit","seconds":s}), 400
        return jsonify({"error":reason}), 400
    db.record_ad_open(uid)
    lo, hi = AD_REWARDS.get(u["user_type"], AD_REWARDS["new"])
    return jsonify({
        "link":       get_ad_link(uid),
        "min_secs":   AD_MIN_WATCH_SEC,
        "reward_min": lo,
        "reward_max": hi,
    })

@api.route("/api/ad/claim", methods=["POST"])
@secure
def api_ad_claim():
    uid = g.uid
    u   = db.get_user(uid)
    if not u: return jsonify({"error":"not_found"}), 404
    watch_secs = time.time() - (u["last_ad_open"] or 0)
    if watch_secs < AD_MIN_WATCH_SEC:
        remaining = int(AD_MIN_WATCH_SEC - watch_secs) + 1
        return jsonify({"error":"too_fast","remaining":remaining}), 400
    can, reason = db.can_watch_ad(uid)
    if not can: return jsonify({"error":reason}), 400
    coins, secs = db.register_ad_watch(uid)
    u = db.get_user(uid)
    rewarded = db.check_missions(uid, "ads", u["total_ads"])
    return jsonify({
        "coins_earned":       round(coins, 1),
        "total_coins":        round(u["coins"], 2),
        "ads_today":          u["ads_today"],
        "missions_completed": [m["es"] for m in rewarded],
    })

@api.route("/api/withdraw/info", methods=["GET"])
@secure
def api_wd_info():
    uid = g.uid
    u   = db.get_user(uid)
    if not u: return jsonify({"error":"not_found"}), 404
    ok, reason = can_withdraw(uid)
    with db.db() as c:
        history = c.execute("""SELECT status,amount_eur,method,requested_at
            FROM withdrawals WHERE user_id=? ORDER BY requested_at DESC LIMIT 5""",
            (uid,)).fetchall()
    return jsonify({
        "coins":       round(u["coins"],2),
        "eur":         round(u["coins"]/COINS_PER_EURO,4),
        "can_withdraw": ok and u["coins"] >= MIN_WITHDRAWAL,
        "reason":      reason if not ok else "",
        "min_coins":   MIN_WITHDRAWAL,
        "methods":     {k:{"name":v["name"],"emoji":v["emoji"]} for k,v in PAYMENT_METHODS.items()},
        "history":     [{"status":r["status"],"eur":r["amount_eur"],"ts":r["requested_at"]} for r in history],
    })

@api.route("/api/withdraw/request", methods=["POST"])
@secure
def api_wd_request():
    uid  = g.uid
    ok, reason = can_withdraw(uid)
    if not ok: return jsonify({"error":reason}), 403
    data   = request.get_json(silent=True) or {}
    method = sanitize(data.get("method",""), 20)
    detail = sanitize(data.get("detail",""), 254)
    if not method or not detail:
        return jsonify({"error":"missing_fields"}), 400
    valid, err = validate_payment(method, detail)
    if not valid: return jsonify({"error":err}), 400
    success, reason, eur = db.request_withdrawal(uid, f"{method}:{detail}")
    if not success: return jsonify({"error":reason}), 400
    return jsonify({"success":True,"amount_eur":eur})

@api.route("/api/referral", methods=["GET"])
@secure
def api_referral():
    uid  = g.uid
    u    = db.get_user(uid)
    import os
    bot_name = os.getenv("BOT_USERNAME","CryptoMinerEmpireBot")
    with db.db() as c:
        earned = c.execute("SELECT COALESCE(SUM(coins),0) FROM referral_earnings WHERE referrer_id=?",
                           (uid,)).fetchone()[0]
    return jsonify({
        "link":    f"https://t.me/{bot_name}?start=ref_{uid}",
        "count":   u["referrals_count"] if u else 0,
        "earned":  round(earned,1),
        "bonus":   REFERRAL_BONUS,
        "pct":     int(REFERRAL_PASSIVE_PCT*100),
    })
