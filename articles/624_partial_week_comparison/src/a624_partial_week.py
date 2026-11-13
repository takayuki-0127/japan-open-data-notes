"""624 週の途中の数字を先週の合計と比べると、どれだけ低く見えるのか

架空の日次売上 2024〜2025年（2年分）を2つの業態で作る。
  店頭型：土日に多い（平日 1、土 1.7、日 1.6）
  事務所型：平日に多い（平日 1、土 0.25、日 0.1）
どちらも本当の水準は変えない（週ごとの振れと日ごとの振れだけ）。週は月曜始まり。
各曜日の夜に「今週ここまで」を3通りの相手と比べる：
  W1 先週の合計、W2 先週の同じ曜日までの合計、W3 直近7日とその前の7日
見かけの増減（%）の平均と散らばり、「10%以上下がった」と出る割合を曜日ごとに数える。
SQL（DuckDB、1スレッド）で W1・W2 の合計を出し、Python と一致を確かめる。数字は置いた曜日の波と振れで決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の日次売上（作成者が乱数で作成、seed 624）"
rng = np.random.default_rng(624)
days = pd.date_range("2024-01-01", "2025-12-31")   # 2024-01-01 は月曜
PAT = {"店頭型": [1, 1, 1, 1, 1.05, 1.7, 1.6], "事務所型": [1, 1, 1, 1, 1, 0.25, 0.1]}
frames = []
for k, pat in PAT.items():
    wk = np.repeat(rng.normal(1, 0.05, len(days) // 7 + 1), 7)[: len(days)]
    s = 100_000 * np.array(pat)[days.dayofweek] * wk * rng.normal(1, 0.08, len(days))
    frames.append(pd.DataFrame({"store": k, "d": days, "sales": np.round(s).astype(int)}))
DF = pd.concat(frames, ignore_index=True)
DOW = ["月", "火", "水", "木", "金", "土", "日"]

rows = []
for k, g in DF.groupby("store"):
    x = g.set_index("d").sales
    cs = x.cumsum()
    for t in x.index[14:]:
        wk = t - pd.Timedelta(days=t.dayofweek)
        this = x[wk:t].sum()
        last_total = x[wk - pd.Timedelta(days=7): wk - pd.Timedelta(days=1)].sum()
        last_same = x[wk - pd.Timedelta(days=7): t - pd.Timedelta(days=7)].sum()
        r7 = x[t - pd.Timedelta(days=6): t].sum(); p7 = x[t - pd.Timedelta(days=13): t - pd.Timedelta(days=7)].sum()
        rows.append({"store": k, "d": t, "dow": t.dayofweek, "this": this, "W1": 100 * (this / last_total - 1),
                     "W2": 100 * (this / last_same - 1), "W3": 100 * (r7 / p7 - 1), "last_total": last_total, "last_same": last_same})
R = pd.DataFrame(rows)
R.round(3).to_csv(RES / "daily_comparisons.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
agg = R.groupby(["store", "dow"]).agg(**{f"{m}_{f}": (m, f) for m in ["W1", "W2", "W3"] for f in ["mean", "std"]},
                                      **{f"{m}_alert": (m, lambda v: 100 * (v <= -10).mean()) for m in ["W1", "W2", "W3"]}).round(2).reset_index()
agg["dow_name"] = [DOW[i] for i in agg.dow]
agg.to_csv(RES / "summary.csv", index=False)

# SQL で2025-06-18（水）の店頭型を確かめる
con = duckdb.connect(); con.execute("SET threads=1"); con.register("daily", DF)
q = (SQL / "02_week_to_date_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
q = q[q.index("WITH"):]
asof = pd.Timestamp("2025-06-18")
a, b, c = con.execute(q, {"asof": asof.date(), "store": "店頭型"}).fetchone()
r = R[(R.store == "店頭型") & (R.d == asof)].iloc[0]
assert a == r["this"] and b == r.last_total and c == r.last_same
pd.DataFrame([{"asof": "2025-06-18", "store": "店頭型", "this_week_to_date": a, "last_week_total": b, "last_week_to_same_day": c}]).to_csv(RES / "sql_example.csv", index=False)

out = {"stores": list(PAT), "pattern": PAT, "summary": agg.to_dict(orient="records"),
       "alert_rate_overall": {k: {m: round(float(100 * (R[R.store == k][m] <= -10).mean()), 2) for m in ["W1", "W2", "W3"]} for k in PAT}}
json.dump(out, open(RES / "a624_main.json", "w"), ensure_ascii=False, indent=1)

COL = {"W1": ORANGE, "W2": BLUE, "W3": GREEN}
LAB = {"W1": "今週ここまで ÷ 先週の合計", "W2": "今週ここまで ÷ 先週の同じ曜日まで", "W3": "直近7日 ÷ その前の7日"}
# 図1：見かけの増減の平均
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"wspace": 0.25})
for i, k in enumerate(PAT):
    a_ = agg[agg.store == k]
    for m in ["W1", "W2", "W3"]:
        ax[i].plot(DOW, a_[f"{m}_mean"], marker="o", color=COL[m], label=LAB[m])
    for xx, v in zip(range(7), a_["W1_mean"]):
        ax[i].text(xx + 0.12, v - 7, f"{v:.0f}%", ha="left", fontsize=8.5, color=ORANGE)
    ax[i].axhline(0, color=GRAY, lw=0.8); ax[i].set_title(f"{k}（本当の水準は変えていない）"); ax[i].set_xlabel("見る曜日（その日の夜）")
    ax[i].set_ylim(-110, 15)
ax[0].set_ylabel("先週との比（%、2年分の平均）"); ax[0].legend(frameon=False, fontsize=8.5, loc="lower right")
save(fig, "a624_mean_change.png", SRC, y=-0.04)

# 図2：散らばり（店頭型、W2 と W3）
fig, ax = plt.subplots(figsize=(8.5, 4))
a_ = agg[agg.store == "店頭型"]
w = 0.38; xs = np.arange(7)
ax.bar(xs - w / 2, a_["W2_std"], w, color=BLUE, label=LAB["W2"])
ax.bar(xs + w / 2, a_["W3_std"], w, color=GREEN, label=LAB["W3"])
for xx, v in zip(xs - w / 2, a_["W2_std"]):
    ax.text(xx, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5)
ax.set_xticks(xs); ax.set_xticklabels(DOW); ax.set_ylabel("先週との比の標準偏差（ポイント）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("店頭型：同じ曜日までで比べると、週の初めほど振れが大きい")
save(fig, "a624_spread.png", SRC)

# 図3：10%以上下がったと出る割合
fig, ax = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"wspace": 0.25})
for i, k in enumerate(PAT):
    a_ = agg[agg.store == k]
    for j, m in enumerate(["W2", "W3"]):
        ax[i].bar(xs + (j - 0.5) * w, a_[f"{m}_alert"], w, color=COL[m], label=LAB[m])
    ax[i].set_xticks(xs); ax[i].set_xticklabels(DOW); ax[i].set_title(k)
ax[0].set_ylabel("「10%以上下がった」と出た日の割合（%）"); ax[0].legend(frameon=False, fontsize=8.5)
save(fig, "a624_alert.png", SRC, y=-0.04)
print(agg.to_string()); print(out["alert_rate_overall"])
