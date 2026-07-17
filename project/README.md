# Competitive Creative Intelligence Engine

Five agents, one loop: **Scout → Analyst → Strategist → Fatigue Monitor → Creative**.

No LLM key required — Analyst and Creative use keyword/template-based logic
instead of calling an LLM. Swap them for an LLM-backed version later without
touching the orchestrator; they just need to keep returning the same shape.

## Project structure
```
config.py                  # all settings, loaded from .env
main.py                    # CLI entry point — runs the full pipeline
requirements.txt
.env.example                 # copy to .env and fill in your keys

agents/
  scout.py                  # SerpAPI (search + Google Ads) + Facebook Ad Library demo data
  analyst.py                 # rule-based — extracts angle/hook/offer/cta via keyword matching
  strategist.py               # TF-IDF clustering + longevity ranking + gap detection
  fatigue_monitor.py          # detects CTR decay on your own ads from a CSV
  creative.py                  # template-based — generates new ad variants for the top gap

orchestrator/
  pipeline.py                  # sequences all five agents, connects their outputs

database/
  store.py                     # JSON-backed persistence (known ad IDs + report history)

utils/
  logger.py                    # shared logging
  prompts.py                    # unused now (kept from the LLM-based version, harmless)

data/
  ctr_history.csv               # sample CTR data to test the Fatigue Monitor
  known_ad_ids.json             # created on first run
  reports/                      # every pipeline run is saved here as timestamped JSON

dashboard/
  index.html                    # neon console UI — client-side demo of the pipeline
```

## Data sources (matched to your actual keys)
- **SerpAPI** — primary source. Organic Google results + Google Ads for each
  competitor in `COMPETITORS`, plus **real ad images via Google Images**.
  Important honesty note: without an official ad-transparency API (Meta Ad
  Library or Google Ads Transparency Center), nothing can guarantee an image
  is *currently a live running ad*. These are genuine images pulled from the
  live web — ad galleries, brand social posts, marketing case studies — real,
  not placeholders or AI-generated, but "images of real ads found via search,"
  not "verified live ad screenshot." Each result's `format` field says
  `Google Images (real image — not a verified live ad)` so this distinction
  stays visible in every report, not flattened into a generic "ad image."
- **Facebook Ad Library** — demo data by default. Meta's real `/ads_archive`
  endpoint only returns general commercial ads for the UK/EU (elsewhere it's
  political/social-issue ads only), so demo data is used unless you set
  `USE_FACEBOOK_DEMO_DATA=False` and provide `FACEBOOK_ACCESS_TOKEN`.
  **Real ad images (`image_url`) only come from this real endpoint** — demo
  data has no genuine creative to show. Two ways to get real images:
  - `META_AD_TYPE=ALL` + `META_AD_REACHED_COUNTRIES=GB` (or any UK/EU country)
    → real commercial ad images for that market.
  - `META_AD_TYPE=POLITICAL_AND_ISSUE_ADS` + any country
    → real political/social-issue ad images, works globally.
  If Meta returns nothing for a competitor (e.g. `ad_type=ALL` outside UK/EU),
  Scout automatically falls back to demo data for that competitor and logs why.
- **ScrapingBee** — optional. Pulls a LinkedIn company snapshot per competitor
  as supplementary context (not fed into the ad-intelligence pipeline itself).
- **Google Custom Search** — configured but unused by default (needs a
  billing-linked Google Cloud project); left in `config.py` for later.

## Running the real pipeline
```bash
pip install -r requirements.txt
cp .env.example .env        # fill in SERPAPI_KEY at minimum, then COMPETITORS, BRAND_NAME, BRAND_PRODUCT
python main.py
```
Each run is saved to `data/reports/report_<timestamp>.json`, and Scout's ad IDs
are remembered in `data/known_ad_ids.json` so the next run can tell you what's new.

Even with zero keys configured, `python main.py` will still run end-to-end using
Facebook demo data and the sample `data/ctr_history.csv` — useful for a first
smoke test before you add real keys.

## Running the dashboard
`dashboard/index.html` is a **standalone, self-contained file** — open it directly
in a browser, no server needed. Type a brand name, hit "Run Scout", then click
through the five agent buttons to see each stage's output.

It's a client-side simulation (deterministic per brand name) — it doesn't call
SerpAPI or ScrapingBee, since those need a server-side secret key. It's there to
demo the *shape* of the pipeline and the UI; `python main.py` is what produces
real data from your actual keys.

## Security note
Never paste real API keys into a chat, README, or commit message. Put them only
in your local `.env` file (already excluded from anything meant to be shared —
add `.env` to `.gitignore` if you push this to a repo).
