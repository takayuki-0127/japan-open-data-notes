"""04 図"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import TwoSlopeNorm, Normalize
from common import FIG, RES, load_topo

r = json.load(open(RES / "results.json", encoding="utf-8"))
rings, _ = load_topo()
LABEL = {"young_f": "15〜39歳女性の割合", "income": "納税者1人あたり所得", "commute_out": "市区町村外への通勤・通学",
         "nursery": "子ども千人あたり保育所数", "tertiary": "第3次産業の割合", "density": "可住地の人口密度",
         "unmarried": "未婚者の割合", "owner": "持ち家の割合", "floor": "1住宅あたり延べ面積"}
xs = r["main"]["x"]
d = pd.read_csv(RES / "data_main.csv", dtype={"code": str}).set_index("code")
g = pd.read_csv(RES / "gwr_local_main.csv", index_col=0, dtype={0: str})
g.index = g.index.astype(str).str.zfill(5)


def draw(ax, values, cmap, norm, title, missing="#e6e6e6"):
    polys, cols = [], []
    for code, rs in rings.items():
        for rr in rs:
            polys.append(rr)
            cols.append(values.get(code, np.nan))
    cols = np.array(cols, dtype=float)
    cm = plt.get_cmap(cmap)
    fc = [missing if np.isnan(v) else cm(norm(v)) for v in cols]
    ax.add_collection(PolyCollection(polys, facecolors=fc, edgecolors="none", linewidths=0))
    ax.set_xlim(128.5, 146.2)
    ax.set_ylim(30.8, 45.7)
    ax.set_aspect(1.25)
    ax.axis("off")
    ax.set_title(title, fontsize=11)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.01)


# 1 出生率の地図
fig, ax = plt.subplots(figsize=(7.5, 7))
v = d["tfr"].to_dict()
draw(ax, v, "RdYlBu", TwoSlopeNorm(vcenter=1.41, vmin=0.9, vmax=1.9), f"合計特殊出生率（ベイズ推定値、2018〜22年）\nMoran's I = {r['main']['moran_y'][0]:.2f}（隣どうしが似ている）")
fig.text(0.02, 0.01, "出典：厚生労働省「人口動態保健所・市区町村別統計」。灰色はデータなし（沖縄・離島の一部は範囲外）", fontsize=7.5)
fig.savefig(FIG / "f20_1_tfr_map.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 2 OLS の残差の地図
fig, ax = plt.subplots(figsize=(7.5, 7))
v = d["ols_resid"].to_dict()
draw(ax, v, "PuOr_r", TwoSlopeNorm(vcenter=0, vmin=-0.4, vmax=0.4),
     f"普通の回帰（OLS）の残差\n残差の Moran's I = {r['main']['moran_resid'][0]:.2f}、決定係数 = {r['main']['ols']['r2']:.2f}")
fig.text(0.02, 0.01, "オレンジ＝回帰の予測より出生率が高い、紫＝低い。外れ方が地域で固まっている", fontsize=7.5)
fig.savefig(FIG / "f20_2_ols_resid_map.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 3 OLS・SAR（直接効果）・SEM の係数比較
fig, ax = plt.subplots(figsize=(8.5, 5.2))
m = r["main"]
ys = np.arange(len(xs))
specs = [("OLS（普通の回帰）", m["ols"]["beta"][1:7], m["ols"]["se"][1:7], "#888888", -0.25),
         ("空間ラグ（直接効果）", m["impacts"]["direct"], None, "#d95f02", 0.0),
         ("空間誤差（SEM）", m["sem"]["beta"][1:7], m["sem"]["se"][1:7], "#1b9e77", 0.25)]
for name, b, se, c, off in specs:
    b = np.array(b)
    if se is not None:
        lo, hi = b - 1.96 * np.array(se), b + 1.96 * np.array(se)
    else:
        lo, hi = np.array(m["impacts_ci"]["direct"][0]), np.array(m["impacts_ci"]["direct"][1])
    ax.errorbar(b, ys + off, xerr=[b - lo, hi - b], fmt="o", color=c, label=name, capsize=3)
ax.axvline(0, color="k", lw=0.8)
ax.set_yticks(ys)
ax.set_yticklabels([LABEL[x] for x in xs])
ax.invert_yaxis()
ax.set_xlabel("説明する変数が1標準偏差高いときの出生率の差（95%区間）")
ax.set_title("空間の偏りを入れると、所得と通勤の向きが変わった")
ax.legend(loc="lower left", fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "f20_3_coef_compare.png", dpi=150)
plt.close(fig)

# 4 GWR の係数の地図（3変数）
fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))
for ax, x in zip(axes, ["young_f", "income", "tertiary"]):
    v = g[x].astype(float).to_dict()
    lim = float(np.nanpercentile(np.abs(g[x].astype(float)), 95))
    draw(ax, v, "RdBu_r", TwoSlopeNorm(vcenter=0, vmin=-lim, vmax=lim), f"GWR の係数：{LABEL[x]}")
fig.suptitle(f"地理的加重回帰（GWR、近い {r['main']['gwr']['bw']} 区域で推定）：赤＝その地域では出生率が高い方向、青＝低い方向", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "f20_4_gwr_maps.png", dpi=150)
plt.close(fig)

# 5 直接効果と間接効果
fig, ax = plt.subplots(figsize=(8.5, 4.8))
dr, ind = np.array(m["impacts"]["direct"]), np.array(m["impacts"]["indirect"])
ax.barh(ys - 0.2, dr, 0.4, color="#d95f02", label="直接効果（その区域の値が変わる）")
ax.barh(ys + 0.2, ind, 0.4, color="#fdb863", label="間接効果（まわりを通じて広がる分）")
ax.axvline(0, color="k", lw=0.8)
ax.set_yticks(ys)
ax.set_yticklabels([LABEL[x] for x in xs])
ax.invert_yaxis()
ax.set_xlabel("出生率の差（1標準偏差あたり）")
ax.set_title(f"空間ラグモデル（ρ = {m['sar']['rho']:.2f}）では、効果の約7割が「間接」になる")
ax.legend(fontsize=9, loc="lower left")
fig.tight_layout()
fig.savefig(FIG / "f20_5_impacts.png", dpi=150)
plt.close(fig)

# 6 頑健性：SEM の係数
runs = [("main", "基本（Queen 隣接）"), ("knn6", "近い6区域"), ("dist30", "30km以内（距離の逆数）"), ("p2013_17", "2013〜17年"),
        ("no_big_city", "政令市の区・23区を除く"), ("with_unmarried", "未婚者の割合を加える"), ("with_housing", "持ち家・住宅の広さを加える")]
fig, ax = plt.subplots(figsize=(12, 5.8))
cols = plt.get_cmap("tab10")
for j, (tag, name) in enumerate(runs):
    o = r[tag]
    b = np.array(o["sem"]["beta"][1:len(xs) + 1])
    se = np.array(o["sem"]["se"][1:len(xs) + 1])
    ax.errorbar(b, ys + (j - 3) * 0.11, xerr=1.96 * se, fmt="o", ms=4, color=cols(j), label=f"{name}（n={o['n']}）", capsize=2)
pf = r["pref_fe"]
ax.errorbar(np.array(pf["sem_beta"]), ys + 4 * 0.11, xerr=1.96 * np.array(pf["sem_se"]), fmt="s", ms=4, color="k", label=f"都道府県ダミーを加える（n={pf['n']}）", capsize=2)
ax.axvline(0, color="k", lw=0.8)
ax.set_yticks(ys)
ax.set_yticklabels([LABEL[x] for x in xs])
ax.invert_yaxis()
ax.set_xlabel("空間誤差モデルの係数（1標準偏差あたり、95%区間）")
ax.set_title("8通りのどれでも、第3次産業の割合が高い区域ほど出生率は低かった")
ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.01, 0.5))
fig.tight_layout()
fig.savefig(FIG / "f20_6_robustness.png", dpi=150)
plt.close(fig)
print("ok")
