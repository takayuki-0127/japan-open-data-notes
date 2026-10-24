"""A202 マンション購入価格の年収倍率は、何倍まで上がったか"""
from common import *

inc, pr, ra = load()
out = pd.concat({"income": inc, "price": pr, "ratio": ra}, axis=1).round(2)
out.to_csv(RES / "income_price_ratio.csv")
c = "condo"
def chg(s, a, b): return (s[b] / s[a] - 1) * 100
with open(RES / "summary.txt", "w") as f:
    for k in ["condo", "detached", "all", "condo_first", "condo_second"]:
        f.write(f"{k}: ratio 2011 {ra[k].get(2011, np.nan):.2f} 2015 {ra[k][2015]:.2f} 2020 {ra[k][2020]:.2f} 2024 {ra[k][2024]:.2f} 2025 {ra[k][2025]:.2f} max {ra[k].max():.2f}@{ra[k].idxmax()} min {ra[k].min():.2f}@{ra[k].idxmin()}\n")
    for k in ["condo", "detached"]:
        f.write(f"{k}: price 2015->2025 {chg(pr[k],2015,2025):.1f}% income {chg(inc[k],2015,2025):.1f}% ; 2011/12->2025 price {chg(pr[k],2012,2025):.1f}% income {chg(inc[k],2012,2025):.1f}% ; 2024->2025 price {chg(pr[k],2024,2025):.1f}% income {chg(inc[k],2024,2025):.1f}%\n")
    f.write(out.to_string() + "\n")
print(open(RES / "summary.txt").read()[:1500])

yrs = ra.index
# fig1 ratio
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.plot(yrs, ra.condo, "-o", color=ORANGE, label="分譲マンション")
ax.plot(yrs, ra.detached, "-o", color=BLUE, label="分譲戸建て")
for k, col in [("condo", ORANGE), ("detached", BLUE)]:
    for y in [yrs[0], 2020, yrs[-1]]:
        ax.annotate(f"{ra[k][y]:.2f}", (y, ra[k][y]), xytext=(0, 7 if k == "condo" else -14), textcoords="offset points", ha="center", fontsize=9, color=col)
ax.set_ylabel("購入資金総額 ÷ 平均世帯年収（倍）"); ax.set_xticks(yrs); ax.set_xticklabels([str(y)[2:] for y in yrs])
ax.set_xlabel("調査年度（20XX年度）"); ax.set_ylim(4.5, 7.2); ax.legend(frameon=False)
ax.set_title("分譲住宅の購入資金は年収の何倍か（三大都市圏）")
save(fig, "a202_ratio.png")

# fig2 index price vs income (condo)
fig, ax = plt.subplots(figsize=(8, 4.8))
b = 2012
for s_, col, lab in [(pr.condo, ORANGE, "マンションの購入資金総額"), (inc.condo, GREEN, "マンション購入世帯の平均年収")]:
    ix = s_ / s_[b] * 100
    ax.plot(yrs[yrs >= b], ix[yrs >= b], "-o", color=col, label=lab)
    ax.annotate(f"{ix[yrs[-1]]:.0f}", (yrs[-1], ix[yrs[-1]]), xytext=(6, 0), textcoords="offset points", va="center", color=col)
ax.axhline(100, color=GRAY, lw=0.8)
ax.set_ylabel(f"{b}年度＝100"); ax.set_xticks(yrs[yrs >= b]); ax.set_xticklabels([str(y)[2:] for y in yrs[yrs >= b]]); ax.set_xlabel("調査年度（20XX年度）")
ax.legend(frameon=False); ax.set_title("価格と年収の伸びを比べる（分譲マンション）")
save(fig, "a202_index.png")

# fig3 first vs second acquisition
fig, ax = plt.subplots(figsize=(8, 4.8))
y2 = yrs[yrs >= 2012]
ax.plot(y2, ra.condo_first[y2], "-o", color=BLUE, label="一次取得（初めて家を買う）")
ax.plot(y2, ra.condo_second[y2], "-o", color=PURPLE, label="二次取得（買い替えなど）")
for k, col in [("condo_first", BLUE), ("condo_second", PURPLE)]:
    ax.annotate(f"{ra[k][2025]:.2f}", (2025, ra[k][2025]), xytext=(6, 0), textcoords="offset points", va="center", color=col)
ax.set_ylabel("購入資金総額 ÷ 平均世帯年収（倍）"); ax.set_xticks(y2); ax.set_xticklabels([str(y)[2:] for y in y2]); ax.set_xlabel("調査年度（20XX年度）")
ax.legend(frameon=False); ax.set_title("分譲マンションの年収倍率：一次取得と二次取得")
save(fig, "a202_first_second.png")
