"""435 対数に直して回帰した予測を元に戻すと、平均はどれだけ小さく出るのか"""
import json
import numpy as np, pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, save

SEED = 435
NSIM, N = 500, 500
B0, B1 = 2.0, 0.6
SRC = "架空のデータ（作成者が乱数で作成、seed 435）"
METHODS = ["そのまま戻す", "分散の半分を足す", "残差の平均で戻す", "一般化線形モデル"]


def gen(rng, n, sigma, kind="正規", hetero=0.0):
    x = rng.uniform(0, 3, n)
    sd = sigma * (1 + hetero * (x - 1.5) / 1.5)                    # hetero>0 なら x が大きいほど散らばりが大きい
    if kind == "正規":
        e = rng.standard_normal(n)
    elif kind == "たまに大きく外れる":                             # 9割はふつう、1割は3倍の散らばり（分散1にそろえる）
        e = rng.standard_normal(n) * np.where(rng.random(n) < 0.1, 3.0, 1.0) / np.sqrt(1.8)
    elif kind == "右に偏る":                                       # ガンマ（形2）を平均0・分散1にそろえる
        e = (rng.gamma(2.0, 1.0, n) - 2.0) / np.sqrt(2.0)
    y = np.exp(B0 + B1 * x + sd * e)
    return x, y, sd


def true_mean(x, sd, kind):
    """E[y|x]。誤差の形ごとに exp(誤差) の平均を掛ける"""
    if kind == "正規":
        m = np.exp(sd ** 2 / 2)
    elif kind == "右に偏る":
        k = sd / np.sqrt(2.0)                                       # exp(k*(G-2))、G~ガンマ(2)：E = exp(-2k) / (1-k)^2
        m = np.exp(-2 * k) / (1 - k) ** 2
    else:
        a = sd / np.sqrt(1.8)
        m = 0.9 * np.exp(a ** 2 / 2) + 0.1 * np.exp(9 * a ** 2 / 2)
    return np.exp(B0 + B1 * x) * m


def predict_all(x, y, xn):
    X = sm.add_constant(x); Xn = sm.add_constant(xn)
    ols = sm.OLS(np.log(y), X).fit()
    lp = ols.predict(Xn); res = ols.resid
    s2 = res @ res / (len(y) - X.shape[1])
    out = {"そのまま戻す": np.exp(lp), "分散の半分を足す": np.exp(lp + s2 / 2), "残差の平均で戻す": np.exp(lp) * np.exp(res).mean()}
    try:
        glm = sm.GLM(y, X, family=sm.families.Gamma(link=sm.families.links.Log())).fit()
        out["一般化線形モデル"] = glm.predict(Xn)
    except Exception:
        out["一般化線形モデル"] = np.full(len(xn), np.nan)
    return out


def scenario(rng, sigma, kind="正規", hetero=0.0, n=N, nsim=NSIM):
    acc = {m: [] for m in METHODS}; hi = {m: [] for m in METHODS}; lo = {m: [] for m in METHODS}
    for _ in range(nsim):
        x, y, _ = gen(rng, n, sigma, kind, hetero)
        xn, yn, sdn = gen(rng, n, sigma, kind, hetero)
        tm = true_mean(xn, sdn, kind)
        ref = tm if not np.isnan(tm).any() else None
        pr = predict_all(x, y, xn)
        for m in METHODS:
            tot = ref.sum() if ref is not None else yn.sum()
            acc[m].append(pr[m].sum() / tot - 1)
            if ref is not None:
                top = xn > 2.0; bot = xn < 1.0
                hi[m].append(pr[m][top].sum() / ref[top].sum() - 1); lo[m].append(pr[m][bot].sum() / ref[bot].sum() - 1)
    r = dict(散らばり=sigma, 誤差の形=kind, 散らばりの偏り=hetero, 件数=n)
    for m in METHODS:
        a = np.array(acc[m]) * 100
        r[f"{m}_合計のずれ_pct"] = float(np.nanmean(a)); r[f"{m}_ずれの散らばり_pct"] = float(np.nanstd(a))
        if hi[m]:
            r[f"{m}_xが大きい所_pct"] = float(np.nanmean(hi[m]) * 100); r[f"{m}_xが小さい所_pct"] = float(np.nanmean(lo[m]) * 100)
    return r


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for sigma in (0.2, 0.5, 0.8, 1.0, 1.5):
        rows.append(scenario(rng, sigma))
    for kind in ("右に偏る", "たまに大きく外れる"):
        for sigma in (0.5, 1.0):
            rows.append(scenario(rng, sigma, kind))
    for sigma in (0.5, 1.0):
        rows.append(scenario(rng, sigma, hetero=0.6))
    for n in (30, 100, 2000):
        rows.append(scenario(rng, 1.0, n=n, nsim=300))
    T = pd.DataFrame(rows); T.round(3).to_csv(RES / "retransformation_bias.csv", index=False)
    theory = pd.DataFrame({"散らばり": [0.2, 0.5, 0.8, 1.0, 1.5]}); theory["式の値_pct"] = (np.exp(-theory.散らばり ** 2 / 2) - 1) * 100
    theory.round(3).to_csv(RES / "theory.csv", index=False)

    # 公的データの例：市区町村の歳出を人口から当てる（対数どうしの回帰）
    d = pd.read_csv(DATA / "municipal_2022_from_F34.csv")
    d = d[(d["pop"] > 0) & (d["spend"] > 0)].reset_index(drop=True)
    lx = np.log(d["pop"].values); y = d["spend"].values
    r2 = np.random.default_rng(SEED + 1)
    fold = r2.permutation(len(d)) % 5
    size = pd.qcut(d["pop"], 5, labels=["小さい順1", "2", "3", "4", "大きい順5"])
    pub, pubinfo = [], dict(団体の数=int(len(d)), 歳出の合計_百万円=float(y.sum()))
    PRED = {}
    for spec, Xm in (("直線（人口の対数）", lx[:, None]), ("曲線（人口の対数とその2乗）", np.column_stack([lx, lx ** 2]))):
        pred = {m: np.zeros(len(d)) for m in METHODS}
        for k in range(5):
            tr, te = fold != k, fold == k
            pr = predict_all(Xm[tr], y[tr], Xm[te])
            for m in METHODS: pred[m][te] = pr[m]
        PRED[spec] = pred
        ols = sm.OLS(np.log(y), sm.add_constant(Xm)).fit()
        pubinfo[spec] = dict(対数の残差の標準偏差=float(np.sqrt(ols.scale)), 残差の歪度=float(pd.Series(ols.resid).skew()), 決定係数=float(ols.rsquared),
                             係数=[float(v) for v in ols.params])
        for m in METHODS:
            row = dict(式の形=spec, 方法=m, 合計のずれ_pct=(pred[m].sum() / y.sum() - 1) * 100, 中央値のずれ_pct=float(np.median(pred[m] / y - 1) * 100),
                       当てた値の平均の絶対誤差_pct=float(np.mean(np.abs(pred[m] / y - 1)) * 100))
            for g in size.cat.categories:
                mk = (size == g).values; row[f"合計のずれ_{g}_pct"] = (pred[m][mk].sum() / y[mk].sum() - 1) * 100
            pub.append(row)
    PUB = pd.DataFrame(pub); PUB.round(3).to_csv(RES / "public_example_municipal_spending.csv", index=False)

    main_ = {"正規の誤差・500件": {str(r["散らばり"]): {m: round(r[f"{m}_合計のずれ_pct"], 2) for m in METHODS} for r in rows[:5]},
             "式 exp(-σ²/2)-1": {str(a): round(b, 2) for a, b in zip(theory.散らばり, theory.式の値_pct)}, "公的データの例": pubinfo}
    json.dump(main_, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    xe, ye, _ = gen(np.random.default_rng(SEED + 2), 500, 1.0)
    pd.DataFrame({"x": xe, "y": ye}).round(4).to_csv(DATA / "example_sigma1.csv", index=False)

    mc = dict(zip(METHODS, (GRAY, BLUE, ORANGE, GREEN)))
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    o = np.argsort(xe); X = sm.add_constant(xe); ol = sm.OLS(np.log(ye), X).fit()
    ax[0].scatter(xe, ye, s=6, color=GRAY, alpha=.5)
    ax[0].plot(xe[o], np.exp(B0 + B1 * xe[o] + 0.5), color=INK, lw=2.2, label="本当の平均")
    ax[0].plot(xe[o], np.exp(ol.predict(X))[o], color=ORANGE, lw=2, ls="--", label="対数の回帰をそのまま戻す")
    ax[0].set_ylim(0, 150); ax[0].set_xlabel("x"); ax[0].set_ylabel("y"); ax[0].set_title("そのまま戻した線は、平均より下（中央値のあたり）を通る"); ax[0].legend(frameon=False)
    N5 = T.iloc[:5]
    for m in METHODS:
        ax[1].plot(N5.散らばり, N5[f"{m}_合計のずれ_pct"], "o-", color=mc[m], label=m)
    ax[1].plot(theory.散らばり, theory.式の値_pct, ":", color=INK, label="式：exp(−σ²/2)−1")
    ax[1].axhline(0, color=GRAY, lw=.6); ax[1].set_xlabel("対数の誤差の標準偏差 σ"); ax[1].set_ylabel("合計の予測のずれ（%）"); ax[1].set_title("散らばりが大きいほど、合計は小さく出る"); ax[1].legend(frameon=False, fontsize=9)
    save(fig, "a435_naive_backtransform.png", SRC, y=-0.03)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    sub = T[(T.件数 == 500)].iloc[5:11].reset_index(drop=True)
    labs = [r.誤差の形.replace("たまに大きく外れる", "たまに大きく\n外れる") + f"\nσ={r.散らばり}" if r.散らばりの偏り == 0 else f"散らばりが\nxで違う\nσ={r.散らばり}" for r in sub.itertuples()]
    w = .2; xs = np.arange(len(sub))
    for i, m in enumerate(METHODS):
        ax[0].bar(xs + (i - 1.5) * w, sub[f"{m}_合計のずれ_pct"], w, color=mc[m], label=m)
    ax[0].axhline(0, color=INK, lw=.8); ax[0].set_xticks(xs); ax[0].set_xticklabels(labs, fontsize=8); ax[0].set_ylabel("合計の予測のずれ（%）"); ax[0].set_title("誤差が正規でない・散らばりが一定でないとき")
    fig.legend(*ax[0].get_legend_handles_labels(), frameon=False, fontsize=9, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.07))
    h = T[(T.散らばりの偏り == 0.6)]
    xs2 = np.arange(2); w2 = .1
    for i, m in enumerate(METHODS):
        ax[1].bar(xs2 * 1.0 + (i - 1.5) * 2 * w2 - w2 / 2, h[f"{m}_xが小さい所_pct"], w2, color=mc[m], alpha=.45)
        ax[1].bar(xs2 * 1.0 + (i - 1.5) * 2 * w2 + w2 / 2, h[f"{m}_xが大きい所_pct"], w2, color=mc[m])
    ax[1].axhline(0, color=INK, lw=.8); ax[1].set_xticks(xs2); ax[1].set_xticklabels([f"σ={v}" for v in h.散らばり]); ax[1].set_ylabel("予測のずれ（%）")
    ax[1].set_title("散らばりが x で違うとき：x が小さい所（薄い色）と大きい所（濃い色）")
    save(fig, "a435_non_normal_and_hetero.png", SRC, y=-0.08)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    specs = list(PRED); w = .38
    for j, (spec, al) in enumerate(zip(specs, (.45, 1.0))):
        v = [float(PUB[(PUB.式の形 == spec) & (PUB.方法 == m)].合計のずれ_pct.iloc[0]) for m in METHODS]
        ax[0].bar(np.arange(4) + (j - .5) * w, v, w, color=[mc[m] for m in METHODS], alpha=al)
    ax[0].axhline(0, color=INK, lw=.8); ax[0].set_xticks(np.arange(4)); ax[0].set_xticklabels(METHODS, fontsize=9); ax[0].set_ylabel("歳出の合計の予測のずれ（%）")
    ax[0].set_title(f"市区町村の歳出を人口から当てる（{len(d):,}団体）\n薄い色：直線の式　濃い色：曲線の式")
    cats = list(size.cat.categories)
    for spec, ls in zip(specs, (":", "-")):
        for m in ("そのまま戻す", "残差の平均で戻す"):
            ax[1].plot(np.arange(5), [float(PUB[(PUB.式の形 == spec) & (PUB.方法 == m)][f"合計のずれ_{g}_pct"].iloc[0]) for g in cats], "o", ls=ls, color=mc[m], label=f"{m}（{spec[:2]}）")
    ax[1].axhline(0, color=INK, lw=.8); ax[1].set_xticks(np.arange(5)); ax[1].set_xticklabels(["小さい", "", "中", "", "大きい"]); ax[1].set_xlabel("人口の大きさで5つに分けた組"); ax[1].set_ylabel("組ごとの合計のずれ（%）"); ax[1].legend(frameon=False, fontsize=8)
    ax[1].set_title("人口の大きさごとに見ると")
    save(fig, "a435_public_example.png", "統計センター「SSDSE-A-2026（市区町村）」を加工して作成（歳出決算総額−災害復旧費 2022年度、総人口 2020年）。5つに分けて、当てはめに使っていない団体で確かめた", y=-0.03)
    pd.set_option("display.width", 250)
    print(json.dumps(main_, ensure_ascii=False, indent=1)); print(T.round(2).T.to_string()); print(PUB.round(2).T.to_string())


if __name__ == "__main__":
    main()
