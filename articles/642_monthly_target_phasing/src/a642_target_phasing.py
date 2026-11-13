"""642 年間の目標を12等分するか、前年の月の比率で分けるかで、「達成した月」の数はどれだけ違うのか

架空の200店の月次売上（2022〜2025年。季節の波は店で少しずつ違い、月ごとの偶然の振れ・年の伸びあり）を作る。
2025年の年間目標＝2024年の売上×1.03 を、
  E 12等分／L 前年（2024年）の月の比率／A 3年（2022〜2024年）平均の月の比率
で月に分け、2025年の実績で、達成した月の数・月ごとの達成率の振れを比べる。DuckDB（1スレッド）の SQL と Python の目標が一致することを確かめる。
数字は置いた季節の波と振れで決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の店別の月次売上（作成者が乱数で作成、seed 642）"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(642)
NS = 200
base_season = np.array([0.88, 0.80, 0.98, 0.97, 1.00, 0.95, 1.08, 1.12, 0.93, 0.98, 1.00, 1.31])
rows = []
for s in range(1, NS + 1):
    level = rng.lognormal(np.log(800), 0.5)               # 万円/月
    season = base_season * np.exp(rng.normal(0, 0.04, 12)); season /= season.mean()
    g = rng.normal(0.03, 0.03)
    for yi, yr in enumerate([2022, 2023, 2024, 2025]):
        noise = np.exp(rng.normal(0, 0.06, 12))
        for m in range(12):
            rows.append((f"S{s:03d}", yr, m + 1, round(level * (1 + g) ** yi * season[m] * noise[m], 1)))
MS = pd.DataFrame(rows, columns=["store_id", "yr", "mon", "sales"])
AT = MS[MS.yr == 2024].groupby("store_id").sales.sum().mul(1.03).round(1).rename("annual_target").reset_index()
MS.to_csv(DATA / "monthly_sales.csv", index=False); AT.to_csv(DATA / "annual_target.csv", index=False)

# Python
p = MS.pivot_table(index=["store_id", "yr"], columns="mon", values="sales")
share = p.div(p.sum(1), axis=0)
tgt = AT.set_index("store_id").annual_target
E = pd.DataFrame(np.outer(tgt / 12, np.ones(12)), index=tgt.index, columns=range(1, 13))
L = share.xs(2024, level="yr").mul(tgt, axis=0)
A = share.loc[(slice(None), [2022, 2023, 2024]), :].groupby(level="store_id").mean().mul(tgt, axis=0)
act = p.xs(2025, level="yr")
# SQL
con = duckdb.connect(); con.execute("SET threads=1"); con.register("monthly_sales", MS); con.register("annual_target", AT)
sq = con.execute((SQL / "02_phasing_duckdb.sql").read_text(encoding="utf-8")).df()
for col, T in [("target_equal", E), ("target_ly", L), ("target_3y", A)]:
    assert np.allclose(sq.pivot(index="store_id", columns="mon", values=col).values, T.loc[sq.store_id.unique()].values), col

res = {}
for k, T in [("E", E), ("L", L), ("A", A)]:
    r = act / T * 100
    res[k] = r
    r.round(2).to_csv(RES / f"achievement_{k}.csv")
summ = {}
for k, r in res.items():
    ach = (r >= 100).sum(1)
    summ[k] = {"months_achieved_mean": round(float(ach.mean()), 2), "months_achieved_sd": round(float(ach.std()), 2),
               "stores_0_3": int((ach <= 3).sum()), "stores_9_12": int((ach >= 9).sum()),
               "within_store_sd_pt": round(float(r.std(1).mean()), 2),
               "dec_ach_mean": round(float(r[12].mean()), 1), "feb_ach_mean": round(float(r[2].mean()), 1),
               "month_mean_min": round(float(r.mean().min()), 1), "month_mean_max": round(float(r.mean().max()), 1),
               "months_below90_per_store": round(float((r < 90).sum(1).mean()), 2)}
annual_ach = act.sum(1) / tgt * 100
out = {"stores": NS, "annual_achieved_stores": int((annual_ach >= 100).sum()), "annual_ach_median": round(float(annual_ach.median()), 1),
       "summary": summ,
       "month_mean": {k: [round(float(x), 1) for x in r.mean().values] for k, r in res.items()},
       "dist_months_achieved": {k: (r >= 100).sum(1).value_counts().sort_index().to_dict() for k, r in res.items()}}
for k, r in res.items():
    ach = (r >= 100).sum(1)
    summ[k]["corr_months_vs_annual"] = round(float(np.corrcoef(ach, annual_ach.loc[ach.index])[0, 1]), 3)
    summ[k]["annual_ok_stores_months_mean"] = round(float(ach[annual_ach.loc[ach.index] >= 100].mean()), 2)
    summ[k]["annual_ng_stores_months_mean"] = round(float(ach[annual_ach.loc[ach.index] < 100].mean()), 2)
pd.DataFrame(summ).T.to_csv(RES / "summary.csv")
json.dump(out, open(RES / "a642_main.json", "w"), ensure_ascii=False, indent=1, default=int)

lab = {"E": "12等分", "L": "前年の月の比率", "A": "3年平均の月の比率"}
col = {"E": ORANGE, "L": BLUE, "A": GREEN}
# 図1：月ごとの達成率（全店の平均）
fig, ax = plt.subplots(figsize=(8.5, 4))
for k in ["E", "L", "A"]:
    ax.plot(range(1, 13), res[k].mean().values, marker="o", color=col[k], label=lab[k])
ax.axhline(100, color=GRAY, lw=0.8, ls="--"); ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
ax.set_ylabel("達成率（%、200店の平均）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("12等分では、達成率は季節の波そのものになる（2025年）")
save(fig, "a642_by_month.png", SRC)

# 図2：達成した月の数の分布
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(13); w = 0.28
for i, k in enumerate(["E", "L", "A"]):
    v = (res[k] >= 100).sum(1).value_counts().reindex(x, fill_value=0).values
    ax.bar(x + (i - 1) * w, v, w, color=col[k], label=f"{lab[k]}（平均{summ[k]['months_achieved_mean']:.1f}か月）")
ax.set_xticks(x); ax.set_xlabel("1年のうち達成した月の数"); ax.set_ylabel("店の数（200店中）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("達成した月の数：目標の分け方で、店ごとの数の散らばりが変わる")
save(fig, "a642_months_achieved.png", SRC)

# 図3：店の中での月ごとの達成率の振れ（標準偏差）
fig, ax = plt.subplots(figsize=(8, 3.6))
ks = ["E", "L", "A"]; v = [summ[k]["within_store_sd_pt"] for k in ks]
ax.barh([lab[k] for k in ks][::-1], v[::-1], color=[col[k] for k in ks][::-1])
for i, x_ in enumerate(v[::-1]):
    ax.text(x_, i, f" {x_:.1f}ポイント", va="center", fontsize=9)
ax.set_xlim(0, max(v) * 1.35); ax.set_xlabel("1店の中での、月の達成率の標準偏差（200店の平均、ポイント）")
ax.set_title("月ごとの達成率の振れ：季節を入れると半分前後に")
save(fig, "a642_within_sd.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))
