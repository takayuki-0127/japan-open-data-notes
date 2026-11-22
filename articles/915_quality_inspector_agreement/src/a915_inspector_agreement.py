"""915 検査員によって合否が違うとき、何を数えればよいのか？（架空のデータ）

架空の工場の樹脂部品（ふた）の外観検査。部品ごとに「本当の傷の大きさ」を置き、
1.0mm を超える傷がある部品を本当の不良とする（作成者が置いた物差し）。
検査員は、傷の大きさを見誤り（対数で正規の誤差）、自分の線（しきい値）を超えたら不良と判定する。
"""
import json
from itertools import combinations
from statistics import NormalDist
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 915
SRC = "架空の部品と検査員（作成者が乱数で作成、seed 915）"
N_PART = 2000          # 1回分の部品の数
N_REP = 300            # くり返しの回数
SIZE_SD = 0.6          # 傷の大きさのばらつき（対数の標準偏差）
LIMIT = 1.0            # 本当の不良の線（mm）
BASE_P = 0.05          # 本当の不良の割合（基本）
BASE_EYE = 0.20        # 検査員の見誤り（対数の標準偏差、基本）
INSP = {"A（厳しめ）": 0.85, "B（線どおり）": 1.00, "C（甘め）": 1.20, "D（甘め）": 1.20}
NAMES = list(INSP)


def make_parts(rng, n, p):
    """P(傷 > 1.0mm) = p になる対数正規の傷の大きさ"""
    mu = -SIZE_SD * NormalDist().inv_cdf(1 - p)
    return np.exp(rng.normal(mu, SIZE_SD, n))


def judge(rng, s, eye, insp=INSP):
    return {k: s * np.exp(rng.normal(0, eye, len(s))) > t for k, t in insp.items()}


def kappa(x, y):
    po = (x == y).mean()
    pe = x.mean() * y.mean() + (1 - x.mean()) * (1 - y.mean())
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def one_round(rng, p, eye, insp=INSP):
    s = make_parts(rng, N_PART, p)
    truth = s > LIMIT
    j = judge(rng, s, eye, insp)
    ind = {}
    for k, v in j.items():
        ind[k] = {"reported": v.mean(), "miss": (~v[truth]).mean() if truth.any() else np.nan,
                  "false_reject": v[~truth].mean()}
    pair = {}
    for a, b in combinations(j, 2):
        pair[f"{a[0]}-{b[0]}"] = {"agree": (j[a] == j[b]).mean(), "kappa": kappa(j[a], j[b]),
                                  "both_miss_per_defect": ((~j[a]) & (~j[b]))[truth].mean() if truth.any() else np.nan}
    maj = (j[NAMES[0]].astype(int) + j[NAMES[1]] + j[NAMES[2]]) >= 2
    ind["A・B・Cの多数決"] = {"reported": maj.mean(), "miss": (~maj[truth]).mean(), "false_reject": maj[~truth].mean()}
    return truth.mean(), ind, pair, s, truth, j


def main():
    rng = np.random.default_rng(SEED)

    # 1) 基本の置き方：300回の平均
    ind_rows, pair_rows, true_rate = [], [], []
    for r in range(N_REP):
        tr, ind, pair, *_ = one_round(np.random.default_rng(SEED * 1000 + r), BASE_P, BASE_EYE)
        true_rate.append(tr)
        for k, v in ind.items():
            ind_rows.append({"rep": r, "inspector": k, **v})
        for k, v in pair.items():
            pair_rows.append({"rep": r, "pair": k, **v})
    ind_df = pd.DataFrame(ind_rows).groupby("inspector", sort=False).mean().drop(columns="rep")
    pair_df = pd.DataFrame(pair_rows).groupby("pair", sort=False).mean().drop(columns="rep")
    pair_df = pair_df.round(4)
    pair_df["kappa"] = pair_df["kappa"].round(3)
    ind_df.round(4).to_csv(RES / "inspectors_base.csv")
    pair_df.round(4).to_csv(RES / "pairs_base.csv")

    # 1回分（data）
    tr1, ind1, pair1, s1, truth1, j1 = one_round(rng, BASE_P, BASE_EYE)
    d = pd.DataFrame({"part_id": np.arange(1, N_PART + 1), "flaw_mm": np.round(s1, 4), "true_defect": truth1.astype(int)})
    for k in NAMES:
        d[f"judge_{k[0]}"] = j1[k].astype(int)
    d.to_csv(DATA / "one_round_parts.csv", index=False)

    # 2) 限度見本（本当の不良が分かっている部品）で見逃し率を測ると、何個で読めるか（検査員C）
    ref = {}
    big = make_parts(np.random.default_rng(SEED + 1), 400000, BASE_P)
    defects = big[big > LIMIT]
    goods = big[big <= LIMIT]
    jc_d = judge(np.random.default_rng(SEED + 2), defects, BASE_EYE)
    jc_g = judge(np.random.default_rng(SEED + 3), goods, BASE_EYE)
    true_miss_C = float((~jc_d["C（甘め）"]).mean())
    true_fr_A = float(jc_g["A（厳しめ）"].mean())
    r2 = np.random.default_rng(SEED + 4)
    for k in [10, 30, 100]:
        est = np.array([(~jc_d["C（甘め）"][r2.integers(0, len(defects), k)]).mean() for _ in range(5000)])
        ref[str(k)] = {"p10": round(float(np.quantile(est, .1)), 3), "p90": round(float(np.quantile(est, .9)), 3),
                       "mean": round(float(est.mean()), 3)}

    # 3) 確かめ：不良の割合 × 見誤りの大きさ（9通り）
    grid = []
    for p in [0.01, 0.05, 0.20]:
        for eye in [0.10, 0.20, 0.40]:
            rows_i, rows_p = [], []
            for r in range(100):
                g = np.random.default_rng(SEED * 7 + r + int(p * 1000) * 10 + int(eye * 100))
                _, ind, pair, *_ = one_round(g, p, eye)
                rows_i.append(ind); rows_p.append(pair)
            m = lambda key, sub, rows: float(np.nanmean([x[key][sub] for x in rows]))
            grid.append({"p_defect": p, "eye_sd": eye,
                         "agree_A_C": round(m("A-C", "agree", rows_p), 4), "kappa_A_C": round(m("A-C", "kappa", rows_p), 3),
                         "agree_C_D": round(m("C-D", "agree", rows_p), 4), "kappa_C_D": round(m("C-D", "kappa", rows_p), 3),
                         "agree_A_B": round(m("A-B", "agree", rows_p), 4), "kappa_A_B": round(m("A-B", "kappa", rows_p), 3),
                         "miss_A": round(m("A（厳しめ）", "miss", rows_i), 4), "miss_B": round(m("B（線どおり）", "miss", rows_i), 4),
                         "miss_C": round(m("C（甘め）", "miss", rows_i), 4),
                         "fr_A": round(m("A（厳しめ）", "false_reject", rows_i), 4),
                         "fr_C": round(m("C（甘め）", "false_reject", rows_i), 4),
                         "reported_A": round(m("A（厳しめ）", "reported", rows_i), 4),
                         "reported_C": round(m("C（甘め）", "reported", rows_i), 4),
                         "both_miss_C_D": round(m("C-D", "both_miss_per_defect", rows_p), 4),
                         "both_miss_A_C": round(m("A-C", "both_miss_per_defect", rows_p), 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    cd_gt_ab = int((grid.agree_C_D > grid.agree_A_B).sum())
    cd_missmore = int((grid.both_miss_C_D > grid.both_miss_A_C).sum())
    cd_kappa_gt_ab = int((grid.kappa_C_D > grid.kappa_A_B).sum())
    rng_ = lambda c: [round(float(grid[c].min()), 4), round(float(grid[c].max()), 4)]
    sens = {"n_settings": len(grid), "agree_C_D_gt_A_B": cd_gt_ab, "both_miss_C_D_gt_A_C": cd_missmore,
            "kappa_C_D_gt_A_B": cd_kappa_gt_ab, "kappa_C_D_range": rng_("kappa_C_D"), "kappa_A_B_range": rng_("kappa_A_B"),
            "agree_A_C_range": rng_("agree_A_C"), "kappa_A_C_range": rng_("kappa_A_C"),
            "miss_C_range": rng_("miss_C"), "fr_A_range": rng_("fr_A"),
            "by_p": {str(p): {"agree_A_C": rng_g(grid[grid.p_defect == p], "agree_A_C"),
                              "kappa_A_C": rng_g(grid[grid.p_defect == p], "kappa_A_C"),
                              "miss_C": rng_g(grid[grid.p_defect == p], "miss_C")} for p in [0.01, 0.05, 0.20]},
            "by_eye": {str(e): {"miss_C": rng_g(grid[grid.eye_sd == e], "miss_C"),
                                "kappa_A_C": rng_g(grid[grid.eye_sd == e], "kappa_A_C")} for e in [0.1, 0.2, 0.4]}}

    out = {"settings": {"n_part": N_PART, "n_rep": N_REP, "size_sd_log": SIZE_SD, "limit_mm": LIMIT, "base_p_defect": BASE_P,
                        "base_eye_sd": BASE_EYE, "thresholds_mm": {k[0]: v for k, v in INSP.items()},
                        "reference_reps": 5000, "grid_reps": 100},
           "true_defect_rate_mean": round(float(np.mean(true_rate)), 4),
           "inspectors": ind_df.round(4).reset_index().to_dict("records"),
           "pairs": pair_df.round(4).reset_index().to_dict("records"),
           "reported_ratio_A_over_C": round(float(ind_df.loc["A（厳しめ）", "reported"] / ind_df.loc["C（甘め）", "reported"]), 2),
           "reference_set_C_miss": {"true_miss_C": round(true_miss_C, 3), "true_false_reject_A": round(true_fr_A, 3),
                                    "by_n_defect_samples": ref},
           "one_round": {"true_defects": int(truth1.sum()),
                         "reported": {k[0]: int(j1[k].sum()) for k in NAMES},
                         "agree_A_C": round(float((j1[NAMES[0]] == j1[NAMES[2]]).mean()), 4)},
           "sensitivity": sens}
    json.dump(out, open(RES / "a915_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：検査員ごとの不良と判定した割合・見逃し・誤検出
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.9), sharey=True)
    labels = list(ind_df.index)
    cols = [ORANGE, BLUE, GRAY, GRAY, GREEN]
    for ax, key, ttl, scale in zip(axes, ["reported", "miss", "false_reject"],
                                   ["不良と判定した割合", "見逃し（不良を良品と判定）", "誤検出（良品を不良と判定）"], [1, 1, 1]):
        v = ind_df[key].values * 100
        ax.barh(labels[::-1], v[::-1], color=cols[::-1])
        for i, x in enumerate(v[::-1]):
            if key == "reported":
                ax.text(x - max(v) * 0.02, i, f"{x:.1f}%", va="center", ha="right", fontsize=8.5, color="white", zorder=3)
            else:
                ax.text(x + max(v) * 0.03, i, f"{x:.1f}%", va="center", fontsize=8.5)
        ax.set_xlim(0, max(v) * 1.35); ax.set_title(ttl, fontsize=10.5)
        ax.set_xlabel("%（300回の平均）", fontsize=9)
    axes[0].axvline(BASE_P * 100, color=INK, lw=1, ls="--", zorder=1)
    axes[0].text(BASE_P * 100 + 0.2, 4.45, "本当の不良 5%", fontsize=8)
    ratio = ind_df.loc["A（厳しめ）", "reported"] / ind_df.loc["C（甘め）", "reported"]
    fig.suptitle(f"同じ部品でも、不良と判定した割合は検査員AとCで{ratio:.1f}倍違った（本当の不良5%・部品2,000個）", fontsize=11.5, y=1.02)
    save(fig, "a915_inspectors.png", SRC)

    # 図2：組ごとの一致率・κ・2人とも見逃し
    pr = pair_df.reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.8), sharey=True)
    for ax, key, ttl, mul, fmt in zip(axes, ["agree", "kappa", "both_miss_per_defect"],
                                      ["一致率（%）", "κ（偶然の一致を引いた値）", "2人とも見逃した不良（%）"],
                                      [100, 1, 100], ["{:.1f}", "{:.2f}", "{:.1f}"]):
        v = pr[key].values * mul
        c = [ORANGE if p == "C-D" else BLUE for p in pr["pair"]]
        ax.barh(pr["pair"][::-1], v[::-1], color=c[::-1])
        lo = 80 if key == "agree" else 0
        for i, x in enumerate(v[::-1]):
            ax.text(x + (max(v) * 1.3 - lo) * 0.02, i, fmt.format(x), va="center", fontsize=8.5)
        ax.set_xlim(lo, 101 if key == "agree" else max(v) * 1.3); ax.set_title(ttl, fontsize=10.5)
    axes[0].set_ylabel("検査員の組")
    fig.suptitle("いちばん一致した組（甘めの2人 C-D）は、2人そろって見逃す不良もいちばん多かった", fontsize=11.5, y=1.02)
    save(fig, "a915_pairs.png", SRC)

    # 図3：不良の割合で一致率とκが動く（A-C）
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.6))
    for ax, key, ttl, mul in zip(axes, ["agree_A_C", "kappa_A_C", "miss_C"],
                                 ["A-C の一致率（%）", "A-C のκ", "C の見逃し（%）"], [100, 1, 100]):
        for eye, c in zip([0.1, 0.2, 0.4], [LIGHT, BLUE, INK]):
            g = grid[grid.eye_sd == eye]
            ax.plot(g.p_defect * 100, g[key] * mul, marker="o", color=c, label=f"見誤り {eye}")
        ax.set_xscale("log"); ax.set_xticks([1, 5, 20]); ax.set_xticklabels(["1%", "5%", "20%"])
        ax.set_xlabel("本当の不良の割合"); ax.set_title(ttl, fontsize=10.5)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"不良が少ないほど一致率は高く、κは低く出た。Cの見逃しも置き方で{grid.miss_C.min()*100:.0f}〜{grid.miss_C.max()*100:.0f}%動いた（9通り）",
                 fontsize=11.5, y=1.02)
    fig.tight_layout()
    save(fig, "a915_by_prevalence.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


def rng_g(g, c):
    return [round(float(g[c].min()), 4), round(float(g[c].max()), 4)]


if __name__ == "__main__":
    main()
