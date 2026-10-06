"""
Aero Parts Tracker v2 - thresholds learned from past data
Instead of one fixed rule for every part, it learns from history how long
each kind of part normally takes at each stage, then:

  STUCK   : been at this stage longer than 90% of past parts of the same kind
  AT RISK : adding up the typical time left, it won't be ready by its tunnel date

The live tracker is never changed; the report goes to a separate file.
"""

import math
import pandas as pd
from datetime import datetime, timedelta

# ---- settings you can tweak ----
TODAY       = datetime(2026, 10, 8)
STUCK_PCT   = 0.9   # stuck = slower than this share of past parts (0.9 = 90%)
SAFETY_DAYS = 0     # at risk = predicted to finish with fewer days to spare than this
MIN_HISTORY = 5     # fewer past records than this -> use all parts at that stage

STAGES = ["Design", "Machining", "Inspection", "Model Fit", "Tunnel Ready"]

TRACKER_FILE = "Aero_Parts_Tracker.xlsx"
HISTORY_FILE = "Aero_Parts_History.xlsx"
REPORT_FILE  = f"Aero_Status_Report_v2_{TODAY:%Y-%m-%d}.xlsx"


def summarise(groups):
    """Typical time, stuck limit and number of records for each group."""
    days = groups["Days Taken"]
    return pd.DataFrame({
        "Typical Days": days.median(),
        "Stuck After":  days.quantile(STUCK_PCT),
        "Records":      days.count(),
    })


def learn(path):
    """Learn the norms from past data: per part and stage, plus per stage as a backup."""
    hist = pd.read_excel(path, sheet_name="History")
    by_part  = summarise(hist.groupby(["Part Name", "Stage"]))
    by_stage = summarise(hist.groupby("Stage"))
    return by_part, by_stage


def norm(part, stage, by_part, by_stage):
    """Typical days and stuck limit for this kind of part at this stage."""
    key = (part, stage)
    if key in by_part.index and by_part.loc[key, "Records"] >= MIN_HISTORY:
        row = by_part.loc[key]
    else:
        row = by_stage.loc[stage]     # little or no history for this part: use the stage average
    return row["Typical Days"], row["Stuck After"]


def assess(r, by_part, by_stage):
    """Predict when this part will be ready, and label it."""
    part, stage, days_here = r["Part Name"], r["Current Stage"], r["Days In Stage"]

    if stage == "Tunnel Ready":
        days_left, typical, limit = 0, None, None
    else:
        typical, limit = norm(part, stage, by_part, by_stage)
        days_left = max(typical - days_here, 1)        # at least a day: it isn't finished yet
        later = STAGES[STAGES.index(stage) + 1 : -1]    # stages still to come, before Tunnel Ready
        for s in later:
            days_left += norm(part, s, by_part, by_stage)[0]

    ready = TODAY + timedelta(days=math.ceil(days_left))   # round up, to be on the safe side
    spare = (r["Tunnel Due Date"] - ready).days

    if spare < SAFETY_DAYS:
        status = "AT RISK"
    elif limit is not None and days_here > limit:
        status = "STUCK"
    else:
        status = "OK"

    return pd.Series({"Typical Days Here": typical, "Stuck After": limit,
                      "Predicted Ready": ready, "Days Spare": spare, "Status": status})


def main():
    by_part, by_stage = learn(HISTORY_FILE)

    df = pd.read_excel(TRACKER_FILE)
    df["Tunnel Due Date"] = pd.to_datetime(df["Tunnel Due Date"])
    df = df.join(df.apply(assess, axis=1, args=(by_part, by_stage)))

    # sort so problems rise to the top, least time to spare first
    order = {"AT RISK": 0, "STUCK": 1, "OK": 2}
    df["_s"] = df["Status"].map(order)
    df = df.sort_values(["_s", "Days Spare"]).drop(columns="_s")

    # write the report to a NEW file - live tracker untouched
    with pd.ExcelWriter(REPORT_FILE, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Full Status", index=False)
        flagged = df[df["Status"] != "OK"]
        flagged.to_excel(xl, sheet_name="Needs Attention", index=False)
        by_part.reset_index().to_excel(xl, sheet_name="Learned Norms", index=False)
        bottleneck = df.groupby("Current Stage")["Days In Stage"].agg(["count", "mean"]).round(1)
        bottleneck.to_excel(xl, sheet_name="Bottleneck")

    n_risk  = (df["Status"] == "AT RISK").sum()
    n_stuck = (df["Status"] == "STUCK").sum()
    print(f"Report written to {REPORT_FILE}")
    print(f"  {n_risk} at risk, {n_stuck} stuck, {len(df)} parts total")


if __name__ == "__main__":
    main()
