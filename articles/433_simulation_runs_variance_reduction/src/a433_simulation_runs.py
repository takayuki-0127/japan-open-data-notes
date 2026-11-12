"""433 「200年に1度」の値をシミュレーションで出すには何回くり返せばよいか。減らす工夫はどれだけ効くか"""
import json
import numpy as np, pandas as pd
from scipy import stats, optimize, special
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, save

SEED = 433
P = 0.995
SRC = "架空の損害の合計（件数はポアソン、1件の損害額はガンマ。作成者が置いた数字、seed 433）"
CASES = {"軽い（年100件・指数分布）": dict(lam=100.0, alpha=1.0), "重い（年20件・散らばり2倍）": dict(lam=20.0, alpha=0.25)}
# 1件の損害額は平均1（ガンマ分布：形 alpha、尺度 1/alpha）


def exact_cdf(x, lam, alpha):
    n = np.arange(1, int(lam + 12 * np.sqrt(lam) + 30))
    pn = stats.poisson.pmf(n, lam)
    return float(np.exp(-lam) + (pn * special.gammainc(n * alpha, x * alpha)).sum())


def exact_q(p, lam, alpha):
    return optimize.brentq(lambda x: exact_cdf(x, lam, alpha) - p, lam * 0.2, lam * 6)


def draw(rng, n, lam, alpha):
    N = rng.poisson(lam, n)
    return np.where(N > 0, rng.gamma(np.maximum(N, 1) * alpha, 1 / alpha), 0.0)


def q_plain(rng, n, lam, alpha, p=P):
    return np.quantile(draw(rng, n, lam, alpha), p)


def q_anti(rng, n, lam, alpha, p=P):
    """対になる乱数：一様乱数 u と 1−u を組にする（件数も損害額も逆の向きに）"""
    h = n // 2
    u1, u2 = rng.random(h), rng.random(h)
    def gen(a, b):
        N = stats.poisson.ppf(a, lam)
        return np.where(N > 0, special.gammaincinv(np.maximum(N, 1) * alpha, b) / alpha, 0.0)
    return np.quantile(np.concatenate([gen(u1, u2), gen(1 - u1, 1 - u2)]), p)


def tilt_for(target, lam, alpha):
    """合計の平均が target になるように、指数の形で重みをずらす強さ t を決める"""
    f = lambda t: lam * (1 - t / alpha) ** (-alpha - 1) - target      # ずらした後の平均
    return optimize.brentq(f, 0.0, alpha * 0.999)


def q_is(rng, n, lam, alpha, t, p=P):
    """重みをつけた抽出：大きい合計が出やすい分布から引き、重みで元に戻す"""
    M = (1 - t / alpha) ** (-alpha)                 # 1件の損害額の積率母関数
    lam2 = lam * M; scale2 = 1 / (alpha - t)
    N = rng.poisson(lam2, n)
    S = np.where(N > 0, rng.gamma(np.maximum(N, 1) * alpha, scale2), 0.0)
    w = np.exp(-t * S + lam * (M - 1))
    o = np.argsort(S)[::-1]
    cw = np.cumsum(w[o]) / n                        # 大きい側からの重みの累計＝超える確率の見積もり
    i = np.searchsorted(cw, 1 - p)
    return S[o][min(i, n - 1)]


def rmse(vals, true):
    v = np.asarray(vals)
    return float(np.sqrt(((v / true - 1) ** 2).mean()) * 100), float((v.mean() / true - 1) * 100)


def main():
    rng = np.random.default_rng(SEED)
    rows, hist = [], {}
    truth = {}
    for cname, c in CASES.items():
        lam, alpha = c["lam"], c["alpha"]
        q = exact_q(P, lam, alpha); truth[cname] = dict(q995=q, mean=lam, q90=exact_q(0.90, lam, alpha), q99=exact_q(0.99, lam, alpha))
        t_opt = tilt_for(q, lam, alpha)
        # 密度（数値微分）から、ふつうの方法の理論上の振れ
        h = q * 1e-4; dens = (exact_cdf(q + h, lam, alpha) - exact_cdf(q - h, lam, alpha)) / (2 * h)
        for n in (1_000, 10_000, 100_000, 1_000_000):
            reps = 400 if n <= 10_000 else (200 if n == 100_000 else 40)
            a = [q_plain(rng, n, lam, alpha) for _ in range(reps)]
            r, b = rmse(a, q); rows.append(dict(場面=cname, 方法="ふつう", くり返し=n, 試した回数=reps, 振れ_pct=r, 偏り_pct=b, 理論_pct=np.sqrt(P * (1 - P) / n) / dens / q * 100))
            if n <= 100_000:
                reps2 = reps if n <= 10_000 else 60
                a2 = [q_anti(rng, n, lam, alpha) for _ in range(reps2)]
                r, b = rmse(a2, q); rows.append(dict(場面=cname, 方法="対になる乱数", くり返し=n, 試した回数=reps2, 振れ_pct=r, 偏り_pct=b))
            a3 = [q_is(rng, n, lam, alpha, t_opt) for _ in range(reps)]
            r, b = rmse(a3, q); rows.append(dict(場面=cname, 方法="重みをつけた抽出", くり返し=n, 試した回数=reps, 振れ_pct=r, 偏り_pct=b))
            if n == 10_000: hist[cname] = (np.array(a) / q, np.array(a3) / q)
        truth[cname]["t"] = t_opt
    T = pd.DataFrame(rows); T.round(4).to_csv(RES / "rmse_by_runs.csv", index=False)

    # 同じ精度に要る回数の比（振れの2乗の比）
    eq = []
    for cname in CASES:
        for n in (1_000, 10_000, 100_000, 1_000_000):
            d = T[(T.場面 == cname) & (T.くり返し == n)].set_index("方法").振れ_pct
            eq.append(dict(場面=cname, くり返し=n, 対になる乱数_回数の比=(d["ふつう"] / d["対になる乱数"]) ** 2 if "対になる乱数" in d else np.nan,
                           重みをつけた抽出_回数の比=(d["ふつう"] / d["重みをつけた抽出"]) ** 2))
    EQ = pd.DataFrame(eq); EQ.round(2).to_csv(RES / "equivalent_runs.csv", index=False)

    # ずらす強さを変える・別の量に使う（1万回）
    n = 10_000; tw = []
    for cname, c in CASES.items():
        lam, alpha = c["lam"], c["alpha"]; q = truth[cname]["q995"]
        base = {}
        for lab, p_, tr in (("200年に1度（99.5%点）", 0.995, q), ("10年に1度（90%点）", 0.90, truth[cname]["q90"])):
            a = [q_plain(rng, n, lam, alpha, p_) for _ in range(300)]; base[lab] = rmse(a, tr)[0]
        a = [draw(rng, n, lam, alpha).mean() for _ in range(300)]; base["平均"] = rmse(a, lam)[0]
        for mult in (0.6, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0):
            t = tilt_for(max(q * mult, lam * 1.001), lam, alpha)
            r995 = rmse([q_is(rng, n, lam, alpha, t) for _ in range(300)], q)[0]
            r90 = rmse([q_is(rng, n, lam, alpha, t, 0.90) for _ in range(300)], truth[cname]["q90"])[0]
            M = (1 - t / alpha) ** (-alpha); mm = []
            for _ in range(300):
                N = rng.poisson(lam * M, n); S = np.where(N > 0, rng.gamma(np.maximum(N, 1) * alpha, 1 / (alpha - t)), 0.0)
                mm.append((S * np.exp(-t * S + lam * (M - 1))).mean())
            tw.append(dict(場面=cname, ずらした先_正解の何倍=mult, 振れ_995_pct=r995, ふつうの振れ_995_pct=base["200年に1度（99.5%点）"],
                           振れ_90_pct=r90, ふつうの振れ_90_pct=base["10年に1度（90%点）"], 振れ_平均_pct=rmse(mm, lam)[0], ふつうの振れ_平均_pct=base["平均"]))
    TW = pd.DataFrame(tw); TW.round(4).to_csv(RES / "tilt_strength.csv", index=False)

    main_ = {"正解": {k: {a: round(float(b), 4) for a, b in v.items()} for k, v in truth.items()},
             "ふつうの方法の振れ_pct": {c: {int(r.くり返し): round(r.振れ_pct, 3) for r in T[(T.場面 == c) & (T.方法 == "ふつう")].itertuples()} for c in CASES}}
    json.dump(main_, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    pd.DataFrame([dict(場面=k, **v) for k, v in truth.items()]).round(5).to_csv(DATA / "exact_values.csv", index=False)

    mc = {"ふつう": (GRAY, "o-"), "対になる乱数": (BLUE, "s--"), "重みをつけた抽出": (ORANGE, "^-")}
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
    for a_, cname in zip(ax, CASES):
        for m, (c, st) in mc.items():
            d = T[(T.場面 == cname) & (T.方法 == m)]
            a_.plot(d.くり返し, d.振れ_pct, st, color=c, label=m, lw=1.8)
        a_.set_xscale("log"); a_.set_yscale("log"); a_.set_title(cname); a_.set_xlabel("くり返しの数"); a_.axhline(1, color=GRAY, lw=.6, ls=":")
    ax[0].set_ylabel("200年に1度の値の振れ（正解に対する%）"); ax[0].legend(frameon=False)
    fig.suptitle("くり返しの数と、200年に1度の値の振れ", y=1.02)
    save(fig, "a433_rmse_by_runs.png", SRC, y=-0.03)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
    for a_, cname in zip(ax, CASES):
        pl, is_ = hist[cname]; bins = np.linspace(min(pl.min(), is_.min()), max(pl.max(), is_.max()), 40)
        a_.hist((pl - 1) * 100, bins=(bins - 1) * 100, color=GRAY, alpha=.7, label="ふつう")
        a_.hist((is_ - 1) * 100, bins=(bins - 1) * 100, color=ORANGE, alpha=.7, label="重みをつけた抽出")
        a_.axvline(0, color=INK, lw=.8); a_.set_title(cname); a_.set_xlabel("見積もり − 正解（%）")
    ax[0].set_ylabel("回数（400回のうち）"); ax[0].legend(frameon=False)
    fig.suptitle("1万回のシミュレーションを400回やり直したときの、200年に1度の値", y=1.02)
    save(fig, "a433_estimates_at_10000.png", SRC, y=-0.03)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    for cname, c in zip(CASES, (BLUE, ORANGE)):
        d = TW[TW.場面 == cname]
        ax[0].plot(d.ずらした先_正解の何倍, d.振れ_995_pct / d.ふつうの振れ_995_pct, "o-", color=c, label=cname)
        ax[1].plot(d.ずらした先_正解の何倍, d.振れ_90_pct / d.ふつうの振れ_90_pct, "o-", color=c, label=f"{cname}：10年に1度の値")
        ax[1].plot(d.ずらした先_正解の何倍, d.振れ_平均_pct / d.ふつうの振れ_平均_pct, "s--", color=c, label=f"{cname}：平均")
    for a_ in ax:
        a_.axhline(1, color=INK, lw=.8, ls=":"); a_.set_yscale("log"); a_.set_xlabel("分布をずらした先（200年に1度の値の何倍を中心にしたか）"); a_.set_ylabel("振れ ÷ ふつうの方法の振れ")
    ax[0].set_title("200年に1度の値：ずらしすぎると効きが落ちる"); ax[0].legend(frameon=False, fontsize=9)
    ax[1].set_title("同じ乱数を別の量に使うと、ふつうより悪くなる"); ax[1].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    save(fig, "a433_tilt_strength.png", SRC, y=-0.12)
    print(json.dumps(main_, ensure_ascii=False, indent=1)); print(T.round(3).to_string()); print(EQ.round(2).to_string()); print(TW.round(3).to_string())


if __name__ == "__main__":
    main()
