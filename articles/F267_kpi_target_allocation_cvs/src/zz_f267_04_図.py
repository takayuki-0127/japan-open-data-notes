"""F267 04 図（05_問い直し のあとに流す）"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
BASE = pathlib.Path(__file__).resolve().parents[1]
DATA, RES, FIG = BASE / "data", BASE / "results", BASE / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3, GR = "#2b6cb0", "#c05621", "#2f855a", "#718096"
NOTE = "出典：日本フランチャイズチェーン協会「コンビニエンスストア統計調査」（正会員チェーンの合計）から作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
a = pd.read_csv(DATA / "jfa_cvs_annual.csv"); m = pd.read_csv(DATA / "jfa_cvs_monthly.csv")

# 図1 既存店の売上・客数・客単価の前年比（年）
fig, ax = plt.subplots(figsize=(10, 4.6))
for col, c, lab in [("sales_ex_yoy", "black", "既存店の売上"), ("cust_ex_yoy", C1, "既存店の客数"), ("price_ex_yoy", C2, "既存店の客単価")]:
    ax.plot(a.year, a[col] * 100, color=c, lw=2.4 if c == "black" else 1.8, marker="o", ms=3.5, label=lab)
ax.axhline(0, color=GR, lw=.8); ax.axvspan(2019.5, 2022.5, color=GR, alpha=.12)
ax.text(2021, -9.5, "コロナの時期", ha="center", color=GR, fontsize=9)
ax.set_ylabel("前年比（%）"); ax.set_title("コンビニ既存店：売上の前年比＝客数の前年比×客単価の前年比（年）")
ax.legend(frameon=False, ncol=3, loc="lower left"); ax.grid(axis="y", alpha=.3); ax.set_xticks(range(2005, 2026, 2))
fig.text(0.01, 0.01, NOTE, fontsize=8, color=GR); fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig(FIG / "f267_1_annual_tree.png", dpi=150); plt.close(fig)

# 図2 売上の揺れのうち客数・客単価の寄与（期間別）
R = M["robustness"]; base = M["H1_H2_monthly"]
items = [("2006〜2025年\n（基本）", base), ("コロナの時期\nを除く", R["exclude_covid"]), ("前半\n2006〜2015", R["first_half_2006_2015"]),
         ("後半\n2016〜2025", R["second_half_2016_2025"]), ("後半から\nコロナを除く", R["second_half_ex_covid"])]
fig, ax = plt.subplots(figsize=(10, 4.6)); x = np.arange(len(items)); w = .38
cs = [v["lc"] * 100 for _, v in items]; ps = [v["lp"] * 100 for _, v in items]
b1 = ax.bar(x - w / 2, cs, w, color=C1, label="客数の寄与"); b2 = ax.bar(x + w / 2, ps, w, color=C2, label="客単価の寄与")
for bb, vals in [(b1, cs), (b2, ps)]:
    for r, v in zip(bb, vals): ax.annotate(f"{v:.0f}%", (r.get_x() + r.get_width() / 2, v), xytext=(0, 3 if v >= 0 else -12), textcoords="offset points", ha="center", fontsize=9)
for i, (_, v) in enumerate(items): ax.text(i, -68, f"相関 {v['corr']:+.2f}", ha="center", fontsize=9, color=GR)
ax.axhline(50, color=GR, ls=":", lw=1); ax.axhline(0, color="black", lw=.8)
ax.set_xticks(x); ax.set_xticklabels([t for t, _ in items]); ax.set_ylim(-75, 150)
ax.set_ylabel("既存店の売上の前年同月比の分散に占める割合（%）"); ax.set_title("売上の揺れを客数と客単価に分けると（月次・対数）")
ax.legend(frameon=False, loc="upper left"); fig.text(0.01, 0.01, NOTE + "。相関＝客数と客単価の前年同月比の相関", fontsize=8, color=GR)
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG / "f267_2_variance_share.png", dpi=150); plt.close(fig)

# 図3 散布図 客数 vs 客単価（月次）
d = m[m.year.between(2006, 2025)].copy()
fig, ax = plt.subplots(figsize=(7.6, 6))
grp = [("前半 2006〜2015", d.year <= 2015, GR), ("後半（コロナを除く）", (d.year >= 2016) & ~d.year.isin([2020, 2021, 2022]), C1), ("2020〜2022", d.year.isin([2020, 2021, 2022]), C2)]
for lab, msk, c in grp:
    ax.scatter(d.cust_ex_yoy[msk] * 100, d.price_ex_yoy[msk] * 100, s=16, color=c, alpha=.75, label=lab)
xs = np.linspace(-21, 10, 2)
for s in [-2, 0, 2]: ax.plot(xs, s - xs, color=GR, lw=.7, ls=":")
ax.text(5.6, -4.4, "売上 0%", color=GR, fontsize=8)
ax.axhline(0, color=GR, lw=.6); ax.axvline(0, color=GR, lw=.6)
ax.set_xlabel("既存店の客数 前年同月比（%）"); ax.set_ylabel("既存店の客単価 前年同月比（%）")
ax.set_title("客数と客単価（月次）：同じ月に逆に動くか"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_xlim(-21, 10); ax.set_ylim(-5, 14)
fig.text(0.01, 0.01, NOTE + "。点線は売上の前年比が −2%・0%・+2% の線", fontsize=7.5, color=GR)
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG / "f267_3_scatter.png", dpi=150); plt.close(fig)

# 図4 割り付けのルール別の達成率（目標＝前5年の平均の伸び、2010〜2025年）
S = pd.read_csv(RES / "H3_allocation_summary.csv"); S = S[(S.period == "all") & (S.X == "past5")].set_index("rule")
rules = [("equal", "等分"), ("trend_ratio", "過去の傾向の比"), ("trend_gap", "傾向＋差を等分\n（補助）"), ("price_only", "全部を客単価に")]
fig, ax = plt.subplots(figsize=(10, 4.6)); x = np.arange(len(rules)); w = .26
for k, (col, c, lab) in enumerate([("hit_s", "black", "売上の目標"), ("hit_c", C1, "客数の目標"), ("hit_p", C2, "客単価の目標")]):
    vals = [S.loc[r, col] * 100 for r, _ in rules]
    bb = ax.bar(x + (k - 1) * w, vals, w, color=c, label=lab)
    for r_, v in zip(bb, vals): ax.annotate(f"{int(v + 0.5)}", (r_.get_x() + r_.get_width() / 2, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([l for _, l in rules]); ax.set_ylim(0, 100)
ax.set_ylabel("目標に届いた年の割合（%）"); ax.set_title("売上の目標を客数と客単価に割り付けると、どれだけ届いたか（2010〜2025年の16年）")
ax.legend(frameon=False, ncol=3, loc="upper right"); ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, NOTE + "。目標＝その年の前5年の既存店売上の平均の伸び（前の年までのデータだけで決める）", fontsize=7.5, color=GR)
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG / "f267_4_allocation_hit.png", dpi=150); plt.close(fig)

# 図5 月次の判定が年の判定と食い違う割合
H4 = M["H4"]
labs = [("s", "売上"), ("c", "客数"), ("p", "客単価")]
fig, ax = plt.subplots(figsize=(9, 4.4)); x = np.arange(3); w = .36
for k, (rule, c, lab) in enumerate([("trend_ratio", C1, "過去の傾向の比で割り付け"), ("equal", GR, "等分で割り付け")]):
    vals = [H4[f"{rule}_{s}"]["disagree"] * 100 for s, _ in labs]
    bb = ax.bar(x + (k - .5) * w, vals, w, color=c, label=lab)
    for r_, v in zip(bb, vals): ax.annotate(f"{v:.0f}%", (r_.get_x() + r_.get_width() / 2, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=9)
ax.axhline(30, color=C2, ls=":", lw=1.2); ax.text(2.45, 31, "計画の基準 30%", color=C2, fontsize=8.5, ha="right")
ax.set_xticks(x); ax.set_xticklabels([l for _, l in labs]); ax.set_ylim(0, 45)
ax.set_ylabel("月の判定と年の判定が逆の月の割合（%）"); ax.set_title("毎月の「届いた・届かない」は、年の結論とどれだけ食い違うか（2010〜2025年の192か月）")
ax.legend(frameon=False, loc="upper left"); fig.text(0.01, 0.01, NOTE, fontsize=8, color=GR)
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG / "f267_5_monthly_vs_annual.png", dpi=150); plt.close(fig)

# 図6 問い直し：客単価と物価
y = pd.read_csv(RES / "reask_price_vs_cpi_annual.csv")
for c_ in ["lp", "lc", "ls", "cpi_食料工業製品"]: y[c_] = y[c_] * 100
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(y.year, y["cpi_食料工業製品"], color=C3, lw=2.2, marker="o", ms=4, label="消費者物価：食料工業製品（加工食品）")
ax.plot(y.year, y.lp, color=C2, lw=2.2, marker="o", ms=4, label="コンビニ既存店の客単価")
ax.plot(y.year, y.lc, color=C1, lw=1.6, marker="o", ms=3, ls="--", label="コンビニ既存店の客数")
ax.axhline(0, color=GR, lw=.8); ax.axvspan(2019.5, 2022.5, color=GR, alpha=.12)
ax.set_ylabel("前年比（%、月の対数の前年比の年平均）"); ax.set_title("値段は上がったのに、客単価は物価ほど伸びなかった（2016〜2025年）")
ax.legend(frameon=False, loc="lower left"); ax.grid(axis="y", alpha=.3); ax.set_ylim(-12, 10)
fig.text(0.01, 0.01, NOTE + "、総務省「消費者物価指数」", fontsize=8, color=GR)
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG / "f267_6_price_vs_cpi.png", dpi=150); plt.close(fig)
print(sorted(p.name for p in FIG.glob("*.png")))
