"""記事127：物価がいちばん高い県はどこか。10大費目別の地域差指数（都道府県、2013〜2025年）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import load, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT

df = load()
P = df.pivot_table(index=["year", "pref"], columns="item", values="index")
Y = 2025
p25 = P.loc[Y]

# --- 1. 2025年の順位
rk = p25[["総合", "家賃を除く総合"]].copy()
rk["順位_総合"] = rk["総合"].rank(ascending=False, method="min").astype(int)
rk["順位_家賃を除く総合"] = rk["家賃を除く総合"].rank(ascending=False, method="min").astype(int)
rk.sort_values("総合", ascending=False).to_csv(RES / "a127_rank_2025.csv")

fig, ax = plt.subplots(figsize=(7, 10))
s = rk["総合"].sort_values()
cols = [ORANGE if v >= 101 else (BLUE if v <= 97.5 else GRAY) for v in s]
ax.barh(s.index, s - 100, left=100, color=cols, height=0.7)
ax.axvline(100, color=INK, lw=0.8)
for i, (k, v) in enumerate(s.items()):
    if v >= 101 or v <= 97.5:
        ax.text(v + (0.1 if v >= 100 else -0.1), i, f"{v:.1f}", va="center", ha="left" if v >= 100 else "right", fontsize=8)
ax.set_xlim(95, 105.5); ax.tick_params(axis="y", labelsize=8)
ax.set_title(f"都道府県の物価水準（総合、全国平均＝100、{Y}年）", loc="left")
ax.set_xlabel("消費者物価地域差指数"); fig.text(0, -0.02, SOURCE, fontsize=7, color=GRAY)
fig.savefig(FIG / "a127_rank.png"); plt.close(fig)

# --- 2. 費目ごとの差
items = ["住居", "光熱・水道", "教育", "被服及び履物", "家具・家事用品", "食料", "教養娯楽", "交通・通信", "諸雑費", "保健医療"]
sp = []
for it in items + ["総合", "家賃を除く総合"]:
    v = p25[it]
    sp.append({"item": it, "max_pref": v.idxmax(), "max": v.max(), "min_pref": v.idxmin(), "min": v.min(),
               "range": v.max() - v.min(), "sd": v.std(ddof=0),
               "sd_2018": P.loc[2018][it].std(ddof=0)})
sp = pd.DataFrame(sp); sp.to_csv(RES / "a127_item_spread_2025.csv", index=False)
fig, ax = plt.subplots(figsize=(8, 5.6))
order = sp[sp.item.isin(items)].sort_values("sd").item.tolist()
rng = np.random.default_rng(0)
for i, it in enumerate(order):
    v = p25[it]
    ax.scatter(v, i + rng.uniform(-0.15, 0.15, len(v)), s=12, color=LIGHT, zorder=2)
    ax.scatter(v["東京都"], i, s=30, color=ORANGE, zorder=3)
    ax.text(v.max() + 0.6, i, f"{v.idxmax()} {v.max():.1f}", va="center", fontsize=8)
    ax.text(v.min() - 0.6, i, f"{v.idxmin()} {v.min():.1f}", va="center", ha="right", fontsize=8)
ax.axvline(100, color=INK, lw=0.8)
ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
ax.set_xlim(66, 145)
ax.set_title(f"費目ごとの都道府県の散らばり（{Y}年、全国平均＝100）", loc="left")
ax.set_xlabel("消費者物価地域差指数（点は47都道府県、オレンジは東京都）")
fig.text(0, -0.03, SOURCE, fontsize=7, color=GRAY)
fig.savefig(FIG / "a127_items.png"); plt.close(fig)

# --- 3. 順位の安定性（家賃を除く総合：定義が全期間で同じ）
X = P["家賃を除く総合"].unstack("pref")
rho = {y: spearmanr(X.loc[2013], X.loc[y]).statistic for y in X.index}
top3 = X.apply(lambda r: r.rank(ascending=False, method="min") <= 3, axis=1).sum().sort_values(ascending=False)
ch = (X.loc[2025] - X.loc[2013]).sort_values()
stab = pd.DataFrame({"index_2013": X.loc[2013], "index_2025": X.loc[2025], "change": X.loc[2025] - X.loc[2013],
                     "rank_2013": X.loc[2013].rank(ascending=False, method="min"),
                     "rank_2025": X.loc[2025].rank(ascending=False, method="min"), "years_in_top3": top3})
stab.sort_values("index_2025", ascending=False).to_csv(RES / "a127_stability.csv")
pd.Series(rho, name="spearman_vs_2013").to_csv(RES / "a127_rank_corr.csv")
top1 = X.idxmax(axis=1); top1.to_csv(RES / "a127_top1_by_year.csv")
sdy = X.std(axis=1, ddof=0); sdy.to_csv(RES / "a127_sd_by_year.csv")

fig, ax = plt.subplots(figsize=(8, 5))
hl = {"東京都": ORANGE, "神奈川県": "#c7531f", "沖縄県": BLUE, "北海道": "#1c5aa6"}
for pref in X.columns:
    if pref not in hl:
        ax.plot(X.index, X[pref], color="#d9d8d3", lw=0.8)
for pref, c in hl.items():
    ax.plot(X.index, X[pref], color=c, lw=2)
    ax.text(2025.2, X.loc[2025, pref], f"{pref} {X.loc[2025, pref]:.1f}", color=c, va="center", fontsize=9)
ax.axhline(100, color=INK, lw=0.8)
ax.set_xlim(2013, 2028); ax.set_xticks(range(2013, 2026, 2))
ax.set_title("家賃を除く総合の推移（全国平均＝100）", loc="left")
ax.set_ylabel("地域差指数"); fig.text(0, -0.03, SOURCE, fontsize=7, color=GRAY)
fig.savefig(FIG / "a127_stability.png"); plt.close(fig)

print("top 2025 総合:", rk["総合"].sort_values(ascending=False).head(6).round(1).to_dict())
print("bottom 2025 総合:", rk["総合"].sort_values().head(6).round(1).to_dict())
print("家賃除く top:", rk["家賃を除く総合"].sort_values(ascending=False).head(6).round(1).to_dict(), "bottom:", rk["家賃を除く総合"].sort_values().head(4).round(1).to_dict())
print(sp.round(2).to_string())
print("rho", {k: round(v, 3) for k, v in rho.items()})
print("top1", top1.to_dict()); print("top3 years", top3.head(8).to_dict())
print("change", ch.head(5).round(1).to_dict(), ch.tail(5).round(1).to_dict())
print("sd by year", sdy.round(2).to_dict())
