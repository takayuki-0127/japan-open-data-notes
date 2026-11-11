"""233：レポートの合計が会計の数字と合わないとき、どこから疑うか。
架空の注文データで、5つのよくある原因を1つずつ直し、差がどれだけ縮むかを見る"""
import re, duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from common import DATA, SQL, RES, save, tsql_to_duckdb, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

con = duckdb.connect(); con.execute("CREATE SCHEMA dbo")
for t in ["customers", "customer_addresses", "stores", "orders"]:
    con.execute(f"CREATE TABLE dbo.{t} AS SELECT * FROM read_csv_auto('{DATA / (t + '.csv')}')")
con.execute(f"CREATE TABLE dbo.order_lines AS SELECT order_id, line_no, item_id, qty, unit_price, CAST(tax_rate AS DECIMAL(4,2)) AS tax_rate "
            f"FROM read_csv_auto('{DATA / 'order_lines.csv'}')")  # SQL Server では DECIMAL(4,2) の列を想定
run = lambda q: con.execute(tsql_to_duckdb(q)).df()
one = lambda q: float(run(q).iloc[0, 0])
before, ledger, after = (one((SQL / f).read_text()) for f in ["01_report_before.sql", "02_ledger.sql", "04_report_after.sql"])

# 点検クエリ（03）を名前ごとに流す
checks = {}
for blk in re.split(r"^-- name: ", (SQL / "03_checks.sql").read_text(), flags=re.M)[1:]:
    name = blk.split()[0]; q = blk.split("\n", 1)[1]
    checks[name] = run(q)
    checks[name].to_csv(RES / f"{name}.csv", index=False)

# 原因を点検の順に1つずつ直す（前の直しは残したまま）
NET = "l.qty * l.unit_price"
def q(primary, half_open, done, left, per_order_tax):
    j_addr = "JOIN dbo.customer_addresses AS a ON a.customer_id = o.customer_id" + (" AND a.is_primary = 1" if primary else "")
    j_store = ("LEFT JOIN" if left else "JOIN") + " dbo.stores AS s ON s.store_id = o.store_id"
    w = ("o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01'" if half_open else "o.ordered_at BETWEEN '2026-03-01' AND '2026-03-31'")
    w += " AND o.status = N'完了'" if done else ""
    base = f"FROM dbo.orders AS o JOIN dbo.order_lines AS l ON l.order_id = o.order_id {j_addr} {j_store} WHERE {w}"
    if per_order_tax:
        return f"SELECT SUM(net + tax) FROM (SELECT o.order_id, a.address_id, l.tax_rate, SUM({NET}) AS net, FLOOR(SUM({NET}) * l.tax_rate) AS tax {base} GROUP BY o.order_id, a.address_id, l.tax_rate) AS t"
    return f"SELECT SUM({NET} * (1 + l.tax_rate)) {base}"
steps = [("直す前", (0, 0, 0, 0, 0)), ("① 住所の重複（結合で行が増える）", (1, 0, 0, 0, 0)),
         ("② 期間の端（31日の0時以降が落ちる）", (1, 1, 0, 0, 0)), ("③ 取消の注文が入っている", (1, 1, 1, 0, 0)),
         ("④ 店が NULL の注文が落ちる", (1, 1, 1, 1, 0)), ("⑤ 税の丸め（行ごと→注文ごと）", (1, 1, 1, 1, 1))]
rows = []
for lab, a in steps:
    v = one(q(*a)); rows.append({"step": lab, "total": v, "gap_to_ledger": v - ledger})
w = pd.DataFrame(rows); w["change"] = w.total.diff()
w.to_csv(RES / "waterfall.csv", index=False)

# 順番を変えると1つ1つの効き方が変わるか：全120通りの順で、各原因の「直した分」の幅
import itertools
names = ["住所の重複", "期間の端", "取消", "店NULL", "丸め"]
eff = {n: [] for n in names}
cache = {}
def val(state):
    if state not in cache: cache[state] = one(q(*state))
    return cache[state]
for perm in itertools.permutations(range(5)):
    st = [0] * 5
    for i in perm:
        b = val(tuple(st)); st[i] = 1; eff[names[i]].append(val(tuple(st)) - b)
rng_tbl = pd.DataFrame({n: {"min": min(v), "max": max(v), "shapley_mean": float(np.mean(v))} for n, v in eff.items()}).T
rng_tbl.to_csv(RES / "order_dependence.csv")
summary = {"report_before": before, "ledger": ledger, "report_after": after, "gap_before": before - ledger,
           "gap_before_pct": (before / ledger - 1) * 100, "after_minus_ledger": after - ledger,
           "steps": w.round(2).to_dict("records"), "order_dependence": rng_tbl.round(0).to_dict("index"),
           "c1_counts": checks["c1_counts"].to_dict("records"), "c2_dupkeys": checks["c2_dupkeys"].to_dict("records"),
           "c3_range": checks["c3_range"].astype(str).to_dict("records"), "c4_status": checks["c4_status"].to_dict("records"),
           "c5_nullkey": checks["c5_nullkey"].to_dict("records")}
pd.Series(summary).to_json(RES / "summary.json", force_ascii=False, indent=1, default_handler=str)
print(pd.Series(summary).to_string())

# 図1：点検の順番（流れ図）
fig, ax = plt.subplots(figsize=(8, 4.6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6.2)
box = [("① 件数", "注文の数・行の数を、\n結合の前後で数える"), ("② キーの重複", "結合する相手の表に、\n同じキーが2件以上ないか"),
       ("③ 期間の端", "最初と最後の時刻。\nBETWEEN と日時の型"), ("④ 状態", "取消・返品・テストの\n注文が入っていないか"),
       ("⑤ NULL のキー", "INNER JOIN で\n落ちている行はないか"), ("⑥ 丸め", "税・割引を、行ごとか\n注文ごとかで丸めたか")]
for i, (h, b) in enumerate(box):
    x = 0.2 + (i % 3) * 3.3; y = 3.4 if i < 3 else 0.5
    ax.add_patch(FancyBboxPatch((x, y), 3.0, 2.3, boxstyle="round,pad=0.05", fc=LIGHT if i < 2 else "#eef3fa", ec=BLUE, lw=1.2))
    ax.text(x + 0.15, y + 1.85, h, fontsize=12.5, weight="bold", color=INK, va="center")
    ax.text(x + 0.15, y + 0.85, b, fontsize=9.5, color=INK, va="center")
ax.text(0.2, 6.05, "上から順に、手間が小さく・よく起きるものから見る", fontsize=10, color=GRAY)
save(fig, "a233_order.png")

# 図2：1つずつ直したときの差（ウォーターフォール）
fig, ax = plt.subplots(figsize=(8, 4.4))
labs = ["直す前"] + [s[0].split("（")[0] for s in steps[1:]] + ["会計の数字"]
vals = w.total.tolist(); x = np.arange(len(labs))
ax.bar(0, vals[0] / 1e6, color=GRAY)
for i in range(1, len(vals)):
    lo, hi = sorted([vals[i - 1], vals[i]])
    ax.bar(i, (hi - lo) / 1e6, bottom=lo / 1e6, color=ORANGE if vals[i] < vals[i - 1] else BLUE)
    ax.text(i, hi / 1e6 + 0.3, f"{(vals[i] - vals[i - 1]) / 1e4:+,.0f}万円" if abs(vals[i] - vals[i - 1]) >= 1e4 else f"{vals[i] - vals[i - 1]:+,.0f}円",
            ha="center", fontsize=8.5)
ax.bar(len(vals), ledger / 1e6, color=GREEN)
ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=8.5, rotation=20, ha="right")
ax.set_ylim(min(vals + [ledger]) / 1e6 * 0.9, max(vals) / 1e6 * 1.03)
ax.set_ylabel("3月の売上（税込、百万円）"); ax.set_title("1つずつ直すと、会計の数字にぴったり合った（架空のデータ）")
save(fig, "a233_waterfall.png")

# 図3：結合の前後の件数（表）
c1 = checks["c1_counts"]
fig, ax = plt.subplots(figsize=(8, 2.6)); ax.axis("off")
tb = ax.table(cellText=[[r.step, f"{r.n_rows:,}", f"{r.n_orders:,}"] for r in c1.itertuples()],
              colLabels=["結合した表", "行の数", "注文の数（重複なし）"], loc="center", cellLoc="center", colWidths=[0.4, 0.25, 0.3])
tb.auto_set_font_size(False); tb.set_fontsize(10.5); tb.scale(1, 1.6)
for (r_, c_), cell in tb.get_celld().items():
    cell.set_edgecolor("#dddddd")
    if r_ == 0: cell.set_facecolor(LIGHT)
    if r_ == 3: cell.set_text_props(color=ORANGE, weight="bold")
    if r_ == 4: cell.set_text_props(color=BLUE, weight="bold")
ax.set_title("①件数の点検：住所の表を結合すると行が増え、店の表を結合すると注文が減る", fontsize=11)
save(fig, "a233_counts.png", y=0.02)
