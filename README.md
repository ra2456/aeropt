# Aero Parts Tracker

A prototype tool that tracks aero parts through four manufacturing stages (Design, Machining, Inspection and Model Fit) and flags the ones at risk of missing their tunnel deadline before it's too late.

Built in Python as a personal project to explore how data could support production planning.

> **Note:** the history data here is synthetic. I generated it myself to build and test the method. On real production data, the tool would learn the real stage times.

## What it does

The project has three scripts, each a step up from the last:

- **`aero_tracker_check.py` (v1)** flags parts with two fixed rules. *At risk*: due within four days and still in Design or Machining. *Stuck*: sitting in one stage for eight or more days. It never edits the live tracker; it only reads from it and writes the results to a separate dated report.

- **`aero_tracker_check_v2.py` (v2)** learns its thresholds from history instead of using fixed rules. For each part type at each stage, it learns the typical time (the median) and a stuck limit (the 90th percentile). It then predicts each part's ready date by adding up the typical time for each remaining stage, and flags the parts predicted to miss their deadline.

- **`lead_time_model.py`** tests whether a machine learning model that also knows the queue length can predict stage times more accurately than the simple median. On this data, the ML model was off by 0.74 days on average against 0.84 for the simple method, and it won 20 of 20 tests. That gain is marginal, so the recommendation is to use the simple version and only switch to ML if it clearly beats it on real, unseen data.

## How to run

```
pip install pandas openpyxl scikit-learn
python aero_tracker_check.py
python aero_tracker_check_v2.py
python lead_time_model.py
```

Run the scripts in that order. The two `.xlsx` files are the sample inputs, and each script writes its own report file.

## Files

- `Aero_Parts_Tracker.xlsx`: the live tracker (20 parts)
- `Aero_Parts_History.xlsx`: synthetic history used by v2 and the ML model
