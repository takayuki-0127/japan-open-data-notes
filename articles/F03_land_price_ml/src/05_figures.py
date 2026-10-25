"""図 f01〜f05"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
from cvlib import score

lin = pd.read_csv(RES / "oof_linear.csv"); lg = pd.read_csv(RES / "oof_lgbm.csv")
y = lg["y"].values

# f01 予測と実際（線形・ランダムCV／LightGBM ランダムCV／LightGBM 都道府県ブロックCV）
fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), sharex=True, sharey=True)
panels = [("線形回帰・ランダムCV", lin["lin_random"].values), ("LightGBM・ランダムCV", lg["lgb_random"].values),
          ("LightGBM・都道府県ごとに分けたCV", lg["lgb_pref"].values)]
lo, hi = np.log(300), np.log(1e8)
for ax, (t, p) in zip(axes, panels):
    s = score(y, p)
    ax.hexbin(y, p, gridsize=70, bins="log", cmap="Blues", mincnt=1, extent=(lo, hi, lo, hi))
    ax.plot([lo, hi], [lo, hi], color=ORANGE, lw=1)
    ax.set_title(t, fontsize=11.5)
    ax.text(0.04, 0.96, f"R² = {s['r2']:.3f}\n誤差の中央値 {s['median_ape']*100:.1f}%\n±20%以内 {s['within20']*100:.0f}%",
            transform=ax.transAxes, va="top", fontsize=10)
    tk = [1e3, 1e4, 1e5, 1e6, 1e7]
    ax.set_xticks(np.log(tk)); ax.set_xticklabels(["千", "1万", "10万", "100万", "1000万"])
    ax.set_yticks(np.log(tk)); ax.set_yticklabels(["千", "1万", "10万", "100万", "1000万"])
    ax.set_xlabel("実際の価格（円/㎡）")
axes[0].set_ylabel("予測（円/㎡）")
fig.suptitle("地価公示 25,565地点：学習に使っていない地点をどこまで当てられるか", fontsize=13, x=0.01, ha="left")
save(fig, "f01_cv_scatter.png")

# f02 SHAP の重要度（平均で予測を何%動かすか）
imp = pd.read_csv(RES / "shap_importance.csv").head(15).iloc[::-1]
G = {"立地": ["dist_station", "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km", "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"],
     "規制": ["use_district", "planning_area", "fire_area", "far", "coverage", "land_use_class"]}
col = [BLUE if f in G["立地"] else ORANGE if f in G["規制"] else GREEN for f in imp["feature"]]
pct = (np.exp(imp["mean_abs_shap"]) - 1) * 100
fig, ax = plt.subplots(figsize=(8.5, 6))
ax.barh(imp["label"], pct, color=col)
for i, v in enumerate(pct):
    ax.text(v + 0.8, i, f"{v:.0f}%", va="center", fontsize=9)
ax.set_xlabel("その特徴量が予測を平均で何%動かすか（|SHAP| の平均を％に換算）")
gr = pd.read_csv(RES / "shap_groups.csv")
txt = "　".join(f"{g.split('（')[0]} {s*100:.0f}%" for g, s in zip(gr["group"], gr["share"]))
ax.set_title("何が効いているか（SHAP、上位15）", loc="left")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label="立地（駅・人口・都市圏）"), Patch(color=ORANGE, label="規制（用途地域・容積率など）"), Patch(color=GREEN, label="土地と建物の属性")],
          loc="lower right", frameon=False, fontsize=9)
ax.text(0.99, 0.30, "寄与の合計に占める割合\n" + txt.replace("　", "\n"), transform=ax.transAxes, ha="right", fontsize=9, color=INK)
save(fig, "f02_shap_importance.png")

# f03 部分依存：駅までの距離（徒歩分）と 3km内の乗降客数
pdp = pd.read_csv(RES / "partial_dependence.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
ax = axes[0]
for cls, c in (("商業地", ORANGE), ("住宅地", BLUE)):
    q = pdp[(pdp.feature == "dist_station") & (pdp.cls == cls) & (pdp.value <= 5000)]
    ax.plot(q["value"] / 80, q["rel"] * 100, marker="o", ms=4, color=c, label=cls)
ax.axhline(100, color=GRAY, lw=0.8)
ax.set_xlabel("駅までの距離（徒歩分、80m＝1分）"); ax.set_ylabel("駅から50mを100とした予測の水準")
ax.set_title("駅から離れると、どれだけ下がるか", loc="left"); ax.legend(frameon=False)
ax = axes[1]
for cls, c in (("商業地", ORANGE), ("住宅地", BLUE)):
    q = pdp[(pdp.feature == "log_pass_3km") & (pdp.cls == cls)]
    ax.plot(np.expm1(q["value"]).clip(lower=100), q["rel"] * 100, marker="o", ms=4, color=c, label=cls)
ax.set_xscale("log"); ax.set_xlabel("半径3km内の駅の乗降客数（1日、0は100の位置に表示）")
ax.set_ylabel("乗降客数0を100とした予測の水準")
ax.set_title("周りの駅の利用者が多いほど、どれだけ上がるか", loc="left"); ax.legend(frameon=False)
fig.text(0.01, 1.0, "部分依存：ほかの特徴量はそのままで、その値だけを動かしたときの予測の平均（4,000地点）", fontsize=9.5, color=GRAY)
save(fig, "f03_partial_dependence.png")

# f04 外れる地点の地図（20km四方ブロックCVの予測との比）
r = pd.read_csv(RES / "residuals_block20.csv")
fig, ax = plt.subplots(figsize=(8, 8.5))
r = r.reindex(r["resid"].abs().sort_values().index)
sc = ax.scatter(r["lon"], r["lat"], c=r["resid"].clip(-1.2, 1.2), cmap="RdBu_r", norm=TwoSlopeNorm(0, -1.2, 1.2), s=3, lw=0)
cb = fig.colorbar(sc, ax=ax, shrink=0.6, ticks=np.log([0.33, 0.5, 0.67, 1, 1.5, 2, 3]))
cb.ax.set_yticklabels(["1/3", "1/2", "2/3", "1倍", "1.5倍", "2倍", "3倍"]); cb.set_label("実際 ÷ 予測")
for name, lon, lat, dx in (("倶知安（ニセコ）", 140.69, 42.90, 1.3), ("富良野", 142.38, 43.34, 1.3), ("軽井沢", 138.60, 36.35, 1.3), ("高山", 137.25, 36.15, -4.5), ("沖縄", 127.7, 26.3, 1.3)):
    ax.annotate(name, (lon, lat), xytext=(lon + dx, lat - 0.7), fontsize=9, arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.7))
ax.set_xlim(127, 146.5); ax.set_ylim(24, 45.8); ax.set_aspect(1.2)
ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
ax.set_title("どこで外れるか（赤＝予測より高い、青＝低い）\n20km四方のブロックごとに隠して予測", loc="left")
save(fig, "f04_error_map.png")

# f05 個別地点の SHAP（2地点）
w = pd.read_csv(RES / "shap_two_points.csv")
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for ax, (tag, g) in zip(axes, w.groupby("point", sort=False)):
    g = g.reindex(g["shap"].abs().sort_values(ascending=False).index)
    top = g.head(7); rest = g["shap"].iloc[7:].sum()
    items = list(zip(top["label"], top["shap"])) + [("その他", rest)]
    base = g["base"].iloc[0]; cur = base
    for i, (lab, v) in enumerate(items):
        ax.barh(i, v, left=cur, color=ORANGE if v > 0 else BLUE)
        ax.text(max(cur, cur + v) + 0.05, i, f"{'+' if v>0 else '−'}{abs(v):.2f}", va="center", fontsize=9)
        cur += v
    ax.set_yticks(range(len(items))); ax.set_yticklabels([l for l, _ in items]); ax.invert_yaxis()
    ax.axvline(base, color=GRAY, lw=0.8, ls="--")
    xs = [base] + list(base + np.cumsum([v for _, v in items])); ax.set_xlim(min(xs) - 0.15, max(xs) + 0.35)
    ax.set_xlabel("log(価格) への寄与（点線＝全地点の平均の予測）")
    CITY = {"中央": "東京都中央区", "佐倉": "千葉県佐倉市"}; yen = lambda v: f"{v/1e4:,.0f}万円" if v >= 1e6 else f"{v/1e4:.2f}万円"
    ax.set_title(f"{tag}（{CITY.get(g['city'].iloc[0], g['city'].iloc[0])}）\n実際 {yen(g['price'].iloc[0])}/㎡ → 予測 {yen(np.exp(g['pred'].iloc[0]))}/㎡", loc="left", fontsize=11)
fig.text(0.01, 1.02, f"全地点の平均の予測 {np.exp(w['base'].iloc[0])/1e4:.1f}万円/㎡ から、どの特徴量がどれだけ押し上げ・押し下げたか（+0.69 で約2倍）", fontsize=10, color=GRAY)
save(fig, "f05_shap_two_points.png")
print("ok")
