"""問い直し（結果を見てから足した）：ピーク（2021年度）のあとの減少は、どの機器から来たのか。
版（2025年版・2026年版）で答えが変わるかも確かめる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
df = pd.read_csv(ROOT / "data" / "fgas_long.csv")
USES = ["refrig_commercial", "refrig_household_ac", "refrig_car_ac", "foam", "aerosol"]
NAMES = {"refrig_commercial": "業務用冷凍空調機器", "refrig_household_ac": "家庭用エアコン", "refrig_car_ac": "カーエアコン", "foam": "発泡剤", "aerosol": "エアゾール・MDI"}
rows = []
for ver, a, b in [(2026, 2021, 2024), (2026, 2021, 2023), (2025, 2021, 2023)]:
    d = df[(df.version == ver) & (df.gas == "HFC")].pivot_table(index="fy", columns="use", values="mt")
    tot = float(d.total.loc[b] - d.total.loc[a])
    row = {"version": f"{ver}年版", "period": f"{a}-{b}", "total_change": round(tot, 3)}
    for u in USES:
        v = float(d[u].loc[b] - d[u].loc[a])
        row[u] = round(v, 3); row[u + "_share_pct"] = round(v / tot * 100, 1)
    rows.append(row)
t = pd.DataFrame(rows)
t.to_csv(R / "requestion_post_peak.csv", index=False)
# 2022年度の版による書き換えを用途別に
w = df[(df.gas == "HFC") & (df.fy == 2022)].pivot_table(index="use", columns="version", values="mt")
w["diff"] = w[2026] - w[2025]
w = w.loc[["total"] + USES]
w.round(4).to_csv(R / "requestion_vintage_2022_by_use.csv")
out = {
    "post_peak_2026ver_2021_2024": {NAMES[u]: t.loc[0, u] for u in USES} | {"計": t.loc[0, "total_change"]},
    "post_peak_share_pct_2026ver": {NAMES[u]: t.loc[0, u + "_share_pct"] for u in USES},
    "post_peak_2025ver_2021_2023": {NAMES[u]: t.loc[2, u] for u in USES} | {"計": t.loc[2, "total_change"]},
    "post_peak_2026ver_2021_2023": {NAMES[u]: t.loc[1, u] for u in USES} | {"計": t.loc[1, "total_change"]},
    "vintage_2022_diff_mt": {("計" if u == "total" else NAMES[u]): round(float(w.loc[u, "diff"]), 3) for u in w.index},
}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
