"""705 リピート率を「30日以内」で数えるか「90日以内」で数えるかで、月ごとの比べ方はどれだけ変わるのか

架空の顧客（初回購入 2024-01〜2025-06、データの最終日 2025-06-30）。2回目までの日数は、
「すぐ買い直す人」と「ゆっくり買い直す人」の混ざり。どの月の顧客も本当の買い直しやすさは同じに置く
（2025年1月以降の顧客だけ、すぐ買い直す人を少し増やす：本当の変化）。
  W=30・60・90日の窓、観察期間が W 日ない人を除く／除かない
を比べる。DuckDB（1スレッド）と pandas で一致を確かめる。seed 705。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の顧客の購入履歴（作成者が乱数で作成、seed 705）"
rng = np.random.default_rng(705)
END = pd.Timestamp("2025-06-30")
days = pd.date_range("2024-01-01", END)
N = 24000
first = pd.Series(rng.choice(days, size=N)).sort_values().reset_index(drop=True)
late = first >= "2025-01-01"
# 2回目までの日数：40%はすぐ（平均12日）、30%はゆっくり（平均70日）、30%は買い直さない
p_fast = np.where(late, 0.46, 0.40)
u = rng.random(N)
gap = np.where(u < p_fast, rng.exponential(12, N), np.where(u < p_fast + 0.30, rng.exponential(70, N), np.inf))
gap = np.ceil(gap)
second = first + pd.to_timedelta(np.where(np.isfinite(gap), gap, 0), unit="D")
has2 = np.isfinite(gap) & (second <= END)
rows = [pd.DataFrame({"customer_id": np.arange(1, N + 1), "purchase_date": first})]
rows.append(pd.DataFrame({"customer_id": np.arange(1, N + 1)[has2], "purchase_date": second[has2]}))
P = pd.concat(rows).sort_values(["customer_id", "purchase_date"]).reset_index(drop=True)
P.assign(purchase_date=P.purchase_date.dt.strftime("%Y-%m-%d")).to_csv(DATA / "purchases.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("purchases", P)
q = [x for x in (SQL / "02_repeat_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
S = con.execute(q[0]).df()
# pandas
f = P.groupby("customer_id").purchase_date.agg(first_date="min")
f["second_date"] = P.groupby("customer_id").purchase_date.apply(lambda s: s.iloc[1] if len(s) > 1 else pd.NaT)
f["cohort"] = f.first_date.dt.to_period("M").dt.to_timestamp()
res = {}
for W in [30, 60, 90]:
    hit = (f.second_date <= f.first_date + pd.Timedelta(days=W)).astype(float)
    r = hit.groupby(f.cohort).mean() * 100
    month_end = r.index + pd.offsets.MonthEnd(0)
    res[f"rate{W}"] = r
    res[f"rate{W}_complete"] = r.where(month_end + pd.Timedelta(days=W) <= END)  # 月の最後の日から W 日たった月だけ
T = pd.DataFrame(res); T["customers"] = f.groupby("cohort").size()
assert np.allclose(T.rate30.values, S.rate30.values * 100) and np.allclose(T.rate90.values, S.rate90.values * 100)
assert np.allclose(T.rate90_complete.dropna().values, S.rate90_complete.dropna().values * 100)
T.round(2).to_csv(RES / "by_cohort.csv")
c = T.index
early = (c >= "2024-07-01") & (c <= "2024-12-01"); late6 = (c >= "2025-01-01")
out = {"customers": N, "first_purchase_period": "2024-01-01〜2025-06-30", "data_end": "2025-06-30",
       "true_change": "2025年1月以降の顧客は、すぐ買い直す人が40%→46%（作成者が置いた）",
       "rate_2024H2_mean": {k: round(float(T.loc[early, k].mean()), 1) for k in ["rate30", "rate60", "rate90"]},
       "rate_2025H1_mean": {k: round(float(T.loc[late6, k].mean()), 1) for k in ["rate30", "rate60", "rate90"]},
       "rate_2025_complete_months_mean": {k: round(float(T.loc[late6, k + "_complete"].mean()), 1) for k in ["rate30", "rate60", "rate90"]},
       "complete_last_cohort": {k: str(T[k + "_complete"].last_valid_index().date()) for k in ["rate30", "rate60", "rate90"]},
       "last_cohort_2025_06": {k: round(float(T.loc["2025-06-01", k]), 1) for k in ["rate30", "rate60", "rate90"]},
       "cohort_2025_03": {k: round(float(T.loc["2025-03-01", k]), 1) for k in ["rate30", "rate60", "rate90"]},
       "complete_months_available": {W: int(T[f"rate{W}_complete"].notna().sum()) for W in [30, 60, 90]}}
out["complete_months_available"] = {str(k): v for k, v in out["complete_months_available"].items()}
json.dump(out, open(RES / "a705_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：窓の長さごとの月別リピート率（除かない）
fig, ax = plt.subplots(figsize=(8.5, 3.8))
for W, col in [(30, BLUE), (60, GREEN), (90, ORANGE)]:
    ax.plot(T.index, T[f"rate{W}"], "o-", ms=3, color=col, label=f"{W}日以内")
ax.axvline(pd.Timestamp("2025-01-01"), color=GRAY, lw=0.8, ls="--")
ax.set_ylabel("リピート率（%）"); ax.set_xlabel("初回購入の月"); ax.legend(frameon=False, fontsize=9)
ax.set_title("窓が長いほど、直近の月が「落ちた」ように見える（本当は1月から少し上がった）")
save(fig, "a705_by_window.png", SRC)
# 図2：90日：除かない／除く
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.plot(T.index, T.rate90, "o-", ms=3, color=ORANGE, label="90日以内（観察期間の足りない人も分母に入れる）")
ax.plot(T.index, T.rate90_complete, "s-", ms=3, color=BLUE, label="90日以内（月の最後の日から90日たった月だけ）")
ax.axvline(pd.Timestamp("2025-01-01"), color=GRAY, lw=0.8, ls="--")
ax.set_ylabel("リピート率（%）"); ax.set_xlabel("初回購入の月"); ax.legend(frameon=False, fontsize=9)
ax.set_title("観察期間の足りない月を出さないと、1月からの上がりが見える（最後の3か月は出せない）")
save(fig, "a705_complete.png", SRC)
# 図3：窓の長さ（1〜120日）と 2024年後半の平均リピート率
Ws = np.arange(1, 121)
fe = f[(f.cohort >= "2024-07-01") & (f.cohort <= "2024-12-01")]
curve = [((fe.second_date <= fe.first_date + pd.Timedelta(days=int(w))).mean() * 100) for w in Ws]
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(Ws, curve, color=BLUE)
for w in [30, 60, 90]:
    ax.scatter([w], [curve[w - 1]], color=ORANGE, zorder=3); ax.annotate(f"{w}日：{curve[w - 1]:.0f}%", (w, curve[w - 1]), xytext=(4, -12), textcoords="offset points", fontsize=9)
ax.set_xlabel("窓の長さ（初回から何日以内）"); ax.set_ylabel("リピート率（%）")
ax.set_title("同じ顧客でも、窓の長さでリピート率は大きく変わる（2024年7〜12月の初回）")
save(fig, "a705_window_curve.png", SRC)
pd.DataFrame({"window_days": Ws, "rate_2024H2": np.round(curve, 2)}).to_csv(RES / "window_curve.csv", index=False)
print(json.dumps(out, ensure_ascii=False, indent=1))
