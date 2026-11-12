"""333 1年の損害の合計の「200年に1度」（99.5%点）は、近似でどこまで出せるか（架空の分布、seed 333）"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *

SEED = 333
Q = 0.995
LAMS = [10, 100, 1000]                                    # 1年の事故件数の平均（契約の数にほぼ比例）
SEVS = {"ガンマ（変動係数1）": ("gamma", 1.0), "対数正規 σ=1.0": ("ln", 1.0), "対数正規 σ=1.5": ("ln", 1.5)}   # どれも平均1


def sev_dist(kind, par):
    if kind == "gamma": return stats.gamma(1.0 / par ** 2, scale=par ** 2)       # 変動係数 par、平均1
    return stats.lognorm(par, scale=np.exp(-par ** 2 / 2))                        # 平均1


def sev_moments(kind, par):
    """1事故の損害の E[X], E[X^2], E[X^3]"""
    if kind == "gamma":
        k, th = 1 / par ** 2, par ** 2; return 1.0, k * (k + 1) * th ** 2, k * (k + 1) * (k + 2) * th ** 3
    s = par; return 1.0, float(np.exp(s ** 2)), float(np.exp(3 * s ** 2))


def discretize(d, h, m):
    """損害額を幅 h の目盛りに丸める（k·h の確率＝F((k+0.5)h)−F((k−0.5)h)、最後の目盛りに残りを寄せる）"""
    edges = (np.arange(m + 1) - 0.5) * h; edges[0] = 0.0
    f = np.diff(d.cdf(edges)); f[-1] += d.sf(edges[-1]); return f


def reference(d, lam, top, M=2 ** 21):
    """基準：細かい目盛りでの高速フーリエ変換（複合ポアソンの特性関数を直接計算）"""
    h = top / M; f = discretize(d, h, M)
    g = np.fft.irfft(np.exp(lam * (np.fft.rfft(f) - 1.0)), M)
    c = np.cumsum(np.clip(g, 0, None)); return float(np.searchsorted(c, Q) * h), float(np.searchsorted(c, 0.99) * h)


def panjer(d, lam, h, top):
    """パンジャーの再帰式（事故件数がポアソンのとき）：g_k = (λ/k)·Σ_j j·f_j·g_{k−j}"""
    m = int(top / h) + 1; f = discretize(d, h, m)
    g = np.zeros(m); g[0] = np.exp(lam * (f[0] - 1.0))
    if g[0] == 0.0: return None                                                 # e^{−λ} が0に丸められて始められない
    jf = np.arange(m) * f
    for k in range(1, m):
        g[k] = lam / k * np.dot(jf[1:k + 1], g[k - 1::-1][:k])
    c = np.cumsum(g); return float(np.searchsorted(c, Q) * h)


def panjer_split(d, lam, h, top, parts):
    """λ を parts 等分して再帰式を回し、あとで畳み込んで戻す（e^{−λ} が0になるのを避ける）"""
    m = int(top / h) + 1; f = discretize(d, h, m); l = lam / parts
    g = np.zeros(m); g[0] = np.exp(l * (f[0] - 1.0)); jf = np.arange(m) * f
    for k in range(1, m):
        g[k] = l / k * np.dot(jf[1:k + 1], g[k - 1::-1][:k])
    n = 1 << int(np.ceil(np.log2(m * parts))); G = np.fft.irfft(np.fft.rfft(g, n) ** parts, n)
    c = np.cumsum(np.clip(G, 0, None)); return float(np.searchsorted(c, Q) * h)


def simulate(rng, d, lam, years):
    out = []
    for _ in range(years // 10_000):                                            # 1万年ずつ作る（メモリを使いすぎないため）
        n = rng.poisson(lam, 10_000); x = d.rvs(n.sum(), random_state=rng)
        out.append(np.bincount(np.repeat(np.arange(10_000), n), weights=x, minlength=10_000))
    return np.quantile(np.concatenate(out), Q)


def main():
    rng = np.random.default_rng(SEED); z = stats.norm.ppf(Q); rows = []; res = {}
    for sname, (kind, par) in SEVS.items():
        d = sev_dist(kind, par); m1, m2, m3 = sev_moments(kind, par)
        for lam in LAMS:
            mu, sd, skew = lam * m1, np.sqrt(lam * m2), lam * m3 / (lam * m2) ** 1.5
            top = mu + 80 * sd + 3000
            ref, ref99 = reference(d, lam, top)
            normal = mu + z * sd
            npow = mu + sd * (z + skew / 6 * (z ** 2 - 1))                         # 歪みを1つ足した近似（NP近似）
            a = 4 / skew ** 2; tg = stats.gamma.ppf(Q, a, loc=mu - 2 * sd / skew, scale=sd * skew / 2)   # ずらしたガンマ
            sim = {}
            for years, reps in ((10_000, 100), (100_000, 12)):
                q = np.array([simulate(rng, d, lam, years) for _ in range(reps)])
                sim[years] = (100 * (np.median(q) / ref - 1), 100 * np.sqrt(((q / ref - 1) ** 2).mean()),
                              100 * (np.quantile(q, .1) / ref - 1), 100 * (np.quantile(q, .9) / ref - 1))
            pj = {}
            for div in (2, 10, 50):
                h = 1.0 / div
                ptop = ref * 1.6 + 20
                v = panjer(d, lam, h, ptop) if lam <= 100 else None
                if v is None and lam > 100: v2 = panjer_split(d, lam, h, ptop, 8); pj[div] = (None, 100 * (v2 / ref - 1))
                else: pj[div] = (100 * (v / ref - 1), None)
            rows.append(dict(severity=sname, lam=lam, mean=mu, sd=sd, skew=skew, ref_q995=ref, ref_q99=ref99, q995_over_mean=ref / mu,
                             normal_err=100 * (normal / ref - 1), np_err=100 * (npow / ref - 1), tgamma_err=100 * (tg / ref - 1),
                             sim1e4_bias=sim[10_000][0], sim1e4_rmse=sim[10_000][1], sim1e4_p10=sim[10_000][2], sim1e4_p90=sim[10_000][3],
                             sim1e5_bias=sim[100_000][0], sim1e5_rmse=sim[100_000][1],
                             panjer_h_half=pj[2][0], panjer_h_tenth=pj[10][0], panjer_h_50th=pj[50][0],
                             panjer_split_h_half=pj[2][1], panjer_split_h_tenth=pj[10][1], panjer_split_h_50th=pj[50][1],
                             panjer_plain_fails=bool(np.exp(-lam * 1.0) == 0.0 or lam > 100 and np.exp(lam * (discretize(d, .1, 50)[0] - 1)) == 0.0)))
            print(sname, lam, flush=True)
    T = pd.DataFrame(rows); T.round(4).to_csv(RES / "quantile_errors.csv", index=False)
    # 基準の確かめ：100万年分のシミュレーションと比べる（1つの場面）
    d = sev_dist("ln", 1.0); big = simulate(rng, d, 100, 1_000_000); refc = float(T[(T.severity == "対数正規 σ=1.0") & (T.lam == 100)].ref_q995.iloc[0])
    res["reference_check"] = dict(fft=refc, sim_1m_years=float(big), diff_pct=float(100 * (big / refc - 1)))
    res["underflow"] = dict(exp_minus_1000=float(np.exp(-1000.0)), exp_minus_700=float(np.exp(-700.0)))
    res["settings"] = dict(seed=SEED, q=Q, lams=LAMS, severities=list(SEVS))
    res["table"] = T.round(4).to_dict(orient="records")
    json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    pd.DataFrame({"severity": [s for s in SEVS for _ in LAMS], "lam": LAMS * 3, "mean": T["mean"], "sd": T["sd"].round(3), "skew": T["skew"].round(3)}).to_csv(DATA / "scenarios.csv", index=False)

    # 図1：近似の誤差（正規・NP・ずらしたガンマ）
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4), sharey=True)
    for ax, s in zip(axes, SEVS):
        g = T[T.severity == s]; x = np.arange(len(LAMS))
        for key, c, lab in (("normal_err", ORANGE, "正規近似"), ("np_err", BLUE, "歪みを足した近似"), ("tgamma_err", GREEN, "ずらしたガンマ")):
            ax.plot(x, g[key], "o-", color=c, label=lab)
        ax.axhline(0, color=GRAY, lw=1); ax.set_xticks(x); ax.set_xticklabels([f"{l:,}件" for l in LAMS]); ax.set_title(s, fontsize=11)
    axes[0].set_ylabel("99.5%点の誤差（%）"); axes[1].set_xlabel("1年の事故件数の平均"); axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("正規近似は、件数が少なく裾が重いほど、200年に1度を小さく見積もる", y=1.02)
    save(fig, "a333_approx_error.png", "架空の分布（事故件数はポアソン、1事故の損害の平均は1）。基準は細かい目盛りでの数値計算。seed 333", y=-0.05)

    # 図2：シミュレーションの年数と揺れ
    fig, ax = plt.subplots(figsize=(8, 4.2)); w = 0.38; lab = [f"{s.replace('（変動係数1）','').replace(' σ', chr(10) + 'σ')}\n{l:,}件" for s in SEVS for l in LAMS]
    ax.bar(np.arange(9) - w / 2, T.sim1e4_rmse, w, color=ORANGE, label="1万年分")
    ax.bar(np.arange(9) + w / 2, T.sim1e5_rmse, w, color=BLUE, label="10万年分")
    ax.set_xticks(range(9)); ax.set_xticklabels(lab, fontsize=7.5); ax.set_ylabel("99.5%点の誤差の大きさ（RMSE、%）"); ax.legend(frameon=False)
    ax.set_title("シミュレーションは偏らないが、回すたびに答えが揺れる")
    save(fig, "a333_simulation_noise.png", "架空の分布。1万年分は100回、10万年分は12回くり返したときの、基準からのずれ", y=-0.06)

    # 図3：パンジャーの再帰式と目盛りの幅
    fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(9)
    for key, key2, c, labl in (("panjer_h_half", "panjer_split_h_half", ORANGE, "目盛り＝平均の1/2"), ("panjer_h_tenth", "panjer_split_h_tenth", BLUE, "平均の1/10"), ("panjer_h_50th", "panjer_split_h_50th", GREEN, "平均の1/50")):
        v = T[key].fillna(T[key2]); ax.plot(x, v, "o-", color=c, label=labl)
    ax.axhline(0, color=GRAY, lw=1); ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=7.5); ax.set_ylabel("99.5%点の誤差（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("再帰式は、目盛りを細かくすれば基準にほぼ一致する")
    save(fig, "a333_panjer_grid.png", "架空の分布。1,000件の場面は、そのままでは最初の確率が0に丸められるので、件数を8等分して計算し畳み込みで戻した", y=-0.06)
    print(T[["severity", "lam", "skew", "q995_over_mean", "normal_err", "np_err", "tgamma_err", "sim1e4_bias", "sim1e4_rmse", "sim1e5_rmse", "panjer_h_half", "panjer_h_tenth", "panjer_h_50th", "panjer_split_h_half", "panjer_split_h_tenth", "panjer_split_h_50th"]].round(2).to_string())
    print(res["reference_check"], res["underflow"])


if __name__ == "__main__":
    main()
