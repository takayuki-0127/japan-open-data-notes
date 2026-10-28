"""図6枚"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, AREAS, load, save
from sklearn.gaussian_process.kernels import Matern

LBL = {"knn10": "近い10地点", "gp_map": "GP（地図だけ）", "ridge": "線形回帰", "rk": "回帰＋GP（回帰クリギング）",
       "gp_ard": "GP（座標＋11の特徴）", "lgbm": "LightGBM（F03型）"}
sc = pd.read_csv(RES / "cv_scores.csv")
d = load("住宅地")

# 1) 首都圏の地図（GP の平均）
z = np.load(RES / "grid_首都圏.npz")
mask = z["dist"] > 3
mu = np.ma.masked_where(mask, np.exp(z["mu"]) / 1e4)
fig, ax = plt.subplots(figsize=(7.2, 6.2))
im = ax.pcolormesh(z["gx"], z["gy"], mu, norm=LogNorm(vmin=3, vmax=300), cmap="viridis", shading="auto")
s = d[(d["area"] == "首都圏") & (d["y_km"] > -80)]
ax.scatter(s["x_km"], s["y_km"], s=0.6, c="white", alpha=0.5, lw=0)
XL, YL = (s["x_km"].min() - 3, s["x_km"].max() + 3), (s["y_km"].min() - 3, s["y_km"].max() + 3)
ax.set_xlim(*XL); ax.set_ylim(*YL)
cb = fig.colorbar(im, ax=ax, shrink=0.8); cb.set_label("予測した地価（万円/㎡、対数目盛）")
ax.set_aspect("equal"); ax.set_xlabel("東京駅から東西（km）"); ax.set_ylabel("南北（km）")
ax.set_title("首都圏の住宅地の地価を、緯度経度だけのガウス過程でなめらかに描く")
ax.text(0.01, 0.01, "白い点：地価公示の地点（島しょ部を除く）／ 最寄りの地点から3km以上の場所は描いていない", transform=ax.transAxes, fontsize=8, color=GRAY)
save(fig, "f75_map.png")

# 2) 不確実性の地図
sdm = np.ma.masked_where(mask, np.exp(2 * 1.645 * z["sd"]))
fig, ax = plt.subplots(figsize=(7.2, 6.2))
im = ax.pcolormesh(z["gx"], z["gy"], sdm, cmap="magma_r", vmin=float(np.nanpercentile(sdm.compressed(), 2)),
                   vmax=float(np.nanpercentile(sdm.compressed(), 98)), shading="auto")
ax.scatter(s["x_km"], s["y_km"], s=0.6, c=INK, alpha=0.3, lw=0); ax.set_xlim(*XL); ax.set_ylim(*YL)
cb = fig.colorbar(im, ax=ax, shrink=0.8); cb.set_label("90%予測区間の幅（上限÷下限、倍）")
ax.set_aspect("equal"); ax.set_xlabel("東京駅から東西（km）"); ax.set_ylabel("南北（km）")
ax.set_title("地点が少ない場所ほど、ガウス過程の予測の幅は広がる")
save(fig, "f75_uncertainty.png")

# 3) 精度の比較（中央値の誤差）
models = ["knn10", "gp_map", "ridge", "rk", "gp_ard", "lgbm"]
fig, axes = plt.subplots(1, 3, figsize=(12, 4.6), sharey=True)
for ax, area in zip(axes, AREAS):
    t = sc[sc["area"] == area].set_index(["model", "cv"])["median_ape"]
    y = np.arange(len(models))
    ax.barh(y + 0.2, [t[(m, "random")] * 100 for m in models], 0.4, color=LIGHT, label="ランダムに分けた検証")
    ax.barh(y - 0.2, [t[(m, "blk20")] * 100 for m in models], 0.4, color=BLUE, label="20km四方ごとに分けた検証")
    for i, m in enumerate(models):
        ax.text(t[(m, "blk20")] * 100 + 0.4, i - 0.2, f"{t[(m, 'blk20')] * 100:.1f}", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels([LBL[m] for m in models]); ax.invert_yaxis()
    ax.set_title(f"{area}（{int(sc[sc.area == area]['n'].iloc[0]):,}地点）"); ax.set_xlabel("予測の外れ（中央値、%）")
axes[0].legend(frameon=False, fontsize=8, loc="lower right")
fig.suptitle("住宅地の地価の予測の外れ：モデルと検証の分け方で比べる", y=1.02)
save(fig, "f75_accuracy.png")

# 4) 予測区間の当たり方
gpm = ["gp_map", "rk", "gp_ard"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for j, (col, ttl) in enumerate([("cover90", "90%予測区間に入った割合"), ("width90", "90%予測区間の幅（上限÷下限、倍、中央値）")]):
    ax = axes[j]; x = 0; ticks = []
    for area in AREAS:
        for m in gpm:
            t = sc[(sc.area == area) & (sc.model == m)].set_index("cv")[col]
            ax.bar(x - 0.2, t["random"] * (100 if col == "cover90" else 1), 0.4, color=LIGHT)
            ax.bar(x + 0.2, t["blk20"] * (100 if col == "cover90" else 1), 0.4, color=BLUE)
            ticks.append((x, f"{area[:2]}\n{['地図', '回帰+GP', 'ARD'][gpm.index(m)]}")); x += 1
        x += 0.5
    ax.set_xticks([a for a, b in ticks]); ax.set_xticklabels([b for a, b in ticks], fontsize=8)
    if col == "cover90":
        ax.axhline(90, color=ORANGE, lw=1.2, ls="--"); ax.set_ylim(60, 100); ax.text(8.6, 90.6, "目標90%", color=ORANGE, fontsize=8)
    ax.set_title(ttl, fontsize=11)
from matplotlib.patches import Patch
axes[0].legend(handles=[Patch(color=LIGHT, label="ランダムに分けた検証"), Patch(color=BLUE, label="20km四方ごとに分けた検証")],
               frameon=False, fontsize=8, loc="lower left")
fig.suptitle("ガウス過程の予測区間は、場所で分けた検証でも9割前後に入ったか", y=1.02)
save(fig, "f75_coverage.png")

# 5) カーネル：距離と相関
kf = pd.read_csv(RES / "kernel_full.csv")
fig, ax = plt.subplots(figsize=(7, 4.3))
r = np.linspace(0, 20, 200)
for (_, row), c in zip(kf.iterrows(), [BLUE, ORANGE, GREEN]):
    m = Matern(length_scale=row["length_scale_km"], nu=1.5)
    k = m(np.zeros((1, 2)), np.c_[r, np.zeros_like(r)])[0] * row["spatial_share"]
    ax.plot(r, k, color=c, lw=2, label=f"{row['area']}（長さスケール {row['length_scale_km']:.1f}km、なめらかな部分 {row['spatial_share'] * 100:.0f}%）")
ax.set_xlabel("2地点の距離（km）"); ax.set_ylabel("地価（対数）の相関")
ax.set_title("離れるほど地価は似なくなる：推定したカーネルの形")
ax.legend(frameon=False, fontsize=8); ax.set_ylim(0, 1)
save(fig, "f75_kernel.png")

# 6) 頑健性
rb = pd.read_csv(RES / "robustness.csv")
base = sc[(sc.area == "首都圏") & (sc.cv == "blk20")].set_index("model")["median_ape"]
fig, ax = plt.subplots(figsize=(8.5, 5.2))
rb["lab"] = rb["check"] + "｜" + rb["model"].map(LBL) + "｜" + rb["cv"]
ax.barh(np.arange(len(rb)), rb["median_ape"] * 100, color=[BLUE if m in ("gp_map", "rk") else GRAY for m in rb["model"]])
ax.set_yticks(np.arange(len(rb))); ax.set_yticklabels(rb["lab"], fontsize=7); ax.invert_yaxis()
ax.axvline(base["gp_map"] * 100, color=ORANGE, ls="--", lw=1); ax.text(base["gp_map"] * 100, -0.8, "基本のGP（地図）", color=ORANGE, fontsize=8)
ax.set_xlabel("予測の外れ（中央値、%）"); ax.set_title("頑健性：カーネル・ブロックの大きさ・商業地（首都圏）")
save(fig, "f75_robust.png")
print("ok")
