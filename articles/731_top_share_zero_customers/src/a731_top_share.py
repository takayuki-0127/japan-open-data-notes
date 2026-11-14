"""731 「上位10%の顧客で売上の何割」を、買わなかった会員を含めて数えるか除くかで、どれだけ違うのか

架空の会員10,000人の12か月の購入（月ごとの合計）。
  会員ごとの買う頻度：ガンマ分布（形0.35、平均は月0.4回）。買わない月が多い会員も、ほとんど買わない会員もいる
  1回の金額：対数正規（中央値3,000円）
「上位10%の売上シェア」を2通りで出す：
  買った人だけ：その期間に1回以上買った人を金額順に並べ、上位10%の人の売上÷全体
  会員全員：買わなかった会員も0円として並べ、上位10%（1,000人）の売上÷全体
期間を 1・3・6・12か月に変えて比べる。DuckDB の SQL と Python の結果が一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の会員10,000人の購入（作成者が乱数で作成、seed 731）"
rng = np.random.default_rng(731)
DATA.mkdir(exist_ok=True)
N, MONTHS = 10000, 12
rate = rng.gamma(0.35, 0.4 / 0.35, N)
rows = []
for m in range(1, MONTHS + 1):
    k = rng.poisson(rate)
    for i in np.nonzero(k)[0]:
        amt = int(np.round(rng.lognormal(np.log(3000), 0.7, k[i]).sum(), -1))
        rows.append((f"M{i+1:05d}", m, amt))
P = pd.DataFrame(rows, columns=["member_id", "month", "amount"])
M = pd.DataFrame({"member_id": [f"M{i+1:05d}" for i in range(N)]})
P.to_csv(DATA / "purchases.csv", index=False); M.to_csv(DATA / "members.csv", index=False)


def shares(months):
    a = M.merge(P[P.month <= months].groupby("member_id", as_index=False).amount.sum(), on="member_id", how="left").fillna({"amount": 0})
    a = a.sort_values(["amount", "member_id"], ascending=[False, True]); tot = a.amount.sum()
    top_all = a.head(int(np.ceil(0.1 * len(a)))).amount.sum() / tot
    b = a[a.amount > 0]; top_buy = b.head(int(np.ceil(0.1 * len(b)))).amount.sum() / tot
    return top_all, top_buy, len(b), a


con = duckdb.connect(); con.execute("SET threads=1")
con.register("m0", M); con.register("p0", P)
con.execute("CREATE TABLE members AS SELECT * FROM m0"); con.execute("CREATE TABLE purchases AS SELECT * FROM p0")
sql = (SQL / "02_top_share_duckdb.sql").read_text(encoding="utf-8")
rows = []
for months in [1, 3, 6, 12]:
    ta, tb, nb, a = shares(months)
    dq = con.execute(sql.replace(":months", str(months))).df().set_index("base")
    assert abs(dq.loc["members", "top10_share"] - ta) < 1e-12 and abs(dq.loc["buyers", "top10_share"] - tb) < 1e-12, months
    assert int(dq.loc["buyers", "people"]) == nb
    rows.append({"months": months, "buyers": nb, "buyers_pct": nb / N * 100, "top10_members_pct": ta * 100, "top10_buyers_pct": tb * 100,
                 "people_top_members": int(np.ceil(0.1 * N)), "people_top_buyers": int(np.ceil(0.1 * nb))})
S = pd.DataFrame(rows); S.round(3).to_csv(RES / "by_period.csv", index=False)
# 12か月のローレンツ曲線
_, _, _, a12 = shares(12)
v = a12.amount.values[::-1]; cum = np.r_[0, np.cumsum(v) / v.sum()]; xs = np.linspace(0, 1, len(cum))
vb = v[v > 0]; cumb = np.r_[0, np.cumsum(vb) / vb.sum()]; xb = np.linspace(0, 1, len(cumb))

s12 = S.set_index("months").loc[12]
out = {"members": N, "months": MONTHS, "purchase_rows": len(P),
       "by_period": {str(int(r.months)): {"buyers": int(r.buyers), "buyers_pct": round(r.buyers_pct, 1),
                                          "top10_members_pct": round(r.top10_members_pct, 1), "top10_buyers_pct": round(r.top10_buyers_pct, 1)} for r in S.itertuples()},
       "gap_12m_pt": round(float(s12.top10_members_pct - s12.top10_buyers_pct), 1), "sql_matches_python": True}
json.dump(out, open(RES / "a731_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：12か月の2通り
fig, ax = plt.subplots(figsize=(7, 3.6))
vals = [s12.top10_buyers_pct, s12.top10_members_pct]
ax.bar([f"買った人だけ\n（{int(s12.buyers):,}人の上位{int(np.ceil(0.1 * s12.buyers)):,}人）", f"会員全員\n（{N:,}人の上位{N // 10:,}人）"], vals, color=[BLUE, ORANGE])
for i, v_ in enumerate(vals): ax.text(i, v_ + 1, f"{v_:.1f}%", ha="center")
ax.set_ylabel("上位10%の売上シェア（%）"); ax.set_ylim(0, 100)
ax.set_title("同じ12か月の売上でも、分母の人で「上位10%のシェア」が変わる")
save(fig, "a731_two_bases.png", SRC)

# 図2：期間ごと
fig, ax = plt.subplots(figsize=(8, 3.8)); xx = [f"{m}か月" for m in S.months]
ax.plot(xx, S.top10_members_pct, marker="o", color=ORANGE, label="会員全員の上位10%")
ax.plot(xx, S.top10_buyers_pct, marker="o", color=BLUE, label="買った人だけの上位10%")
for i, r in enumerate(S.itertuples()):
    ax.text(i, r.top10_members_pct + 2, f"{r.top10_members_pct:.0f}%", ha="center", color=ORANGE, fontsize=9)
    ax.text(i, r.top10_buyers_pct - 6, f"{r.top10_buyers_pct:.0f}%", ha="center", color=BLUE, fontsize=9)
    ax.text(i, 3, f"買った人 {r.buyers_pct:.0f}%", ha="center", color=GRAY, fontsize=8.5)
ax.set_ylim(0, 105); ax.set_ylabel("上位10%の売上シェア（%）"); ax.set_xlabel("集計の期間"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("期間が短いほど買わない会員が多く、2つの数え方の差が開く")
save(fig, "a731_by_period.png", SRC)

# 図3：ローレンツ曲線
fig, ax = plt.subplots(figsize=(6, 4.2))
ax.plot(xs * 100, cum * 100, color=ORANGE, label="会員全員（買わなかった人も0円で入れる）")
ax.plot(xb * 100, cumb * 100, color=BLUE, label="買った人だけ")
ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("人の割合（少ない順に並べた累積、%）"); ax.set_ylabel("売上の累積（%）"); ax.legend(frameon=False)
ax.set_title("12か月の売上の集中（ローレンツ曲線）")
save(fig, "a731_lorenz.png", SRC)
print(json.dumps(out, ensure_ascii=False))
