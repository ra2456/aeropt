"""
Aero Parts Tracker - Automation Prototype
Reads the parts tracker, flags parts needing attention, and writes a
dated status report to a SEPARATE file (the live tracker is never changed).

  AT RISK : due in the tunnel soon but still early in the process
  STUCK   : sitting at the same stage longer than expected
"""

import pandas as pd
from datetime import datetime

# ---- settings you can tweak ----
TODAY        = datetime(2026, 10, 8)
AT_RISK_DAYS = 4                        # due within this many days...
EARLY_STAGES = ["Design", "Machining"] # ...but still here = at risk
STUCK_LIMIT  = 8                        # days at one stage before "stuck"

TRACKER_FILE = "Aero_Parts_Tracker.xlsx"
REPORT_FILE  = f"Aero_Status_Report_{TODAY:%Y-%m-%d}.xlsx"

def load(path):
    df = pd.read_excel(path)
    df["Tunnel Due Date"] = pd.to_datetime(df["Tunnel Due Date"])
    df["Days Until Due"]  = (df["Tunnel Due Date"] - TODAY).dt.days
    return df

def classify(r):
    if r["Days Until Due"] <= AT_RISK_DAYS and r["Current Stage"] in EARLY_STAGES:
        return "AT RISK"
    if r["Days In Stage"] >= STUCK_LIMIT and r["Current Stage"] != "Tunnel Ready":
        return "STUCK"
    return "OK"

def main():
    df = load(TRACKER_FILE)
    df["Status"] = df.apply(classify, axis=1)

    # sort so problems rise to the top
    order = {"AT RISK": 0, "STUCK": 1, "OK": 2}
    df["_s"] = df["Status"].map(order)
    df = df.sort_values(["_s", "Days Until Due"]).drop(columns="_s")

    # write the report to a NEW file - live tracker untouched
    with pd.ExcelWriter(REPORT_FILE, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Full Status", index=False)
        flagged = df[df["Status"] != "OK"]
        flagged.to_excel(xl, sheet_name="Needs Attention", index=False)

    n_risk  = (df["Status"] == "AT RISK").sum()
    n_stuck = (df["Status"] == "STUCK").sum()
    print(f"Report written to {REPORT_FILE}")
    print(f"  {n_risk} at risk, {n_stuck} stuck, {len(df)} parts total")

if __name__ == "__main__":
    main()
