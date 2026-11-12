"""318 見積もった支払備金の「幅」は、正解を何%含むのか
マックの方法（式で出す標準誤差）とブートストラップ（残差を引き直す）の95%区間が、
架空の支払データ1,000組のうち何組で正解の備金を含むかを数える。三角形の大きさと、データの作り方を変える。"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, LIGHT, save

SEED, NSIM, NBOOT, CV = 318, 1000, 500, 0.12
SOURCE = "架空のデータ（作成者が乱数で作成、seed 318）"
SIZES = (10, 7, 5)


def G(t): return 1 - np.exp(-(np.asarray(t, float) / 3.2) ** 1.1)


def pattern(n):
    """n年で払い終わる進み方（10年の形を n年に縮める）。累計の割合"""
    return G(np.arange(1, n + 1) * 10 / n) / G(10)


def sim_cell(rng, n, nsim, infl_change=None):
    """1マスごとに独立にばらつく型（316 と同じ）。infl_change=(g0,g1) なら直近3年から先でインフレが変わる"""
    cum = pattern(n); share = np.diff(np.r_[0.0, cum])
    prem = 1000 * 1.03 ** np.arange(n)
    s2 = np.log(1 + 0.08 ** 2)
    U = prem * rng.lognormal(np.log(0.65) - 0.5 * s2, np.sqrt(s2), (nsim, n))
    X = U[:, :, None] * share * rng.gamma(1 / CV ** 2, CV ** 2, (nsim, n, n))
    if infl_change:
        g0, g1 = infl_change; cal = np.arange(2 * n)
        idx = np.cumprod(np.r_[1.0, 1 + np.where(cal[1:] >= n - 3, g1, g0)])
        X = X * idx[np.add.outer(np.arange(n), np.arange(n))]
    return X


def sim_mack(rng, n, nsim):
    """マックの前提どおりの型：次の累計＝いまの累計×比＋ばらつき（分散はいまの累計に比例）"""
    cum = pattern(n); f = cum[1:] / cum[:-1]
    prem = 1000 * 1.03 ** np.arange(n)
    s2 = np.log(1 + 0.08 ** 2)
    U = prem * rng.lognormal(np.log(0.65) - 0.5 * s2, np.sqrt(s2), (nsim, n))
    C = np.empty((nsim, n, n))
    C[:, :, 0] = U * cum[0] * rng.gamma(1 / CV ** 2, CV ** 2, (nsim, n))
    for j in range(n - 1):
        mean = C[:, :, j] * (f[j] - 1)                       # 次の1年に払う額の平均
        sig2 = (CV * (f[j] - 1)) ** 2 * 650 * cum[j]         # 分散＝sig2×いまの累計（ふつうの大きさで変動係数12%）
        var = sig2 * C[:, :, j]
        C[:, :, j + 1] = C[:, :, j] + rng.gamma(mean ** 2 / var, var / mean)
    return np.diff(np.concatenate([np.zeros((nsim, n, 1)), C], axis=2), axis=2)


def cl_fit(C, n):
    """累計の三角形（左上だけ使う）から伸びの比と、対角線から先の累計を出す。C の形は [..., n, n]"""
    f = np.empty(C.shape[:-2] + (n - 1,))
    for j in range(n - 1):
        f[..., j] = C[..., :n - 1 - j, j + 1].sum(-1) / C[..., :n - 1 - j, j].sum(-1)
    full = C.copy()
    for i in range(1, n):
        for j in range(n - i, n):
            full[..., i, j] = full[..., i, j - 1] * f[..., j - 1]
    return f, full


def mack(X, n):
    """マックの式による備金の合計と標準誤差"""
    C = np.cumsum(X, axis=2); S = C.shape[0]
    f, full = cl_fit(C, n)
    sig2 = np.zeros((S, n - 1))
    for j in range(n - 2):
        m = n - 1 - j
        sig2[:, j] = (C[:, :m, j] * (C[:, :m, j + 1] / C[:, :m, j] - f[:, [j]]) ** 2).sum(1) / (m - 1)
    sig2[:, n - 2] = np.minimum(sig2[:, n - 3] ** 2 / np.maximum(sig2[:, n - 4], 1e-12), np.minimum(sig2[:, n - 4], sig2[:, n - 3]))
    colsum = np.stack([C[:, :n - 1 - k, k].sum(1) for k in range(n - 1)], axis=1)
    ult = full[:, :, n - 1]
    paid = np.stack([C[:, i, n - 1 - i] for i in range(n)], axis=1)
    mse = np.zeros(S)
    for i in range(1, n):
        ks = np.arange(n - 1 - i, n - 1)
        term = (sig2[:, ks] / f[:, ks] ** 2)
        mse_i = ult[:, i] ** 2 * (term * (1 / full[:, i, ks] + 1 / colsum[:, ks])).sum(1)
        cov = ult[:, i] * ult[:, i + 1:].sum(1) * (2 * term / colsum[:, ks]).sum(1)
        mse += mse_i + cov
    return (ult - paid).sum(1), np.sqrt(mse)


def bootstrap(X, n, rng, nboot=NBOOT, chunk=100):
    """残差を引き直すブートストラップ（イングランドとヴェラルの形）。備金の合計の2.5%・97.5%点を返す"""
    S = X.shape[0]; tri = np.add.outer(np.arange(n), np.arange(n)) < n
    lo = np.empty(S); hi = np.empty(S); p = 2 * n - 1; N = n * (n + 1) // 2
    for a in range(0, S, chunk):
        x = X[a:a + chunk]; s = x.shape[0]
        C = np.cumsum(x, axis=2)
        f, full = cl_fit(C, n)
        # 当てはめ値：対角線の累計を比で割り戻す
        fit = np.empty_like(C)
        for i in range(n):
            d = n - 1 - i; fit[:, i, d] = C[:, i, d]
            for j in range(d - 1, -1, -1): fit[:, i, j] = fit[:, i, j + 1] / f[:, j]
        m = np.diff(np.concatenate([np.zeros((s, n, 1)), fit], axis=2), axis=2)
        m = np.where(tri, np.maximum(m, 1e-9), 1.0)
        r = np.where(tri, (x - m) / np.sqrt(m), 0.0)
        phi = (r ** 2).sum((1, 2)) / (N - p)
        r = r * np.sqrt(N / (N - p))
        pool = r[:, tri]                                           # [s, N] 引き直す元の残差
        # 残差が0になる隅の2マス（右上と左下）は引き直しから外す
        keep = np.ones(N, bool); order = np.argwhere(tri)
        for q, (i, j) in enumerate(order):
            if (i == 0 and j == n - 1) or (i == n - 1 and j == 0): keep[q] = False
        pool = pool[:, keep]
        pick = rng.integers(0, pool.shape[1], (s, nboot, N))
        rs = np.take_along_axis(pool[:, None, :].repeat(nboot, 1), pick, axis=2)
        xb = np.zeros((s, nboot, n, n)); xb[:, :, tri] = m[:, None][:, :, tri] + rs * np.sqrt(m[:, None][:, :, tri])
        Cb = np.cumsum(xb, axis=3)
        fb, fullb = cl_fit(Cb, n)
        mb = np.diff(fullb, axis=3)                                # 先の1マスごとの見積もり
        fut = ~tri[:, 1:]
        mean = np.maximum(mb[:, :, fut], 1e-9)
        var = phi[:, None, None] * mean
        proc = rng.gamma(mean ** 2 / var, var / mean)              # 先の支払いそのもののばらつき
        tot = proc.sum(2)
        lo[a:a + chunk], hi[a:a + chunk] = np.quantile(tot, [0.025, 0.975], axis=1)
    return lo, hi


def main():
    rng = np.random.default_rng(SEED)
    gens = {"マックの前提どおりの型": lambda n: sim_mack(rng, n, NSIM),
            "1マスごとに独立にばらつく型": lambda n: sim_cell(rng, n, NSIM),
            "インフレが強まる型（年1%→6%）": lambda n: sim_cell(rng, n, NSIM, (0.01, 0.06))}
    rows = []; t0 = time.time(); ex = None
    for gname, gen in gens.items():
        for n in SIZES:
            X = gen(n)
            tri = np.add.outer(np.arange(n), np.arange(n)) < n
            truth = (X * ~tri).sum((1, 2))
            R, se = mack(X, n)
            s2 = np.log(1 + (se / R) ** 2)
            ln_lo = np.exp(np.log(R) - s2 / 2 - 1.96 * np.sqrt(s2)); ln_hi = np.exp(np.log(R) - s2 / 2 + 1.96 * np.sqrt(s2))
            bl, bh = bootstrap(X, n, rng)
            for mname, lo, hi in [("マック（正規分布で幅をとる）", R - 1.96 * se, R + 1.96 * se), ("マック（対数正規分布で幅をとる）", ln_lo, ln_hi), ("ブートストラップ", bl, bh)]:
                rows.append({"データの型": gname, "事故年度の数": n, "方法": mname,
                             "95%区間が正解を含んだ割合（%）": round(100 * float(((truth >= lo) & (truth <= hi)).mean()), 1),
                             "正解が上に外れた割合（%）": round(100 * float((truth > hi).mean()), 1),
                             "正解が下に外れた割合（%）": round(100 * float((truth < lo).mean()), 1),
                             "幅の半分÷見積もり（中央値、%）": round(100 * float(np.median((hi - lo) / 2 / R)), 1),
                             "見積もりの誤差の平均（%）": round(100 * float((R / truth - 1).mean()), 1),
                             "見積もりの誤差の大きさ（RMSE、%）": round(100 * float(np.sqrt(((R / truth - 1) ** 2).mean())), 1)})
            if gname == "1マスごとに独立にばらつく型" and n == 10:
                ex = pd.DataFrame({"組": np.arange(1, 61), "正解の備金": truth[:60].round(1), "見積もり": R[:60].round(1),
                                   "マックの下限": ln_lo[:60].round(1), "マックの上限": ln_hi[:60].round(1),
                                   "ブートストラップの下限": bl[:60].round(1), "ブートストラップの上限": bh[:60].round(1)})
                C0 = np.cumsum(X[0], axis=1)
                pd.DataFrame([{"事故年度": i + 1, "経過年": j + 1, "累計支払額": round(float(C0[i, j]), 1)} for i in range(n) for j in range(n - i)]).to_csv(DATA / "example_triangle.csv", index=False)
            print(gname, n, round(time.time() - t0), "秒", flush=True)
    df = pd.DataFrame(rows); df.to_csv(RES / "coverage.csv", index=False); ex.to_csv(RES / "example_intervals.csv", index=False)
    # 二項分布の誤差：1,000組で95%なら ±1.4ポイント
    json.dump({"設定": {"組の数": NSIM, "引き直しの回数": NBOOT, "1マスのばらつき": CV, "事故年度の数": list(SIZES),
                        "割合の誤差の目安（1,000組で95%のとき、±ポイント）": round(196 * float(np.sqrt(0.95 * 0.05 / NSIM)), 1)},
               "結果": rows}, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    figs(df, ex)
    print(df.drop(columns=["見積もりの誤差の平均（%）"]).to_string())


def figs(df, ex):
    gn = list(dict.fromkeys(df["データの型"])); mn = list(dict.fromkeys(df["方法"])); col = {mn[0]: LIGHT, mn[1]: BLUE, mn[2]: ORANGE}
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 4.3), sharey=True)
    for ax, g in zip(axs, gn):
        d = df[df["データの型"] == g]
        for k, m in enumerate(mn):
            v = d[d["方法"] == m].set_index("事故年度の数")["95%区間が正解を含んだ割合（%）"].reindex(SIZES)
            xs = np.arange(len(SIZES)) + (k - 1) * 0.27
            ax.bar(xs, v.values, 0.25, color=col[m], label=m if ax is axs[0] else None)
            for x, y in zip(xs, v.values): ax.text(x, y + 1, f"{y:.0f}", ha="center", fontsize=8.5)
        ax.axhline(95, color=GRAY, lw=1, ls="--"); ax.set_xticks(range(len(SIZES))); ax.set_xticklabels([f"{n}年" for n in SIZES])
        ax.set_title(g, fontsize=11.5); ax.set_xlabel("事故年度の数（三角形の大きさ）"); ax.set_ylim(0, 108)
    axs[0].set_ylabel("95%区間が正解を含んだ割合（%）")
    fig.legend(frameon=False, fontsize=9.5, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.09))
    fig.suptitle("95%のつもりの幅は、正解を何%含んだか（各1,000組。点線が95%）", y=1.03, fontsize=13)
    save(fig, "a318_coverage.png", SOURCE, y=-0.1)

    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    e = ex.sort_values("見積もり").reset_index(drop=True); x = np.arange(len(e))
    hit = (e["正解の備金"] >= e["ブートストラップの下限"]) & (e["正解の備金"] <= e["ブートストラップの上限"])
    ax.vlines(x, e["ブートストラップの下限"], e["ブートストラップの上限"], color=LIGHT, lw=5, label="ブートストラップの95%区間")
    ax.plot(x, e["見積もり"], "_", color=BLUE, ms=7, label="見積もり")
    ax.plot(x[hit], e["正解の備金"][hit], "o", color=GREEN, ms=4, label="正解（区間の中）")
    ax.plot(x[~hit], e["正解の備金"][~hit], "o", color=ORANGE, ms=6, label="正解（区間の外）")
    ax.set_xlabel("三角形60組（見積もりの小さい順）"); ax.set_ylabel("支払備金（百万円）"); ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper left")
    ax.set_title(f"60組の例：区間の外に出たのは{int((~hit).sum())}組（1マスごとに独立にばらつく型、事故年度10年）")
    save(fig, "a318_example.png", SOURCE)

    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2))
    d = df[df["方法"] == "ブートストラップ"]
    for g, c in zip(gn, [BLUE, GREEN, ORANGE]):
        v = d[d["データの型"] == g].set_index("事故年度の数").reindex(SIZES)
        axs[0].plot(range(3), v["幅の半分÷見積もり（中央値、%）"], "-o", color=c, label=g)
        axs[1].plot(range(3), v["見積もりの誤差の大きさ（RMSE、%）"], "-o", color=c)
    for ax, t in zip(axs, ["区間の幅の半分（見積もりに対する%、中央値）", "見積もりそのものの誤差の大きさ（RMSE、%）"]):
        ax.set_xticks(range(3)); ax.set_xticklabels([f"{n}年" for n in SIZES]); ax.set_xlabel("事故年度の数"); ax.set_title(t, fontsize=11.5); ax.set_ylim(0)
    axs[0].legend(frameon=False, fontsize=9)
    fig.suptitle("幅は足りているか：ブートストラップの幅と、実際の誤差", y=1.03, fontsize=13)
    save(fig, "a318_width.png", SOURCE)


if __name__ == "__main__":
    main()
