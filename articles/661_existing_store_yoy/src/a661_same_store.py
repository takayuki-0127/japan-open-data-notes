"""661 新しく開いた店と閉じた店を含めたまま前年比を出すと、既存店だけの前年比とどれだけ違うのか

架空のチェーン（2023年末に100店）。2024〜2025年に新店を開き、古い店を閉じる。新店は開店から半年ほどかけて売上が伸びる。
既存の店の売上は本当は毎月 前年比+1%（季節の波あり）。2025年の月ごとに前年比を3通りで出す。
  Y1 全店の合計どうし（新店・閉店を含む）
  Y2 既存店（前年の同じ月も今年もまる1か月営業した店）だけ
  Y3 全店の売上を、営業した店の日数（店×日）で割ってから比べる
DuckDB（1スレッド）と pandas の一致を確かめる。seed 661。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空のチェーンの月次売上（作成者が乱数で作成、seed 661）"
rng = np.random.default_rng(661)
months = pd.period_range("2023-01", "2025-12", freq="M")
season = {1: 0.92, 2: 0.88, 3: 1.0, 4: 0.98, 5: 1.0, 6: 0.97, 7: 1.05, 8: 1.08, 9: 0.97, 10: 1.0, 11: 1.02, 12: 1.15}
stores = []
for i in range(100):
    stores.append({"store_id": f"S{i + 1:03d}", "open": pd.Timestamp("2015-01-01"), "close": None, "base": rng.lognormal(np.log(1500), 0.3)})
# 新店：2024年に8店、2025年に18店（前半に多い）。閉店：2024年に3店、2025年に10店（売上の小さい店）
def add_new(year, k, early):
    for _ in range(k):
        mo = int(rng.choice(range(1, 13), p=early))
        day = int(rng.integers(1, 28))
        stores.append({"store_id": f"S{len(stores) + 1:03d}", "open": pd.Timestamp(year, mo, day), "close": None, "base": rng.lognormal(np.log(1600), 0.3)})
p24 = np.ones(12) / 12; p25 = np.array([3, 3, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1], float); p25 /= p25.sum()
add_new(2024, 8, p24); add_new(2025, 18, p25)
old = sorted(range(100), key=lambda i: stores[i]["base"])
for i in old[:3]:
    stores[i]["close"] = pd.Timestamp(2024, int(rng.integers(2, 12)), int(rng.integers(1, 28)))
for i in old[3:13]:
    stores[i]["close"] = pd.Timestamp(2025, int(rng.integers(1, 12)), int(rng.integers(1, 28)))
rows = []
for s in stores:
    for p in months:
        start, end = p.start_time, p.end_time.normalize()
        o = max(start, s["open"]); c = min(end, s["close"] - pd.Timedelta(days=1)) if s["close"] is not None else end
        days = (c - o).days + 1
        if days <= 0:
            continue
        age_m = (p.start_time - s["open"]).days / 30.4
        ramp = 1.0 if s["open"] < pd.Timestamp("2023-01-01") else min(1.0, 0.55 + 0.45 * max(age_m, 0) / 6)
        growth = 1.01 ** ((p.year - 2023) + (p.month - 1) / 12)
        sales = s["base"] * season[p.month] * growth * ramp * days / p.days_in_month * rng.normal(1, 0.03)
        rows.append((s["store_id"], str(p), round(sales, 1), days, p.days_in_month))
M = pd.DataFrame(rows, columns=["store_id", "ym", "sales", "open_days", "days_in_month"])
M.to_csv(DATA / "monthly.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("monthly", M)
q = [x for x in (SQL / "02_same_store_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
D = con.execute(q[0]).df().set_index("ym")
# pandas
M["year"] = M.ym.str[:4].astype(int); M["mm"] = M.ym.str[5:]
cur = M[M.year == 2025].set_index(["store_id", "mm"]); prv = M[M.year == 2024].set_index(["store_id", "mm"])
full = lambda d: d.open_days == d.days_in_month
j = cur.join(prv, rsuffix="_p", how="inner")
same = j[full(j) & (j.open_days_p == j.days_in_month_p)]
old_ids = {x["store_id"] for x in stores if x["open"] < pd.Timestamp("2024-01-01")}
same13 = same[same.index.get_level_values("store_id").isin(old_ids)]
P = pd.DataFrame({"all": cur.groupby("mm").sales.sum(), "all_p": prv.groupby("mm").sales.sum(),
                  "same": same.groupby("mm").sales.sum(), "same_p": same.groupby("mm").sales_p.sum(),
                  "sd": cur.groupby("mm").open_days.sum(), "sd_p": prv.groupby("mm").open_days.sum(),
                  "n_all": cur.groupby("mm").size(), "n_same": same.groupby("mm").size(),
                  "s13": same13.groupby("mm").sales.sum(), "s13_p": same13.groupby("mm").sales_p.sum()})
P.index = ["2025-" + m for m in P.index]
assert np.allclose(P["all"], D.sales_all) and np.allclose(P.all_p, D.sales_all_prev) and np.allclose(P.same, D.sales_same) and np.allclose(P.same_p, D.sales_same_prev)
P["Y1_all"] = (P["all"] / P.all_p - 1) * 100; P["Y2_same"] = (P.same / P.same_p - 1) * 100
P["Y4_same_old"] = (P.s13 / P.s13_p - 1) * 100
P["Y3_per_store_day"] = ((P["all"] / P.sd) / (P.all_p / P.sd_p) - 1) * 100
P.round(3).to_csv(RES / "monthly_yoy.csv")
ann = lambda a, b: (P[a].sum() / P[b].sum() - 1) * 100
out = {"stores_end_2023": 100, "opened_2024": 8, "opened_2025": 18, "closed_2024": 3, "closed_2025": 10,
       "true_same_store_growth_pct": 1.0,
       "annual_2025": {"Y1_all": round(ann("all", "all_p"), 2), "Y2_same": round(ann("same", "same_p"), 2), "Y4_same_old": round(ann("s13", "s13_p"), 2),
                       "Y3_per_store_day": round(float(((P["all"].sum() / P.sd.sum()) / (P.all_p.sum() / P.sd_p.sum()) - 1) * 100), 2)},
       "monthly": {m: {"Y1": round(float(P.loc[m, "Y1_all"]), 1), "Y2": round(float(P.loc[m, "Y2_same"]), 1), "Y3": round(float(P.loc[m, "Y3_per_store_day"]), 1), "Y4": round(float(P.loc[m, "Y4_same_old"]), 1),
                       "n_all": int(P.loc[m, "n_all"]), "n_same": int(P.loc[m, "n_same"])} for m in P.index},
       "Y1_range": [round(float(P.Y1_all.min()), 1), round(float(P.Y1_all.max()), 1)],
       "Y2_range": [round(float(P.Y2_same.min()), 1), round(float(P.Y2_same.max()), 1)],
       "Y4_range": [round(float(P.Y4_same_old.min()), 1), round(float(P.Y4_same_old.max()), 1)],
       "Y3_range": [round(float(P.Y3_per_store_day.min()), 1), round(float(P.Y3_per_store_day.max()), 1)]}
json.dump(out, open(RES / "a661_main.json", "w"), ensure_ascii=False, indent=1)

lab = [m[5:] + "月" for m in P.index]
# 図1
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(lab, P.Y1_all, marker="o", color=ORANGE, label="全店の合計どうし")
ax.plot(lab, P.Y2_same, marker="s", color=BLUE, label="既存店だけ")
ax.plot(lab, P.Y3_per_store_day, marker="^", color=GREEN, label="店×営業日あたり")
ax.plot(lab, P.Y4_same_old, marker="d", color=GRAY, label="既存店のうち2023年以前からの店")
ax.axhline(1, color="black", ls="--", lw=1, label="本当の既存店の伸び +1%"); ax.axhline(0, color=GRAY, lw=0.6)
ax.set_ylabel("2025年の前年比（%）"); ax.legend(frameon=False, fontsize=9); ax.set_title("全店の前年比は、新店が増えるほど上に離れていく")
save(fig, "a661_yoy.png", SRC)
# 図2：店の数
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.bar(lab, P.n_all, color=LIGHT, label="その月に営業した店")
ax.bar(lab, P.n_same, color=BLUE, label="既存店（前年も今年もまる1か月）")
ax.set_ylabel("店の数"); ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_ylim(0, P.n_all.max() * 1.15)
ax.set_title("既存店に入るのは、営業した店の8〜9割")
save(fig, "a661_store_counts.png", SRC)
# 図3：年間
fig, ax = plt.subplots(figsize=(8.5, 3.6))
lab3 = ["全店の合計どうし", "店×営業日あたり", "既存店だけ", "既存店のうち2023年以前からの店"]
v3 = [out["annual_2025"]["Y1_all"], out["annual_2025"]["Y3_per_store_day"], out["annual_2025"]["Y2_same"], out["annual_2025"]["Y4_same_old"]]
ax.barh(lab3[::-1], v3[::-1], color=[ORANGE, GREEN, BLUE, GRAY][::-1])
for i, v in enumerate(v3[::-1]):
    ax.text(v, i, f" {v:+.1f}%", va="center", fontsize=9)
ax.axvline(1, color="black", ls="--", lw=1); ax.set_xlim(min(0, min(v3)) - 1, max(v3) * 1.25); ax.set_xlabel("2025年の年間の前年比（%）")
ax.set_title("年間でも、全店の前年比は既存店の何倍にも見える")
save(fig, "a661_annual.png", SRC, y=-0.05)
print(json.dumps(out, ensure_ascii=False, indent=1))
