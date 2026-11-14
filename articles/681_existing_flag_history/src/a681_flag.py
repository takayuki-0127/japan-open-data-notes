"""681 「有効」フラグの立った商品だけで集計すると、廃番になった商品の過去の売上はどれだけ消えるのか

架空の商品マスタと月ごとの売上（2023年1月〜2025年12月の3年分）。
  2023年1月の時点で 200品。毎年、その時点の品の約12%が年の途中で廃番になり、新しい品が毎年25品出る。
  廃番が近い品は、最後の6か月で売上が落ちていく。廃番の品の一部（20%）は、廃番の後1〜2か月、在庫処分の売上が少しある。
  マスタは 2025年12月末の時点のもの：is_active（いま売っているか）と、valid_from・valid_to（売り始めの月・廃番の月）。
集計は3通り：
  フラグで絞る：is_active = 1 の品だけ
  期間つきで絞る：売上の月が valid_from〜valid_to の間にある行だけ
  絞らない：売上の表をそのまま
本当の売上は「絞らない」。年ごとの売上・前年比・消えた売上を比べる。DuckDB の SQL（1スレッド）でも出し、Python と一致を確かめる。
数字は置いた廃番の割合と売上で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の商品マスタと売上（作成者が乱数で作成、seed 681）"
rng = np.random.default_rng(681)
MONTHS = pd.period_range("2023-01", "2025-12", freq="M")
NM = len(MONTHS)
season = 1 + 0.15 * np.sin(2 * np.pi * (np.arange(NM) % 12 - 2) / 12)

prods = []                       # (id, start_idx, end_idx or None)
pid = 0
for _ in range(200):
    pid += 1; prods.append([pid, 0, None])
for y in range(3):
    alive = [p for p in prods if p[2] is None and p[1] <= 12 * y]
    for p in rng.choice(len(alive), int(round(len(alive) * 0.12)), replace=False):
        alive[p][2] = 12 * y + int(rng.integers(0, 12))       # 廃番の月（この月まで売る）
    for _ in range(25):
        pid += 1; prods.append([pid, 12 * y + int(rng.integers(0, 12)), None])
level = rng.lognormal(np.log(40), .7, pid + 1)                  # 万円/月
clear = rng.random(pid + 1) < .2

rows = []
for p, s, e in prods:
    for m in range(s, NM):
        if e is not None and m > e:
            if clear[p] and m <= e + int(1 + p % 2):
                rows.append((p, m, round(level[p] * .15 * season[m], 1)))
            continue
        ramp = min(1.0, (m - s + 1) / 4)                            # 売り始めは4か月かけて伸びる
        fade = 1.0 if e is None else min(1.0, max(.25, (e - m + 1) / 6))
        amt = level[p] * season[m] * ramp * fade * rng.lognormal(0, .15)
        rows.append((p, m, round(amt, 1)))
sales = pd.DataFrame(rows, columns=["product_id", "m", "amount"])
sales["month"] = MONTHS[sales.m].astype(str)
master = pd.DataFrame([(p, str(MONTHS[s]), str(MONTHS[e]) if e is not None else None, int(e is None)) for p, s, e in prods],
                      columns=["product_id", "valid_from", "valid_to", "is_active"])
master["product_name"] = master.product_id.map(lambda i: f"商品{i:03d}")
DATA.mkdir(exist_ok=True)
master[["product_id", "product_name", "valid_from", "valid_to", "is_active"]].to_csv(DATA / "products.csv", index=False)
sales[["month", "product_id", "amount"]].to_csv(DATA / "sales.csv", index=False)

# Python の集計
S = sales.merge(master, on="product_id")
S["year"] = S.month.str[:4].astype(int)
in_period = (S.month >= S.valid_from) & (S.valid_to.isna() | (S.month <= S.valid_to))
Y = pd.DataFrame({"none": S.groupby("year").amount.sum(),
                  "flag": S[S.is_active == 1].groupby("year").amount.sum(),
                  "period": S[in_period].groupby("year").amount.sum()})
Y.round(1).to_csv(RES / "by_year.csv")
Mo = pd.DataFrame({"none": S.groupby("month").amount.sum(), "flag": S[S.is_active == 1].groupby("month").amount.sum()})
Mo["lost_pct"] = 100 * (1 - Mo.flag / Mo.none)
Mo.round(2).to_csv(RES / "by_month.csv")

# DuckDB
con = duckdb.connect(); con.execute("SET threads=1")
con.register("products", master); con.register("sales", sales[["month", "product_id", "amount"]])
q = (SQL / "02_flag_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df().set_index("year")
for c in ["none", "flag", "period"]:
    assert np.allclose(sq[c].values, Y[c].values, atol=.05), c

yoy = {c: {str(y): round(100 * (Y[c][y] / Y[c][y - 1] - 1), 2) for y in (2024, 2025)} for c in Y}
lost = {str(y): round(float(100 * (1 - Y.flag[y] / Y.none[y])), 2) for y in Y.index}
n_disc = int(master.is_active.eq(0).sum())
clear_amt = float(S[~in_period].amount.sum())
out = {"products": int(len(master)), "discontinued": n_disc, "sales_rows": int(len(sales)),
       "sales_by_year": {c: {str(y): round(float(Y[c][y]), 1) for y in Y.index} for c in Y},
       "flag_lost_pct": lost, "yoy_pct": yoy,
       "period_lost_amount": round(clear_amt, 1),
       "period_lost_pct_total": round(100 * clear_amt / float(Y.none.sum()), 3),
       "flag_lost_pct_2023_01": round(float(Mo.lost_pct.iloc[0]), 1),
       "flag_lost_pct_2025_12": round(float(Mo.lost_pct.iloc[-1]), 1)}
json.dump(out, open(RES / "a681_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：年ごとの売上
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(3); w = .38
b1 = ax.bar(x - w / 2, Y.none / 1e4, w, color=GRAY, label="絞らない（本当の売上）")
b2 = ax.bar(x + w / 2, Y.flag / 1e4, w, color=ORANGE, label="「有効」フラグで絞る")
for b, v, l in zip(b2, Y.flag / 1e4, [lost[str(y)] for y in Y.index]):
    ax.text(b.get_x() + b.get_width() / 2, v + .3, f"{v:.1f}億円\n（−{l:.1f}%）", ha="center", fontsize=9)
for b, v in zip(b1, Y.none / 1e4):
    ax.text(b.get_x() + b.get_width() / 2, v + .3, f"{v:.1f}億円", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in Y.index]); ax.set_ylabel("売上（億円）")
ax.set_ylim(0, Y.none.max() / 1e4 * 1.22); ax.legend(frameon=False, loc="upper left", ncol=2)
ax.set_title("いま「有効」な品だけで集計すると、昔の年ほど売上が消える")
save(fig, "a681_by_year.png", SRC)

# 図2：消えた売上の割合（月ごと）
fig, ax = plt.subplots(figsize=(9, 4.6))
xm = np.arange(NM)
ax.plot(xm, Mo.lost_pct.values, color=ORANGE, lw=2.2)
ax.fill_between(xm, 0, Mo.lost_pct.values, color=ORANGE, alpha=.15)
ax.set_xticks(xm[::6]); ax.set_xticklabels([str(m) for m in MONTHS[::6]])
ax.set_ylabel("フラグで絞ると消える売上の割合（%）"); ax.set_ylim(0, Mo.lost_pct.max() * 1.15)
ax.set_title("消える割合は、集計の時点から離れた月ほど大きい（マスタは2025年12月末のもの）")
save(fig, "a681_lost_by_month.png", SRC)

# 図3：前年比
fig, ax = plt.subplots(figsize=(9, 4.4))
labels = ["絞らない（本当）", "期間つきで絞る", "「有効」フラグで絞る"]; keys = ["none", "period", "flag"]
cols = [GRAY, BLUE, ORANGE]
x = np.arange(2); w = .26
for i, (k, l, c) in enumerate(zip(keys, labels, cols)):
    vals = [yoy[k]["2024"], yoy[k]["2025"]]
    bars = ax.bar(x + (i - 1) * w, vals, w, color=c, label=l)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (.3 if v >= 0 else -.3), f"{v:+.1f}%", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=9)
ax.axhline(0, color=INK, lw=.8)
ax.set_xticks(x); ax.set_xticklabels(["2024年の前年比", "2025年の前年比"]); ax.set_ylabel("前年比（%）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("フラグで絞ると、前年比が実際より高く見える")
save(fig, "a681_yoy.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
