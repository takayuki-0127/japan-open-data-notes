"""575 顧客が引っ越したとき、売上を「売った時点の住所」で数えるか「今の住所」で数えるかで、地域別の売上はどれだけ動くのか（架空の顧客、seed 575）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

rng = np.random.default_rng(575)
SRC = "架空の顧客と住所の履歴・注文（作成者が乱数で作成、seed 575）"
REG = [f"地域{c}" for c in "ABCDEFGH"]
N = 40000
start, end = pd.Timestamp("2021-01-01"), pd.Timestamp("2025-12-31")
# 最初の住所の割合と、引っ越し先の選ばれやすさ（A・B に向かいやすい、G・H から出やすい）
p0 = np.array([.16, .14, .13, .13, .12, .12, .10, .10])
pull = np.array([2.2, 1.8, 1.0, 1.0, .9, .8, .6, .5]); pull = pull / pull.sum()
hist = []
for cid in range(1, N + 1):
    r = rng.choice(8, p=p0); t = start
    seg = [(r, t)]
    while True:
        gap = rng.exponential(365 / (.07 if r < 6 else .10))   # 1年あたりの引っ越し率 7%（G・H は10%）
        t = t + pd.Timedelta(days=int(gap))
        if t > end: break
        q = r
        while q == r: q = rng.choice(8, p=pull)
        r = q; seg.append((r, t))
    for k, (rr, tt) in enumerate(seg):
        to = seg[k + 1][1] if k + 1 < len(seg) else pd.Timestamp("9999-12-31")
        hist.append((cid, REG[rr], tt, to))
H = pd.DataFrame(hist, columns=["customer_id", "region", "valid_from", "valid_to"])
H.to_csv(DATA / "address_history.csv", index=False, date_format="%Y-%m-%d")
# 注文：1人あたり年2回くらい、金額は対数正規
n_ord = rng.poisson(10, N)
cust = np.repeat(np.arange(1, N + 1), n_ord)
od = start + pd.to_timedelta(rng.integers(0, (end - start).days + 1, len(cust)), "D")
O = pd.DataFrame({"order_id": np.arange(1, len(cust) + 1), "customer_id": cust, "ordered_on": od,
                  "amount": np.round(rng.lognormal(np.log(6000), .7, len(cust)), -1).astype(int)})
O = O.sort_values(["ordered_on", "order_id"]).reset_index(drop=True); O["order_id"] = np.arange(1, len(O) + 1)
# 1ファイル10MB未満にするため、注文は2つに分けて書き出す
O[O.ordered_on < "2024-01-01"].to_csv(DATA / "orders_2021_2023.csv", index=False, date_format="%Y-%m-%d")
O[O.ordered_on >= "2024-01-01"].to_csv(DATA / "orders_2024_2025.csv", index=False, date_format="%Y-%m-%d")

con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE address_history AS SELECT * FROM read_csv_auto('{DATA/'address_history.csv'}')")
con.execute(f"CREATE TABLE orders AS SELECT * FROM read_csv_auto(['{DATA/'orders_2021_2023.csv'}', '{DATA/'orders_2024_2025.csv'}'])")
q = (SQL / "02_region_duckdb.sql").read_text()
parts = q.split("\n-- @")                              # 3つの SQL：売った時点・今・登録時
parts = [parts[0]] + [p.split("\n", 1)[1] for p in parts[1:]]
at, now, first = [con.execute(p).df() for p in parts]
def pv(d): return d.pivot(index="region", columns="yr", values="sales").reindex(REG)
AT, NOW, FIRST = pv(at), pv(now), pv(first)
for nm, df in [("at_sale", AT), ("current", NOW), ("registered", FIRST)]: df.to_csv(RES / f"sales_{nm}.csv")
diff_now = (NOW / AT - 1) * 100; diff_first = (FIRST / AT - 1) * 100
diff_now.to_csv(RES / "diff_current_pct.csv", float_format="%.2f"); diff_first.to_csv(RES / "diff_registered_pct.csv", float_format="%.2f")
gr = lambda df: (df[2025] / df[2021] - 1) * 100
GR = pd.DataFrame({"売った時点の住所": gr(AT), "今の住所": gr(NOW), "登録時の住所": gr(FIRST)}).round(1); GR.to_csv(RES / "growth_2021_2025.csv")
# 年ごとに「違う地域に入る売上」の割合
oo = O.merge(H, on="customer_id")
oo_at = oo[(oo.valid_from <= oo.ordered_on) & (oo.ordered_on < oo.valid_to)][["order_id", "region", "amount", "ordered_on"]]
cur = H[H.valid_to == pd.Timestamp("9999-12-31")].set_index("customer_id").region
oo_at = oo_at.assign(cur=O.set_index("order_id").customer_id.reindex(oo_at.order_id).map(cur).values)
mis = oo_at.groupby(oo_at.ordered_on.dt.year).apply(lambda d: (d.amount * (d.region != d.cur)).sum() / d.amount.sum() * 100, include_groups=False)
# Python の時点の住所と SQL の一致
chk = bool((oo_at.groupby([oo_at.ordered_on.dt.year, "region"]).amount.sum().unstack(0).reindex(REG).values == AT.values).all())
rank = lambda df: df[2021].rank(ascending=False).astype(int)
moved = int(H.groupby("customer_id").size().gt(1).sum())
res = {"customers": N, "orders": len(O), "moved_customers": moved, "moved_pct": round(moved / N * 100, 1),
       "misattributed_pct_by_year": {int(k): round(float(v), 2) for k, v in mis.items()},
       "diff_current_2021": {k: round(float(v), 1) for k, v in diff_now[2021].items()},
       "diff_current_2025": {k: round(float(v), 1) for k, v in diff_now[2025].items()},
       "diff_registered_2025": {k: round(float(v), 1) for k, v in diff_first[2025].items()},
       "growth": GR.to_dict(), "rank2021_at": rank(AT).to_dict(), "rank2021_now": rank(NOW).to_dict(),
       "rank_changes_2021": int((rank(AT) != rank(NOW)).sum()), "sql_match": chk}
json.dump(res, open(RES / "a575_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False)); print(GR)

# 図1：2021年の地域別売上の差（今の住所／登録時の住所 − 売った時点）
fig, ax = plt.subplots(figsize=(8, 4)); x = np.arange(8)
ax.bar(x - .2, diff_now[2021], .4, color=ORANGE, label="今の住所で数えた場合")
ax.bar(x + .2, diff_first[2021], .4, color=GRAY, label="登録時の住所で数えた場合")
ax.axhline(0, color=INK, lw=.6); ax.set_xticks(x); ax.set_xticklabels(REG); ax.set_ylabel("売った時点の住所との差（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"2021年の売上を今の住所で数えると、地域によって−{-diff_now[2021].min():.0f}%〜+{diff_now[2021].max():.0f}%ずれる")
save(fig, "a575_diff_2021.png", "出典：" + SRC)
# 図2：2021→2025の伸び率
fig, ax = plt.subplots(figsize=(8, 4))
for k, (c, col) in enumerate(zip(GR.columns, [INK, ORANGE, GRAY])):
    ax.bar(x + (k - 1) * .27, GR[c], .27, color=col, label=c)
ax.axhline(0, color=INK, lw=.6); ax.set_xticks(x); ax.set_xticklabels(REG); ax.set_ylabel("2021年→2025年の売上の伸び（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("今の住所で数えると、人が集まる地域の伸びが小さく見える")
save(fig, "a575_growth.png", "出典：" + SRC)
# 図3：年ごとに違う地域に入る売上の割合
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(mis.index.astype(str), mis.values, color=BLUE)
for xx, v in zip(mis.index.astype(str), mis.values): ax.text(xx, v + .3, f"{v:.1f}%", ha="center")
ax.set_xlabel("注文の年"); ax.set_ylabel("今の住所だと別の地域に入る売上（%）")
ax.set_title("古い年の売上ほど、今の住所では別の地域に入る")
save(fig, "a575_by_year.png", "出典：" + SRC + "。今の住所は2025年末時点")
