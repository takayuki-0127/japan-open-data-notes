"""図を作る。"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import DATA, RES, FIG, RAW

FIG.mkdir(exist_ok=True)
PREF = pd.read_csv(RAW / "pref_points_F33.csv")["pref"].tolist()
S = json.load(open(RES / "summary.json", encoding="utf-8"))
df = pd.read_csv(DATA / "flu_weekly_pref.csv")
MAIN = [f"{y}/{str(y + 1)[-2:]}" for y in range(2012, 2020)]


def sw_label(sw):
    w = sw + 36
    return f"{w}週" if w <= 52 else f"{w - 52}週"


# 1. ある1シーズンの週×県のヒートマップ（北から順）
s0 = "2018/19"
w = df[df["season"] == s0].pivot(index="pcode", columns="sw", values="per").sort_index()
w = w.loc[:, (w.columns >= 6) & (w.columns <= 32)]
fig, ax = plt.subplots(figsize=(9, 7.2))
im = ax.imshow(np.log1p(w.values), aspect="auto", cmap="magma_r")
ax.set_yticks(range(47)); ax.set_yticklabels([p.replace("県", "").replace("府", "").replace("都", "") if p != "北海道" else p for p in PREF], fontsize=6)
xt = list(range(0, w.shape[1], 3))
ax.set_xticks(xt); ax.set_xticklabels([sw_label(w.columns[i]) for i in xt], fontsize=8)
cb = fig.colorbar(im, ax=ax, shrink=0.7)
ticks = [0, 1, 5, 10, 30, 60]
cb.set_ticks(np.log1p(ticks)); cb.set_ticklabels([str(t) for t in ticks]); cb.set_label("定点当たり報告数")
ax.set_title(f"{s0}シーズン：都道府県ごとのインフルエンザ（定点当たり、北から順）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f52_heatmap.png"); plt.close()

# 2. 開始の早さ（コロナ前8シーズンの平均、中央値との差）の地図
rel = pd.read_csv(RES / "onset_relative_main.csv", index_col=0)
mr = rel.mean(1)
g = gpd.read_file(RAW / "pref_F10.geojson").set_index("N03_001").loc[PREF]
g["mr"] = mr.values
from shapely.geometry import box
m = g.index == "沖縄県"
# 沖縄は本島周辺だけを左上の枠に寄せて表示（先島諸島は枠の外に出るため省く）
g.loc[m, "geometry"] = g.loc[m, "geometry"].intersection(box(126.5, 25.8, 129.5, 27.5)).translate(xoff=5.5, yoff=15.5)
fig, ax = plt.subplots(figsize=(7.5, 7.5))
lim = 3.0   # 沖縄（−7.3週）は色の端に張り付かせる
g.plot(ax=ax, column="mr", cmap="RdBu", norm=TwoSlopeNorm(0, -lim, lim), edgecolor="white", linewidth=0.4, legend=True,
       legend_kwds={"shrink": 0.6, "label": "全国の中央値より何週早い(−)／遅い(+)か（±3で頭打ち）"})
ax.plot([131.6, 135.2, 135.2], [40.9, 40.9, 43.0], color="#999", lw=0.6)
ax.text(133.4, 43.1, "沖縄", fontsize=7, color="#777", ha="center")
ax.set_xlim(128.5, 146.2); ax.set_ylim(30.5, 45.8); ax.set_axis_off()
mo = S["moran_mean_rel"]
ax.set_title(f"流行開始の早さ（2012/13〜2019/20の平均）　沖縄は {g.loc['沖縄県','mr']:+.1f}週\nMoran's I = {mo['I']}（p = {mo['p']:.3f}）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f52_onset_map.png"); plt.close()

# 3. 開始の順番の一貫性：シーズン×県の開始週（中央値との差）
order = mr.sort_values().index
fig, ax = plt.subplots(figsize=(8, 8.5))
M_ = rel.loc[order, MAIN]
lim2 = np.nanpercentile(np.abs(M_.values), 97)
im = ax.imshow(M_.values, aspect="auto", cmap="RdBu", norm=TwoSlopeNorm(0, -lim2, lim2))
ax.set_yticks(range(47)); ax.set_yticklabels([PREF[i - 1] for i in order], fontsize=6)
ax.set_xticks(range(len(MAIN))); ax.set_xticklabels(MAIN, fontsize=8, rotation=30)
fig.colorbar(im, ax=ax, shrink=0.6, label="中央値との差（週）")
o = S["order"]
ax.set_title(f"シーズンごとの開始週（平均で早い順に並べた）\n順位相関の平均 {o['spearman_mean']}、Kendall の W = {o['kendall_W']}", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f52_onset_consistency.png"); plt.close()

# 4. 時空間の自己回帰の係数と、1週先予測の改善
coef = pd.read_csv(RES / "st_ar_coef.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axes[0]
lab = {"w_adj": "隣の県（先週）", "w_mig": "人の行き来が多い県（先週）", "w_dist": "近い県（距離、先週）"}
rows = [("adj", "w_adj"), ("mig", "w_mig"), ("dist", "w_dist"), ("adj_mig", "w_adj"), ("adj_mig", "w_mig")]
names = ["隣接だけ", "移動だけ", "距離だけ", "両方：隣接", "両方：移動"]
for i, (mo_, v) in enumerate(rows):
    r = coef[(coef["model"] == mo_) & (coef["var"] == v)].iloc[0]
    ax.errorbar(r.b, i, xerr=[[r.b - r.lo], [r.hi - r.b]], fmt="o", color="#2f6f9f", capsize=3)
ax.axvline(0, color="#999", lw=0.8)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9); ax.invert_yaxis()
ax.set_xlabel("係数（対数、95%区間）")
ax.set_title("周りの県の先週の値の効き方\n（シーズン×週・シーズン×県の固定効果）", fontsize=10)
ax = axes[1]
fc = S["forecast"]
ks = ["own", "own_adj", "own_mig", "own_adj_mig"]
lb = ["自分＋全国", "＋隣接", "＋移動", "＋両方"]
vals = [fc[k]["growth_vs_own_pct"] for k in ks]
ax.bar(lb, vals, color=["#bbb", "#2f6f9f", "#e07b39", "#3a9a5b"])
for i, v in enumerate(vals):
    ax.text(i, v, f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
ax.axhline(0, color="#999", lw=0.8)
ax.set_ylabel("RMSE の変化（自分＋全国との比、%）")
ax.set_title("1週先の予測：ピーク前8週の誤差\n（1シーズン抜きの検証）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f52_model.png"); plt.close()

# 5. 頑健性とコロナ後
R = pd.read_csv(RES / "robustness.csv")
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
ax = axes[0]
sub = R[R["spearman_mean"].notna()]
ax.barh(sub["setting"], sub["spearman_mean"], color="#2f6f9f")
ax.axvline(o["spearman_mean"], color="#c0504d", ls="--", lw=1, label=f"基本 {o['spearman_mean']}")
ax.set_xlabel("開始の順番の順位相関（平均）"); ax.legend(fontsize=8); ax.invert_yaxis()
ax.tick_params(axis="y", labelsize=8)
ax.set_title("開始の順番の一貫性", fontsize=10)
ax = axes[1]
sub = R[R["b_adj"].notna()].copy()
base = coef[(coef["model"] == "adj_mig")].set_index("var")["b"]
short = {s: ("沖縄を除く" if "沖縄" in s else "コロナ後の4シーズン" if "コロナ後" in s else "偽の隣接（隣接だけのモデル、20回の平均）") for s in sub["setting"]}
labs = ["基本（コロナ前8シーズン）"] + [short[s] for s in sub["setting"]]
ba = [base["w_adj"]] + sub["b_adj"].tolist()
bm = [base["w_mig"]] + sub["b_mig"].fillna(0).tolist()
y = np.arange(len(labs))
ax.barh(y - 0.2, ba, 0.4, label="隣の県", color="#2f6f9f")
ax.barh(y + 0.2, bm, 0.4, label="人の行き来が多い県", color="#e07b39")
ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8); ax.invert_yaxis()
ax.set_xlabel("係数（両方を入れたモデル）"); ax.legend(fontsize=8)
ax.set_title("時空間の自己回帰：設定を変えると", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f52_robust.png"); plt.close()
print("ok")
