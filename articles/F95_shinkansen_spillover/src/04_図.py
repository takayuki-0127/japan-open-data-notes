"""04 図：f01 県のグループ／f02 福井・岐阜の実績と合成／f03 直接効果と波及の比較／f04 距離と推定値／f05 頑健性"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

E = pd.read_csv(RES / "estimates_main.csv")
S = json.load(open(RES / "summary.json"))
R = pd.read_csv(RES / "robustness.csv")
DV = pd.read_csv(RES / "effect_vs_distance.csv")
ser = pd.read_csv(RES / "series_neighbors.csv", index_col=0, parse_dates=True)
C = coords(); ADJ = adjacency()
RING2 = S["ring2"]; BASE = S["base_donors"]

# f01 県のグループ（県庁所在地の位置、中部・近畿の周辺）
fig, ax = plt.subplots(figsize=(7.2, 6.2))
grp = {}
for p in C.index:
    grp[p] = ("処置（石川・富山）" if p in TREATED else "隣・駅なし（福井・岐阜）" if p in RING1_BORDER else
              "隣・駅あり（新潟・長野）" if p in RING1_LINE else "隣の隣" if p in RING2 else
              "対照" if p in BASE else "除外（別の新幹線・震災）")
col = {"処置（石川・富山）": ORANGE, "隣・駅なし（福井・岐阜）": BLUE, "隣・駅あり（新潟・長野）": LIGHT,
       "隣の隣": GREEN, "対照": GRAY, "除外（別の新幹線・震災）": "#dddddd"}
for a in TREATED:
    for b in ADJ[a]:
        ax.plot(*zip(C.loc[a], C.loc[b]), color=ORANGE, lw=1, alpha=.5, zorder=1)
for g, c in col.items():
    ps = [p for p in C.index if grp[p] == g]
    ax.scatter(C.loc[ps, "cap_lon"], C.loc[ps, "cap_lat"], s=70, color=c, label=g, zorder=3, edgecolor="white")
for p in C.index:
    lo, la = C.loc[p]
    if 132.5 < lo < 141.5 and 33.3 < la < 39:
        dx = -.42 if p in ("京都", "山形") else .08
        ax.text(lo + dx, la + .06, p, fontsize=8.5, color=INK)
ax.set_xlim(132.5, 141.5); ax.set_ylim(33.3, 39); ax.set_aspect(1.2)
ax.set_xlabel("経度"); ax.set_ylabel("緯度")
ax.set_title("県のグループ分け（点は県庁所在地、線は石川・富山と県境を接する県）", loc="left")
ax.legend(fontsize=8.5, loc="lower right", frameon=False)
save(fig, "f01_groups.png")

# f02 福井・岐阜：実績と SDID の合成（事前の同じ月の平均との差、%）
fig, axs = plt.subplots(2, 1, figsize=(8.5, 6.4), sharex=True)
for ax, p in zip(axs, RING1_BORDER):
    a = ser[p + "_actual"].rolling(3, center=True).mean(); s_ = ser[p + "_SDID"].rolling(3, center=True).mean()
    ax.plot(a.index, np.expm1(a) * 100, color=BLUE, lw=1.8, label=f"{p}（実績）")
    ax.plot(s_.index, np.expm1(s_) * 100, color=GRAY, lw=1.5, ls="--", label="合成した対照（SDID）")
    ax.axvline(OPEN, color=ORANGE, lw=1); ax.axhline(0, color=INK, lw=.5)
    att = E.query("unit==@p and method=='SDID'").att_pct.iloc[0]
    ax.set_title(f"{p}：開業後の平均の差 {att:+.1f}%", loc="left")
    ax.set_ylabel("事前の同じ月との差（%）"); ax.legend(fontsize=8.5, frameon=False, loc="upper left")
axs[0].text(OPEN, axs[0].get_ylim()[1], " 2015年3月 開業", color=ORANGE, fontsize=8.5, va="top")
fig.suptitle("隣の県の日本人の延べ宿泊者数（3か月移動平均）", x=0.01, ha="left", fontsize=13)
save(fig, "f02_neighbors_series.png")

# f03 直接効果と波及（SDID、プラセボの標準偏差による95%区間）
rows = [("石川（直接）", E.query("unit=='石川' and method=='SDID' and group=='直接：隣を外した対照（32県）'").iloc[0], ORANGE),
        ("富山（直接）", E.query("unit=='富山' and method=='SDID' and group=='直接：隣を外した対照（32県）'").iloc[0], ORANGE),
        ("福井（隣・駅なし）", E.query("unit=='福井' and method=='SDID'").iloc[0], BLUE),
        ("岐阜（隣・駅なし）", E.query("unit=='岐阜' and method=='SDID'").iloc[0], BLUE),
        ("福井＋岐阜", R.query("kind=='基本'").iloc[0].rename({"att_pct": "att_pct"}), BLUE),
        ("新潟（隣・駅あり）", E.query("unit=='新潟' and method=='SDID'").iloc[0], LIGHT),
        ("長野（隣・駅あり）", E.query("unit=='長野' and method=='SDID'").iloc[0], LIGHT)]
fig, ax = plt.subplots(figsize=(8, 4.6))
for i, (lab, r, c) in enumerate(rows[::-1]):
    ax.plot([r.lo, r.hi], [i, i], color=c, lw=3, alpha=.6); ax.scatter(r.att_pct, i, color=c, s=60, zorder=3)
    ax.text(r.hi + .8, i, f"{r.att_pct:+.1f}%", va="center", fontsize=9)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows[::-1]])
ax.axvline(0, color=INK, lw=.7); ax.set_xlabel("開業後（2015/3〜2019/12）の平均の効果（%）")
ax.set_title("新幹線が来た県と、その隣の県の推定値（SDID、横線はプラセボによる95%区間）", loc="left", fontsize=11.5)
save(fig, "f03_direct_vs_spillover.png")

# f04 距離と推定値：隣の県の値は、対照の県を「処置」とみなした値の中でどこにあるか
fig, ax = plt.subplots(figsize=(8, 4.8))
d0 = DV[DV.role == "対照（プラセボ）"]
ax.scatter(d0.dist_km, d0.att_pct, color=GRAY, s=30, alpha=.7, label="対照の県を「処置」とみなした値")
for role, c in [("隣（駅なし）", BLUE), ("隣（駅あり）", LIGHT), ("処置", ORANGE)]:
    d = DV[DV.role == role]; ax.scatter(d.dist_km, d.att_pct, color=c, s=70, label=role, edgecolor="white", zorder=3)
    for _, r in d.iterrows(): ax.text(r.dist_km + 12, r.att_pct, r.pref, fontsize=9, va="center")
sd = d0.att_pct.std(); ax.axhspan(-1.96 * sd, 1.96 * sd, color=GRAY, alpha=.12)
ax.axhline(0, color=INK, lw=.6)
ax.set_xlabel("石川・富山の県庁所在地からの距離（近い方、km）"); ax.set_ylabel("推定値（%）")
ax.set_title("距離と推定値（SDID）：灰色の帯は「何もなくてもこのくらいはぶれる」範囲", loc="left", fontsize=11.5)
ax.legend(fontsize=8.5, frameon=False, loc="center right")
save(fig, "f04_distance.png")

# f05 頑健性：福井＋岐阜（または別の「隣」）をまとめた推定
fig, ax = plt.subplots(figsize=(8.8, 6.2))
R = R.reset_index(drop=True)
colk = {"基本": ORANGE, "隣の定義": BLUE, "期間": GREEN, "対照": "#7a5cc4", "系列": GRAY, "時点のプラセボ": INK}
lab = [l if len(l) < 30 else l[:29] + "…" for l in R.label]
for i, r in R.iloc[::-1].reset_index(drop=True).iterrows():
    c = colk[r.kind]; ax.plot([r.lo, r.hi], [i, i], color=c, lw=3, alpha=.5); ax.scatter(r.att_pct, i, color=c, s=40, zorder=3)
ax.set_yticks(range(len(R))); ax.set_yticklabels([f"［{k}］{l}" for k, l in zip(R.kind, lab)][::-1], fontsize=8.5)
ax.axvline(0, color=INK, lw=.7); ax.set_xlabel("推定値（%、横線はプラセボによる95%区間）")
ax.set_title("頑健性：隣の定義・期間・対照・系列を変えても、0をまたぐ", loc="left")
save(fig, "f05_robustness.png")
print("ok")
