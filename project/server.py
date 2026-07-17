"""
server.py
Local web server that bridges the SCOUT dashboard (dashboard/index.html)
to the REAL agent pipeline — replacing the dashboard's client-side JS
simulation with genuine API-backed results.

Run with:
    python server.py

Then open:
    http://localhost:5000
"""
from flask import Flask, request, jsonify, send_from_directory

from agents import scout, analyst, strategist, fatigue_monitor, creative
from config import CTR_CSV_PATH
from utils.logger import get_logger
from utils.emailer import send_fatigue_alert

log = get_logger("server")

app = Flask(__name__, static_folder="dashboard", static_url_path="")


@app.route("/")
def index():
    return send_from_directory("dashboard", "index.html")


@app.route("/api/run", methods=["POST"])
def run_scout_api():
    """
    Agents 01-03: Scout -> Analyst -> Strategist (including top-5 ranking)
    for a single competitor brand typed into the dashboard.
    """
    data = request.get_json(silent=True) or {}
    brand = (data.get("brand") or "").strip()

    if not brand:
        return jsonify({"error": "No brand name provided"}), 400

    log.info("Dashboard request: running Scout for '%s'", brand)

    # 1. Scout — real SerpAPI / Facebook (demo or live) / image search
    ads = scout._fetch_competitor(brand)

    # 2. Analyst — real rule-based extraction
    insights = analyst.run(ads) if ads else {}

    # 3. Strategist — real TF-IDF clustering + longevity ranking + top-5
    if ads:
        brief = strategist.run(ads, insights)
        top_ads = strategist.rank_top_ads(ads, insights, top_n=5)
    else:
        brief = {"winning_angles": [], "gaps": [], "clusters": {}}
        top_ads = []

    # LinkedIn — supplementary real scrape for this brand
    linkedin = scout.get_linkedin_snapshot(brand)

    return jsonify({
        "brand": brand,
        "ads": ads,
        "insights": insights,
        "brief": brief,
        "top_ads": top_ads,
        "linkedin": linkedin,
    })


@app.route("/api/fatigue", methods=["POST"])
def fatigue_api():
    """
    Agent 04: checks YOUR OWN brand's CTR history and, if fatigue is
    detected, sends a real email alert.
    """
    data = request.get_json(silent=True) or {}
    own_brand = (data.get("own_brand") or "").strip() or "Your brand"

    log.info("Dashboard request: fatigue check for own brand '%s'", own_brand)

    try:
        alerts = fatigue_monitor.run(CTR_CSV_PATH)
    except FileNotFoundError:
        log.warning("No CTR history file at %s.", CTR_CSV_PATH)
        return jsonify({
            "own_brand": own_brand,
            "alerts": [],
            "email": {"sent": False, "reason": f"No CTR history file found at {CTR_CSV_PATH}"},
        })

    email_result = {"sent": False, "reason": "No fatigue detected — no alert needed"}
    if alerts:
        email_result = send_fatigue_alert(alerts, own_brand)

    return jsonify({
        "own_brand": own_brand,
        "alerts": alerts,
        "email": email_result,
    })


@app.route("/api/creative", methods=["POST"])
def creative_api():
    """
    Agent 05: generates a professional, unique ad from real user-supplied
    inputs (product, audience, offer, tone, CTA preference). Uses Groq
    (Llama) if configured, otherwise a personalized template fallback.
    """
    data = request.get_json(silent=True) or {}

    product = (data.get("product") or "").strip()
    if not product:
        return jsonify({"error": "Product/service is required"}), 400

    inputs = {
        "product": product,
        "audience": (data.get("audience") or "").strip(),
        "offer": (data.get("offer") or "").strip(),
        "tone": (data.get("tone") or "professional").strip(),
        "cta_preference": (data.get("cta_preference") or "").strip(),
    }

    log.info("Dashboard request: generating creative for product '%s'", product)
    ad = creative.generate_custom(inputs)

    return jsonify({"ad": ad, "inputs": inputs})


if __name__ == "__main__":
    print("=" * 60)
    print("SCOUT server starting — open http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, port=5000, use_reloader=False)
