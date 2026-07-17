"""
main.py — entry point for the Competitive Creative Intelligence Engine.

Usage:
    python main.py                     # uses CTR_CSV_PATH from .env/config
    python main.py path/to/ctr.csv     # override the CTR history file
"""
import sys
from orchestrator.pipeline import run_pipeline


def print_report(report: dict) -> None:
    print("\n" + "=" * 70)
    print("COMPETITIVE CREATIVE INTELLIGENCE — RUN REPORT")
    print("=" * 70)
    print(f"New competitor ads found: {report['new_ads_found']}")
    print(f"Total ads tracked:        {report['total_ads_tracked']}")

    print("\n--- Scout — Competitor Ads ---")
    for ad in report.get("scout_ads", []):
        print(f"  • [{ad['format']}] {ad['competitor']}: {ad['headline']}")
        if ad.get("image_url"):
            print(f"    🖼  {ad['image_url']}")

    print("\n--- Winning Angles (competitor longevity-ranked) ---")
    if report["strategy"]["winning_angles"]:
        for w in report["strategy"]["winning_angles"]:
            print(f"  • {w['angle']}: avg {w['avg_days_running']} days running, {w['n_ads']} ads")
    else:
        print("  None identified yet.")

    print("\n--- Messaging Gaps (winning angles you haven't tried) ---")
    if report["strategy"]["gaps"]:
        for g in report["strategy"]["gaps"]:
            print(f"  • {g['angle']}")
    else:
        print("  No gaps identified.")

    print("\n--- Fatigue Alerts ---")
    if report["fatigue_alerts"]:
        for a in report["fatigue_alerts"]:
            print(f"  ⚠️  {a['message']}")
    else:
        print("  None — no creative fatigue detected this run.")

    print("\n--- Generated Creative Variants ---")
    if report["creative_variants"]:
        for i, v in enumerate(report["creative_variants"], 1):
            print(f"  {i}. [{v.get('angle')}] {v.get('headline')}")
            print(f"     {v.get('body')}")
            print(f"     CTA: {v.get('cta')}")
    else:
        print("  None generated this run.")

    if report.get("linkedin"):
        print("\n--- LinkedIn (supplementary) ---")
        for l in report["linkedin"]:
            print(f"  • {l['competitor']}: {l['status']}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    csv_override = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_pipeline(ctr_csv_path=csv_override)
    print_report(result)
