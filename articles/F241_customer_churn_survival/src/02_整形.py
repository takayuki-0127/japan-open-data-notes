"""整形：Telco は契約月数（tenure）と解約の有無、法人は設立年ごとの存続月数に直す。"""
import pandas as pd, numpy as np, pathlib
B = pathlib.Path(__file__).resolve().parents[1]
t = pd.read_csv(B / "data/raw/Telco-Customer-Churn.csv")
t["TotalCharges"] = pd.to_numeric(t["TotalCharges"], errors="coerce")
t["event"] = (t["Churn"] == "Yes").astype(int)
t["duration"] = t["tenure"].clip(lower=0)
keep = ["customerID","duration","event","Contract","InternetService","PaymentMethod","MonthlyCharges","SeniorCitizen","Partner","Dependents","PaperlessBilling","TechSupport","OnlineSecurity"]
t[keep].to_csv(B / "data/telco_clean.csv", index=False)
h = pd.read_csv(B / "data/raw/houjin_new_2015_2026.csv.gz", dtype=str)
h = h[h["kind"].isin(["301","305"])].copy()               # 株式会社・合同会社
h["a"] = pd.to_datetime(h["assign"]); h["c"] = pd.to_datetime(h["close"])
END = pd.Timestamp("2026-09-30")
h = h[(h["a"] >= "2016-01-01") & (h["a"] <= "2025-12-31")]
h["cohort"] = h["a"].dt.year
h["event"] = h["c"].notna() & (h["c"] <= END)
last = h["c"].where(h["event"], END)
h["months"] = ((last - h["a"]).dt.days / 30.4375).clip(lower=0)
h["kind_j"] = h["kind"].map({"301":"株式会社","305":"合同会社"})
h[["cohort","kind_j","months","event"]].assign(event=lambda d: d.event.astype(int)).to_csv(B / "data/houjin_cohort.csv.gz", index=False, compression="gzip")
print(len(t), t["event"].mean().round(4), len(h), h["event"].mean().round(4))
