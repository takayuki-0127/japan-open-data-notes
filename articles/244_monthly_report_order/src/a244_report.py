"""244：月次レポートを「結論→要因→次に確かめること」の順に、数字から自動で書く型。
要因を「金額の差」で選ぶか「率の差」で選ぶかで、いちばん大きな要因がどれだけ入れ替わるかも数える"""
import json
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, tsql_to_duckdb, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

con = duckdb.connect(); con.execute("CREATE SCHEMA dbo")
con.execute(f"CREATE TABLE dbo.monthly_dept AS SELECT dept, CAST(ym AS DATE) ym, actual, budget FROM read_csv_auto('{DATA / 'monthly_dept.csv'}')")
c = con.execute(tsql_to_duckdb((SQL / "02_contrib.sql").read_text())).df()
c = c[c.ym >= pd.Timestamp("2025-01-01")]
d = pd.read_csv(DATA / "monthly_dept.csv", parse_dates=["ym"])
tot = d.groupby("ym")[["actual", "budget"]].sum()
tot["yoy"] = tot.actual.pct_change(12)


def headline(ym):
    g = c[c.ym == ym].sort_values("rank_by_amount")
    t = tot.loc[pd.Timestamp(ym)]
    gap = t.actual - t.budget
    top = g.head(2)
    share = top["diff"].abs().sum() / g["diff"].abs().sum()  # 部門の動きの大きさ（絶対値の合計）のうち、上位2部門の割合
    offset = g["diff"].abs().sum() / abs(gap) if gap != 0 else np.inf  # 2を超えると、部門どうしの打ち消し合いが大きい
    s1 = f"{ym.month}月の売上は{t.actual / 100:.1f}億円で、予算比{(t.actual / t.budget - 1) * 100:+.1f}%（{gap:+.0f}百万円）、前年同月比{t.yoy * 100:+.1f}%。"
    s2 = "予算との差の主な要因は" + "・".join(f"{r.dept}（{r['diff']:+.0f}百万円）" for _, r in top.iterrows()) + f"で、部門の動きの{share * 100:.0f}%。" + ("プラスとマイナスの部門が打ち消し合い、全体の差は部門の差より小さい。" if offset > 2 else "")
    nxt = top.iloc[0]
    s3 = f"次に確かめること：{nxt.dept}の{'不足' if nxt['diff'] < 0 else '上振れ'}が来月も続くか（客数か客単価か）。"
    return s1, s2, s3, share, offset


recs = []
for ym in sorted(c.ym.unique()):
    g = c[c.ym == ym]
    a = g.loc[g.rank_by_amount == 1, "dept"].iloc[0]
    r = g.loc[g.rank_by_rate == 1, "dept"].iloc[0]
    s1, s2, s3, share, offset = headline(ym)
    t = tot.loc[pd.Timestamp(ym)]
    same_sign = np.sign(g["diff"]).eq(np.sign(t.actual - t.budget)).sum()
    recs.append({"ym": str(ym), "vs_budget_pct": round((t.actual / t.budget - 1) * 100, 2), "gap": round(t.actual - t.budget, 1),
                 "top_by_amount": a, "top_by_rate": r, "same": a == r, "top2_share_pct": round(share * 100, 1), "offset_ratio": round(offset, 2),
                 "depts_same_sign_as_total": int(same_sign), "s1": s1, "s2": s2, "s3": s3})
R = pd.DataFrame(recs)
R.to_csv(RES / "auto_headlines.csv", index=False)
chk = {"months": len(R), "top_differs_amount_vs_rate": int((~R.same).sum()),
       "rate_top_counts": R.top_by_rate.value_counts().to_dict(), "amount_top_counts": R.top_by_amount.value_counts().to_dict(),
       "top2_share_median_pct": float(R.top2_share_pct.median()), "top2_share_min_pct": float(R.top2_share_pct.min()),
       "top2_share_max_pct": float(R.top2_share_pct.max()),
       "months_offset_over_2": int((R.offset_ratio > 2).sum()),
       "dept_sales_share_2025": (d[d.ym.dt.year == 2025].groupby("dept").actual.sum() / d[d.ym.dt.year == 2025].actual.sum() * 100).round(1).to_dict()}
# 確かめ：部門の差の合計＝全体の差（月ごと）
chk["sum_check_maxdiff"] = float((c.groupby("ym")["diff"].sum().values - c.groupby("ym")["diff_total"].first().values).__abs__().max())
json.dump(chk, open(RES / "checks.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(chk, ensure_ascii=False, indent=1))
EX = pd.Timestamp("2025-09-01")
print(headline(EX))

# 図1：レポートの3段の型（例：2025年9月）
s1, s2, s3, _, _ = headline(EX)
fig, ax = plt.subplots(figsize=(9, 3.9)); ax.axis("off")
blocks = [("① 結論（1文）", s1, BLUE), ("② 要因（大きい順に2つまで）", s2, GREEN), ("③ 次に確かめること", s3, ORANGE)]
import textwrap
for i, (h, s, col) in enumerate(blocks):
    y = 0.92 - i * 0.31
    ax.add_patch(plt.Rectangle((0.0, y - 0.25), 0.012, 0.25, color=col, transform=ax.transAxes))
    ax.text(0.03, y - 0.02, h, transform=ax.transAxes, fontsize=11.5, weight="bold", va="top")
    ax.text(0.03, y - 0.10, "\n".join(textwrap.wrap(s.replace("次に確かめること：", ""), 46)), transform=ax.transAxes, fontsize=10, va="top")
ax.set_title("月次レポートの最初の3段（架空のチェーン、2025年9月、文はコードで自動作成）", fontsize=11.5, loc="left")
save(fig, "a244_template.png", y=0.0)

# 図2：予算→部門ごとの差→実績（滝のグラフ、2025年9月）
g = c[c.ym == EX].sort_values("rank_by_amount")
t = tot.loc[pd.Timestamp(EX)]
fig, ax = plt.subplots(figsize=(8.4, 4.2))
x = 0; ax.bar(x, t.budget, color=GRAY); ax.text(x, t.budget + 3, f"{t.budget:.0f}", ha="center", fontsize=9)
cur = t.budget
for i, (_, r) in enumerate(g.iterrows(), start=1):
    col = BLUE if r["diff"] >= 0 else ORANGE
    ax.bar(i, r["diff"], bottom=cur, color=col)
    ax.text(i, max(cur, cur + r["diff"]) + 3, f"{r['diff']:+.0f}", ha="center", fontsize=9)
    cur += r["diff"]
ax.bar(len(g) + 1, t.actual, color=INK); ax.text(len(g) + 1, t.actual + 3, f"{t.actual:.0f}", ha="center", fontsize=9)
ax.set_xticks(range(len(g) + 2)); ax.set_xticklabels(["予算"] + list(g.dept) + ["実績"])
lo = min(t.budget, t.actual) - 25; ax.set_ylim(lo, max(t.budget, t.actual) + 15)
ax.set_ylabel("売上（百万円、縦軸は途中から）")
ax.set_title("予算との差を部門に分ける（2025年9月）：差の大きい順に並べると、②の要因の文になる", fontsize=11)
save(fig, "a244_waterfall.png")

# 図3：12か月の「いちばん大きな要因」：金額で選ぶか率で選ぶか
fig, ax = plt.subplots(figsize=(9, 4.4)); ax.axis("off")
cell = [[r.ym[:7], f"{r.vs_budget_pct:+.1f}%", r.top_by_amount, r.top_by_rate, "同じ" if r.same else "違う", f"{r.top2_share_pct:.0f}%"] for r in R.itertuples()]
tb = ax.table(cellText=cell, colLabels=["月", "予算比", "最大の要因（金額）", "最大の要因（率）", "", "上位2部門の割合"], loc="center", cellLoc="center",
              colWidths=[0.12, 0.12, 0.2, 0.2, 0.1, 0.18])
tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 1.25)
for (i, j), ce in tb.get_celld().items():
    ce.set_edgecolor("#dddddd")
    if i == 0: ce.set_facecolor("#eef3fb"); ce.set_text_props(weight="bold")
    elif j == 4 and cell[i - 1][4] == "違う": ce.set_text_props(color=ORANGE, weight="bold")
ax.set_title(f"率で選ぶと、12か月中{chk['top_differs_amount_vs_rate']}か月で「いちばん大きな要因」が金額と違う部門になった", fontsize=11.5)
save(fig, "a244_amount_vs_rate.png", y=0.02)
