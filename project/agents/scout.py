"""Scout Agent — collects competitor ad-like data from SerpAPI (Google organic,
Google Ads, and Google Images) and the Facebook Ad Library, plus an optional
LinkedIn company snapshot via ScrapingBee.

Real ad images: without an official ad-transparency API (Meta Ad Library or
Google Ads Transparency Center), nothing can guarantee an image is *currently
a live running ad*. What SerpAPI's Google Images engine gives us instead is
genuine images pulled from the live web — ad galleries, brand social posts,
marketing case studies that feature real creative. It's real, not a
placeholder or AI-generated, but it's "images of real ads found via search,"
not "verified live ad screenshot." Every image-bearing result is labeled
accordingly (see `format` field below) so this distinction stays visible
downstream instead of getting flattened into one generic "ad image."

Why Facebook demo data: Meta's official /ads_archive endpoint only returns
general commercial ads for the UK/EU (elsewhere it's scoped to political/
social-issue ads only — see https://www.facebook.com/ads/library/api). Since
this isn't a UK/EU political-ads use case, we use representative demo data
for this source rather than forcing empty/irrelevant results out of an API
that wasn't built to provide them. Flip USE_FACEBOOK_DEMO_DATA off in .env
if you do have a working UK/EU or political-ads token.
"""
import hashlib
from datetime import date

import requests

from config import (
    SERPAPI_KEY, SCRAPINGBEE_API_KEY, FACEBOOK_ACCESS_TOKEN,
    USE_FACEBOOK_DEMO_DATA, COMPETITORS, META_AD_TYPE, META_AD_REACHED_COUNTRIES,
)
from utils.logger import get_logger

log = get_logger("scout")


def _make_ad_id(*parts) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _search_serpapi(query: str, num_results: int = 5) -> dict:
    """Returns {"organic": [...], "ads": [...]} via SerpAPI's Google engine."""
    if not SERPAPI_KEY:
        log.warning("SERPAPI_KEY missing — skipping SerpAPI search for '%s'", query)
        return {"organic": [], "ads": []}
    try:
        from serpapi import GoogleSearch
    except ImportError:
        log.error("Missing package. Run: pip install google-search-results")
        return {"organic": [], "ads": []}

    params = {
        "q": query, "engine": "google", "location": "United States",
        "api_key": SERPAPI_KEY, "num": num_results,
    }
    try:
        data = GoogleSearch(params).get_dict()
        if "error" in data:
            log.error("SerpAPI error for '%s': %s", query, data["error"])
            return {"organic": [], "ads": []}
        organic = [
            {"title": r.get("title"), "link": r.get("link"), "snippet": r.get("snippet")}
            for r in data.get("organic_results", [])
        ]
        ads = [
            {"title": a.get("title"), "advertiser": a.get("displayed_link"), "link": a.get("link")}
            for a in data.get("ads", [])
        ]
        return {"organic": organic, "ads": ads}
    except Exception as e:
        log.error("SerpAPI request failed for '%s': %s", query, e)
        return {"organic": [], "ads": []}


def _search_serpapi_images(query: str, num_results: int = 3) -> list:
    """Real images from Google Images via SerpAPI.

    Honesty note: these are genuine images pulled from the live web (ad
    galleries, brand social posts, marketing case studies) — not placeholders,
    not AI-generated. But unlike Meta's ad_snapshot_url, there's no guarantee
    a given image is *currently a live running ad* — that guarantee only comes
    from an official ad-transparency API (Meta/Google Ads Transparency Center).
    This is the best real-image source available with a SerpAPI-only setup.
    """
    if not SERPAPI_KEY:
        log.warning("SERPAPI_KEY missing — skipping image search for '%s'", query)
        return []
    try:
        from serpapi import GoogleSearch
    except ImportError:
        log.error("Missing package. Run: pip install google-search-results")
        return []

    params = {"q": query, "engine": "google_images", "api_key": SERPAPI_KEY}
    try:
        data = GoogleSearch(params).get_dict()
        if "error" in data:
            log.error("SerpAPI image search error for '%s': %s", query, data["error"])
            return []
        results = []
        for r in data.get("images_results", [])[:num_results]:
            image_url = r.get("original") or r.get("thumbnail")
            if not image_url:
                continue
            results.append({
                "title": r.get("title"),
                "image_url": image_url,
                "source_link": r.get("link"),
            })
        return results
    except Exception as e:
        log.error("SerpAPI image search failed for '%s': %s", query, e)
        return []


def _facebook_demo_ads(competitor: str) -> list:
    """Representative sample ad data — see module docstring for why."""
    return [
        {"advertiser": competitor,
         "ad_text": f"{competitor}: rated best by thousands of happy customers — see why.",
         "start_date": "2026-06-01"},
        {"advertiser": competitor,
         "ad_text": f"{competitor}: 20% off today only, this week only.",
         "start_date": "2026-06-20"},
    ]


META_API_URL = "https://graph.facebook.com/v21.0/ads_archive"
META_FIELDS = "id,ad_creative_bodies,ad_creative_link_titles,ad_delivery_start_time,publisher_platforms,ad_snapshot_url"


def _fetch_real_facebook_ads(competitor: str) -> list:
    """Real Meta Ad Library call. Returns [] on any failure so the caller can
    fall back to demo data — never raises out of this function."""
    if not FACEBOOK_ACCESS_TOKEN:
        return []
    try:
        resp = requests.get(
            META_API_URL,
            params={
                "search_terms": competitor,
                "ad_type": META_AD_TYPE,
                "ad_reached_countries": str(META_AD_REACHED_COUNTRIES).replace("'", '"'),
                "fields": META_FIELDS,
                "limit": 10,
                "access_token": FACEBOOK_ACCESS_TOKEN,
            },
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            log.warning("Meta Ad Library error for '%s': %s", competitor,
                        data["error"].get("message", data["error"]))
            return []

        results = []
        for item in data.get("data", []):
            start = (item.get("ad_delivery_start_time") or date.today().isoformat())[:10]
            days = (date.today() - date.fromisoformat(start)).days
            body = " / ".join(item.get("ad_creative_bodies", [])) or ""
            title = " / ".join(item.get("ad_creative_link_titles", [])) or body[:60]
            results.append({
                "ad_id": _make_ad_id("fb_real", competitor, item.get("id")),
                "competitor": competitor,
                "headline": title,
                "body": body,
                "format": ", ".join(item.get("publisher_platforms", [])) or "Facebook Ad Library (real)",
                "start_date": start,
                "days_running": max(days, 0),
                "image_url": item.get("ad_snapshot_url"),  # link to the real ad creative screenshot
            })
        return results
    except Exception as e:
        log.warning("Meta Ad Library request failed for '%s': %s", competitor, e)
        return []


def _fetch_competitor(competitor: str) -> list:
    """Gathers everything Scout can find for one competitor into a unified ad list."""
    ads = []

    serp = _search_serpapi(f"{competitor} ad")
    for r in serp["organic"]:
        ads.append({
            "ad_id": _make_ad_id("organic", competitor, r.get("link")),
            "competitor": competitor,
            "headline": r.get("title") or "",
            "body": r.get("snippet") or "",
            "format": "Google Search (organic)",
            "start_date": None,
            "days_running": 0,  # duration unknown for a single organic snapshot
            "image_url": None,  # SerpAPI organic/ads results don't include creative images
        })
    for a in serp["ads"]:
        ads.append({
            "ad_id": _make_ad_id("serpads", competitor, a.get("link")),
            "competitor": a.get("advertiser") or competitor,
            "headline": a.get("title") or "",
            "body": "",
            "format": "Google Ads",
            "start_date": None,
            "days_running": 0,  # duration unknown for a single snapshot
            "image_url": None,
        })

    images = _search_serpapi_images(f"{competitor} advertisement campaign")
    for img in images:
        ads.append({
            "ad_id": _make_ad_id("img", competitor, img.get("image_url")),
            "competitor": competitor,
            "headline": img.get("title") or f"{competitor} ad creative",
            "body": f"Real image found at: {img.get('source_link')}" if img.get("source_link") else "",
            "format": "Google Images (real image — not a verified live ad)",
            "start_date": None,
            "days_running": 0,
            "image_url": img.get("image_url"),
        })

    fb_ads = []
    if not USE_FACEBOOK_DEMO_DATA and FACEBOOK_ACCESS_TOKEN:
        fb_ads = _fetch_real_facebook_ads(competitor)
        if fb_ads:
            log.info("Scout: %d real Facebook ad(s) with images for '%s'", len(fb_ads), competitor)
        else:
            log.warning("Meta Ad Library returned nothing for '%s' — falling back to demo data. "
                        "This is normal outside the UK/EU with ad_type=ALL (see module docstring).",
                        competitor)

    if fb_ads:
        ads.extend(fb_ads)
    else:
        for fb in _facebook_demo_ads(competitor):
            start = fb["start_date"]
            days = (date.today() - date.fromisoformat(start)).days
            ads.append({
                "ad_id": _make_ad_id("fb_demo", competitor, fb["ad_text"]),
                "competitor": fb["advertiser"],
                "headline": fb["ad_text"],
                "body": fb["ad_text"],
                "format": "Facebook Ad Library (demo)",
                "start_date": start,
                "days_running": max(days, 0),
                "image_url": None,  # demo data has no real creative to show
            })

    return ads


def get_linkedin_snapshot(competitor: str) -> dict:
    """Optional supplementary lookup — LinkedIn company page via ScrapingBee.
    Not fed into the ad-intelligence pipeline (a company page isn't ad creative);
    surfaced separately alongside the report for extra context.
    """
    slug = competitor.strip().lower().replace(" ", "-")
    url = f"https://www.linkedin.com/company/{slug}/"
    if not SCRAPINGBEE_API_KEY:
        return {"competitor": competitor, "status": "skipped (no ScrapingBee key)", "url": url}
    try:
        resp = requests.get(
            "https://app.scrapingbee.com/api/v1/",
            params={"api_key": SCRAPINGBEE_API_KEY, "url": url, "render_js": "true"},
            timeout=60,
        )
        if resp.status_code == 200:
            return {"competitor": competitor, "status": "success", "url": url}
        log.warning("ScrapingBee error for '%s': %s — %s", competitor, resp.status_code, resp.text[:150])
        return {"competitor": competitor, "status": "unavailable", "url": url}
    except Exception as e:
        log.warning("ScrapingBee request failed for '%s': %s", competitor, e)
        return {"competitor": competitor, "status": "unavailable", "url": url}


def run(known_ids: set):
    """Main entry point — matches the orchestrator's expected signature."""
    if not COMPETITORS:
        log.warning("No COMPETITORS configured in .env — Scout has nothing to search for.")
        return [], []

    ads = []
    for comp in COMPETITORS:
        fetched = _fetch_competitor(comp)
        log.info("Scout: %d items for '%s'", len(fetched), comp)
        ads.extend(fetched)

    new = [a for a in ads if a["ad_id"] not in known_ids]
    log.info("Scout: %d total, %d new", len(ads), len(new))
    return ads, new


if __name__ == "__main__":
    all_ads, new_ads = run(set())
    for ad in all_ads[:10]:
        print(f"- [{ad['format']}] {ad['competitor']}: {ad['headline']}")
