"""A346 契約が何件あれば、損害率は安定するのか（架空のデータ、seed 346）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

SEED = 346
LAM = 0.08            # 1契約あたりの年間の事故件数（平均）
MEAN = 1.0            # 1事故の損害額の平均（単位：百万円）
LR0 = 0.60            # 見込みの損害率
TOL = 0.05            # ±5%（見込みの損害率に対する割合。60%なら57〜63%）
REPS = 2000
NS = [500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000]

def sev_gamma(rng, n):            # 裾が軽い：指数分布（変動係数1）
    return rng.exponential(MEAN, n)
def sev_ln(sig):
    mu = np.log(MEAN) - sig ** 2 / 2
    return lambda rng, n: rng.lognormal(mu, sig, n)
def sev_pareto(alpha):            # ロマックス分布（平均 MEAN）
    scale = MEAN * (alpha - 1)
    return lambda rng, n: scale * rng.pareto(alpha, n)

SEVS = {
    "指数（裾が軽い）": (sev_gamma, 1.0),
    "対数正規 σ=1.0": (sev_ln(1.0), float(np.sqrt(np.exp(1.0) - 1))),
    "対数正規 σ=1.5": (sev_ln(1.5), float(np.sqrt(np.exp(2.25) - 1))),
    "パレート α=2.5": (sev_pareto(2.5), float(np.sqrt(2.5 / 0.5))),
    "パレート α=1.8（分散が無限大）": (sev_pareto(1.8), float("inf")),
}
PREMIUM = LAM * MEAN / LR0        # 1契約の保険料（見込みの損害率が60%になる額）

def loss_ratios(rng, sev, n, reps, cap=None):
    """n 契約の1年の損害率を reps 回"""
    counts = rng.poisson(LAM * n, reps)
    x = sev(rng, int(counts.sum()))
    if cap is not None:
        x = np.minimum(x, cap)
    idx = np.repeat(np.arange(reps), counts)
    tot = np.bincount(idx, weights=x, minlength=reps)
    return tot / (n * PREMIUM)

def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for name, (sev, cv) in SEVS.items():
        for n in NS:
            reps = REPS if n <= 200000 else 1000
            lr = loss_ratios(rng, sev, n, reps)
            rel = lr / LR0 - 1
            rows.append(dict(sev=name, n=n, reps=reps, within5=float((np.abs(rel) <= TOL).mean()),
                             within10=float((np.abs(rel) <= 0.10).mean()),
                             p10=float(np.quantile(lr, 0.1)), p50=float(np.median(lr)), p90=float(np.quantile(lr, 0.9)),
                             mean=float(lr.mean()), sd=float(lr.std()), p99=float(np.quantile(lr, 0.99))))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "within_by_size.csv", index=False)

    # 「10年のうち9年が±5%に収まる」のに必要な件数：式（正規近似）と、シミュレーションでの探索
    z = 1.6449
    need = []
    for name, (sev, cv) in SEVS.items():
        formula = (z / TOL) ** 2 * (1 + cv ** 2) / LAM if np.isfinite(cv) else float("nan")
        # シミュレーション：件数を対数の目盛りで動かし、収まる割合が初めて90%を超える所（線形補間）
        grid = np.unique(np.round(np.logspace(3, 7.3, 44)).astype(int))
        prev = None; found = float("nan")
        r2 = np.random.default_rng(SEED + 1)
        for n in grid:
            reps = 2000 if n <= 300000 else (800 if n <= 3000000 else 400)
            lr = loss_ratios(r2, sev, int(n), reps)
            w = float((np.abs(lr / LR0 - 1) <= TOL).mean())
            if w >= 0.90:
                if prev is None: found = float(n)
                else:
                    n0, w0 = prev
                    found = float(np.exp(np.log(n0) + (0.90 - w0) / (w - w0) * (np.log(n) - np.log(n0))))
                break
            prev = (n, w)
        need.append(dict(sev=name, cv=cv, need_formula=formula, need_sim=found))
    nd = pd.DataFrame(need)
    base = nd.loc[0, "need_sim"]
    nd["ratio_to_light"] = nd["need_sim"] / base
    nd.to_csv(RES / "need_contracts.csv", index=False)

    # 1事故の上限（平均の20倍）で切った場合
    cap = 20 * MEAN
    caprows = []
    r3 = np.random.default_rng(SEED + 2)
    for name, (sev, cv) in SEVS.items():
        x = np.minimum(sev(r3, 4_000_000), cap)
        m, s = x.mean(), x.std()
        cvc = s / m
        caprows.append(dict(sev=name, kept_share=float(m / MEAN), cv_capped=float(cvc),
                            need_formula_capped=float((z / TOL) ** 2 * (1 + cvc ** 2) / LAM)))
        for n in (10000, 100000):
            lr = loss_ratios(r3, sev, n, 2000, cap=cap) / (m / MEAN)     # 上限つきの見込みに対する比
            caprows[-1][f"within5_n{n}"] = float((np.abs(lr / LR0 - 1) <= TOL).mean())
    cp = pd.DataFrame(caprows); cp.to_csv(RES / "capped.csv", index=False)

    # 例のデータ：1万件の会社の20年分の損害率（裾が軽い・重い）
    r4 = np.random.default_rng(SEED + 3)
    ex = pd.DataFrame({"year": np.arange(1, 21),
                       "指数（裾が軽い）": loss_ratios(r4, SEVS["指数（裾が軽い）"][0], 10000, 20),
                       "対数正規 σ=1.5": loss_ratios(r4, SEVS["対数正規 σ=1.5"][0], 10000, 20),
                       "パレート α=1.8（分散が無限大）": loss_ratios(r4, SEVS["パレート α=1.8（分散が無限大）"][0], 10000, 20)})
    ex.round(4).to_csv(DATA / "example_loss_ratio_10000.csv", index=False)

    out = dict(seed=SEED, lam=LAM, lr0=LR0, tol=TOL, reps=REPS, premium=PREMIUM,
               within=df.to_dict("records"), need=nd.to_dict("records"), capped=cp.to_dict("records"))
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    src = "架空のデータ（作成者が乱数で作成、seed 346）。事故は1契約あたり年0.08件、見込みの損害率60%"
    cols = [BLUE, GREEN, ORANGE, "#8a5cc2", INK]
    # 図1：件数と「±5%に収まった年の割合」
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for (name, _), c in zip(SEVS.items(), cols):
        d = df[df.sev == name]
        ax.plot(d.n, d.within5 * 100, marker="o", ms=4, color=c, label=name)
    ax.axhline(90, color=GRAY, lw=0.8, ls="--"); ax.text(520, 91.5, "90%（10年のうち9年）", fontsize=8.5, color=GRAY)
    ax.set_xscale("log"); ax.set_xlabel("契約の件数"); ax.set_ylabel("損害率が見込みの±5%に収まった年の割合（%）")
    ax.set_xticks([1000, 10000, 100000, 1000000]); ax.set_xticklabels(["1千", "1万", "10万", "100万"])
    ax.set_ylim(0, 102); ax.legend(fontsize=8.5, frameon=False, loc="upper left", bbox_to_anchor=(0.0, 0.88))
    ax.set_title("契約が増えるほど損害率は安定するが、裾が重いと届くのが遅い")
    save(fig, "a346_within_by_size.png", src)

    # 図2：必要な件数（式とシミュレーション）
    fig, ax = plt.subplots(figsize=(8, 4.4))
    y = np.arange(len(nd))[::-1]
    ax.barh(y + 0.19, nd.need_sim, height=0.36, color=BLUE, label="シミュレーション")
    ax.barh(y - 0.19, nd.need_formula.fillna(0), height=0.36, color=LIGHT, label="式（正規分布での近似）")
    for yy, a, b in zip(y, nd.need_sim, nd.need_formula):
        ax.text(a * 1.08, yy + 0.19, f"{a/1e4:,.1f}万件" if np.isfinite(a) else "2,000万件でも届かず", va="center", fontsize=9)
        ax.text((b if np.isfinite(b) else 1500) * 1.08, yy - 0.19, f"{b/1e4:,.1f}万件" if np.isfinite(b) else "式では出せない", va="center", fontsize=9, color=GRAY)
    ax.set_yticks(y); ax.set_yticklabels(nd.sev, fontsize=9.5); ax.set_xscale("log"); ax.set_xlim(1e3, 1.5e8)
    ax.set_xlabel("10年のうち9年、損害率が見込みの±5%に収まるのに必要な契約の件数（対数の目盛り）")
    ax.legend(fontsize=9, frameon=False, loc="lower right"); ax.set_title("必要な件数は、損害額の散らばりで桁が変わる")
    save(fig, "a346_need_contracts.png", src)

    # 図3：1万件・10万件のときの損害率の幅（10〜90%）
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for i, ((name, _), c) in enumerate(zip(SEVS.items(), cols)):
        for j, n in enumerate((10000, 100000)):
            d = df[(df.sev == name) & (df.n == n)].iloc[0]
            yy = len(SEVS) - 1 - i + (0.17 if j == 0 else -0.17)
            ax.plot([d.p10 * 100, d.p90 * 100], [yy, yy], color=c, lw=6 if j == 0 else 3, alpha=0.55 if j == 0 else 1, solid_capstyle="butt")
            ax.plot(d.p50 * 100, yy, "o", color=INK, ms=4)
            ax.text(d.p90 * 100 + 0.6, yy, f"{d.p10*100:.0f}〜{d.p90*100:.0f}%（{'1万件' if j == 0 else '10万件'}）", va="center", fontsize=8.5)
    ax.axvspan(57, 63, color=GRAY, alpha=0.15); ax.axvline(60, color=GRAY, lw=0.8)
    ax.set_yticks(range(len(SEVS))); ax.set_yticklabels(list(SEVS)[::-1], fontsize=9.5)
    ax.set_xlabel("1年の損害率（%）。線は10年のうち8年が入る範囲、点は中央値、灰色の帯は57〜63%"); ax.set_xlim(35, 100)
    ax.set_title("同じ1万件でも、損害率の幅は損害額の裾で大きく違う")
    save(fig, "a346_range_10k_100k.png", src)
    print(nd.to_string()); print(cp.to_string()); print(df[df.n.isin([10000, 100000])].to_string())

if __name__ == "__main__":
    main()
