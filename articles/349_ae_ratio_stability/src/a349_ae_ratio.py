"""A349 実際の死亡数と見込みの比（A/E 比）は、何人分のデータで安定するのか（架空の集団、seed 349）"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import *

SEED = 349
REPS = 4000
TOL = 0.10
std = pd.read_csv(DATA / "standard_qx_2024_male.csv")     # 見込みに使う標準の表：令和6年簡易生命表（男）20〜94歳
AGE = std.age.values; Q = std.qx.values

def mix(lo, hi):
    w = np.where((AGE >= lo) & (AGE <= hi), 1.0, 0.0); return w / w.sum()
GROUPS = {"若い集団（25〜54歳）": mix(25, 54), "中年の集団（45〜69歳）": mix(45, 69), "高齢の集団（65〜89歳）": mix(65, 89)}
SIG_AMT = 1.0                                              # 保険金額の散らばり（対数正規、変動係数1.31）

def sim_ae(rng, w, py, reps, ratio=None):
    n = np.round(py * w).astype(int); q = Q if ratio is None else np.minimum(Q * ratio, 1)
    d = rng.binomial(n, q, size=(reps, len(AGE)))
    return d.sum(axis=1) / (n * Q).sum(), float((n * Q).sum())

def need_py(rng, w, tol=TOL, target=0.90):
    grid = np.unique(np.round(np.logspace(3, 6.7, 50)).astype(int)); prev = None
    for py in grid:
        ae, E = sim_ae(rng, w, int(py), REPS); f = float((np.abs(ae - 1) <= tol).mean())
        if f >= target:
            if prev is None: return float(py), E
            p0, f0, E0 = prev; t = (target - f0) / (f - f0)
            return float(np.exp(np.log(p0) + t * (np.log(py) - np.log(p0)))), float(E0 + t * (E - E0))
        prev = (py, f, E)
    return float("nan"), float("nan")

def sim_ae_amount(rng, w, py, reps):
    """金額で数えた A/E 比：1人ごとの保険金額（対数正規、平均1）をかけて足す"""
    n = np.round(py * w).astype(int); out = np.empty(reps); Eamt = (n * Q).sum()
    mu = -SIG_AMT ** 2 / 2
    for r in range(reps):
        d = rng.binomial(n, Q); out[r] = rng.lognormal(mu, SIG_AMT, int(d.sum())).sum() / Eamt
    return out

def main():
    rng = np.random.default_rng(SEED)
    # 1) 見込みの死亡数と A/E 比の幅（どの集団でもほぼ同じ形になる）
    funnel = []
    w = GROUPS["中年の集団（45〜69歳）"]; avg_q = float((w * Q).sum())
    for E in [5, 10, 20, 50, 100, 200, 300, 500, 1000, 2000]:
        py = int(round(E / avg_q)); ae, Ee = sim_ae(rng, w, py, REPS)
        d = np.round(ae * Ee)
        lo = np.where(d > 0, stats.chi2.ppf(0.025, 2 * d) / 2, 0) / Ee; hi = stats.chi2.ppf(0.975, 2 * (d + 1)) / 2 / Ee
        funnel.append(dict(expected=Ee, person_years=py, p05=float(np.quantile(ae, 0.05)), p50=float(np.median(ae)), p95=float(np.quantile(ae, 0.95)),
                           within10=float((np.abs(ae - 1) <= TOL).mean()), within20=float((np.abs(ae - 1) <= 0.20).mean()),
                           ci_cover=float(((lo <= 1) & (hi >= 1)).mean()), ci_lo_med=float(np.median(lo)), ci_hi_med=float(np.median(hi))))
    df = pd.DataFrame(funnel); df.to_csv(RES / "ae_by_expected_deaths.csv", index=False)

    # 2) ±10%に10回中9回収まるのに必要な人数×年数（年齢の構成ごと、件数と金額）
    need = []
    for g, w in GROUPS.items():
        py, E = need_py(rng, w); aq = float((w * Q).sum())
        # 金額：必要な見込み死亡数は (1+変動係数^2) 倍（式）。シミュレーションでも確かめる
        cv2 = np.exp(SIG_AMT ** 2) - 1; py_amt_formula = (1.6449 / TOL) ** 2 * (1 + cv2) / aq
        ae_amt = sim_ae_amount(rng, w, int(round(py_amt_formula)), 1500)
        need.append(dict(group=g, avg_q=aq, need_py=py, need_expected=E, formula_expected=(1.6449 / TOL) ** 2,
                         need_py_amount_formula=float(py_amt_formula), amount_within10_at_formula=float((np.abs(ae_amt - 1) <= TOL).mean()),
                         amount_within10_at_count_need=float((np.abs(sim_ae_amount(rng, w, int(round(py)), 1500) - 1) <= TOL).mean())))
    dn = pd.DataFrame(need); dn.to_csv(RES / "need_person_years.csv", index=False)

    # 3) 年齢でずれ方が違うとき：全体の A/E 比は年齢の構成で変わる
    ratio = np.where(AGE < 50, 0.80, np.where(AGE < 70, 1.00, 1.15))       # 本当の死亡率÷標準の表
    mixrows = []
    def lin(a, b):
        k = (AGE >= 40) & (AGE <= 79); w = np.where(k, a + (b - a) * (AGE - 40) / 39, 0.0); return w / w.sum()
    MIXES = {"40〜79歳・若い人が多い": lin(1.0, 0.2), "40〜79歳・どの年齢も同じ人数": lin(1.0, 1.0), "40〜79歳・高齢の人が多い": lin(0.2, 1.0)}
    for g, w in MIXES.items():
        ae_true = float((w * Q * ratio).sum() / (w * Q).sum())
        ae, E = sim_ae(rng, w, 2_000_000, 400, ratio)
        bands = {}
        for b, (a0, a1) in {"50歳未満": (0, 49), "50〜69歳": (50, 69), "70歳以上": (70, 200)}.items():
            k = (AGE >= a0) & (AGE <= a1); bands[b] = float((w[k] * Q[k]).sum() / (w * Q).sum())
        mixrows.append(dict(group=g, overall_ae=ae_true, overall_ae_sim=float(ae.mean()), **{f"share_expected_{b}": v for b, v in bands.items()}))
    dm = pd.DataFrame(mixrows)
    # ある集団の全体の比を、別の集団の見込みにそのまま使ったときのずれ
    cross = []
    for g1 in MIXES:
        for g2 in MIXES:
            a1 = dm[dm.group == g1].overall_ae.iloc[0]; a2 = dm[dm.group == g2].overall_ae.iloc[0]
            cross.append(dict(ratio_from=g1, applied_to=g2, error_pct=float((a1 / a2 - 1) * 100)))
    grp = [dict(group=g, overall_ae=float((w * Q * ratio).sum() / (w * Q).sum())) for g, w in GROUPS.items()]
    pd.DataFrame(grp).to_csv(RES / "age_range_overall_ae.csv", index=False)
    under50 = [dict(group=g, overall_ae=float(a), error_if_used_for_under50_pct=float((a / 0.80 - 1) * 100)) for g, a in zip(dm.group, dm.overall_ae)]
    dc = pd.DataFrame(cross); dm.to_csv(RES / "age_mix_overall_ae.csv", index=False); dc.to_csv(RES / "age_mix_cross_error.csv", index=False)

    # 例のデータ：中年の集団1万人×5年の年ごとの A/E 比
    r2 = np.random.default_rng(SEED + 1); w = GROUPS["中年の集団（45〜69歳）"]
    ae, E = sim_ae(r2, w, 10_000, 5)
    pd.DataFrame({"year": range(1, 6), "expected_deaths": round(E, 1), "actual_deaths": np.round(ae * E).astype(int), "ae_ratio": np.round(ae, 3)}).to_csv(DATA / "example_ae_10000x5.csv", index=False)
    json.dump(dict(seed=SEED, reps=REPS, tol=TOL, funnel=df.to_dict("records"), need=dn.to_dict("records"),
                   age_mix=dm.to_dict("records"), cross=dc.to_dict("records"), age_range=grp, under50=under50, true_ratio_by_age={"50歳未満": 0.8, "50〜69歳": 1.0, "70歳以上": 1.15},
                   amount_sigma=SIG_AMT), open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    src = "見込みの表：厚生労働省「令和6年簡易生命表」（男）。集団は架空（作成者が乱数で作成、seed 349）"
    # 図1：見込みの死亡数と A/E 比の幅
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.fill_between(df.expected, df.p05, df.p95, color=LIGHT, alpha=0.7, label="20回のうち18回が入る範囲")
    ax.plot(df.expected, df.p50, color=BLUE, lw=1.5, label="中央値")
    ax.axhline(1.1, color=GRAY, ls="--", lw=0.8); ax.axhline(0.9, color=GRAY, ls="--", lw=0.8); ax.text(2100, 1.115, "±10%", ha="right", fontsize=9, color=GRAY)
    for E_, lo, hi in zip(df.expected, df.p05, df.p95):
        if round(E_) in (5, 20, 100, 300, 1000): ax.text(E_, hi + 0.03, f"{lo:.2f}〜{hi:.2f}", ha="center", fontsize=8.5)
    ax.set_xscale("log"); ax.set_xticks([5, 10, 20, 50, 100, 300, 1000, 2000]); ax.set_xticklabels(["5", "10", "20", "50", "100", "300", "1,000", "2,000"])
    ax.set_xlabel("見込みの死亡数（人）"); ax.set_ylabel("実際の死亡数÷見込みの死亡数"); ax.set_ylim(0.2, 2.1)
    ax.legend(fontsize=9, frameon=False); ax.set_title("本当は見込みどおり（比1.00）でも、死亡数が少ないと比は大きく振れる")
    save(fig, "a349_funnel.png", src)

    # 図2：必要な人数×年数
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(dn))[::-1]
    ax.barh(y + 0.19, dn.need_py, 0.36, color=BLUE, label="件数で数えた比")
    ax.barh(y - 0.19, dn.need_py_amount_formula, 0.36, color=ORANGE, label="保険金額で数えた比（金額の変動係数1.3）")
    for yy, a, b in zip(y, dn.need_py, dn.need_py_amount_formula):
        ax.text(a * 1.08, yy + 0.19, f"{a/1e4:,.1f}万人年", va="center", fontsize=9); ax.text(b * 1.08, yy - 0.19, f"{b/1e4:,.1f}万人年", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(dn.group, fontsize=9.5); ax.set_xscale("log"); ax.set_xlim(3e3, 1.2e7)
    ax.set_xlabel("比が10回のうち9回、±10%に収まるのに必要な人数×年数（対数の目盛り）"); ax.legend(fontsize=9, frameon=False, loc="lower right")
    ax.set_title("必要なのは「見込みの死亡数で約270人」。人数に直すと年齢で2桁違う")
    save(fig, "a349_need_person_years.png", src)

    # 図3：年齢の構成で全体の比が変わる
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(dm)); bars = ax.bar(x, dm.overall_ae, 0.5, color=[BLUE, GREEN, ORANGE])
    for xi, r_ in zip(x, dm.to_dict("records")): ax.text(xi, 0.63, f"見込みの死亡のうち\n70歳以上が{r_['share_expected_70歳以上']*100:.0f}%", ha="center", fontsize=9, color="white")
    for b_, v in zip(bars, dm.overall_ae): ax.text(b_.get_x() + b_.get_width() / 2, v + 0.012, f"{v:.2f}", ha="center", fontsize=11)
    ax.axhline(1, color=GRAY, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(dm.group, fontsize=9.5); ax.set_ylim(0.6, 1.25)
    ax.set_ylabel("全体の A/E 比（データが十分あるとき）")
    ax.set_title("年齢ごとのずれ方が同じでも、年齢の構成で全体の比は変わる\n（本当の死亡率÷標準の表：50歳未満0.80・50〜69歳1.00・70歳以上1.15）", fontsize=12)
    save(fig, "a349_age_mix.png", src)
    print(df.round(3).to_string()); print(dn.round(3).to_string()); print(dm.round(3).to_string()); print(dc.round(1).to_string()); print(grp, under50)

if __name__ == "__main__":
    main()
