"""548 過去の損害を今の水準に直すトレンド率が1ポイントずれると、見込みの損害はどれだけずれるのか（手法の解説・保険数理）

架空の10年分（2016〜2025年）の損害。1件あたりの損害（損害額）は、本当のトレンド（物価などで毎年 3% 伸びる）に乗る。
  損害額 ＝ ふつうの損害（対数正規、2016年の平均 50万円）か、確率 p で大きな損害（パレート、下限 300万円、α=1.8）。p = 0・1%・3%。
  件数は毎年 ポアソン（平均 1,000件）。
見込み：各年の平均損害額を、トレンド率 r で 2027年（見込みの対象の年）の水準に直し、使う年数（直近 3・5・10年）で平均する。
  (1) r を本当の値から ±1・±2ポイントずらしたとき、見込みはどれだけずれるか
  (2) r をデータから推定したとき（年ごとの平均損害額の対数に直線を当てる）、推定の振れと見込みの振れ
  (3) 免責 500万円を超えた分（1件あたり）の見込みで、1ポイントのずれがどれだけになるか（1件ずつトレンドを当ててから免責を引く）
各場面 2,000回、乱数の種 548。数字は置いた前提で決まる。料率や準備金の助言ではない。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "出典：架空の損害（作成者が乱数で作成、seed 548）"
YEARS = np.arange(2016, 2026)
TARGET = 2027
TRUE_I = 0.03
MU_SMALL = 500_000
SIG = 1.0
LARGE_MIN, ALPHA = 3_000_000, 1.8
NCLAIM = 1000
D = 5_000_000
REPS = 2000
PS = [0.0, 0.01, 0.03]
USE = [3, 5, 10]
DELTAS = [-0.02, -0.01, 0.0, 0.01, 0.02]


def draw(rng, n, p):
    m = np.log(MU_SMALL) - SIG ** 2 / 2
    x = rng.lognormal(m, SIG, n)
    big = rng.random(n) < p
    x[big] = LARGE_MIN * (1 + rng.pareto(ALPHA, big.sum()))
    return x


def true_values(p, rng):
    x = draw(rng, 4_000_000, p) * (1 + TRUE_I) ** (TARGET - 2016)
    return x.mean(), np.maximum(x - D, 0).mean()


def main():
    rng = np.random.default_rng(548)
    rows, est_rows = [], []
    truth = {}
    for p in PS:
        tm, te = true_values(p, rng); truth[p] = (tm, te)
        for r_ in range(REPS):
            claims = [draw(rng, rng.poisson(NCLAIM), p) * (1 + TRUE_I) ** (y - 2016) for y in YEARS]
            avg = np.array([c.mean() for c in claims])
            for n in USE:
                yy, aa = YEARS[-n:], avg[-n:]
                for dl in DELTAS:
                    r = TRUE_I + dl
                    proj = np.mean(aa * (1 + r) ** (TARGET - yy))
                    ex = np.mean([np.maximum(c * (1 + r) ** (TARGET - y) - D, 0).mean() for c, y in zip(claims[-n:], yy)])
                    rows.append(dict(p=p, rep=r_, years_used=n, delta=dl, proj_err=proj / tm - 1, excess_err=ex / te - 1))
                if n >= 5:
                    b = np.polyfit(yy - yy.mean(), np.log(aa), 1)[0]; rhat = np.exp(b) - 1
                    proj = np.mean(aa * (1 + rhat) ** (TARGET - yy))
                    est_rows.append(dict(p=p, rep=r_, years_used=n, r_hat=rhat, proj_err=proj / tm - 1))
    df = pd.DataFrame(rows); es = pd.DataFrame(est_rows)
    df.to_csv(RES / "reps_fixed_rate.csv", index=False, float_format="%.6f")
    es.to_csv(RES / "reps_estimated_rate.csv", index=False, float_format="%.6f")
    sm = df.groupby(["p", "years_used", "delta"]).agg(mean_proj_err=("proj_err", "mean"), p05=("proj_err", lambda v: v.quantile(0.05)),
                                                       p95=("proj_err", lambda v: v.quantile(0.95)), mean_excess_err=("excess_err", "mean")).reset_index()
    sm.to_csv(RES / "summary_fixed_rate.csv", index=False, float_format="%.4f")
    se = es.groupby(["p", "years_used"]).agg(r_hat_mean=("r_hat", "mean"), r_hat_sd=("r_hat", "std"),
                                             r_hat_p05=("r_hat", lambda v: v.quantile(0.05)), r_hat_p95=("r_hat", lambda v: v.quantile(0.95)),
                                             share_off_1pt=("r_hat", lambda v: (np.abs(v - TRUE_I) > 0.01).mean()),
                                             proj_err_p05=("proj_err", lambda v: v.quantile(0.05)), proj_err_p95=("proj_err", lambda v: v.quantile(0.95))).reset_index()
    se.to_csv(RES / "summary_estimated_rate.csv", index=False, float_format="%.4f")
    print(sm[sm.p == 0.01].to_string()); print(se.to_string())
    # 1ポイントのずれの影響（真の r との差）
    base = sm[sm.delta == 0].set_index(["p", "years_used"])
    eff = []
    for (p, n), g in sm.groupby(["p", "years_used"]):
        b = base.loc[(p, n)]
        for dl in [-0.01, 0.01]:
            x = g[np.isclose(g.delta, dl)].iloc[0]
            eff.append(dict(p=p, years_used=n, delta=dl, proj_shift_pct=((1 + x.mean_proj_err) / (1 + b.mean_proj_err) - 1) * 100,
                            excess_shift_pct=((1 + x.mean_excess_err) / (1 + b.mean_excess_err) - 1) * 100))
    ef = pd.DataFrame(eff); ef.to_csv(RES / "one_point_effect.csv", index=False, float_format="%.3f"); print(ef.to_string())
    json.dump({"truth": {str(k): {"mean_severity_2027": v[0], "excess_per_claim_2027": v[1]} for k, v in truth.items()},
               "one_point_effect": ef.round(3).to_dict("records"), "estimated_rate": se.round(4).to_dict("records")},
              open(RES / "a548_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：ずれ幅と見込みのずれ（大きな損害なし、使う年数別）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for n, c in zip(USE, [LIGHT, BLUE, ORANGE]):
        g = sm[(sm.p == 0.0) & (sm.years_used == n)]
        b = g[g.delta == 0].mean_proj_err.iloc[0]
        v = ((1 + g.mean_proj_err) / (1 + b) - 1) * 100
        ax.plot(g.delta * 100, v, "-o", color=c, label=f"直近{n}年を使う")
        vv = v[np.isclose(g.delta, 0.01)].iloc[0]
        ax.annotate(f"{vv:+.1f}%", (1, vv), xytext={3: (8, -14), 5: (10, -2), 10: (-46, 6)}[n], textcoords="offset points", fontsize=9.5, color=c if n != 3 else GRAY)
    ax.axhline(0, color=INK, lw=0.8); ax.axvline(0, color=GRAY, lw=0.8, ls=":")
    ax.set_xlabel("トレンド率のずれ（ポイント、本当は年3%）"); ax.set_ylabel("2027年の見込みの平均損害額のずれ（%）")
    ax.set_title("1ポイントのずれは、古い年を使うほど大きく効く")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a548_shift_by_years.png", SRC)

    # 図2：推定したトレンド率の分布（10年、大きな損害の割合別）
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); bins = np.linspace(-0.02, 0.08, 51)
    for p, c in zip(PS, [GRAY, BLUE, ORANGE]):
        v = es[(es.p == p) & (es.years_used == 10)].r_hat
        ax.hist(v, bins=bins, histtype="step", lw=2, color=c, label=f"大きな損害 {p*100:.0f}%（ばらつき {v.std()*100:.1f}pt）")
    ax.axvline(TRUE_I, color=INK, lw=1, ls="--"); ax.text(TRUE_I + 0.003, ax.get_ylim()[1] * 0.92, "本当は3%", fontsize=9)
    ax.set_xlabel("10年分から推定したトレンド率"); ax.set_ylabel("回数（2,000回のうち）")
    ax.set_title("大きな損害が混じると、推定したトレンド率は大きく振れる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a548_rhat_hist.png", SRC)

    # 図3：全体と免責を超えた分、1ポイントのずれの効き方
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    g = ef[(ef.p == 0.01) & (ef.delta == 0.01)]
    x = np.arange(len(USE)); w = 0.36
    b1 = ax.bar(x - w / 2, g.proj_shift_pct, w, color=BLUE, label="1件あたりの損害額（全体）")
    b2 = ax.bar(x + w / 2, g.excess_shift_pct, w, color=ORANGE, label="免責500万円を超えた分")
    for bb in list(b1) + list(b2):
        ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 0.2, f"+{bb.get_height():.1f}%", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"直近{n}年" for n in USE])
    ax.set_ylabel("見込みの増え方（%）")
    ax.set_title("トレンド率を1ポイント高くすると、免責を超えた分は約2.2倍動く（大きな損害1%）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a548_excess_leverage.png", SRC)


if __name__ == "__main__":
    main()
