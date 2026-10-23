"""川や海に比べて、湖だけ環境基準の達成率が低いのはなぜか（環境省 公共用水域水質測定結果、1974〜2024年度）"""
from common import *

a = load("achievement_rate.csv").set_index("fiscal_year")
m = load("mean_bod_cod.csv").set_index("fiscal_year")
t = load("achievement_by_type_2024.csv")
dl = load("designated_lakes_cod.csv")
L = []
for y in [1974, 1984, 1994, 2004, 2014, 2024]:
    L.append(f"{y}年度 達成率 河川 {a.loc[y,'river_bod']}% 湖沼 {a.loc[y,'lake_cod']}% 海域 {a.loc[y,'sea_cod']}%")
for c, nm in [("river_bod", "河川"), ("lake_cod", "湖沼"), ("sea_cod", "海域")]:
    L.append(f"{nm}: 1974-83平均 {a.loc[1974:1983, c].mean():.1f}% / 2015-24平均 {a.loc[2015:2024, c].mean():.1f}% / 最高 {a[c].max()}%（{a[c].idxmax()}）")
for c, nm in [("river_all", "河川BOD"), ("lake_all", "湖沼COD"), ("sea_all", "海域COD")]:
    L.append(f"{nm} 年間平均値: 1979 {m.loc[1979,c]} → 2004 {m.loc[2004,c]} → 2024 {m.loc[2024,c]} mg/L（最小 {m[c].min()}）")
L.append(f"湖沼COD 2015〜2024: {list(m.loc[2015:2024,'lake_all'])}")
d24 = dl[dl.fiscal_year == 2024].copy()
std = {"AA": 1, "A": 3, "B": 5}
d24["std"] = d24.type.map(std); d24["ratio"] = d24.cod_75pct_max / d24["std"]
d24 = d24.sort_values("ratio")
d24.to_csv(RES / "a149_designated_lakes_2024.csv", index=False, encoding="utf-8")
for _, r in d24.iterrows():
    L.append(f"{r.lake}（{r.type}類型・基準{r['std']}mg/L）COD75%値 {r.cod_75pct_max} 平均 {r.cod_mean} → 基準の{r.ratio:.1f}倍")
L.append("指定湖沼全体の平均（表7）: 2015 5.9 → 2024 6.2 mg/L")
L.append(f"湖沼 類型別 2024: " + ", ".join(f"{r.type} {r.rate_2024}%（{r.achieved_2024}/{r.waters_2024}）" for _, r in t[t.water == 'lake'].iterrows()))
(RES / "a149_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1 達成率の推移
fig, ax = plt.subplots(figsize=(9.5, 4.6))
for c, nm, col in [("river_bod", "河川（BOD）", BLUE), ("sea_cod", "海域（COD）", GREEN), ("lake_cod", "湖沼（COD）", ORANGE)]:
    ax.plot(a.index, a[c], color=col, lw=2.4)
    ax.text(2025, a.loc[2024, c], f"{nm} {a.loc[2024, c]:.1f}%", color=col, va="center", fontsize=10)
ax.set_ylim(0, 100); ax.set_xlim(1973, 2034); ax.set_ylabel("環境基準の達成率（%）"); ax.set_xlabel("年度")
ax.set_xticks(range(1975, 2026, 10)); ax.grid(axis="y", color="#e5e5e5")
ax.set_title("BOD・CODの環境基準を満たした水域の割合")
save(fig, "a149_rate.png")

# 図2 年間平均値の推移（1979=100 ではなく実数）
fig, ax = plt.subplots(figsize=(9.5, 4.6))
for c, nm, col in [("river_all", "河川（BOD）", BLUE), ("sea_all", "海域（COD）", GREEN), ("lake_all", "湖沼（COD）", ORANGE)]:
    ax.plot(m.index, m[c], color=col, lw=2.4)
    ax.text(2025, m.loc[2024, c], f"{nm} {m.loc[2024, c]:.1f}", color=col, va="center", fontsize=10)
ax.set_ylim(0, 4.6); ax.set_xlim(1978, 2034); ax.set_ylabel("年間平均値（mg/L）"); ax.set_xlabel("年度")
ax.set_xticks(range(1980, 2026, 10)); ax.grid(axis="y", color="#e5e5e5")
ax.set_title("水の汚れ（BOD・COD）の年間平均値：河川は3分の1に、湖沼はほぼ横ばい")
save(fig, "a149_mean.png")

# 図3 指定湖沼 2024年度 COD75%値と環境基準
fig, ax = plt.subplots(figsize=(9.5, 5.0))
y = np.arange(len(d24))
ax.barh(y, d24.cod_75pct_max, color=[GREEN if r <= 1 else ORANGE for r in d24.ratio], height=0.65)
ax.scatter(d24["std"], y, marker="|", s=420, color=INK, lw=2.2, zorder=3, label="その湖の環境基準値")
for yi, (_, r) in zip(y, d24.iterrows()):
    ax.text(max(r.cod_75pct_max, r['std']) + 0.25, yi, f"{r.cod_75pct_max:.1f}（基準の{r.ratio:.1f}倍）", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels([f"{r.lake}［{r.type}］" for _, r in d24.iterrows()], fontsize=9.5)
ax.set_xlabel("COD 75%値（mg/L、環境基準点のうち最も高い値）"); ax.set_xlim(0, 19)
ax.legend(frameon=False, loc="center right", fontsize=9)
ax.set_title("指定湖沼のCOD（2024年度）：基準を満たしたのは野尻湖だけ")
save(fig, "a149_lakes.png")
