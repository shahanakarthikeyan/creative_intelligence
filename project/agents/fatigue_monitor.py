"""Fatigue Monitor — time-series anomaly detection on own-ad CTR.

Method: rolling 7-day baseline vs recent 3-day mean. Flags fatigue when
recent CTR drops >= 20% below baseline AND frequency exceeds 3.0 —
thresholds drawn from industry-published fatigue playbooks
(TheOptimizer, Triple Whale)."""
import pandas as pd
from config import (FATIGUE_CTR_DROP_PCT, FATIGUE_BASELINE_DAYS,
                    FATIGUE_RECENT_DAYS, FATIGUE_FREQUENCY_LIMIT)
from utils.logger import get_logger

log = get_logger("fatigue")

def run(ctr_csv_path) -> list:
    df = pd.read_csv(ctr_csv_path)
    alerts = []
    for name, g in df.groupby("ad_name"):
        g = g.sort_values("day")
        if len(g) < FATIGUE_BASELINE_DAYS + FATIGUE_RECENT_DAYS:
            continue  # not enough history yet
        baseline = g["ctr"].iloc[
            -(FATIGUE_BASELINE_DAYS + FATIGUE_RECENT_DAYS):-FATIGUE_RECENT_DAYS
        ].mean()
        recent = g["ctr"].iloc[-FATIGUE_RECENT_DAYS:].mean()
        freq = g["frequency"].iloc[-1]
        drop = (baseline - recent) / baseline if baseline > 0 else 0.0
        if drop >= FATIGUE_CTR_DROP_PCT and freq >= FATIGUE_FREQUENCY_LIMIT:
            msg = (f"'{name}': CTR down {drop:.0%} vs 7-day baseline "
                   f"(freq {freq:.1f}) — creative fatigue detected.")
            alerts.append({"ad_name": name, "message": msg, "ctr_drop": round(drop, 3)})
            log.info("ALERT %s", msg)
    log.info("Fatigue monitor: %d alert(s)", len(alerts))
    return alerts