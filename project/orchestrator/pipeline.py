"""orchestrator/pipeline.py — runs the full agent loop end to end.

    Scout -> Analyst -> Strategist -> Fatigue Monitor -> Creative

Each agent in agents/ is independent and can be unit-tested on its own.
This module only handles sequencing, persistence between runs, and the
fatigue-gated trigger for creative generation (per the product loop:
"when fatigue is detected, generate new variants using the gap angle").
"""
from agents import scout, analyst, strategist, fatigue_monitor, creative
from database.store import load_known_ids, save_known_ids, save_report
from config import CTR_CSV_PATH, COMPETITORS
from utils.logger import get_logger

log = get_logger("orchestrator")


def run_pipeline(ctr_csv_path: str = None) -> dict:
    ctr_csv_path = ctr_csv_path or CTR_CSV_PATH

    # 1. Scout — pull competitor ads, diff against what we've already seen
    known_ids = load_known_ids()
    all_ads, new_ads = scout.run(known_ids)
    save_known_ids(known_ids | {a["ad_id"] for a in all_ads})

    if not all_ads:
        log.warning("Scout returned no ads this run — downstream agents will run on empty data.")

    # 2. Analyst — extract angle/hook/offer/cta per ad
    insights = analyst.run(all_ads) if all_ads else {}

    # 3. Strategist — cluster messaging, rank by longevity, find gaps
    brief = strategist.run(all_ads, insights)

    # 4. Fatigue Monitor — check the user's own ad performance (CSV-based)
    try:
        fatigue_alerts = fatigue_monitor.run(ctr_csv_path)
    except FileNotFoundError:
        log.warning("No CTR history file found at %s — skipping fatigue check.", ctr_csv_path)
        fatigue_alerts = []

    # 5. Creative — only spend an LLM call generating variants when fatigue
    #    was actually detected, so the loop stays "detect -> then generate"
    #    rather than generating creative on every single run.
    if fatigue_alerts:
        variants = creative.run(brief)
    else:
        variants = []
        log.info("No fatigue detected — creative generation skipped this run.")

    # 6. LinkedIn — optional supplementary context, not part of the ad pipeline
    linkedin_snapshots = [scout.get_linkedin_snapshot(c) for c in COMPETITORS]

    report = {
        "new_ads_found": len(new_ads),
        "total_ads_tracked": len(all_ads),
        "scout_ads": all_ads,
        "insights": insights,
        "strategy": brief,
        "fatigue_alerts": fatigue_alerts,
        "creative_variants": variants,
        "linkedin": linkedin_snapshots,
    }
    path = save_report(report)
    log.info("Pipeline complete. Report saved to %s", path)
    return report
