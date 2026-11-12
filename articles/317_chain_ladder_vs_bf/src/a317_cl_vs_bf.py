"""317 新しい事故年度の見積もりは、実績から延ばす（チェインラダー法）のと、見込みの損害率に寄せる
（ボーンヒュッター・ファーガソン法）のと、どちらが近いか。架空の支払データ（最終の支払額が分かる）で比べる。"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK, save

SEED, NSIM, N = 317, 2000, 10
SOURCE = "架空のデータ（作成者が乱数で作成、seed 317）"
ELR = 0.65                                       # 本当の損害率の平均
PREM = 1000 * 1.03 ** np.arange(N)               # 保険料（百万円）


def G(t):
    return 1 - np.exp(-(np.asarray(t, float) / 3.2) ** 1.1)


SHARE = np.diff(np.r_[0.0, G(np.arange(1, N + 1)) / G(N)])   # 経過年ごとに払う割合（316 と同じ進み方）


def simulate(rng, cv_cell=0.12, cv_lr=0.08, nsim=NSIM):
    s2 = np.log(1 + cv_lr ** 2)
    lr = rng.lognormal(np.log(ELR) - 0.5 * s2, np.sqrt(s2), (nsim, N))
    noise = rng.gamma(1 / cv_cell ** 2, cv_cell ** 2, (nsim, N, N))
    return (PREM * lr)[:, :, None] * SHARE * noise           # X[組, 事故年度, 経過]


def estimates(X, priors):
    """チェインラダー法（CL）、ボーンヒュッター・ファーガソン法（BF、見込みの損害率ごと）、ケープコッド法（CC）"""
    C = np.cumsum(X, axis=2)
    f = np.ones((X.shape[0], N - 1))
    for j in range(N - 1):
        f[:, j] = C[:, :N - 1 - j, j + 1].sum(1) / C[:, :N - 1 - j, j].sum(1)
    paid = np.stack([C[:, i, N - 1 - i] for i in range(N)], axis=1)
    cdf = np.stack([np.prod(f[:, N - 1 - i:], axis=1) for i in range(N)], axis=1)   # いまの累計→最終への倍率
    q = 1 - 1 / cdf                                                                 # まだ払っていない割合の見積もり
    out = {"CL": paid * cdf}
    for name, p in priors.items():
        out[name] = paid + q * PREM * p                      # 払った分＋（未払いの割合×保険料×見込みの損害率）
    cc = paid.sum(1) / (PREM / cdf).sum(1)                   # データから決めた損害率（ケープコッド）
    out["CC"] = paid + q * PREM * cc[:, None]
    return out, paid, cc


def rmse(a): return float(np.sqrt((a ** 2).mean()))


def main():
    rng = np.random.default_rng(SEED)
    priors = {"BF 見込みが正しい（65%）": ELR, "BF 見込みが1割高い（71.5%）": ELR * 1.1, "BF 見込みが1割低い（58.5%）": ELR * 0.9}
    out = {"設定": {"事故年度": N, "回数": NSIM, "本当の損害率の平均": ELR, "年度ごとの損害率のばらつき（基本）": 0.08, "1マスのばらつき（基本）": 0.12}}

    # ① 基本の場面：事故年度ごと
    X = simulate(rng); U = X.sum(2)
    est, paid, cc = estimates(X, priors)
    rows = []
    for i in range(N):
        r = {"事故年度": i + 1, "払い終わった割合": round(float((paid[:, i] / U[:, i]).mean()), 3)}
        for k, v in est.items():
            r[k + " 誤差の大きさ（RMSE、%）"] = round(100 * rmse(v[:, i] / U[:, i] - 1), 2)
            r[k + " 誤差の平均（%）"] = round(100 * float((v[:, i] / U[:, i] - 1).mean()), 2)
        rows.append(r)
    by_ay = pd.DataFrame(rows); by_ay.to_csv(RES / "by_accident_year.csv", index=False)
    res_true = (U - paid).sum(1)
    out["基本の場面"] = {"正解の支払備金（平均、百万円）": round(float(res_true.mean()), 1),
                        "ケープコッドの損害率（平均）": round(float(cc.mean()), 4), "ケープコッドの損害率（標準偏差）": round(float(cc.std()), 4),
                        "備金の誤差": {k: {"平均（%）": round(100 * float((((v - paid).sum(1)) / res_true - 1).mean()), 1),
                                         "大きさ（RMSE、%）": round(100 * rmse((v - paid).sum(1) / res_true - 1), 1)} for k, v in est.items()}}
    # CL が BF（1割ずれ）より近くなる事故年度
    for k in ("BF 見込みが1割高い（71.5%）", "BF 見込みが1割低い（58.5%）", "BF 見込みが正しい（65%）"):
        better = [int(r["事故年度"]) for _, r in by_ay.iterrows() if r["CL 誤差の大きさ（RMSE、%）"] < r[k + " 誤差の大きさ（RMSE、%）"]]
        out["基本の場面"][f"CL のほうが近い事故年度（対 {k}）"] = better

    # ② 見込みの損害率のずれを −30%〜+30% で動かす：備金全体と、いちばん新しい事故年度
    devs = np.round(np.arange(-0.30, 0.3001, 0.05), 2)
    pr = {f"{d:+.2f}": ELR * (1 + d) for d in devs}
    est2, paid2, _ = estimates(X, pr)
    sweep = []
    for d in devs:
        v = est2[f"{d:+.2f}"]
        sweep.append({"見込みのずれ（%）": int(round(100 * d)), "備金の誤差の大きさ（RMSE、%）": round(100 * rmse((v - paid2).sum(1) / res_true - 1), 2),
                      "最新年度の最終額の誤差の大きさ（RMSE、%）": round(100 * rmse(v[:, -1] / U[:, -1] - 1), 2)})
    sw = pd.DataFrame(sweep); sw.to_csv(RES / "prior_error_sweep.csv", index=False)
    cl_res = 100 * rmse((est["CL"] - paid).sum(1) / res_true - 1); cl_new = 100 * rmse(est["CL"][:, -1] / U[:, -1] - 1)
    out["見込みのずれ"] = {"CL の備金の誤差の大きさ（%）": round(cl_res, 2), "CL の最新年度の誤差の大きさ（%）": round(cl_new, 2),
                        "BF の備金が CL より近い、見込みのずれの範囲（%）": [int(x) for x in sw.loc[sw["備金の誤差の大きさ（RMSE、%）"] < cl_res, "見込みのずれ（%）"]],
                        "BF の最新年度が CL より近い、見込みのずれの範囲（%）": [int(x) for x in sw.loc[sw["最新年度の最終額の誤差の大きさ（RMSE、%）"] < cl_new, "見込みのずれ（%）"]]}

    # ③ 年度ごとの損害率のばらつきを変える：最新年度の誤差（CL、BF 正しい、CC）
    var = []
    for cv in (0.03, 0.05, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30):
        Xv = simulate(rng, cv_lr=cv); Uv = Xv.sum(2)
        ev, pv, _ = estimates(Xv, {"BF": ELR})
        rt = (Uv - pv).sum(1)
        var.append({"損害率のばらつき（変動係数、%）": int(round(100 * cv)),
                    **{f"{k} 最新年度（RMSE、%）": round(100 * rmse(v[:, -1] / Uv[:, -1] - 1), 2) for k, v in ev.items()},
                    **{f"{k} 備金（RMSE、%）": round(100 * rmse((v - pv).sum(1) / rt - 1), 2) for k, v in ev.items()}})
    vr = pd.DataFrame(var); vr.to_csv(RES / "lr_variability.csv", index=False)
    out["損害率のばらつき"] = {"最新年度で CL が BF（見込みが正しい）より近くなる、ばらつきの最小（%）":
                           next((int(r["損害率のばらつき（変動係数、%）"]) for _, r in vr.iterrows() if r["CL 最新年度（RMSE、%）"] < r["BF 最新年度（RMSE、%）"]), None)}
    # ④ 1マスのばらつきが大きい場合（25%）
    Xn = simulate(rng, cv_cell=0.25); Un = Xn.sum(2); en, pn, _ = estimates(Xn, priors); rn = (Un - pn).sum(1)
    out["1マスのばらつきが25%の場合"] = {k: {"最新年度（RMSE、%）": round(100 * rmse(v[:, -1] / Un[:, -1] - 1), 1),
                                       "備金（RMSE、%）": round(100 * rmse((v - pn).sum(1) / rn - 1), 1)} for k, v in en.items()}

    C0 = np.cumsum(X[0], axis=1)
    pd.DataFrame([{"事故年度": i + 1, "保険料": round(float(PREM[i]), 1), "経過年": j + 1, "累計支払額": round(float(C0[i, j]), 1)}
                  for i in range(N) for j in range(N - i)]).to_csv(DATA / "example_triangle.csv", index=False)
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    figs(by_ay, sw, vr, cl_res, cl_new)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(by_ay[[c for c in by_ay.columns if "RMSE" in c or c in ("事故年度",)]].to_string()); print(vr.to_string())


def figs(by_ay, sw, vr, cl_res, cl_new):
    fig, ax = plt.subplots(figsize=(9, 4.6))
    sty = {"CL": (BLUE, "-o", "チェインラダー法（実績から延ばす）"), "BF 見込みが正しい（65%）": (ORANGE, "-o", "BF法：見込みの損害率が正しい"),
           "BF 見込みが1割高い（71.5%）": (ORANGE, "--^", "BF法：見込みが1割高い"), "BF 見込みが1割低い（58.5%）": (ORANGE, ":v", "BF法：見込みが1割低い"),
           "CC": (GREEN, "-s", "見込みをデータから決める（ケープコッド法）")}
    for k, (c, m, lab) in sty.items():
        ax.plot(by_ay["事故年度"], by_ay[k + " 誤差の大きさ（RMSE、%）"], m, color=c, ms=5, label=lab)
    ax.set_xticks(range(1, N + 1)); ax.set_xlabel("事故年度（10がいちばん新しい）"); ax.set_ylabel("最終の支払額の誤差の大きさ（RMSE、%）")
    ax.set_title("事故年度ごとの誤差（2,000組）"); ax.legend(frameon=False, fontsize=9.5)
    save(fig, "a317_by_accident_year.png", SOURCE)

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, col, cl, t in [(axs[0], "最新年度の最終額の誤差の大きさ（RMSE、%）", cl_new, "いちばん新しい事故年度の最終額"), (axs[1], "備金の誤差の大きさ（RMSE、%）", cl_res, "支払備金の合計")]:
        ax.plot(sw["見込みのずれ（%）"], sw[col], "-o", color=ORANGE, ms=4, label="BF法")
        ax.axhline(cl, color=BLUE, lw=2, label="チェインラダー法")
        ax.set_title(t); ax.set_xlabel("見込みの損害率のずれ（%）"); ax.set_ylabel("誤差の大きさ（RMSE、%）"); ax.set_ylim(0)
    axs[0].legend(frameon=False, fontsize=9.5)
    fig.suptitle("見込みの損害率がどこまでずれても、BF法のほうが近いか", y=1.02, fontsize=13)
    save(fig, "a317_prior_error.png", SOURCE)

    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    x = vr["損害率のばらつき（変動係数、%）"]
    ax.plot(x, vr["CL 最新年度（RMSE、%）"], "-o", color=BLUE, label="チェインラダー法")
    ax.plot(x, vr["BF 最新年度（RMSE、%）"], "-o", color=ORANGE, label="BF法（見込みは平均として正しい）")
    ax.plot(x, vr["CC 最新年度（RMSE、%）"], "-s", color=GREEN, label="ケープコッド法")
    ax.set_xlabel("事故年度ごとの本当の損害率のばらつき（変動係数、%）"); ax.set_ylabel("最新年度の最終額の誤差の大きさ（RMSE、%）"); ax.set_ylim(0)
    ax.set_title("年度ごとの損害率がばらつくほど、見込みに寄せる方法は外れる"); ax.legend(frameon=False, fontsize=9.5)
    save(fig, "a317_lr_variability.png", SOURCE)


if __name__ == "__main__":
    main()
