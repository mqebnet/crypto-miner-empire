from config import AD_NETWORKS
from core.database import get_user
import time

def get_ad_link(uid: int) -> str:
    u = get_user(uid)
    if not u: return AD_NETWORKS["new"]["url"]
    return AD_NETWORKS.get(u["user_type"], AD_NETWORKS["new"])["url"]

def can_withdraw(uid: int) -> tuple:
    u = get_user(uid)
    if not u:              return False, "not_found"
    if u["is_banned"]:     return False, "banned"
    if u["risk_score"] >= 7: return False, "high_risk"
    if u["is_suspicious"]: return False, "suspicious"
    return True, "ok"
