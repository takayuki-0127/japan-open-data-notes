"""540 事故の件数をポアソン回帰で当てるとき、契約の期間（露出）を入れ忘れると、要因の効き目はどれだけずれるのか（保険数理・回帰）

架空の自動車の契約。1年あたりの事故率は λ = exp(b0 + b1·X)、X は「業務で使う」(0/1)。本当の効き目 exp(b1) = 1.5倍。
契約の期間 t（年）は 1年の契約が6割、残りは0.05〜1年の一様（途中加入・途中解約）。件数 ~ ポアソン(λ t)。
X と期間の関係：X=1 になる確率を期間とつなげ、相関がおよそ −0.4〜+0.4 になるように変える。
当て方：(a) log t をオフセットに入れる、(b) 何も入れない、(c) log t を説明変数に入れる（係数を自由にする）。
契約 20,000件、各場面 100回（乱数の種 540）。ポアソン回帰は IRLS（ニュートン法）。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の契約と事故件数（作成者が乱数で作成、seed 540）"
N = 20_000
REPS = 100
B0, B1 = np.log(0.08), np.log(1.5)
KS = [-4.0, -2.0, -1.0, 0.0, 1.0, 2.0, 4.0]      # X と期間のつながりの強さ


def pois_fit(X, y, off):
    beta = np.zeros(X.shape[1]); beta[0] = np.log(max(y.mean(), 1e-6)) - off.mean()
    for _ in range(60):
        mu = np.exp(X @ beta + off)
        step = np.linalg.solve((X * mu[:, None]).T @ X, X.T @ (y - mu))
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return beta


def main():
    rng = np.random.default_rng(540)
    rows = []
    for k in KS:
        for r in range(REPS):
            full = rng.random(N) < 0.6
            t = np.where(full, 1.0, rng.uniform(0.05, 1.0, N))
            px = 1 / (1 + np.exp(-(np.log(0.3 / 0.7) + k * (t - t.mean()))))
            x = (rng.random(N) < px).astype(float)
            y = rng.poisson(np.exp(B0 + B1 * x) * t).astype(float)
            one = np.ones(N); lt = np.log(t)
            ba = pois_fit(np.column_stack([one, x]), y, lt)
            bb = pois_fit(np.column_stack([one, x]), y, np.zeros(N))
            bc = pois_fit(np.column_stack([one, x, lt]), y, np.zeros(N))
            rows.append(dict(k=k, rep=r, corr_x_t=float(np.corrcoef(x, t)[0, 1]), mean_t_x1=float(t[x == 1].mean()),
                             mean_t_x0=float(t[x == 0].mean()), share_x1=float(x.mean()), claims=float(y.sum()),
                             rr_offset=float(np.exp(ba[1])), rr_none=float(np.exp(bb[1])), rr_covar=float(np.exp(bc[1])),
                             coef_logt=float(bc[2])))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "reps.csv", index=False, float_format="%.6f")
    sm = df.groupby("k").agg(corr_x_t=("corr_x_t", "mean"), mean_t_x1=("mean_t_x1", "mean"), mean_t_x0=("mean_t_x0", "mean"),
                             share_x1=("share_x1", "mean"), claims=("claims", "mean"),
                             rr_offset=("rr_offset", "mean"), rr_offset_p05=("rr_offset", lambda v: v.quantile(0.05)),
                             rr_offset_p95=("rr_offset", lambda v: v.quantile(0.95)),
                             rr_none=("rr_none", "mean"), rr_none_p05=("rr_none", lambda v: v.quantile(0.05)),
                             rr_none_p95=("rr_none", lambda v: v.quantile(0.95)),
                             rr_covar=("rr_covar", "mean"), coef_logt=("coef_logt", "mean")).reset_index()
    sm["none_vs_true_pct"] = (sm.rr_none / 1.5 - 1) * 100
    sm["offset_vs_true_pct"] = (sm.rr_offset / 1.5 - 1) * 100
    sm["covar_vs_true_pct"] = (sm.rr_covar / 1.5 - 1) * 100
    sm["ratio_mean_t"] = sm.mean_t_x1 / sm.mean_t_x0
    sm.to_csv(RES / "summary.csv", index=False, float_format="%.6f")
    json.dump({"true_rr": 1.5, "rows": sm.round(6).to_dict("records")}, open(RES / "a540_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：相関と推定の倍率
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.fill_between(sm.corr_x_t, sm.rr_none_p05, sm.rr_none_p95, color=ORANGE, alpha=0.15)
    ax.plot(sm.corr_x_t, sm.rr_none, "o-", color=ORANGE, label="(b) 期間を入れない")
    ax.fill_between(sm.corr_x_t, sm.rr_offset_p05, sm.rr_offset_p95, color=BLUE, alpha=0.15)
    ax.plot(sm.corr_x_t, sm.rr_offset, "s-", color=BLUE, label="(a) オフセットに入れる")
    ax.axhline(1.5, color=INK, ls=":", lw=1); ax.text(sm.corr_x_t.min(), 1.52, "本当の値 1.5倍", fontsize=8)
    ax.set_xlabel("「業務で使う」と契約の期間の相関"); ax.set_ylabel("推定した効き目（倍）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("期間を入れ忘れると、期間と要因の相関の分だけ効き目がずれる")
    save(fig, "a540_rr_vs_corr.png", SRC + "。線は100回の平均、帯は5〜95%点")

    # 図2：ずれ（%）と期間の平均の比
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(sm.ratio_mean_t, sm.rr_none / 1.5, "o-", color=ORANGE, label="(b) の推定 ÷ 本当の値")
    lim = [sm.ratio_mean_t.min() * 0.97, sm.ratio_mean_t.max() * 1.03]
    ax.plot(lim, lim, color=GRAY, ls=":", label="y = x")
    ax.set_xlabel("期間の平均の比（業務 ÷ 業務以外）"); ax.set_ylabel("推定 ÷ 本当の値")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("ずれの倍率は、2群の期間の平均の比とほぼ同じ")
    save(fig, "a540_bias_vs_exposure_ratio.png", SRC)

    # 図3：3つの当て方（相関 ≈ +0.2 前後と −0.2 前後）
    fig, ax = plt.subplots(figsize=(7.5, 4))
    xx = np.arange(len(sm)); w = 0.26
    ax.bar(xx - w, sm.rr_offset, w, color=BLUE, label="(a) オフセット")
    ax.bar(xx, sm.rr_none, w, color=ORANGE, label="(b) 入れない")
    ax.bar(xx + w, sm.rr_covar, w, color=GREEN, label="(c) 説明変数に")
    ax.axhline(1.5, color=INK, ls=":", lw=1)
    ax.set_xticks(xx); ax.set_xticklabels([f"{c:+.2f}".replace("-0.00", "0.00").replace("+0.00", "0.00") for c in sm.corr_x_t], fontsize=9)
    ax.set_xlabel("「業務で使う」と期間の相関"); ax.set_ylabel("推定した効き目（倍）")
    ax.set_ylim(0.8, max(2.05, sm.rr_none.max() * 1.05)); ax.legend(frameon=False, fontsize=9, ncol=3)
    ax.set_title("期間を説明変数に入れても、効き目はほぼ戻る")
    save(fig, "a540_three_methods.png", SRC + "。100回の平均")
    print(sm.round(4).to_string())


if __name__ == "__main__":
    main()
