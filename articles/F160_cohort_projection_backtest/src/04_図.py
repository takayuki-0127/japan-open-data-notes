"""F160 の図（figures/）。"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import RES, FIG

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
S = json.load(open(RES / "summary.json", encoding="utf-8"))
C_OWN, C_IPSS, C_GRAY, C_ACC = "#2b6cb0", "#c05621", "#a0aec0", "#2f855a"

# 1. 方法ごとの外れ（3つの答え合わせ）
bt = pd.read_csv(RES / "r2_backtest_methods.csv")
methods = ["そのまま（人口が変わらない）", "移動ゼロ", "直近5年の移動率", "直近10年の平均", "移動率を県へ縮める", "社人研", "自作と社人研の平均"]
cases = [(2015, 2020, "2015年基準→2020年\n（5年先）"), (2015, 2025, "2015年基準→2025年\n（10年先）"), (2020, 2025, "2020年基準→2025年\n（5年先）")]
fig, axes = plt.subplots(1, 3, figsize=(13, 5.2), sharey=True)
for ax, (b, t, lab) in zip(axes, cases):
    g = bt[(bt.base == b) & (bt.target == t)].set_index("method")
    vals = [g.mape.get(m, np.nan) for m in methods]
    cols = [C_IPSS if m == "社人研" else (C_ACC if m == "自作と社人研の平均" else (C_GRAY if m in methods[:2] else C_OWN)) for m in methods]
    y = np.arange(len(methods))
    ax.barh(y, vals, color=cols)
    for yi, v in zip(y, vals):
        ax.text(v + 0.15 if np.isfinite(v) else 0.2, yi, f"{v:.2f}%" if np.isfinite(v) else "（10年前のデータなし）", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(methods)
    ax.invert_yaxis(); ax.set_title(lab, fontsize=11)
    ax.set_xlim(0, max(16, np.nanmax(vals) * 1.25))
    ax.set_xlabel("市区町村の人口の外れ（平均絶対誤差、%）")
fig.suptitle("自作の推計と社人研の推計の外れ（1,681市区町村）", fontsize=13)
fig.tight_layout(); fig.savefig(FIG / "fig1_methods.png", dpi=150); plt.close(fig)

# 2. 移動率をどこまで県の値へ縮めるか（k）
kg = pd.read_csv(RES / "r1_shrink_grid.csv")
lab = [str(k) if k != "pref" else "県の値" for k in kg.k]
x = np.arange(len(kg))
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(x, kg.tune_2015_2020, "o-", color=C_OWN, label="選んだ期間：2015年基準→2020年")
ax.plot(x, kg.test_2020_2025, "s-", color=C_IPSS, label="確かめ：2020年基準→2025年")
ax.plot(x, kg.test_2015_2025 / 2, "^--", color=C_GRAY, label="参考：2015年基準→2025年（÷2）")
kb = int(np.argmin(kg.tune_2015_2020))
ax.axvline(kb, color="#718096", lw=0.8, ls=":")
ax.text(kb + 0.1, ax.get_ylim()[1] * 0.98, f"選んだ k={kg.k[kb]}", va="top", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(lab)
ax.set_xlabel("縮める強さ k（年齢・男女の人口が k 人のとき、市区町村と県の値を半々に混ぜる）")
ax.set_ylabel("平均絶対誤差（%）")
ax.set_title("小さな市区町村の移動率を県の値に寄せると、外れは減るか")
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "fig2_shrink.png", dpi=150); plt.close(fig)

# 3. 自作と社人研の外れは同じ場所で起きる
u = pd.read_csv(RES / "r2_units_2025.csv")
eo = (u.own / u.act2025 - 1) * 100; ei = (u.ipss / u.act2025 - 1) * 100
fig, ax = plt.subplots(figsize=(6.6, 6))
sz = np.clip(np.sqrt(u.pop2020) / 25, 2, 60)
ax.scatter(ei, eo, s=sz, alpha=0.35, color=C_OWN, edgecolor="none")
lim = 15
ax.plot([-lim, lim], [-lim, lim], color="#718096", lw=0.8)
ax.axhline(0, color="#cbd5e0", lw=0.6); ax.axvline(0, color="#cbd5e0", lw=0.6)
ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
ax.set_xlabel("社人研2023年推計の外れ（%、2025年）")
ax.set_ylabel("自作（移動率を県へ縮める）の外れ（%、2025年）")
c = S["own_vs_ipss"]["2020→2025"]["corr_err"]
ax.set_title(f"2020年基準→2025年：2つの推計の外れの相関 {c:.2f}\n（点の大きさは2020年の人口）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig3_err_scatter.png", dpi=150); plt.close(fig)

# 4. 規模別
bs = pd.read_csv(RES / "r3_by_size.csv")
g = bs[(bs.base == 2020)]
sizes = ["5千人未満", "5千～2万人", "2万～10万人", "10万人以上"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
w = 0.26
for j, (m, col) in enumerate((("直近5年の移動率", C_GRAY), ("移動率を県へ縮める", C_OWN), ("社人研", C_IPSS))):
    h = g[g.method == m].set_index("size").loc[sizes]
    axes[0].bar(np.arange(4) + (j - 1) * w, h.mape, w, color=col, label=m)
    axes[1].bar(np.arange(4) + (j - 1) * w, h.bias, w, color=col, label=m)
for ax, t in zip(axes, ("平均絶対誤差（%）", "平均の外れの向き（%、＋は多すぎ）")):
    ax.set_xticks(np.arange(4)); ax.set_xticklabels([f"{s}\n({int(g[g["size"]==s].n.iloc[0])})" for s in sizes])
    ax.set_ylabel(t); ax.axhline(0, color="#718096", lw=0.6)
axes[0].legend(frameon=False, fontsize=9)
fig.suptitle("2020年の人口の規模別：2020年基準→2025年の外れ", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig4_by_size.png", dpi=150); plt.close(fig)

# 5. 外れの出どころ
orc = pd.read_csv(RES / "r4_oracle.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
cols = [C_OWN, C_IPSS, C_ACC, C_GRAY]
y = np.arange(len(orc))
for ax, col, t in ((axes[0], "mape", "総人口の平均絶対誤差（%）"), (axes[1], "mape_age04", "0～4歳の人口の平均絶対誤差（%）")):
    ax.barh(y, orc[col], color=cols)
    for yi, v in zip(y, orc[col]):
        ax.text(v + max(orc[col]) * 0.02, yi, f"{v:.2f}", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(orc.case if ax is axes[0] else [""] * len(y)); ax.invert_yaxis()
    ax.set_xlabel(t); ax.set_xlim(0, max(orc[col]) * 1.2)
fig.suptitle("2020年基準→2025年：仮定を「答え」に差し替えると外れはどれだけ消えるか", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig5_oracle.png", dpi=150); plt.close(fig)

# 6. 2025年基準の自作の2050年と、社人研2023年推計の2050年
v = pd.read_csv(RES / "r6_units_2050.csv").dropna()
bins = np.linspace(0.2, 1.6, 57)
fig, ax = plt.subplots(figsize=(9, 4.8))
for col, lab, c, ls in (("ipss2050", "社人研2023年推計（2020年基準）", C_IPSS, "-"),
                        ("own_shrink2050", "自作：2020～25年の移動率を県へ縮める", C_OWN, "-"),
                        ("own_avg2050", "自作：2015～25年の10年平均", C_ACC, "--")):
    r = v[col] / v.pop2025
    h, e = np.histogram(r, bins=bins)
    ax.step(e[:-1], h, where="post", color=c, ls=ls, label=lab, lw=1.6)
ax.axvline(1, color="#718096", lw=0.6)
ax.set_xlabel("2050年の人口 ÷ 2025年の人口（市区町村）")
ax.set_ylabel("市区町村の数")
o = pd.DataFrame(S["outlook2050"]).set_index("method")
ax.set_title(f"2050年の見通し：合計はほぼ同じ（自作 {o.loc['移動率を県へ縮める','total2050']/1e8:.3f}億人／社人研 {o.loc['移動率を県へ縮める','ipss2050']/1e8:.3f}億人）だが、\n自作は市区町村の間の差が大きい", fontsize=11)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "fig6_outlook2050.png", dpi=150); plt.close(fig)
print("ok")
