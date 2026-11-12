"""485 論理削除のフラグを見落として集計すると、件数と金額は何%多くなるのか（架空の顧客2万人・注文30万件）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "架空の顧客・注文（作成者が乱数で作成、seed 485）"
rng = np.random.default_rng(485)
NC, NO = 20_000, 300_000
D0 = pd.Timestamp("2023-01-01"); ND = 3 * 365 + 1
# 顧客：5%は削除済み（テスト用・重複して統合したもの）。15%は住所や区分の変更で履歴が2〜3行
cust_del = rng.random(NC) < 0.05
rows = []
for c in range(NC):
    nv = 1 if rng.random() > 0.15 else rng.choice([2, 3])
    cuts = np.sort(rng.integers(30, ND - 30, nv - 1))
    starts = [0] + list(cuts); ends = list(cuts) + [99999]
    seg = rng.choice(["一般", "法人"], p=[.8, .2])
    for v, (a, b) in enumerate(zip(starts, ends)):
        if v > 0 and rng.random() < 0.3: seg = "法人" if seg == "一般" else "一般"
        rows.append((c, v + 1, int(a), int(b), seg, bool(cust_del[c])))
C = pd.DataFrame(rows, columns=["customer_id", "version", "valid_from", "valid_to", "segment", "is_deleted"])
C["segment"] = [str(x) for x in C.segment]
# 注文：削除済みの顧客（テスト用など）の注文は、注文側には削除の印がない。注文の4%はキャンセルで論理削除、2025年3月だけ取り消しが多い
cid = rng.integers(0, NC, NO)
day = rng.integers(0, ND, NO)
amt = np.round(np.exp(rng.normal(np.log(6000), 0.9, NO)) / 10) * 10
mth = (D0 + pd.to_timedelta(day, "D")).to_period("M")
p_del = np.where(mth == pd.Period("2025-03", "M"), 0.15, 0.04)
o_del = rng.random(NO) < p_del
O = pd.DataFrame({"order_id": np.arange(NO), "customer_id": cid, "day": day, "amount": amt, "is_deleted": o_del})
C.to_csv(DATA / "fictional_customers.csv", index=False); O.to_csv(DATA / "fictional_orders.csv", index=False)

con = duckdb.connect()
con.register("C", C); con.register("O", O)
con.execute("""CREATE VIEW v_orders AS
  SELECT o.order_id, o.customer_id, o.day, o.amount, c.segment
  FROM O o JOIN C c ON c.customer_id = o.customer_id AND o.day >= c.valid_from AND o.day < c.valid_to
  WHERE NOT o.is_deleted AND NOT c.is_deleted""")
Q = {
 "正しい（削除を除き、注文日の版とつなぐ）": "SELECT COUNT(*) n, SUM(amount) amt, COUNT(DISTINCT customer_id) cust FROM v_orders",
 "注文の削除フラグを見落とす": """SELECT COUNT(*), SUM(o.amount), COUNT(DISTINCT o.customer_id) FROM O o JOIN C c
      ON c.customer_id=o.customer_id AND o.day>=c.valid_from AND o.day<c.valid_to WHERE NOT c.is_deleted""",
 "顧客の削除フラグを見落とす": """SELECT COUNT(*), SUM(o.amount), COUNT(DISTINCT o.customer_id) FROM O o JOIN C c
      ON c.customer_id=o.customer_id AND o.day>=c.valid_from AND o.day<c.valid_to WHERE NOT o.is_deleted""",
 "両方の削除フラグを見落とす": """SELECT COUNT(*), SUM(o.amount), COUNT(DISTINCT o.customer_id) FROM O o JOIN C c
      ON c.customer_id=o.customer_id AND o.day>=c.valid_from AND o.day<c.valid_to""",
 "履歴の期間を見ずにつなぐ（削除は除く）": """SELECT COUNT(*), SUM(o.amount), COUNT(DISTINCT o.customer_id) FROM O o JOIN C c
      ON c.customer_id=o.customer_id WHERE NOT o.is_deleted AND NOT c.is_deleted""",
 "削除も履歴も見落とす": """SELECT COUNT(*), SUM(o.amount), COUNT(DISTINCT o.customer_id) FROM O o JOIN C c ON c.customer_id=o.customer_id""",
 "注文表だけで数える（注文の削除は除く）": "SELECT COUNT(*), SUM(amount), COUNT(DISTINCT customer_id) FROM O WHERE NOT is_deleted",
}
out = []
for k, q in Q.items():
    n, a, cu = con.execute(q).fetchone(); out.append({"way": k, "orders": int(n), "amount": float(a), "customers": int(cu)})
T = pd.DataFrame(out)
t0 = T.iloc[0]
for c in ["orders", "amount", "customers"]: T[c + "_pct"] = (T[c] / t0[c] - 1) * 100
# pandas で正解を別に出して一致を確かめる
truth = O[~O.is_deleted & ~cust_del[O.customer_id.values]]
assert len(truth) == t0.orders and abs(truth.amount.sum() - t0.amount) < 1e-6 and truth.customer_id.nunique() == t0.customers
T.to_csv(RES / "totals_by_way.csv", index=False)
# 区分別（法人・一般）の売上：注文日の版と、今の版
seg_now = C.sort_values("version").groupby("customer_id").segment.last()
SEG = con.execute("SELECT segment, SUM(amount) FROM v_orders GROUP BY 1 ORDER BY 1").df().set_index("segment").iloc[:, 0]
t2 = truth.assign(seg_now=seg_now.reindex(truth.customer_id).values).groupby("seg_now").amount.sum()
segtab = pd.DataFrame({"注文日の区分": SEG, "今の区分": t2}); segtab.to_csv(RES / "segment_asof_vs_now.csv")
# 月ごと：削除フラグを見落としたときの上振れ、前年同月比
con.register("CD", pd.DataFrame({"customer_id": np.arange(NC), "cdel": cust_del}))
mo = con.execute("""SELECT date_trunc('month', DATE '2023-01-01' + CAST(o.day AS INTEGER)) m,
        SUM(o.amount) FILTER (WHERE NOT o.is_deleted AND NOT d.cdel) ok, SUM(o.amount) all_amt
        FROM O o JOIN CD d USING (customer_id) GROUP BY 1 ORDER BY 1""").df()
mo["m"] = pd.to_datetime(mo["m"]); mo = mo[mo.m <= "2025-12-01"]
mo["over_pct"] = (mo.all_amt / mo.ok - 1) * 100
mo["yoy_ok"] = (mo.ok / mo.ok.shift(12) - 1) * 100; mo["yoy_all"] = (mo.all_amt / mo.all_amt.shift(12) - 1) * 100
mo.to_csv(RES / "monthly_overstatement.csv", index=False)
mar = mo[mo.m == "2025-03-01"].iloc[0]
res = {"customers": NC, "customer_rows": len(C), "customers_with_history": int((C.groupby("customer_id").size() > 1).sum()),
       "orders": NO, "deleted_orders": int(o_del.sum()), "deleted_customers": int(cust_del.sum()),
       "by_way": T.round(3).to_dict("records"),
       "monthly_over_pct": {"min": float(mo.over_pct.min()), "max": float(mo.over_pct.max()), "median": float(mo.over_pct.median())},
       "march_2025": {"over_pct": float(mar.over_pct), "yoy_ok": float(mar.yoy_ok), "yoy_all": float(mar.yoy_all)},
       "segment": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in segtab.to_dict().items()}}
json.dump(res, open(RES / "a485_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：集計の仕方ごとの件数・金額・顧客数のずれ
fig, ax = plt.subplots(figsize=(11, 4.8))
T2 = T.iloc[1:]
ys = np.arange(len(T2))[::-1]; h = .26
for j, (c, colr, lab) in enumerate([("orders_pct", BLUE, "注文の件数"), ("amount_pct", ORANGE, "金額"), ("customers_pct", GRAY, "顧客の数")]):
    ax.barh(ys + (1 - j) * h, T2[c], h, color=colr, label=lab)
    for y, v in zip(ys + (1 - j) * h, T2[c]): ax.text(v + .3, y, f"{v:+.1f}%", va="center", fontsize=7.5)
ax.set_yticks(ys); ax.set_yticklabels(T2.way, fontsize=9); ax.axvline(0, color=INK, lw=.8)
ax.set_xlabel("正しい集計からのずれ（%）"); ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.set_title("集計の仕方ごとのずれ（正しい集計：削除を除き、注文日の版とつなぐ）", loc="left", fontsize=11)
save(fig, "a485_overstatement.png", SRC)
# 図2：月ごとの上振れと前年同月比
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
axs[0].bar(mo.m, mo.over_pct, width=20, color=ORANGE); axs[0].set_ylabel("両方の削除フラグを見落とした上振れ（%）")
axs[0].set_title("月ごとの上振れ", loc="left", fontsize=11)
import matplotlib.dates as mdates
axs[0].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); axs[0].xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
m2 = mo[mo.m >= "2024-01-01"]
axs[1].plot(m2.m, m2.yoy_ok, color=BLUE, lw=2, marker="o", ms=3, label="削除を除く")
axs[1].plot(m2.m, m2.yoy_all, color=ORANGE, lw=2, ls="--", marker="o", ms=3, label="削除を見落とす")
axs[1].axhline(0, color=INK, lw=.8); axs[1].set_ylabel("前年同月比（%）"); axs[1].legend(frameon=False, fontsize=8)
axs[1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10])); axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); axs[1].set_title("前年同月比（2024〜2025年）", loc="left", fontsize=11)
save(fig, "a485_monthly.png", SRC)
# 図3：区分別の売上（注文日の版 vs 今の版）
fig, ax = plt.subplots(figsize=(7.5, 4.2))
xs = np.arange(len(segtab))
ax.bar(xs - .2, segtab["注文日の区分"] / 1e6, .4, color=BLUE, label="注文日の区分でつなぐ")
ax.bar(xs + .2, segtab["今の区分"] / 1e6, .4, color=ORANGE, label="今の区分でつなぐ")
for x, a, b in zip(xs, segtab["注文日の区分"], segtab["今の区分"]):
    ax.text(x + .2, b / 1e6 + 5, f"{(b / a - 1) * 100:+.1f}%", ha="center", fontsize=9)
ax.set_xticks(xs); ax.set_xticklabels(segtab.index); ax.set_ylabel("3年の売上（百万円）"); ax.legend(frameon=False, fontsize=8)
ax.set_title("同じ注文を、区分の履歴のどの版とつなぐか", loc="left", fontsize=11)
save(fig, "a485_segment_version.png", SRC)
print(T.round(2).to_string()); print(json.dumps({k: res[k] for k in ["monthly_over_pct", "march_2025", "segment", "customers_with_history", "deleted_orders"]}, ensure_ascii=False, default=float))
