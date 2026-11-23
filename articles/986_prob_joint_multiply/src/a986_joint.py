"""986 2つの出来事が同時に起きる確率は、掛け算でよいのか？（架空のデータ）

架空の会社のサーバー2台（主と予備）。どちらも1日に1%の確率で止まると作成者が置く。
両方を同じ日に止める「共通の原因の日」（共通の更新作業の不具合など）を作成者が置き、
両方が同じ日に止まる割合が、掛け算（1%×1%）とどれだけずれるかを、乱数で作った日々で数える。式の値とも比べる。
"""
import json
from math import erf, sqrt
from statistics import NormalDist
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 986
SRC = "架空のサーバーの停止の記録（作成者が乱数で作成、seed 986）"
P = 0.01          # 1台が1日に止まる確率
S_BASE = 0.001    # 共通の原因の日の割合（その日は2台とも止まる）
N_DAYS = 10_000_000


def r6(x):
    return round(float(x), 6)


def joint_formula(p, s, units=2):
    """共通の原因の日（確率 s）は全台が止まる。それ以外の日は台ごとにばらばらに確率 l で止まる（1台の確率は p のまま）"""
    l = (p - s) / (1 - s)
    return s + (1 - s) * l ** units


def phi_corr(p, j):
    """2台の「止まった（1/0）」の相関"""
    return (j - p * p) / (p * (1 - p))


def sim_days(rng, n, p, s, units=2):
    l = (p - s) / (1 - s)
    cause = rng.random(n) < s
    stops = (rng.random((units, n)) < l) | cause
    return cause, stops


def gauss_joint(p, rho, m=40001):
    """2台の止まりやすさが相関 rho の正規分布に従い、下から p の日に止まると置いたときの、同時に止まる確率（数値積分）"""
    a = NormalDist().inv_cdf(p)
    if rho == 0:
        return p * p
    x = np.linspace(-9, a, m)
    phi = np.exp(-x * x / 2) / sqrt(2 * np.pi)
    z = (a - rho * x) / sqrt(1 - rho * rho)
    cdf = 0.5 * (1 + np.array([erf(v / sqrt(2)) for v in z]))
    y = phi * cdf
    return float(((y[1:] + y[:-1]) / 2 * np.diff(x)).sum())


def main():
    out = {}
    # 1) 基本：2台、1日1%、共通の原因の日0.1%（1,000万日）
    rng = np.random.default_rng(SEED)
    cause, st = sim_days(rng, N_DAYS, P, S_BASE)
    a, b = st
    j_sim = (a & b).mean()
    j_frm = joint_formula(P, S_BASE)
    out["base"] = {"days": N_DAYS, "p": P, "s_common": S_BASE, "stop_a": r6(a.mean()), "stop_b": r6(b.mean()),
                   "product": r6(a.mean() * b.mean()), "joint_sim": r6(j_sim), "joint_formula": r6(j_frm),
                   "ratio_sim": round(float(j_sim / (a.mean() * b.mean())), 3), "ratio_formula": round(j_frm / P ** 2, 3),
                   "phi_formula": round(phi_corr(P, j_frm), 4), "phi_sim": round(float(np.corrcoef(a, b)[0, 1]), 4),
                   "share_joint_from_common": r6(cause.sum() / (a & b).sum())}
    # 独立（s=0）も同じ日数で
    rng = np.random.default_rng(SEED + 1)
    _, st0 = sim_days(rng, N_DAYS, P, 0.0)
    out["independent"] = {"joint_sim": r6((st0[0] & st0[1]).mean()), "joint_formula": r6(P * P)}

    # 2) 共通の原因の日の割合 × 1台の止まる確率（式＋各200万日のシミュレーション）
    rows = []
    for i, p in enumerate([0.001, 0.01, 0.05]):
        for k, s in enumerate([0, 0.0001, 0.0005, 0.001, 0.002, 0.005]):
            if s > p:
                continue
            j = joint_formula(p, s)
            rng = np.random.default_rng(SEED * 100 + i * 10 + k)
            _, stt = sim_days(rng, 2_000_000, p, s)
            rows.append({"p": p, "s_common": s, "product": r6(p * p), "joint_formula": r6(j),
                         "joint_sim_2m_days": r6((stt[0] & stt[1]).mean()), "ratio": round(j / p ** 2, 3),
                         "phi": round(phi_corr(p, j), 4),
                         "three_units_formula": float(f"{joint_formula(p, s, 3):.4g}"),
                         "three_units_ratio": round(joint_formula(p, s, 3) / p ** 3, 1)})
    grid_s = pd.DataFrame(rows)
    grid_s.to_csv(RES / "grid_common_cause.csv", index=False)

    # 3) 同じ相関でも、まれな出来事ほど掛け算から離れる（正規分布の相関、数値積分）
    rows = []
    for p in [0.1, 0.01, 0.001]:
        for rho in [-0.3, 0, 0.1, 0.2, 0.3, 0.5]:
            j = gauss_joint(p, rho)
            rows.append({"p": p, "rho_latent": rho, "product": r6(p * p), "joint": float(f"{j:.6g}"),
                         "ratio": round(j / p ** 2, 3), "phi": round(phi_corr(p, j), 4)})
    grid_r = pd.DataFrame(rows)
    grid_r.to_csv(RES / "grid_latent_corr.csv", index=False)
    # 数値積分の確かめ（p=1%、rho=0.3、500万日の乱数）
    rng = np.random.default_rng(SEED + 2)
    z1 = rng.standard_normal(5_000_000); z2 = 0.3 * z1 + sqrt(1 - 0.09) * rng.standard_normal(5_000_000)
    th = NormalDist().inv_cdf(0.01)
    out["latent_check"] = {"p": 0.01, "rho": 0.3, "joint_integral": float(f"{gauss_joint(0.01, 0.3):.6g}"),
                           "joint_sim_5m": r6(((z1 < th) & (z2 < th)).mean())}

    # 4) 記録の長さ：1年（365日）・3年・10年（3,650日）の記録を各4,000通り
    rows = []
    for i, (lab, s) in enumerate([("共通の原因 0.1%", S_BASE), ("独立（共通の原因なし）", 0.0)]):
        for k, days in enumerate([365, 1095, 3650]):
            rng = np.random.default_rng(SEED * 1000 + i * 10 + k)
            n_rec = 4000
            _, stt = sim_days(rng, n_rec * days, P, s)
            aa = stt[0].reshape(n_rec, days); bb = stt[1].reshape(n_rec, days)
            jc = (aa & bb).sum(1)
            exp_prod = aa.mean(1) * bb.mean(1) * days        # 記録の1台ごとの割合の掛け算から見込んだ同時の日数
            j = joint_formula(P, s)
            rows.append({"case": lab, "s_common": s, "days": days, "records": n_rec,
                         "share_zero_joint": round(float((jc == 0).mean()), 4),
                         "share_zero_joint_formula": round((1 - j) ** days, 4),
                         "mean_joint_days": round(float(jc.mean()), 3),
                         "mean_expected_by_product": round(float(exp_prod.mean()), 3),
                         "share_joint_ge_2": round(float((jc >= 2).mean()), 4)})
    rec = pd.DataFrame(rows)
    rec.to_csv(RES / "record_length.csv", index=False)

    # 1回分の10年の記録（data）
    rng = np.random.default_rng(SEED + 3)
    c10, s10 = sim_days(rng, 3650, P, S_BASE)
    pd.DataFrame({"day": np.arange(1, 3651), "common_cause": c10.astype(int), "stop_main": s10[0].astype(int),
                  "stop_backup": s10[1].astype(int)}).to_csv(DATA / "days_10years.csv", index=False)
    out["one_record_10y"] = {"stop_main_days": int(s10[0].sum()), "stop_backup_days": int(s10[1].sum()),
                             "both_days": int((s10[0] & s10[1]).sum()), "common_cause_days": int(c10.sum()),
                             "expected_by_product": round(float(s10[0].mean() * s10[1].mean() * 3650), 3)}

    out["grid_common_cause"] = grid_s.to_dict("records")
    out["grid_latent_corr"] = grid_r.to_dict("records")
    out["record_length"] = rec.to_dict("records")
    chk = grid_s[grid_s.joint_formula * 2_000_000 >= 100]   # 同時の日が見込み100日以上の場合だけ比べる
    out["grid_sim_check"] = {"n_cases_checked": int(len(chk)), "n_cases": int(len(grid_s)),
                             "max_rel_diff": round(float(((chk.joint_sim_2m_days - chk.joint_formula).abs()
                                                          / chk.joint_formula).max()), 3)}
    json.dump(out, open(RES / "a986_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：共通の原因の日の割合と、掛け算の何倍か（1日1%）
    g = grid_s[grid_s.p == 0.01]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = np.arange(len(g))
    ax.bar(xs, g.joint_formula * 100, color=[GRAY] + [BLUE] * (len(g) - 1), width=.6)
    ax.axhline(P * P * 100, color=ORANGE, lw=1.2, ls="--", label="掛け算（1%×1%＝0.01%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    for x, (v, r) in enumerate(zip(g.joint_formula * 100, g.ratio)):
        ax.text(x, v * 1.04, f"{v:.4f}%\n（{r:.2f}倍）", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{s*100:g}%" for s in g.s_common])
    ax.set_xlabel("両方を止める共通の原因の日の割合（1台はどれも1日1%で止まる）")
    ax.set_ylabel("2台が同じ日に止まる割合（%）"); ax.set_ylim(0, g.joint_formula.max() * 100 * 1.25)
    ax.set_title(f"共通の原因の日が0.1%あるだけで、同時に止まる日は掛け算の{g[g.s_common == S_BASE].ratio.iloc[0]:.2f}倍", fontsize=12)
    save(fig, "a986_common_cause.png", SRC)

    # 図2：同じ相関でも、まれなほど掛け算から離れる
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for p, c in [(0.1, LIGHT), (0.01, BLUE), (0.001, INK)]:
        d = grid_r[grid_r.p == p]
        ax.plot(d.rho_latent, d.ratio, "o-", color=c, label=f"1台が止まる確率 {p*100:g}%")
    ax.axhline(1, color=GRAY, lw=.8)
    ax.set_yscale("log"); ax.set_xlabel("2台の止まりやすさの相関（正規分布に置いた値）")
    ax.set_ylabel("同時に止まる割合 ÷ 掛け算（対数の目盛り）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("同じ相関でも、まれな出来事ほど掛け算から大きく離れる", fontsize=12)
    save(fig, "a986_rare_corr.png", SRC)

    # 図3：記録の長さと、同時に止まった日が0日の記録の割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = .38
    for off, (lab, c) in zip([-w / 2, w / 2], [("共通の原因 0.1%", BLUE), ("独立（共通の原因なし）", GRAY)]):
        d = rec[rec.case == lab]
        xs = np.arange(len(d))
        ax.bar(xs + off, d.share_zero_joint * 100, width=w, color=c, label=lab)
        for x, v in zip(xs + off, d.share_zero_joint * 100):
            ax.text(x, v + 1.5, f"{v:.2f}%", ha="center", fontsize=8.5)
    ax.set_xticks(np.arange(3)); ax.set_xticklabels(["1年（365日）", "3年", "10年（3,650日）"])
    ax.set_ylabel("同時に止まった日が0日だった記録（%）"); ax.set_ylim(0, 110)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("1年の記録では、掛け算の10倍を超えていても、同時の停止が0回の記録が多い", fontsize=12)
    save(fig, "a986_record_length.png", SRC)
    print(json.dumps({k: out[k] for k in ["base", "independent", "latent_check", "one_record_10y",
                                          "grid_sim_check"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
