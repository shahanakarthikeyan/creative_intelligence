"""Analyst Agent — extracts structured intelligence (angle, hook, offer, cta)
from each ad using keyword/rule-based matching. No LLM key required.

This trades some nuance for zero API dependency: it won't catch a clever
angle phrased in an unusual way, but it's fast, free, and deterministic.
Swap this for an LLM-backed version later (see the angle/offer/cta keys it
produces — any replacement just needs to return the same shape).
"""
import re
from utils.logger import get_logger

log = get_logger("analyst")

# Order matters — first matching angle wins, so put more specific signals first.
ANGLE_KEYWORDS = {
    "discount": ["% off", "discount", "deal", "sale", "save"],
    "urgency": ["today only", "limited", "hurry", "last chance", "ends soon", "this week only"],
    "social proof": ["rated", "reviews", "customers", "trusted", "loved by", "5 star", "5-star"],
    "free_shipping": ["free shipping", "free delivery"],
    "convenience": ["easy", "fast delivery", "in 2 days", "next day", "hassle-free"],
    "quality": ["premium", "best", "top rated", "top-rated", "durable", "handcrafted"],
}

CTA_KEYWORDS = {
    "Shop Now": ["shop now", "shop the"],
    "Buy Now": ["buy now", "order now"],
    "Sign Up": ["sign up", "join now"],
    "Get Yours": ["get yours", "claim"],
    "Learn More": ["learn more", "find out"],
}


def _detect_angle(text: str) -> str:
    text = text.lower()
    for angle, keywords in ANGLE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return angle
    return "general"


def _detect_offer(text: str) -> str:
    match = re.search(r"(\d{1,3}\s?%\s?off)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    if "free" in text.lower():
        return "free offer mentioned"
    return "none"


def _detect_cta(text: str) -> str:
    text = text.lower()
    for cta, keywords in CTA_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cta
    return "Learn More"


def _analyze_one(ad: dict) -> dict:
    text = f"{ad.get('headline', '')} {ad.get('body', '')}"
    return {
        "angle": _detect_angle(text),
        "hook": ad.get("headline") or (ad.get("body") or "")[:60],
        "offer": _detect_offer(text),
        "cta": _detect_cta(text),
    }


def run(ads: list) -> dict:
    insights = {}
    for ad in ads:
        try:
            insights[ad["ad_id"]] = _analyze_one(ad)
        except Exception as e:
            log.warning("Analyst failed on %s: %s", ad.get("ad_id"), e)
            insights[ad["ad_id"]] = {
                "angle": "unknown", "hook": ad.get("headline", ""),
                "offer": "unknown", "cta": "unknown",
            }
    log.info("Analyst: %d ads analyzed (rule-based, no LLM)", len(insights))
    return insights
