"""L1：地価はバブルのピークの何%か。1983〜2026年の地価公示を、継続する標準地の前年比でつないだ連鎖指数（圏域×用途）"""
from common import *
d = load()
AREAS = ["東京圏", "大阪圏", "名古屋圏", "地方圏"]; USES = ["住宅地", "商業地"]
I = pd.DataFrame({f"{a}・{u}": chain_index(d[(d.area == a) & (d.use == u)]) for a in AREAS for u in USES})
I.round(2).to_csv(RES / "l1_index_2026base.csv", encoding="utf-8-sig")
rows = []
for c in I.columns:
    s = I[c].dropna(); pk = s.idxmax()
    after = s.loc[pk:]; bottom = after.idxmin()
    rows.append({"series": c, "peak_year": pk, "now_vs_peak_pct": 100 / s[pk] * 100, "bottom_year": bottom, "now_vs_bottom_pct": (100 / s[bottom] - 1) * 100,
                 "now_vs_1983_pct": (100 / s[1983] * 100) if 1983 in s.index else np.nan, "since_2013_pct": (100 / s[2013] - 1) * 100, "since_2016_pct": (100 / s[2016] - 1) * 100,
                 "n_points_2026": int(((d.area + "・" + d.use) == c).sum())})
T = pd.DataFrame(rows); T.round(1).to_csv(RES / "l1_summary_table.csv", index=False, encoding="utf-8-sig"); print(T.round(1).to_string())
# 比べるために、1991年＝100 にそろえた表も保存
(I / I.loc[1991] * 100).round(1).to_csv(RES / "l1_index_1991base.csv", encoding="utf-8-sig")
# 標準地の数（年ごと、価格のある地点）
cnt = pd.Series({y: int(d[y].notna().sum()) for y in YEARS}); cnt.to_csv(RES / "l1_points_per_year.csv", header=["n"])
s = {"n_points_2026": len(d), "n_points_1983": int(d[1983].notna().sum()), "n_points_1991": int(d[1991].notna().sum())}
for _, r in T.iterrows(): s[f"{r.series}_now_vs_peak"] = r.now_vs_peak_pct; s[f"{r.series}_since_2013"] = r.since_2013_pct
pd.Series(s).to_csv(RES / "l1_summary.csv", header=["value"]); print(pd.Series(s).round(1))

cols = {"東京圏": BLUE, "大阪圏": ORANGE, "名古屋圏": GREEN, "地方圏": GRAY}
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, u in zip(axs, USES):
    for a in AREAS: ax.plot(I.index, I[f"{a}・{u}"], color=cols[a], lw=2, label=a)
    ax.axhline(100, color=INK, lw=0.6, ls=":"); ax.set_title(u, loc="left", fontsize=12); ax.set_yscale("log")
    ax.set_yticks([50, 100, 200, 300, 500], ["50", "100", "200", "300", "500"]); from matplotlib.ticker import NullFormatter; ax.yaxis.set_minor_formatter(NullFormatter())
axs[0].set_ylabel("2026年＝100（対数目盛）"); axs[1].legend(frameon=False, loc="upper right")
fig.suptitle("地価公示の連鎖指数：2026年の地価は、バブルのピークの2〜6割", x=0.01, ha="left", fontsize=13)
fig.text(0.01, -0.04, SOURCE + "（2026年版の標準地の価格履歴。圏域は都道府県で近似）", fontsize=7, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "l1_index.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.2)); yy = np.arange(len(T))
ax.barh(yy, T.now_vs_peak_pct, color=[cols[c.split("・")[0]] for c in T.series])
for i, v in enumerate(T.now_vs_peak_pct): ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
ax.set_yticks(yy, T.series); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("2026年の地価 ÷ ピーク（1991〜92年）の地価（%）")
ax.set_title("今の地価は、バブルのピークの何%か", loc="left")
fig.text(0.01, -0.05, SOURCE, fontsize=7, color="#8a8984"); fig.savefig(FIG / "l1_vs_peak.png"); plt.close(fig)
