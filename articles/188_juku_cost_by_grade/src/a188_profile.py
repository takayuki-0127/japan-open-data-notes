"""塾代は何年生でピークになるか：学年別プロファイル（子供の学習費調査 2018・2021・2023年度）"""
from common import *

a = load("learning_cost_by_grade.csv")
r = load("juku_spending_rate_by_grade.csv")
a = a[a.grade_seq != "avg"].assign(g=lambda x: x.grade_seq.astype(int))
r = r[r.grade_seq != "avg"].assign(g=lambda x: x.grade_seq.astype(int))
LAB = [f"小{i}" for i in range(1, 7)] + [f"中{i}" for i in range(1, 4)] + [f"高{i}" for i in range(1, 4)]
juku = a[a.item == "学習塾費"]
pub = juku[juku.setting == "公立"].pivot(index="g", columns="year", values="yen")
pri = juku[juku.setting == "私立"].pivot(index="g", columns="year", values="yen")
rp = r[r.setting == "公立"].set_index(["year", "g"])
tot = a[(a.item == "学習費総額") & (a.setting == "公立")].pivot(index="g", columns="year", values="yen")
hojo = a[(a.item == "補助学習費") & (a.setting == "公立")].pivot(index="g", columns="year", values="yen")
out = pd.DataFrame({"grade": LAB}, index=range(1, 13))
for y in [2018, 2021, 2023]:
    out[f"pub_juku_{y}"] = pub[y]; out[f"pri_juku_{y}"] = pri[y]
    out[f"pub_rate_{y}"] = rp.loc[y].rate_pct; out[f"pub_spender_k_{y}"] = rp.loc[y].spender_avg_thousand_yen
    out[f"pub_juku_share_total_{y}"] = (pub[y] / tot[y] * 100).round(1)
out.to_csv(RES / "a188_profile.csv")

L = []
for y in [2018, 2021, 2023]:
    s = pub[y]; k = s.idxmax()
    L.append(f"{y} 公立 学習塾費 ピーク {LAB[k-1]} {s.max():,.0f}円 / 小1 {s[1]:,.0f} 小6 {s[6]:,.0f} 中1 {s[7]:,.0f} 中3 {s[9]:,.0f} 高1 {s[10]:,.0f} 高3 {s[12]:,.0f} / 12年合計 {s.sum():,.0f}円")
    rr = rp.loc[y]
    L.append(f"{y} 公立 支出率 最高 {LAB[rr.rate_pct.idxmax()-1]} {rr.rate_pct.max():.1f}% / 支出者平均 最高 {LAB[rr.spender_avg_thousand_yen.idxmax()-1]} {rr.spender_avg_thousand_yen.max():.0f}千円 / 中3 支出率{rr.rate_pct[9]:.1f}% 平均{rr.spender_avg_thousand_yen[9]:.0f}千円 / 高3 支出率{rr.rate_pct[12]:.1f}% 平均{rr.spender_avg_thousand_yen[12]:.0f}千円 / 小6 支出率{rr.rate_pct[6]:.1f}% 平均{rr.spender_avg_thousand_yen[6]:.0f}千円 / 高1 支出率{rr.rate_pct[10]:.1f}%")
    L.append(f"{y} 公立 学習塾費が学習費総額に占める割合 中3 {pub[y][9]/tot[y][9]:.1%} 高3 {pub[y][12]/tot[y][12]:.1%} 小6 {pub[y][6]/tot[y][6]:.1%}; 中3の学習塾費/補助学習費 {pub[y][9]/hojo[y][9]:.1%}")
    L.append(f"{y} 私立小 学習塾費 ピーク {LAB[pri[y].iloc[:6].idxmax()-1]} {pri[y].iloc[:6].max():,.0f}円 / 私立中 中3 {pri[y][9]:,.0f} / 私立高 高3 {pri[y][12]:,.0f}")
L.append(f"中3→高1 公立 学習塾費 2023 {pub[2023][10]/pub[2023][9]-1:+.1%}; 中1→中3 {pub[2023][9]/pub[2023][7]:.2f}倍; 小1→小6 {pub[2023][6]/pub[2023][1]:.2f}倍")
L.append(f"公立中3 2018→2023 {pub[2023][9]/pub[2018][9]-1:+.1%}; 公立高3 2018→2023 {pub[2023][12]/pub[2018][12]-1:+.1%}; 公立小6 2018→2023 {pub[2023][6]/pub[2018][6]-1:+.1%}")
(RES / "a188_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

x = np.arange(1, 13)
def grade_axis(ax):
    ax.set_xticks(x); ax.set_xticklabels(LAB)
    for b in [6.5, 9.5]:
        ax.axvline(b, color=GRAY, lw=0.8, ls=":")

# 図1：公立 学習塾費の学年別プロファイル（3回の調査）
fig, ax = plt.subplots(figsize=(10, 4.4))
for y, c, lw in [(2018, LIGHT, 1.6), (2021, GRAY, 1.6), (2023, BLUE, 2.6)]:
    ax.plot(x, pub[y] / 1e4, color=c, lw=lw, marker="o", ms=4, label=f"{y}年度")
k = pub[2023].idxmax()
ax.annotate(f"{pub[2023][k]/1e4:.1f}万円", (k, pub[2023][k] / 1e4), xytext=(6, 4), textcoords="offset points", color=BLUE, fontsize=9)
grade_axis(ax); ax.set_ylabel("1人あたり年額（万円）"); ax.set_ylim(0, 42)
ax.set_title("学習塾費（公立の小・中・高、通っていない子も含めた平均）")
ax.legend(frameon=False, loc="upper left")
save(fig, "a188_profile.png")

# 図2：通う割合と、通う子の平均額（公立 2023年度）
r23 = rp.loc[2023]
fig, ax1 = plt.subplots(figsize=(10, 4.4))
ax1.bar(x, r23.rate_pct, color=LIGHT, width=0.6, label="塾代を払った割合（左）")
ax1.set_ylim(0, 100); ax1.set_ylabel("支出率（%）")
ax2 = ax1.twinx()
ax2.plot(x, r23.spender_avg_thousand_yen / 10, color=ORANGE, lw=2.2, marker="o", ms=4, label="払った子の平均額（右）")
ax2.set_ylim(0, 50); ax2.set_ylabel("万円"); ax2.spines["right"].set_visible(True)
grade_axis(ax1)
ax1.set_title("塾代を払った割合と、払った子の平均額（公立、2023年度）")
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
save(fig, "a188_rate.png")

# 図3：公立と私立（2023年度）
fig, ax = plt.subplots(figsize=(10, 4.4))
ax.plot(x, pub[2023] / 1e4, color=BLUE, lw=2.4, marker="o", ms=4, label="公立")
ax.plot(x, pri[2023] / 1e4, color=PURPLE, lw=2.4, marker="o", ms=4, label="私立")
grade_axis(ax); ax.set_ylabel("1人あたり年額（万円）"); ax.set_ylim(0, 48)
ax.set_title("学習塾費：公立と私立（2023年度、学年ごとの1人あたり平均）")
ax.legend(frameon=False, loc="upper right")
save(fig, "a188_pub_pri.png")
