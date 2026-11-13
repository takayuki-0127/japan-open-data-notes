"""655 平均の購入間隔を「2回以上買った人」だけで出すと、本当の間隔よりどれだけ短く出るのか

架空の会員1万人。2024-01-01〜2025-12-31 のあいだに少しずつ登録し、登録した日から観察の終わり（2025-12-31）まで買い物をする。
1人ずつ「本当の平均の購入間隔」を持ち（中央値90日、人による差が大きい）、購入はその間隔でランダムに起きる（ポアソン）。
  I0 本当の間隔の平均（1人を同じ重さで）
  I1 2回以上買った人だけで、購入と購入のあいだの日数を平均（よくある出し方）
  I2 2回以上買った人ごとの平均間隔を、人で平均
  I3 見ていた日数の合計 ÷ 購入回数の合計（最後の購入のあとも数に入れる、生存分析の考え方）
  I4 登録から1年以上たった人だけで I1
DuckDB（1スレッド）と pandas の一致を確かめる。seed 655。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空の会員と購入（作成者が乱数で作成、seed 655）"
rng = np.random.default_rng(655)
N = 10000
END = pd.Timestamp("2025-12-31")
reg = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 730, N), unit="D")
m = np.exp(rng.normal(np.log(90), 0.7, N))          # 本当の平均の購入間隔（日）
obs = (END - reg).days.values.astype(float)
rows = []
for i in range(N):
    t = rng.exponential(m[i])
    while t < obs[i]:
        rows.append((i + 1, reg[i] + pd.Timedelta(days=int(t)))); t += rng.exponential(m[i])
P = pd.DataFrame(rows, columns=["customer_id", "bought_on"]).drop_duplicates().sort_values(["customer_id", "bought_on"]).reset_index(drop=True)
C = pd.DataFrame({"customer_id": np.arange(1, N + 1), "registered_on": reg, "true_interval": m.round(2)})
C[["customer_id", "registered_on"]].assign(registered_on=C.registered_on.dt.strftime("%Y-%m-%d")).to_csv(DATA / "customers.csv", index=False)
P.assign(bought_on=P.bought_on.dt.strftime("%Y-%m-%d")).to_csv(DATA / "purchases.csv", index=False)
C[["customer_id", "true_interval"]].to_csv(RES / "true_interval.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("purchases", P.assign(bought_on=P.bought_on.dt.date)); con.register("customers", C[["customer_id", "registered_on"]].assign(registered_on=C.registered_on.dt.date))
q = [x for x in (SQL / "02_interval_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
r1 = con.execute(q[0]).df().iloc[0]; r2 = con.execute(q[1]).df().iloc[0]
P["gap"] = P.groupby("customer_id").bought_on.diff().dt.days
I1 = P.gap.mean()
I2 = P.dropna().groupby("customer_id").gap.mean().mean()
I3 = obs.sum() / len(P)
assert np.isclose(r1.mean_gap_2plus, I1) and np.isclose(r2.days_per_purchase, I3)
long = set(C.customer_id[obs >= 365])
I4 = P[P.customer_id.isin(long)].gap.mean()
npur = P.groupby("customer_id").size().reindex(C.customer_id).fillna(0).values
I0 = m.mean(); I0_med = np.median(m)
# I3 が当てているのは「全体で見て何日に1回買われるか」（見ていた日数で重みを付けた、購入の頻度の逆数）
I0_harm = obs.sum() / (obs / m).sum()
# 観察の長さ別
C["obs_days"] = obs; C["n"] = npur
bins = [0, 90, 180, 365, 545, 731]; labs = ["〜3か月", "3〜6か月", "6〜12か月", "12〜18か月", "18〜24か月"]
C["obs_bin"] = pd.cut(C.obs_days, bins, labels=labs, right=False)
P2 = P.merge(C[["customer_id", "obs_bin"]], on="customer_id")
byb = pd.DataFrame({"customers": C.groupby("obs_bin", observed=False).size(),
                    "share_2plus_pct": C.groupby("obs_bin", observed=False).n.apply(lambda s: (s >= 2).mean() * 100),
                    "I1": P2.dropna().groupby("obs_bin", observed=False).gap.mean(),
                    "true_mean_of_2plus": C[C.n >= 2].groupby("obs_bin", observed=False).true_interval.mean(),
                    "true_mean_all": C.groupby("obs_bin", observed=False).true_interval.mean()})
byb.round(2).to_csv(RES / "by_observation_length.csv")
out = {"customers": N, "purchases": len(P), "share_customers_2plus_pct": round(float((npur >= 2).mean() * 100), 1),
       "share_customers_0_pct": round(float((npur == 0).mean() * 100), 1),
       "I0_true_mean_interval": round(float(I0), 1), "I0_true_median": round(float(I0_med), 1),
       "I1_gap_mean_2plus": round(float(I1), 1), "I2_person_mean_2plus": round(float(I2), 1),
       "I3_days_per_purchase": round(float(I3), 1), "I4_gap_mean_obs_1y_plus": round(float(I4), 1),
       "I1_vs_I0_pct": round(float((I1 / I0 - 1) * 100), 1), "I2_vs_I0_pct": round(float((I2 / I0 - 1) * 100), 1),
       "I3_vs_I0_pct": round(float((I3 / I0 - 1) * 100), 1), "I4_vs_I0_pct": round(float((I4 / I0 - 1) * 100), 1),
       "true_mean_interval_of_2plus_buyers": round(float(C[C.n >= 2].true_interval.mean()), 1),
       "true_mean_interval_of_0or1_buyers": round(float(C[C.n < 2].true_interval.mean()), 1),
       "true_days_per_purchase_overall": round(float(I0_harm), 1), "I3_vs_true_overall_pct": round(float((I3 / I0_harm - 1) * 100), 1),
       "by_obs": {k: {c: round(float(byb.loc[k, c]), 1) for c in byb.columns} for k in labs}}
json.dump(out, open(RES / "a655_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：出し方ごと
fig, ax = plt.subplots(figsize=(8.5, 4.2))
lab = ["本当：1人ずつの間隔の平均", "本当：全体で何日に1回", "2回以上の人：間隔の平均", "2回以上の人：1人ずつの平均", "1年以上見た人：間隔の平均", "見ていた日数÷購入回数"]
val = [I0, I0_harm, I1, I2, I4, I3]; col = [GRAY, GRAY, ORANGE, ORANGE, BLUE, GREEN]
ax.barh(lab[::-1], val[::-1], color=col[::-1])
for i, v in enumerate(val[::-1]):
    ax.text(v, i, f" {v:.0f}日", va="center", fontsize=9)
ax.set_xlim(0, max(val) * 1.2); ax.set_xlabel("平均の購入間隔（日）")
ax.set_title("2回以上買った人だけで出すと、本当の半分より短くなる")
save(fig, "a655_methods.png", SRC)
# 図2：観察の長さ別
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(len(labs)); w = 0.27
ax.bar(x - w, byb.true_mean_all, w, color=GRAY, label="本当の間隔（その人たち全員）")
ax.bar(x, byb.true_mean_of_2plus, w, color=LIGHT, label="本当の間隔（2回以上買った人）")
ax.bar(x + w, byb.I1, w, color=ORANGE, label="測った間隔の平均（2回以上の人）")
ax.set_xticks(x); ax.set_xticklabels([f"{l}\n（2回以上 {s:.0f}%）" for l, s in zip(labs, byb.share_2plus_pct)], fontsize=8.5)
ax.set_ylabel("日"); ax.legend(frameon=False, fontsize=8.5); ax.set_xlabel("登録から観察の終わりまでの長さ")
ax.set_title("登録して間もない人ほど、2回以上買えるのは間隔の短い人だけ")
save(fig, "a655_by_obs.png", SRC)
# 図3：残る人の本当の間隔
fig, ax = plt.subplots(figsize=(8, 3.8))
bins_h = np.arange(0, 600, 15)
ax.hist(C[C.n >= 2].true_interval.clip(upper=595), bins=bins_h, color=BLUE, alpha=0.7, label="2回以上買った人")
ax.hist(C[C.n < 2].true_interval.clip(upper=595), bins=bins_h, color=ORANGE, alpha=0.6, label="0回か1回の人（計算から外れる）")
ax.set_xlabel("本当の平均の購入間隔（日、595日以上はまとめた）"); ax.set_ylabel("人数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("計算から外れるのは、間隔の長い人")
save(fig, "a655_who_dropped.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
