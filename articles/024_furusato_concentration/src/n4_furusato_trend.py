"""N4：ふるさと納税の受入額は、どれくらい一部の自治体に集中しているか（平成20〜令和7年度の推移）"""
from common import *
SRC2 = "出典：総務省「ふるさと納税に関する現況調査」（各自治体のふるさと納税受入額及び受入件数（平成20年度～令和7年度））をもとに作成者が加工して作成"

raw = pd.read_excel(ROOT / "data" / "raw_extra" / "furusato_history_h20_r7.xlsx", header=None).iloc[4:]
m = raw[raw[1].notna() & ~raw[0].isin(["市町村合計", "合計", "全国合計"])].copy()          # 市区町村の行（都道府県の行は除く）
YEARS = list(range(2008, 2026))
amt = m[[2 + 2 * i for i in range(len(YEARS))]].apply(pd.to_numeric, errors="coerce").fillna(0) / 1e5   # 千円 → 億円
amt.columns = YEARS; amt.index = (m[0].astype(str) + m[1].astype(str)).values

def gini(x):
    x = np.sort(x); n = len(x); return (2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())

rows = []
for y in YEARS:
    s = amt[y].sort_values(ascending=False); n = len(s)
    rows.append({"year": y, "total_oku": s.sum(), "top1pct_share": s.head(round(n * .01)).sum() / s.sum(), "top10pct_share": s.head(round(n * .1)).sum() / s.sum(),
                 "gini": gini(s.values), "top1": s.index[0], "top1_oku": s.iloc[0], "top1_share": s.iloc[0] / s.sum()})
t = pd.DataFrame(rows); t.round(4).to_csv(RES / "n4_concentration.csv", index=False, encoding="utf-8-sig"); print(t.round(3))
top = pd.DataFrame({y: [f"{i}（{v:.0f}億円）" for i, v in amt[y].nlargest(5).items()] for y in [2017, 2018, 2019, 2025]}); top.to_csv(RES / "n4_top5.csv", encoding="utf-8-sig"); print(top)
s = {"n_muni": len(amt), "total_2008": t.total_oku.iloc[0], "total_2025": t.total_oku.iloc[-1], "top1pct_2018": t.set_index("year").loc[2018, "top1pct_share"],
     "top1pct_2019": t.set_index("year").loc[2019, "top1pct_share"], "top1pct_2025": t.set_index("year").loc[2025, "top1pct_share"],
     "top10pct_2018": t.set_index("year").loc[2018, "top10pct_share"], "top10pct_2025": t.set_index("year").loc[2025, "top10pct_share"],
     "gini_2018": t.set_index("year").loc[2018, "gini"], "gini_2025": t.set_index("year").loc[2025, "gini"]}
pd.Series(s).round(4).to_csv(RES / "n4_summary.csv", header=["value"]); print(pd.Series(s).round(3))

# 図1：受入額の合計
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(t.year, t.total_oku, color=BLUE)
for y, v in zip(t.year, t.total_oku):
    if y in (2008, 2015, 2019, 2025): ax.text(y, v + 200, f"{v:,.0f}", ha="center", fontsize=8)
ax.set_ylabel("市区町村の受入額の合計（億円）"); ax.set_xticks(YEARS[::2], [str(y) for y in YEARS[::2]])
ax.set_title("市区町村の受入額は18年で約180倍に", loc="left")
fig.text(0.01, -0.05, SRC2 + "（年度）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "n4_total.png"); plt.close(fig)

# 図2：集中度の推移
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(t.year, t.top10pct_share * 100, color=BLUE, marker="o", ms=4, label="上位10%の市区町村のシェア")
ax.plot(t.year, t.top1pct_share * 100, color=ORANGE, marker="o", ms=4, label="上位1%（17市区町村）のシェア")
ax.axvline(2019, color=GRAY, ls="--", lw=1); ax.text(2019.15, 78, "2019年6月\n指定制度の開始\n（返礼品は3割以下・地場産品）", fontsize=8, color="#52514e", va="top")
ax.set_ylim(0, 80); ax.set_ylabel("受入額全体に占める割合（%）"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_xticks(YEARS[::2], [str(y) for y in YEARS[::2]])
ax.set_title("2018年度に跳ね上がった上位への集中は、2019年度の制度変更のあと下がった", loc="left")
fig.text(0.01, -0.05, SRC2 + "（年度）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "n4_concentration.png"); plt.close(fig)
