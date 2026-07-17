"""
config.py
Central configuration for the Competitive Creative Intelligence Engine.
Loads all API keys and thresholds from .env.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# --- Scout Agent data sources ---
SERPAPI_KEY = os.getenv("SERPAPI_KEY")                       # primary search + Google Ads data
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")       # LinkedIn company snapshot (supplementary)

# Facebook Ad Library: Meta's /ads_archive endpoint only returns general
# commercial ads for the UK/EU (elsewhere it's political/social-issue ads
# only — see facebook.com/ads/library/api). We use demo data unless you
# explicitly turn this off and provide a token.
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
USE_FACEBOOK_DEMO_DATA = os.getenv("USE_FACEBOOK_DEMO_DATA", "True") == "True"

# Only the real /ads_archive endpoint returns ad_snapshot_url (the actual ad
# creative image/screenshot) — demo data has no real image to show.
# ad_type: "ALL" requires ad_reached_countries to be UK/EU. Use
# "POLITICAL_AND_ISSUE_ADS" to search globally (political/social-issue ads only).
META_AD_TYPE = os.getenv("META_AD_TYPE", "ALL")
META_AD_REACHED_COUNTRIES = [c.strip() for c in os.getenv("META_AD_REACHED_COUNTRIES", "GB").split(",") if c.strip()]

# Google Custom Search — optional, not used by default (requires a billing-linked
# Google Cloud project). Kept here in case you wire it in later.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX_ID = os.getenv("GOOGLE_CX_ID")

COMPETITORS = [c.strip() for c in os.getenv("COMPETITORS", "").split(",") if c.strip()]

# --- Your brand (used by the Creative Agent) ---
BRAND_NAME = os.getenv("BRAND_NAME", "YourBrand")
BRAND_PRODUCT = os.getenv("BRAND_PRODUCT", "your product")

# --- Strategist Agent (clustering + longevity ranking) ---
N_CLUSTERS = int(os.getenv("N_CLUSTERS", "4"))
LONGEVITY_SUCCESS_DAYS = int(os.getenv("LONGEVITY_SUCCESS_DAYS", "14"))

# --- Fatigue Monitor (own-ad CTR decay detection) ---
CTR_CSV_PATH = os.getenv("CTR_CSV_PATH", "data/ctr_history.csv")
FATIGUE_CTR_DROP_PCT = float(os.getenv("FATIGUE_CTR_DROP_PCT", "0.20"))
FATIGUE_BASELINE_DAYS = int(os.getenv("FATIGUE_BASELINE_DAYS", "7"))
FATIGUE_RECENT_DAYS = int(os.getenv("FATIGUE_RECENT_DAYS", "3"))
FATIGUE_FREQUENCY_LIMIT = float(os.getenv("FATIGUE_FREQUENCY_LIMIT", "3.0"))

# --- Email alerts (Fatigue Monitor) ---
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")               # Gmail address to SEND from
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")     # Gmail App Password (not your normal password)
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "shahanakarthikeyan0@gmail.com")  # where alerts go

# --- Creative Agent (AI-generated ad copy) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- General settings ---
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "IN")
DEFAULT_RESULT_LIMIT = int(os.getenv("DEFAULT_RESULT_LIMIT", "5"))


def check_config():
    """Returns a dict summarizing which sources are configured and active."""
    return {
        "serpapi": bool(SERPAPI_KEY),
        "scrapingbee": bool(SCRAPINGBEE_API_KEY),
        "facebook": "demo_data" if USE_FACEBOOK_DEMO_DATA else bool(FACEBOOK_ACCESS_TOKEN),
        "google_search_configured_but_unused": bool(GOOGLE_API_KEY and GOOGLE_CX_ID),
        "competitors_configured": len(COMPETITORS),
        "ctr_csv_exists": os.path.exists(CTR_CSV_PATH),
        "email_configured": bool(EMAIL_ADDRESS and EMAIL_APP_PASSWORD),
        "groq_configured": bool(GROQ_API_KEY),
    }
