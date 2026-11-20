"""818 面積や太さで量を表すと、何倍の差に見えるのか？（架空のデータ）

架空の会社の5店の年間売上を、3つの描き方で描く。
  1) 棒の長さを売上に比例させる
  2) 円の面積を売上に比例させる
  3) 円の半径（太さ）を売上に比例させる（絵を縦横とも同じ倍率で大きくするのと同じ）
描いた図の上での「長さの比」「面積の比」は計算で決まる。
読み手が何倍に感じるかは、知覚の研究でよく使われる「べき乗の関係」（感じる比＝描いた比^指数）の形を借り、
指数とばらつきは作成者が置いた（長さ1.0、面積0.8、読み手ごとのばらつき0.1、1回ごとの読み誤り0.15）。
架空の読み手2,000人で数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 818
SRC = "架空の会社の5店の売上と架空の読み手（作成者が乱数で作成、seed 818）"
STORES = pd.DataFrame({"store": ["A店", "B店", "C店", "D店", "E店"], "sales": [1000, 1500, 2000, 3000, 5000]})
METHODS = {"棒の長さ": ("length", 1), "円の面積": ("area", 1), "円の半径（太さ）": ("area", 2)}
# (感じ方の種類, 描いた量が売上の何乗になるか)
BASE = {"beta_length": 1.0, "beta_area": 0.8, "beta_sd": 0.1, "noise": 0.15, "readers": 2000}
RATIOS = np.round(np.arange(1.0, 5.01, 0.25), 2)


def perceive(ratio, method, rng, beta_length=1.0, beta_area=0.8, beta_sd=0.1, noise=0.15, readers=2000):
    kind, power = METHODS[method]
    drawn = ratio ** power                                # 図の上での長さの比・面積の比
    b = rng.normal(beta_length if kind == "length" else beta_area, beta_sd, readers)
    return drawn ** b * np.exp(rng.normal(0, noise, readers))


def table(rng, ratios=RATIOS, **kw):
    rows = []
    for meth in METHODS:
        for r in ratios:
            p = perceive(r, meth, rng, **kw)
            kind, power = METHODS[meth]
            rows.append({"method": meth, "true_ratio": r, "drawn_ratio": round(r ** power, 3),
                         "perceived_median": round(float(np.median(p)), 3),
                         "p10": round(float(np.quantile(p, .1)), 3), "p90": round(float(np.quantile(p, .9)), 3),
                         "within20": round(float((np.abs(p / r - 1) <= 0.2).mean()), 3)})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    STORES.to_csv(DATA / "stores.csv", index=False)

    main_tab = table(rng)
    main_tab.to_csv(RES / "perceived_by_ratio.csv", index=False)

    # 5店について、A店を1としたときの見え方
    st = []
    for meth in METHODS:
        for _, s in STORES.iterrows():
            r = s.sales / STORES.sales.iloc[0]
            p = perceive(r, meth, rng)
            st.append({"method": meth, "store": s.store, "true_ratio": r, "drawn_ratio": round(r ** METHODS[meth][1], 2),
                       "perceived_median": round(float(np.median(p)), 2)})
    st = pd.DataFrame(st)
    st.to_csv(RES / "stores_perceived.csv", index=False)

    # 確かめ：面積の指数・ばらつき・読み誤りを変える（2倍と5倍）
    sens = []
    settings = [("基本（面積の指数0.8）", {}), ("面積の指数0.7", {"beta_area": 0.7}), ("面積の指数0.9", {"beta_area": 0.9}),
                ("面積の指数1.0（面積どおりに感じる）", {"beta_area": 1.0}), ("読み手のばらつき0.2", {"beta_sd": 0.2}),
                ("読み誤り0.3", {"noise": 0.3})]
    for k, (label, kw) in enumerate(settings):
        t = table(np.random.default_rng(SEED * 100 + k), ratios=[2.0, 5.0], **kw)
        t.insert(0, "setting", label)
        sens.append(t)
    sens = pd.concat(sens, ignore_index=True)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    pick = main_tab[main_tab.true_ratio.isin([1.5, 2.0, 3.0, 5.0])]
    out = {"assumptions": BASE, "stores": STORES.to_dict("records"),
           "main_at_1_5_2_3_5": pick.to_dict("records"), "stores_perceived": st.to_dict("records"),
           "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a818_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ売上を3つの描き方で
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.6))
    sales = STORES.sales.values / 1000
    x = np.arange(5) * 3.0
    ax = axes[0]
    ax.bar(x, sales, width=1.2, color=BLUE)
    ax.set_ylim(0, 5.8); ax.set_xticks(x); ax.set_xticklabels(STORES.store); ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    for xi, s in zip(x, STORES.sales):
        ax.text(xi, s / 1000 + 0.15, f"{s:,}万円", ha="center", fontsize=8.5)
    ax.set_title("① 棒の長さを売上に比例（E店はA店の5倍の長さ）", fontsize=11, loc="left")
    for ax, (title, rad, col) in zip(axes[1:], [("② 円の面積を売上に比例（E店はA店の5倍の面積）", np.sqrt(sales) * 0.6, GREEN),
                                                 ("③ 円の半径を売上に比例（E店はA店の25倍の面積）", sales * 0.27, ORANGE)]):
        for xi, rr in zip(x, rad):
            ax.add_patch(Circle((xi, 0), rr, color=col, alpha=.85, lw=0))
        ax.set_xlim(x[0] - 1.5, x[-1] + 1.6); ax.set_ylim(-1.45, 1.45); ax.set_aspect("equal")
        ax.set_xticks(x); ax.set_xticklabels(STORES.store); ax.set_yticks([])
        for sp in ["left", "bottom"]:
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.set_title(title, fontsize=11, loc="left")
    fig.suptitle("同じ5店の売上（1,000〜5,000万円）を3つの描き方で", y=1.0)
    fig.tight_layout()
    save(fig, "a818_three_ways.png", SRC)

    # 図2：本当の比と、読み手が感じる比
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    cols = {"棒の長さ": BLUE, "円の面積": GREEN, "円の半径（太さ）": ORANGE}
    for meth in METHODS:
        g = main_tab[main_tab.method == meth]
        ax.fill_between(g.true_ratio, g.p10, g.p90, color=cols[meth], alpha=.15, lw=0)
        ax.plot(g.true_ratio, g.perceived_median, color=cols[meth], lw=2, label=meth)
    ax.plot(RATIOS, RATIOS, color=INK, ls=":", lw=1, label="本当の比（棒の長さとほぼ重なる）")
    ax.set_xlabel("本当の売上の比（何倍か）"); ax.set_ylabel("読み手が感じる比（中央値と10〜90%）")
    ax.set_yscale("log"); ax.set_yticks([1, 2, 3, 5, 10, 20]); ax.set_yticklabels(["1", "2", "3", "5", "10", "20"])
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("半径で描くと差は大きく、面積で描くと小さく感じられる（置いた感じ方で）")
    save(fig, "a818_perceived.png", SRC)

    # 図3：確かめ（本当の2倍が何倍に感じられるか）
    fig, ax = plt.subplots(figsize=(8, 4))
    labs = [s for s, _ in settings]
    yy = np.arange(len(labs))[::-1]
    for off, meth in [(0.27, "棒の長さ"), (0, "円の面積"), (-0.27, "円の半径（太さ）")]:
        v = [float(sens[(sens.setting == s) & (sens.method == meth) & (sens.true_ratio == 2.0)].perceived_median.iloc[0]) for s in labs]
        ax.barh(yy + off, v, 0.26, color=cols[meth], label=meth)
        for yi, vv in zip(yy + off, v):
            ax.text(vv + 0.04, yi, f"{vv:.1f}倍", va="center", fontsize=8)
    ax.axvline(2, color=INK, ls=":", lw=1)
    ax.set_yticks(yy); ax.set_yticklabels(labs, fontsize=9); ax.set_xlim(0, 4.8)
    ax.set_xlabel("本当は2倍の売上が、何倍に感じられるか（中央値）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("感じ方の置き方を変えても、半径で描いた2倍は2倍より大きく見える")
    save(fig, "a818_sens.png", SRC)
    print(pick.to_string()); print(st.to_string()); print(sens.to_string())


if __name__ == "__main__":
    main()
