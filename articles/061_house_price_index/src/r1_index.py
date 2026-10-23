"""中古マンション・戸建ての圏域別ヘドニック価格指数（時間ダミー法、市区町村固定効果、2021Q1=100）"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

d = load()
d = d[(d.price > 0) & d.age.between(0, 60)].copy()


def controls(g, kind):
    X = pd.DataFrame(index=g.index)
    X["age"] = g.age; X["age2"] = g.age ** 2 / 100
    wb = pd.cut(g.walk.fillna(-1), [-2, 0, 5, 10, 15, 20, 999], labels=["不明", "~5", "6-10", "11-15", "16-20", "21~"])
    X = X.join(pd.get_dummies(wb, prefix="walk", dtype=float).drop(columns="walk_~5"))
    X["special"] = g.special
    if kind == "マンション":
        X["larea"] = np.log(g.area)
        X["src"] = (g.struct == "ＳＲＣ").astype(float)
        lay = g.layout.str.replace("＋Ｓ", "").replace({"１Ｒ": "1R/1K", "１Ｋ": "1R/1K", "１ＤＫ": "1R/1K", "１ＬＤＫ": "1LDK", "２ＤＫ": "2DK", "２ＬＤＫ": "2LDK",
                                                     "３ＤＫ": "3DK", "３ＬＤＫ": "3LDK", "４ＬＤＫ": "4LDK+"})
        lay = lay.where(lay.isin(["1R/1K", "1LDK", "2DK", "2LDK", "3DK", "3LDK", "4LDK+"]), "他・不明")
        X = X.join(pd.get_dummies(lay, prefix="lay", dtype=float).drop(columns="lay_3LDK"))
    else:
        X["larea"] = np.log(g.area); X["lfloor"] = np.log(g.floor)
        X["wood"] = (g.struct == "木造").astype(float)
    return X


def prep(kind):
    g = d[d.kind == kind].copy()
    if kind == "マンション":
        g = g[g.area.between(15, 200)]
        g["y"] = np.log(g.price / g.area)
    else:
        g = g[g.area.between(50, 1000) & g.floor.between(40, 400)]
        g["y"] = np.log(g.price)
    lo, hi = g.y.quantile([.005, .995]); g = g[g.y.between(lo, hi)]
    return g


def fit(g, kind):
    X = controls(g, kind)
    T = pd.get_dummies(g.t, prefix="t", dtype=float).drop(columns="t_0")
    X = X.join(T)
    Z = pd.concat([g[["y", "muni"]], X], axis=1)
    cols = ["y"] + list(X.columns)
    W = demean(Z, cols, "muni")
    keep = W.columns[(W.abs().sum() > 0)]
    m = sm.OLS(W["y"], W[[c for c in keep if c != "y"]]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.muni)[0]})
    tc = [c for c in m.params.index if c.startswith("t_")]
    out = pd.DataFrame({"t": [int(c[2:]) for c in tc], "b": m.params[tc].values, "se": m.bse[tc].values})
    out = pd.concat([pd.DataFrame({"t": [0], "b": [0.0], "se": [0.0]}), out]).sort_values("t")
    out["index"] = 100 * np.exp(out.b); out["lo"] = 100 * np.exp(out.b - 1.96 * out.se); out["hi"] = 100 * np.exp(out.b + 1.96 * out.se)
    return out, m


if __name__ == "__main__":
    rows, coefs, raws = [], [], []
    for kind in ["マンション", "戸建て"]:
        G = prep(kind)
        for src in ["取引", "成約"]:
            for r in REGIONS:
                g = G[(G.src == src) & (G.region == r)]
                out, m = fit(g, kind)
                out["kind"], out["src"], out["region"], out["n"] = kind, src, r, len(g)
                rows.append(out)
                if src == "取引":
                    c = m.params.drop([c for c in m.params.index if c.startswith("t_")])
                    coefs.append(pd.DataFrame({"kind": kind, "region": r, "var": c.index, "coef": c.values, "se": m.bse[c.index].values}))
                raw = g.groupby("t").y.median(); raws.append(pd.DataFrame({"t": raw.index, "raw": 100 * np.exp(raw.values - raw.iloc[0]), "kind": kind, "src": src, "region": r}))
                print(kind, src, r, len(g), round(out["index"].iloc[-1], 1), round(m.rsquared, 3))
    idx = pd.concat(rows); idx.to_csv(RES / "r1_index.csv", index=False, encoding="utf-8-sig")
    pd.concat(coefs).to_csv(RES / "r1_controls.csv", index=False, encoding="utf-8-sig")
    raw = pd.concat(raws); raw.to_csv(RES / "r1_raw_median.csv", index=False, encoding="utf-8-sig")

    # 2021年平均→2025年平均の上昇率
    idx["year"] = 2021 + idx.t // 4
    summ = idx.groupby(["kind", "src", "region", "year"])["index"].mean().unstack("year")
    summ["chg_pct"] = (summ[2025] / summ[2021] - 1) * 100
    summ = summ.reset_index(); summ.to_csv(RES / "r1_change.csv", index=False, encoding="utf-8-sig"); print(summ.round(1))

    labs = [f"{2021 + t // 4}Q{t % 4 + 1}" for t in range(20)]
    for kind, fn in [("マンション", "r1_condo_index.png"), ("戸建て", "r1_house_index.png")]:
        fig, ax = plt.subplots(figsize=(8.6, 4.8))
        for r in REGIONS:
            for src, ls in [("取引", "-"), ("成約", "--")]:
                s = idx[(idx.kind == kind) & (idx.src == src) & (idx.region == r)]
                ax.plot(s.t, s["index"], ls, color=RCOL[r], lw=2 if src == "取引" else 1.3, label=f"{r}" if src == "取引" else None)
                if src == "取引": ax.fill_between(s.t, s.lo, s.hi, color=RCOL[r], alpha=.12, lw=0)
        ax.axhline(100, color=GRAY, lw=.8)
        ax.set_xticks(range(0, 20, 2)); ax.set_xticklabels(labs[::2], rotation=0, fontsize=8.5)
        ax.set_ylabel("2021年1〜3月期＝100")
        ax.set_title(f"中古{'マンション' if kind == 'マンション' else '戸建て'}の品質調整済み価格指数（実線＝取引価格、破線＝成約価格）", loc="left", fontsize=11.5)
        ax.legend(frameon=False, ncol=5, fontsize=9, loc="upper left")
        note(ax, SOURCE + "\n築年・面積・駅距離・構造などと市区町村の差を調整。帯は95%信頼区間", -0.12)
        fig.savefig(FIG / fn); plt.close(fig)

    # 上昇率の棒グラフ
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)
    for ax, kind in zip(axes, ["マンション", "戸建て"]):
        s = summ[(summ.kind == kind)]
        for i, r in enumerate(REGIONS):
            for j, (src, col) in enumerate([("取引", None), ("成約", None)]):
                v = s[(s.region == r) & (s.src == src)].chg_pct.iloc[0]
                ax.bar(i + (j - .5) * .38, v, .36, color=RCOL[r], alpha=1 if src == "取引" else .45)
                ax.text(i + (j - .5) * .38, v + (.6 if v >= 0 else -2.2), f"{v:.0f}", ha="center", fontsize=8)
        ax.set_xticks(range(5)); ax.set_xticklabels(REGIONS, fontsize=9.5); ax.axhline(0, color=INK, lw=.6)
        ax.set_title(f"中古{kind}", loc="left")
    axes[0].set_ylabel("2021年平均→2025年平均（%）")
    fig.suptitle("品質をそろえた価格は4年で何%動いたか（濃い棒＝取引価格、薄い棒＝成約価格）", x=.02, y=1.05, ha="left", fontsize=12)
    note(axes[0], SOURCE, -0.13)
    fig.savefig(FIG / "r1_change.png"); plt.close(fig)

    # 東京圏マンション：生の中央値 vs 品質調整
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for r in ["東京圏", "その他"]:
        s = idx[(idx.kind == "マンション") & (idx.src == "取引") & (idx.region == r)]
        w = raw[(raw.kind == "マンション") & (raw.src == "取引") & (raw.region == r)]
        ax.plot(s.t, s["index"], color=RCOL[r], lw=2.2, label=f"{r}：品質調整済み")
        ax.plot(w.t, w.raw, ":", color=RCOL[r], lw=1.6, label=f"{r}：㎡単価の中央値（調整なし）")
    ax.axhline(100, color=GRAY, lw=.8); ax.set_xticks(range(0, 20, 2)); ax.set_xticklabels(labs[::2], fontsize=8.5)
    ax.set_ylabel("2021年1〜3月期＝100"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("中央値と品質調整済み指数のちがい（中古マンション・取引価格）", loc="left")
    note(ax, SOURCE, -0.12)
    fig.savefig(FIG / "r1_raw_vs_hedonic.png"); plt.close(fig)
