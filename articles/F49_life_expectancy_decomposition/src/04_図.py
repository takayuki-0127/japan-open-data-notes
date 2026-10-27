"""図を作る（6枚）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, BANDS, BAND_COLORS

FIG.mkdir(exist_ok=True)
LT = pd.read_csv(DATA / "lifetables.csv")
S = json.load(open(RES / "summary.json", encoding="utf-8"))
BL = [b[2] for b in BANDS]


def fig_rebuild():
    chk = pd.read_csv(RES / "rebuild_check.csv")
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for (y, s), c, ls in [((2000, "男"), "#1f77b4", "--"), ((2020, "男"), "#1f77b4", "-"),
                          ((2000, "女"), "#d62728", "--"), ((2020, "女"), "#d62728", "-")]:
        d = LT[(LT.year == y) & (LT.pref_code == 0) & (LT.sex == s) & (LT.age <= 95)]
        ax[0].plot(d.age, d.lx / 1000, c=c, ls=ls, label=f"{y}年 {s}")
    ax[0].set_xlabel("年齢")
    ax[0].set_ylabel("生存数（10万人のうち、千人）")
    ax[0].set_title("全国の生命表：その年齢まで生きている人の数")
    ax[0].legend(fontsize=9)
    ax[0].grid(alpha=.3)
    ax[1].hist(chk.diff0, bins=40, color="#7f7f7f")
    ax[1].set_xlabel("自作の平均寿命 − 公表の平均寿命（年）")
    ax[1].set_ylabel("表の数")
    ax[1].set_title(f"死亡率から作り直した生命表と公表値の差（480表）\n最大 {S['rebuild']['max_abs_diff_e0']:.3f} 年")
    ax[1].grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "f49_rebuild.png", dpi=150)


def fig_e0():
    e = pd.read_csv(RES / "e0_2020.csv", index_col=0)
    fig, axs = plt.subplots(1, 2, figsize=(12, 7.5))
    for ax, s, c in [(axs[0], "男", "#1f77b4"), (axs[1], "女", "#d62728")]:
        nat = S["e0_2020"][s]["national"]
        g = (e[s] - nat).sort_values()
        ax.barh(range(len(g)), g.values, color=c, alpha=.75)
        ax.set_yticks(range(len(g)))
        ax.set_yticklabels(g.index, fontsize=7)
        ax.axvline(0, c="k", lw=.8)
        ax.set_xlabel("全国との差（年）")
        ax.set_title(f"{s}：2020年の平均寿命（全国 {nat:.2f} 年）\n最も長い県と短い県の差 {S['e0_2020'][s]['range']:.2f} 年")
        ax.grid(axis="x", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "f49_e0_2020.png", dpi=150)


def fig_arriaga():
    fig, axs = plt.subplots(1, 2, figsize=(13, 8))
    for ax, s in zip(axs, ["男", "女"]):
        c = pd.read_csv(RES / f"arriaga_2020_{s}.csv", index_col=0)
        c = c.loc[c.sum(axis=1).sort_values().index]
        y = np.arange(len(c))
        pos = np.zeros(len(c))
        neg = np.zeros(len(c))
        for b, col in zip(BL, BAND_COLORS):
            v = c[b].values
            ax.barh(y, np.where(v > 0, v, 0), left=pos, color=col, label=b)
            ax.barh(y, np.where(v < 0, v, 0), left=neg, color=col)
            pos += np.where(v > 0, v, 0)
            neg += np.where(v < 0, v, 0)
        ax.plot(c.sum(axis=1).values, y, "k|", ms=8, label="差の合計")
        ax.set_yticks(y)
        ax.set_yticklabels(c.index, fontsize=7)
        ax.axvline(0, c="k", lw=.8)
        ax.set_xlabel("全国との平均寿命の差への寄与（年）")
        ax.set_title(f"{s}：何歳の死亡率の違いで差が生まれているか（2020年）")
        ax.grid(axis="x", alpha=.3)
    axs[1].legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "f49_arriaga_2020.png", dpi=150)


def fig_varshare():
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, s in zip(axs, ["男", "女"]):
        ch = S["change_2000_2020"][s]
        a = [ch["var_share2000"][b] for b in BL]
        b2 = [ch["var_share2020"][b] for b in BL]
        x = np.arange(len(BL))
        ax.bar(x - .2, a, .4, color="#bbbbbb", label="2000年")
        ax.bar(x + .2, b2, .4, color="#1f77b4" if s == "男" else "#d62728", label="2020年")
        ax.set_xticks(x)
        ax.set_xticklabels(BL, rotation=30, fontsize=8)
        ax.set_title(f"{s}：県の差のばらつきのうち、各年齢の死亡率で生まれる割合")
        ax.grid(axis="y", alpha=.3)
        ax.legend()
    axs[0].set_ylabel("ばらつき（分散）に占める割合")
    fig.tight_layout()
    fig.savefig(FIG / "f49_varshare.png", dpi=150)


def fig_trend():
    td = pd.read_csv(RES / "trend_dispersion.csv")
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for s, c in [("男", "#1f77b4"), ("女", "#d62728")]:
        d = td[td.sex == s]
        ax[0].plot(d.year, d["std"], "o-", c=c, label=f"{s}（標準偏差）")
        ax[0].plot(d.year, d["range"] / 4, ":", c=c, label=f"{s}（最長−最短）÷4")
    ax[0].set_title("47都道府県の平均寿命のばらつき（1965〜2020年）")
    ax[0].set_ylabel("年")
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=.3)
    x = np.arange(len(BL))
    for k, (s, c) in enumerate([("男", "#1f77b4"), ("女", "#d62728")]):
        v = [S["change_2000_2020"][s]["by_band"][b] for b in BL]
        ax[1].bar(x + (k - .5) * .4, v, .4, color=c, label=f"{s}（計 {S['change_2000_2020'][s]['national_change']:.2f} 年）")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(BL, rotation=30, fontsize=8)
    ax[1].set_title("全国の平均寿命の延び（2000→2020年）の年齢別の内訳")
    ax[1].set_ylabel("延びへの寄与（年）")
    ax[1].legend(fontsize=8)
    ax[1].grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "f49_trend.png", dpi=150)


def fig_robust():
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2))
    for ax, s in zip(axs, ["男", "女"]):
        r = pd.read_csv(RES / f"robust_varshare_{s}.csv", index_col=0)
        im = ax.imshow(r.values, cmap="Blues", vmin=0, vmax=.45, aspect="auto")
        ax.set_xticks(range(r.shape[1]))
        ax.set_xticklabels(r.columns, rotation=30, fontsize=8)
        ax.set_yticks(range(r.shape[0]))
        ax.set_yticklabels(r.index, fontsize=8)
        for i in range(r.shape[0]):
            for j in range(r.shape[1]):
                ax.text(j, i, f"{r.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
        ax.set_title(f"{s}：設定を変えたときの、県の差に占める各年齢の割合")
    fig.tight_layout()
    fig.savefig(FIG / "f49_robust.png", dpi=150)


if __name__ == "__main__":
    fig_rebuild(); fig_e0(); fig_arriaga(); fig_varshare(); fig_trend(); fig_robust()
    print("ok")
