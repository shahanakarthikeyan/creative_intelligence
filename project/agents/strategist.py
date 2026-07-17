"""Strategist Agent — clusters competitor messaging with TF-IDF embeddings,
ranks angles by ad longevity (longevity = proven performance proxy),
identifies messaging gaps the user hasn't tried, and ranks the top 5
individual ads with human-readable reasoning for each ranking."""
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from config import N_CLUSTERS, LONGEVITY_SUCCESS_DAYS
from utils.logger import get_logger

log = get_logger("strategist")

# Angles the user's own brand currently uses (their creative inventory)
USER_CURRENT_ANGLES = {"discount", "quality"}


def run(ads: list, insights: dict) -> dict:
    if not ads:
        return {"winning_angles": [], "gaps": [], "clusters": {}}

    # 1. Cluster ad texts into messaging groups (TF-IDF + KMeans)
    texts = [a["headline"] + " " + a["body"] for a in ads]
    n_clusters = min(N_CLUSTERS, len(texts))
    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform(texts)
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(X)

    # 2. Rank angles by average longevity of ads using them
    angle_days = defaultdict(list)
    for ad in ads:
        angle = insights.get(ad["ad_id"], {}).get("angle", "general")
        angle_days[angle].append(ad["days_running"])
    ranked = sorted(
        ((angle, sum(d) / len(d), len(d)) for angle, d in angle_days.items()),
        key=lambda t: t[1], reverse=True,
    )
    winning = [
        {"angle": a, "avg_days_running": round(avg, 1), "n_ads": n}
        for a, avg, n in ranked if avg >= LONGEVITY_SUCCESS_DAYS
    ]

    # 3. Gaps = winning angles the user's brand hasn't tried
    gaps = [w for w in winning if w["angle"] not in USER_CURRENT_ANGLES]

    # 4. Cluster summary (for the dashboard)
    clusters = defaultdict(list)
    for ad, lbl in zip(ads, labels):
        clusters[int(lbl)].append(ad["headline"])

    brief = {"winning_angles": winning, "gaps": gaps, "clusters": dict(clusters)}
    log.info("Strategist: %d winning angles, %d gaps found", len(winning), len(gaps))
    return brief


def _score_ad(ad: dict, insight: dict, max_days: int) -> float:
    """
    Composite score (0-1) used to rank individual ads. Built entirely
    from real, observable signals — no fabricated metrics:
      - Longevity (days_running) vs the longest-running ad in this batch
      - Whether a real creative image was found (stronger signal — visual
        ads are typically higher-investment, higher-confidence creative)
      - Whether a concrete offer was detected (% off, free shipping, etc.)
      - Whether the ad uses an angle that already qualifies as "winning"
        (i.e. avg longevity >= LONGEVITY_SUCCESS_DAYS across the batch)
    """
    score = 0.0

    # Longevity — the single strongest real signal we have (60% weight)
    if max_days > 0:
        score += 0.6 * (ad.get("days_running", 0) / max_days)

    # Has a real image (15% weight)
    if ad.get("image_url"):
        score += 0.15

    # Has a concrete offer detected (15% weight)
    offer = insight.get("offer", "none")
    if offer and offer != "none" and offer != "unknown":
        score += 0.15

    # Uses a currently-winning angle (10% weight) — set by caller
    if insight.get("_is_winning_angle"):
        score += 0.10

    return round(min(score, 1.0), 3)


def _build_reason(ad: dict, insight: dict, rank: int, max_days: int) -> str:
    """Builds a human-readable, data-grounded explanation for why this
    ad ranked where it did — used directly in the dashboard UI."""
    reasons = []

    days = ad.get("days_running", 0)
    if days > 0:
        if max_days > 0 and days == max_days:
            reasons.append(f"longest-running ad in this sweep at {days} days")
        else:
            reasons.append(f"running for {days} days")

    if ad.get("image_url"):
        reasons.append("backed by a real creative image asset")

    offer = insight.get("offer", "none")
    if offer and offer not in ("none", "unknown"):
        reasons.append(f"features a concrete offer ({offer})")

    angle = insight.get("angle", "general")
    if insight.get("_is_winning_angle"):
        reasons.append(f"uses the '{angle}' angle, which already qualifies as high-performing across this batch")
    elif angle != "general":
        reasons.append(f"uses a '{angle}' angle")

    if not reasons:
        reasons.append("included based on available signals in this sweep")

    return f"#{rank}: " + "; ".join(reasons).capitalize() + "."


def rank_top_ads(ads: list, insights: dict, top_n: int = 5) -> list:
    """
    Ranks the collected ads and returns the top N with a real,
    data-grounded reason for each ranking. Used by the dashboard's
    Strategist panel (Agent 03).
    """
    if not ads:
        return []

    max_days = max((a.get("days_running", 0) for a in ads), default=0)

    # Mark which insights belong to a "winning" angle for this batch,
    # using the same threshold as run()'s winning_angles calculation.
    angle_days = defaultdict(list)
    for ad in ads:
        angle = insights.get(ad["ad_id"], {}).get("angle", "general")
        angle_days[angle].append(ad.get("days_running", 0))
    winning_angle_set = {
        angle for angle, days_list in angle_days.items()
        if (sum(days_list) / len(days_list)) >= LONGEVITY_SUCCESS_DAYS
    }
    for ad in ads:
        ins = insights.get(ad["ad_id"], {})
        ins["_is_winning_angle"] = ins.get("angle") in winning_angle_set

    scored = []
    for ad in ads:
        ins = insights.get(ad["ad_id"], {"angle": "general", "offer": "unknown", "cta": "unknown"})
        score = _score_ad(ad, ins, max_days)
        scored.append((score, ad, ins))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_n]

    results = []
    for i, (score, ad, ins) in enumerate(top, start=1):
        results.append({
            "rank": i,
            "competitor": ad.get("competitor"),
            "headline": ad.get("headline"),
            "format": ad.get("format"),
            "days_running": ad.get("days_running", 0),
            "image_url": ad.get("image_url"),
            "score": score,
            "reason": _build_reason(ad, ins, i, max_days),
        })

    log.info("Strategist: ranked top %d ads", len(results))
    return results
