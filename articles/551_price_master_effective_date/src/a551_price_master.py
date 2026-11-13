"""551 月の途中で単価が変わったとき、適用開始日を見ずに今の単価で集計すると、金額はどれだけずれるのか

架空の単価マスタ（80品目、2025年中に月の途中で単価が変わる。適用開始日 valid_from・次の開始日 valid_to）と、
2025年の売上明細（6万行）を作り、明細に単価を付ける4通りの結び方で金額を比べる。
  J0 正しい：valid_from <= 日付 < valid_to（valid_to が空なら今も有効）
  J1 今の単価：valid_to が空の行（いま有効な単価）で結ぶ
  J2 月初の単価：明細の月の1日に有効だった単価で結ぶ（月単位で単価を引く作り）
  J3 BETWEEN：valid_from <= 日付 <= valid_to（両端を含める）。切り替え日の明細が2行に増える
ずれた明細の件数・金額の差・月別の差を数える。Python と SQL（DuckDB、1スレッド）で J0〜J3 の合計が一致することを確かめる。
数字は、置いた単価の変わり方と売れ方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の単価マスタと売上明細（作成者が乱数で作成、seed 551）"
rng = np.random.default_rng(551)
N_ITEM, N_LINE = 80, 60000
days = pd.date_range("2025-01-01", "2025-12-31")

# 単価マスタ：品目ごとに 0〜3 回、月の途中（2〜28日）で単価が変わる。上げが多め
pm = []
for i in range(1, N_ITEM + 1):
    base = int(rng.choice([120, 180, 250, 380, 500, 800, 1200, 2000]))
    k = int(rng.choice([0, 1, 1, 2, 2, 3], p=[0.2, 0.25, 0.15, 0.2, 0.1, 0.1]))
    months = np.sort(rng.choice(np.arange(2, 13), k, replace=False))
    starts = [pd.Timestamp("2024-04-01")] + [pd.Timestamp(2025, int(m), int(rng.integers(2, 29))) for m in months]
    price = base
    for j, s in enumerate(starts):
        if j > 0:
            price = int(round(price * rng.choice([0.9, 1.05, 1.08, 1.1, 1.15], p=[0.15, 0.25, 0.25, 0.2, 0.15]), -1))
        end = starts[j + 1] if j + 1 < len(starts) else pd.NaT
        pm.append((f"I{i:03d}", price, s, end))
PM = pd.DataFrame(pm, columns=["item_id", "price", "valid_from", "valid_to"])

# 売上明細：品目の売れやすさはばらつく。数量 1〜5
w = rng.gamma(1.2, 1.0, N_ITEM); w /= w.sum()
SL = pd.DataFrame({"line_id": np.arange(1, N_LINE + 1),
                   "item_id": [f"I{i:03d}" for i in rng.choice(np.arange(1, N_ITEM + 1), N_LINE, p=w)],
                   "sold_on": rng.choice(days, N_LINE),
                   "qty": rng.choice([1, 1, 1, 2, 2, 3, 5], N_LINE)})
SL = SL.sort_values(["sold_on", "line_id"]).reset_index(drop=True)
PM.assign(valid_from=PM.valid_from.dt.strftime("%Y-%m-%d"), valid_to=PM.valid_to.dt.strftime("%Y-%m-%d")).to_csv(DATA / "price_master.csv", index=False)
SL.assign(sold_on=SL.sold_on.dt.strftime("%Y-%m-%d")).to_csv(DATA / "sales_lines.csv", index=False)

# --- 4つの結び方（Python）
m = SL.merge(PM, on="item_id")
far = pd.Timestamp("2099-12-31")
vt = m.valid_to.fillna(far)
j0 = m[(m.sold_on >= m.valid_from) & (m.sold_on < vt)]
j1 = m[m.valid_to.isna()]
ms = m.sold_on.dt.to_period("M").dt.start_time
j2 = m[(ms >= m.valid_from) & (ms < vt)]
j3 = m[(m.sold_on >= m.valid_from) & (m.sold_on <= vt)]
J = {}
for k, x in [("J0", j0), ("J1", j1), ("J2", j2), ("J3", j3)]:
    J[k] = x.assign(amount=x.qty * x.price)[["line_id", "item_id", "sold_on", "qty", "price", "amount"]]
assert len(J["J0"]) == N_LINE and len(J["J1"]) == N_LINE and len(J["J2"]) == N_LINE

# --- SQL（DuckDB）で合計を出して突き合わせる
con = duckdb.connect(); con.execute("SET threads=1")
con.register("price_master", PM); con.register("sales_lines", SL)
q0 = (SQL / "02_price_join_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sql = {"J0": f"SELECT COUNT(*), SUM(amount) FROM ({q0})",
       "J1": "SELECT COUNT(*), SUM(d.qty*m.price) FROM sales_lines d JOIN price_master m ON m.item_id=d.item_id AND m.valid_to IS NULL",
       "J2": "SELECT COUNT(*), SUM(d.qty*m.price) FROM sales_lines d JOIN price_master m ON m.item_id=d.item_id AND date_trunc('month', d.sold_on) >= m.valid_from AND (m.valid_to IS NULL OR date_trunc('month', d.sold_on) < m.valid_to)",
       "J3": "SELECT COUNT(*), SUM(d.qty*m.price) FROM sales_lines d JOIN price_master m ON m.item_id=d.item_id AND d.sold_on BETWEEN m.valid_from AND COALESCE(m.valid_to, TIMESTAMP '2099-12-31')"}
for k, s in sql.items():
    n, a = con.execute(s).fetchone()
    assert n == len(J[k]) and int(a) == int(J[k].amount.sum()), k

# --- 比べる
ref = J["J0"].set_index("line_id").amount
tot0 = int(ref.sum())
summ = {}
for k in ["J1", "J2", "J3"]:
    x = J[k]
    a = x.groupby("line_id").amount.sum()
    rows = x.groupby("line_id").size()
    diff = a.reindex(ref.index) - ref
    summ[k] = {"rows": int(len(x)), "lines_wrong": int((diff != 0).sum()), "pct_lines_wrong": round(100 * (diff != 0).mean(), 2),
               "dup_lines": int((rows > 1).sum()), "total": int(a.sum()), "diff": int(a.sum() - tot0),
               "diff_pct": round(100 * (a.sum() - tot0) / tot0, 2), "abs_diff": int(diff.abs().sum())}
changed_items = int(PM.groupby("item_id").size().gt(1).sum())
n_changes = int(len(PM) - N_ITEM)

# 月別の差（J1・J2）
mon = pd.DataFrame({"J0": J["J0"].groupby(J["J0"].sold_on.dt.month).amount.sum()})
for k in ["J1", "J2", "J3"]:
    mon[k] = J[k].groupby(J[k].sold_on.dt.month).amount.sum()
for k in ["J1", "J2", "J3"]:
    mon[k + "_diff_pct"] = (mon[k] / mon.J0 - 1) * 100
mon.round(2).to_csv(RES / "by_month.csv")

# 品目別：J1 のずれ（変更回数ごと）
it = pd.DataFrame({"J0": J["J0"].groupby("item_id").amount.sum(), "J1": J["J1"].groupby("item_id").amount.sum()})
it["n_change"] = PM.groupby("item_id").size() - 1
it["diff_pct"] = (it.J1 / it.J0 - 1) * 100
it.round(2).to_csv(RES / "by_item.csv")
by_nc = it.groupby("n_change").agg(items=("J0", "size"), diff_pct_med=("diff_pct", "median"), diff_pct_max=("diff_pct", "max")).round(2)
by_nc.to_csv(RES / "by_change_count.csv")
# 品目の売上順位の入れ替わり
r0 = it.J0.rank(ascending=False); r1 = it.J1.rank(ascending=False)
rank_moved = int((r0 != r1).sum())
top10_changed = int(len(set(it.J0.nlargest(10).index) ^ set(it.J1.nlargest(10).index)) // 2)

# J3：切り替え日の明細
chg_days = PM.dropna(subset=["valid_to"])[["item_id", "valid_to"]]
on_chg = SL.merge(chg_days, left_on=["item_id", "sold_on"], right_on=["item_id", "valid_to"])
pd.DataFrame(summ).T.to_csv(RES / "summary.csv")

out = {"items": N_ITEM, "lines": N_LINE, "items_with_change": changed_items, "price_changes": n_changes,
       "total_J0": tot0, "summary": summ, "rank_moved_items_J1": rank_moved, "top10_swapped_J1": top10_changed,
       "lines_on_change_day": int(len(on_chg)),
       "month_diff_pct": {k: {"min": round(float(mon[k + "_diff_pct"].min()), 2), "max": round(float(mon[k + "_diff_pct"].max()), 2)} for k in ["J1", "J2", "J3"]},
       "by_change_count": by_nc.reset_index().to_dict(orient="records")}
json.dump(out, open(RES / "a551_main.json", "w"), ensure_ascii=False, indent=1)

# --- 図1：結び方ごとの合計のずれとずれた明細の件数
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"wspace": 0.75})
COL = {"J1": BLUE, "J2": ORANGE, "J3": GREEN}
lab = {"J1": "今の単価で結ぶ", "J2": "月初の単価で結ぶ", "J3": "BETWEEN（両端を含む）"}
ks = ["J1", "J2", "J3"]
ax[0].barh([lab[k] for k in ks][::-1], [summ[k]["lines_wrong"] for k in ks][::-1], color=[COL[k] for k in ks][::-1])
for i, k in enumerate(ks[::-1]):
    ax[0].text(summ[k]["lines_wrong"], i, f" {summ[k]['lines_wrong']:,}行（{summ[k]['pct_lines_wrong']}%）", va="center", fontsize=9)
ax[0].set_title("金額がずれた明細の行数（6万行中）"); ax[0].set_xlim(0, max(summ[k]["lines_wrong"] for k in ks) * 1.9)
vals = [summ[k]["diff_pct"] for k in ks][::-1]
ax[1].barh([lab[k] for k in ks][::-1], vals, color=[COL[k] for k in ks][::-1])
for i, v in enumerate(vals):
    ax[1].text(v, i, f" {v:+.2f}%", va="center", fontsize=9)
ax[1].axvline(0, color=GRAY, lw=0.8); ax[1].set_title("年間の売上合計のずれ（正しい結び方との差）")
ax[1].set_xlim(min(0, min(vals)) * 1.4 - 0.2, max(vals) * 1.5)
fig.suptitle(f"正しい結び方の年間合計は{tot0/1e6:.1f}百万円", fontsize=10, y=0.02)
save(fig, "a551_methods.png", SRC, y=-0.06)

# --- 図2：月別のずれ
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(mon.index, mon.J1_diff_pct, marker="o", color=BLUE, label="今の単価で結ぶ")
ax.plot(mon.index, mon.J2_diff_pct, marker="s", color=ORANGE, label="月初の単価で結ぶ")
ax.plot(mon.index, mon.J3_diff_pct, marker="^", color=GREEN, label="BETWEEN（両端を含む）")
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{i}月" for i in range(1, 13)])
ax.set_ylabel("正しい結び方との差（%）"); ax.legend(frameon=False, fontsize=9); ax.set_title("月別の売上のずれ：今の単価で結ぶと、年の前半ほど大きくずれる")
save(fig, "a551_by_month.png", SRC)

# --- 図3：品目別（変更回数ごと）
fig, ax = plt.subplots(figsize=(8, 4))
for nc, c in zip(sorted(it.n_change.unique()), [GRAY, LIGHT, BLUE, ORANGE]):
    s = it[it.n_change == nc]
    ax.scatter(np.full(len(s), nc) + rng.uniform(-0.15, 0.15, len(s)), s.diff_pct, color=c, s=22)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(sorted(it.n_change.unique()))
ax.set_xticklabels([f"{n}回\n（{int((it.n_change==n).sum())}品目）" for n in sorted(it.n_change.unique())])
ax.set_xlabel("2025年中の単価の変更回数"); ax.set_ylabel("今の単価で結んだときの差（%）")
ax.set_title("品目別：今の単価で結んだときの年間売上の差")
save(fig, "a551_by_item.png", SRC, y=-0.08)
print(json.dumps(out, ensure_ascii=False, indent=1))
