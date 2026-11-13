"""529 月別の事故件数を1年分だけで見ると、季節の山は偶然と見分けられるのか（保険数理・リスク）

架空の月別の事故件数。
- 月の平均 = λ × (1 + A × cos(2π(月−1)/12))（1月が山、7月が谷）。A = 0・0.1・0.2・0.4、λ = 5・20・100件/月
- 件数はポアソン。比較として、ばらつきが平均の2倍の負の二項も置く（季節なしのとき）
- 1年・3年・10年分を月ごとに合計し、「12か月とも同じ」をカイ二乗検定（5%）で調べる
見つかる割合（検出率）、季節がないのに見つかる割合（誤検出率）、山の月が当たる割合、季節指数の誤差を出す。乱数の種 529、各場面 5,000回。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の月別の事故件数（作成者が乱数で作成、seed 529）"
SIMS = 5000
AMPS = [0.0, 0.1, 0.2, 0.4]
LAMS = [5, 20, 100]
YEARS = [1, 3, 10]
M = np.arange(12)


def draw(rng, lam, A, years, disp=1.0):
    mu = lam * (1 + A * np.cos(2 * np.pi * M / 12))
    if disp == 1.0:
        x = rng.poisson(mu, (SIMS, years, 12))
    else:
        k = mu / (disp - 1)              # 分散 = 平均 × disp
        x = rng.negative_binomial(k, k / (k + mu), (SIMS, years, 12))
    return x.sum(axis=1), mu


def evaluate(tot, mu):
    exp_ = tot.mean(axis=1, keepdims=True)
    chi = ((tot - exp_) ** 2 / np.where(exp_ > 0, exp_, 1)).sum(axis=1)
    p = stats.chi2.sf(chi, 11)
    p[exp_[:, 0] == 0] = 1.0
    true_idx = mu / mu.mean()
    est_idx = tot / np.where(exp_ > 0, exp_, 1)
    rmse = np.sqrt(((est_idx - true_idx) ** 2).mean(axis=1))
    peak = tot.argmax(axis=1)
    peak_ok = np.isin(peak, [11, 0, 1])          # 12月・1月・2月（真の山の前後1か月）
    return p, rmse, peak_ok


def main():
    rng = np.random.default_rng(529)
    rows = []
    keep = {}
    for lam in LAMS:
        for A in AMPS:
            for y in YEARS:
                tot, mu = draw(rng, lam, A, y)
                p, rmse, peak_ok = evaluate(tot, mu)
                rows.append(dict(count="ポアソン", lam=lam, amp=A, years=y, reject=round(float((p < 0.05).mean()), 4),
                                 idx_rmse=round(float(rmse.mean()), 4), peak_hit=round(float(peak_ok.mean()), 4)))
                if lam == 20 and y == 1 and A in (0.0, 0.2):
                    keep[A] = tot[:3]
        for y in YEARS:
            tot, mu = draw(rng, lam, 0.0, y, disp=2.0)
            p, rmse, peak_ok = evaluate(tot, mu)
            rows.append(dict(count="負の二項（ばらつき2倍）", lam=lam, amp=0.0, years=y, reject=round(float((p < 0.05).mean()), 4),
                             idx_rmse=round(float(rmse.mean()), 4), peak_hit=round(float(peak_ok.mean()), 4)))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "summary.csv", index=False)
    po = df[df["count"] == "ポアソン"]
    nb = df[df["count"] != "ポアソン"]
    out = {"検出率（ポアソン）": {f"λ={l}": {f"A={a}": {f"{y}年": float(po[(po.lam == l) & (po.amp == a) & (po.years == y)].reject.iloc[0]) for y in YEARS} for a in AMPS} for l in LAMS},
           "誤検出率（負の二項・季節なし）": {f"λ={l}": {f"{y}年": float(nb[(nb.lam == l) & (nb.years == y)].reject.iloc[0]) for y in YEARS} for l in LAMS},
           "季節指数の誤差（ポアソン・A=0.2）": {f"λ={l}": {f"{y}年": float(po[(po.lam == l) & (po.amp == 0.2) & (po.years == y)].idx_rmse.iloc[0]) for y in YEARS} for l in LAMS},
           "山の月が前後1か月で当たる割合（A=0.2）": {f"λ={l}": {f"{y}年": float(po[(po.lam == l) & (po.amp == 0.2) & (po.years == y)].peak_hit.iloc[0]) for y in YEARS} for l in LAMS}}
    json.dump(out, open(RES / "a529_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：1年分の見本（λ=20）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for j, A in enumerate([0.0, 0.2]):
        mu = 20 * (1 + A * np.cos(2 * np.pi * M / 12))
        for k, c in enumerate([BLUE, ORANGE, GREEN]):
            ax[j].plot(M + 1, keep[A][k], marker="o", ms=3, color=c, lw=1.2, label=f"見本{k+1}")
        ax[j].plot(M + 1, mu, color=INK, ls="--", lw=1.2, label="本当の平均")
        ax[j].set_xticks(M + 1); ax[j].set_xlabel("月")
        ax[j].set_title("季節なし（A=0）" if A == 0 else "季節あり（A=0.2、1月が山）", fontsize=11)
    ax[0].set_ylabel("件数（月平均20件、1年分）"); ax[0].legend(frameon=False, fontsize=8.5, ncol=2)
    fig.suptitle("1年分だけだと、季節がなくても山と谷に見える", fontsize=12, y=1.03)
    save(fig, "a529_examples.png", SRC)

    # 図2：検出率（A=0.2）と誤検出率
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for lam, c in zip(LAMS, [GRAY, BLUE, ORANGE]):
        s = po[(po.lam == lam) & (po.amp == 0.2)]
        ax[0].plot(s.years, s.reject * 100, marker="o", color=c, label=f"月平均 {lam}件")
        for x_, y_ in zip(s.years, s.reject * 100):
            ax[0].text(x_, y_ + 2.5, f"{y_:.0f}", ha="center", fontsize=8.5, color=c)
        s2 = po[(po.lam == lam) & (po.amp == 0.0)]
        s3 = nb[nb.lam == lam]
        ax[1].plot(s2.years, s2.reject * 100, marker="o", color=c, label=f"ポアソン・{lam}件")
        ax[1].plot(s3.years, s3.reject * 100, marker="s", ls="--", color=c, label=f"ばらつき2倍・{lam}件")
    ax[0].set_title("季節を見つける割合（山の大きさ A=0.2）", fontsize=10.5)
    ax[1].set_title("季節がないのに見つかる割合", fontsize=11)
    for a in ax:
        a.set_xscale("log"); a.set_xticks(YEARS); a.set_xticklabels([f"{y}年" for y in YEARS]); a.set_xlabel("使う年数")
    ax[1].axhline(5, color=INK, lw=0.8, ls=":")
    ax[0].set_ylabel("割合（%）"); ax[0].set_ylim(0, 108); ax[0].legend(frameon=False, fontsize=8.5, loc="lower right"); ax[1].legend(frameon=False, fontsize=8, ncol=2)
    fig.suptitle("件数が少ないと1年では見つからず、ばらつきが大きいと季節がなくても見つかってしまう", fontsize=12, y=1.03)
    save(fig, "a529_power_fp.png", SRC)

    # 図3：季節指数の誤差
    fig, ax = plt.subplots(figsize=(8, 4.3))
    for lam, c in zip(LAMS, [GRAY, BLUE, ORANGE]):
        s = po[(po.lam == lam) & (po.amp == 0.2)]
        ax.plot(s.years, s.idx_rmse, marker="o", color=c, label=f"月平均 {lam}件")
        for x_, y_ in zip(s.years, s.idx_rmse):
            ax.text(x_, y_ + 0.012, f"{y_:.2f}", ha="center", fontsize=8.5, color=c)
    ax.axhline(0.2 / np.sqrt(2), color=INK, ls=":", lw=1)
    ax.text(1.05, 0.2 / np.sqrt(2) + 0.008, "季節の山の大きさ（A=0.2 の季節指数の標準偏差）", ha="left", fontsize=8.5)
    ax.set_xscale("log"); ax.set_xticks(YEARS); ax.set_xticklabels([f"{y}年" for y in YEARS])
    ax.set_xlabel("使う年数"); ax.set_ylabel("季節指数の誤差（平均二乗誤差の平方根）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("季節指数の誤差：月平均5件では10年分でも山の大きさに近い", fontsize=12)
    save(fig, "a529_index_error.png", SRC)
    print(df.to_string())


if __name__ == "__main__":
    main()
