"""図（5枚）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, SRC_LAND, SRC_POWER, BLOCKS, DENS, KENS, save
t = pd.read_csv(RES / "group_metrics_main.csv")
base = t[t.setting == "基本（空間ブロックCV）"]
def half(w): return np.sqrt(1 + w)   # 区間の上端／予測（下端は予測÷これ）

# 図1：グループ別の誤差（中央値）と偏り
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"width_ratios": [1.35, 1]})
order = [("blk", BLOCKS), ("dens", DENS), ("ken", KENS)]
labels, ape, bias, col = [], [], [], []
for gd, gs in order:
    for g in gs:
        r = base[(base.group_def == gd) & (base.group == g)].iloc[0]
        labels.append(g); ape.append(r.med_ape * 100); bias.append(r.bias * 100); col.append({"blk": BLUE, "dens": GREEN, "ken": ORANGE}[gd])
    labels.append(""); ape.append(np.nan); bias.append(np.nan); col.append("w")
labels, ape, bias, col = labels[:-1], ape[:-1], bias[:-1], col[:-1]
y = np.arange(len(labels))[::-1]
allape = base[base.group == "全体"].med_ape.iloc[0] * 100
for ax, v, ttl, ref in ((axes[0], ape, "誤差の中央値（%）", allape), (axes[1], bias, "平均の偏り（%、＋は高く予測）", 0)):
    ax.barh(y, v, color=col, height=0.7)
    ax.axvline(ref, color=INK, lw=0.8, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(labels if ax is axes[0] else [""] * len(labels)); ax.set_title(ttl, fontsize=11)
    for yy, vv in zip(y, v):
        if not np.isnan(vv): ax.text(vv + (0.3 if vv >= 0 else -0.3), yy, f"{vv:.1f}", va="center", ha="left" if vv >= 0 else "right", fontsize=8)
axes[1].set_xlim(-12, 8)
fig.suptitle("地価の予測（空間ブロックCV）の外れ方：地方ブロック・人口密度・圏域で比べる", fontsize=12.5, y=1.0)
fig.text(0.01, 0.005, "誤差＝|予測÷実際−1| の中央値。偏り＝対数の外れの平均を％に直したもの。破線は全体（誤差18.7%）", fontsize=8, color=GRAY)
save(fig, "fig1_group_error.png", SRC_LAND)

# 図2：価格帯で分けると「安い所を高く、高い所を安く」に見える（実際の価格で分けたとき）
pb = pd.read_csv(RES / "price_band_bias.csv")
fig, ax = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(5)
for i, (basis, c) in enumerate((("実際の価格", ORANGE), ("予測した価格", BLUE))):
    v = pb[pb.basis == basis].sort_values("group").bias.values * 100
    ax.bar(x + (i - 0.5) * 0.38, v, width=0.38, color=c, label=f"{basis}で5つに分けた")
    for xx, vv in zip(x + (i - 0.5) * 0.38, v): ax.text(xx, vv + (0.4 if vv >= 0 else -0.4), f"{vv:+.1f}", ha="center", va="bottom" if vv >= 0 else "top", fontsize=8)
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(["価格帯1（安い）", "2", "3", "4", "価格帯5（高い）"])
ax.set_ylabel("平均の偏り（%、＋は高く予測）"); ax.legend(frameon=False, loc="upper right")
ax.set_title("同じ予測でも、何で分けるかで「偏り」の見え方が変わる", fontsize=12)
save(fig, "fig2_price_band.png", SRC_LAND)

# 図3：90% の区間のカバー率（全体で1つの幅 vs グループ別の幅）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
for ax, (gd, gs, ttl) in zip(axes, (("blk", BLOCKS, "地方ブロック"), ("dens", DENS, "人口密度（市区町村）"))):
    s = base[base.group_def == gd].set_index("group").loc[gs]
    x = np.arange(len(gs))
    ax.bar(x - 0.2, s.cover * 100, width=0.4, color=GRAY, label="全体で1つの幅")
    ax.bar(x + 0.2, s.cover_m * 100, width=0.4, color=BLUE, label="グループ別の幅")
    ax.axhline(90, color=INK, lw=0.8, ls="--")
    for xx, w in zip(x, s.width_m): ax.text(xx + 0.2, 101, f"×{half(w):.1f}", ha="center", fontsize=7.5, color=BLUE)
    ax.set_ylim(70, 104); ax.set_xticks(x); ax.set_xticklabels(gs, rotation=35, ha="right", fontsize=9)
    ax.set_title(ttl, fontsize=11); ax.set_ylabel("区間に入った割合（%）")
axes[0].legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 0.9), fontsize=9, ncol=2)
fig.suptitle("90% の予測区間：全体で幅を決めると地域で入り方が違う\n" + f"（青の上の数字は、グループ別の区間の上端が予測の何倍か。全体で1つの幅なら、どこでも×{half(base.width.iloc[0]):.1f}）", fontsize=11, y=1.04)
save(fig, "fig3_coverage.png", SRC_LAND, y=-0.09)

# 図4：補正の比較
sets = ["基本（空間ブロックCV）", "偏りの差し引き（地方ブロック別）", "偏りの差し引き（人口密度別）", "重み付け（ブロックごとの重みをそろえる）", "グループを特徴量に足す"]
short = ["補正なし", "偏りの差し引き\n（ブロック別）", "偏りの差し引き\n（人口密度別）", "重み付け\n（ブロック）", "グループを\n特徴量に"]
def summ(s, gd, key):
    u = t[(t.setting == s) & (t.group_def == gd) & (t.group != "全体")]
    return {"bias": u.bias.abs().max() * 100, "gap": (u.med_ape.max() - u.med_ape.min()) * 100}[key]
panels = [("全体の誤差の中央値（%）", lambda s: t[(t.setting == s) & (t.group == "全体")].med_ape.iloc[0] * 100),
          ("ブロックの偏りの最大（%）", lambda s: summ(s, "blk", "bias")),
          ("人口密度の偏りの最大（%）", lambda s: summ(s, "dens", "bias")),
          ("ブロックの誤差の差（ポイント）", lambda s: summ(s, "blk", "gap"))]
fig, axes = plt.subplots(1, 4, figsize=(13, 4.6), sharey=True)
y = np.arange(len(sets))[::-1]
for ax, (ttl, f) in zip(axes, panels):
    v = [f(s) for s in sets]
    ax.barh(y, v, color=[GRAY] + [BLUE] * 4, height=0.6)
    for yy, vv in zip(y, v): ax.text(vv, yy, f" {vv:.1f}", va="center", fontsize=8.5)
    ax.set_title(ttl, fontsize=10); ax.set_xlim(0, max(v) * 1.3)
axes[0].set_yticks(y); axes[0].set_yticklabels(short, fontsize=9)
fig.suptitle("補正で何が変わったか：狙ったグループの偏りは消えるが、誤差の差はほぼ残る", fontsize=12, y=1.02)
save(fig, "fig4_corrections.png", SRC_LAND)

# 図5：電力（東京、F92 の予測）：日の種類別
pw = pd.read_csv(RES / "power_group_metrics.csv")
s = pw[(pw.setting == "過去の年度だけで幅を決める") & (pw.level == 0.9) & (pw.group_def == "daytype") & (pw.group != "全体")]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
x = np.arange(len(s))
axes[0].bar(x, s.mape * 100, color=[GRAY, GRAY, GRAY, ORANGE])
for xx, v in zip(x, s.mape * 100): axes[0].text(xx, v + 0.05, f"{v:.1f}", ha="center", fontsize=9)
axes[0].set_xticks(x); axes[0].set_xticklabels([g.replace("（", "\n（") for g in s.group], fontsize=8.5); axes[0].set_title("誤差の平均（%）", fontsize=11)
axes[1].bar(x - 0.2, s.cover * 100, width=0.4, color=GRAY, label="全体で1つの幅")
axes[1].bar(x + 0.2, s.cover_g * 100, width=0.4, color=BLUE, label="日の種類別の幅")
axes[1].axhline(90, color=INK, lw=0.8, ls="--"); axes[1].set_ylim(70, 102)
for xx, w in zip(x, s.width_g): axes[1].text(xx + 0.2, 99.5, f"±{(half(w)-1)*100:.0f}%", ha="center", fontsize=7.5, color=BLUE)
axes[1].set_xticks(x); axes[1].set_xticklabels([g.replace("（", "\n（") for g in s.group], fontsize=8.5); axes[1].set_title("90% の区間に入った割合（%）", fontsize=11)
axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 0.88), fontsize=8.5, ncol=2)
fig.suptitle("1日の最大電力の予測（東京、2021〜2026年度上期）：連休だけ外れやすく、区間からもはみ出しやすい", fontsize=11.5, y=1.02)
save(fig, "fig5_power_daytype.png", SRC_POWER)
print("ok")
