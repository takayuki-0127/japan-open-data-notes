"""1043 大きく外れた要素が1つあると、ほかを正しくしても全体はどれだけずれるのか？（架空のデータ）

架空のA町の「エアコンの掃除の依頼件数（年）」を、6つの要素の掛け算で概算する。本当の要素と答えは作成者が置く。
① 1つの要素だけを M 倍に外し、ほかの要素の誤差を 0〜0.3 に変えて、答えのずれを数える。
② どの要素にもときどき「大きな外れ」（3〜12倍）が入る置き方で、小さな誤差を減らすのと大きな外れをなくすのとで、
   2倍以内に入る割合がどれだけ変わるかを比べる。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1043
SRC = "架空のA町の概算（作成者が乱数で作成、seed 1043）"
FACTORS = [("人口", 30000), ("1÷世帯の人数", 1 / 2.5), ("1世帯のエアコンの台数", 2.0), ("1台を年に業者に頼む割合", 0.1),
           ("町内の店を選ぶ割合", 0.5), ("1÷1件で掃除する台数", 1 / 1.6)]
TRUE = float(np.prod([v for _, v in FACTORS]))
K = len(FACTORS)
BIG_FACTOR = 3  # ①で外す要素（0から数えて3＝「1台を年に業者に頼む割合」）
MS = [1.5, 2, 3, 5, 10]
SS = [0.0, 0.1, 0.2, 0.3]
BASE = {"p": 0.10, "s": 0.25, "k": 6, "big_lo": 3.0, "big_hi": 12.0}
N = 200_000
L2, L3 = math.log(2), math.log(3)


def part_a(rng, M, s, n=N):
    e = s * rng.standard_normal((n, K))
    e[:, BIG_FACTOR] = math.log(M)  # 外した要素は誤差なしで M 倍
    tot = e.sum(1)
    return {"M": M, "s_others": s, "within2x": float((np.abs(tot) <= L2).mean()),
            "median_ratio": float(np.exp(np.median(tot))), "p10_ratio": float(np.exp(np.quantile(tot, .1))),
            "p90_ratio": float(np.exp(np.quantile(tot, .9)))}


def errors_b(rng, n, k, p, s, big_lo, big_hi):
    small = s * rng.standard_normal((n, k))
    has_big = rng.random((n, k)) < p
    mag = rng.uniform(math.log(big_lo), math.log(big_hi), (n, k)) * rng.choice([-1, 1], (n, k))
    return small, has_big, mag


def score(tot):
    a = np.abs(tot)
    return {"within2x": float((a <= L2).mean()), "beyond3x": float((a > L3).mean()),
            "median_miss": float(np.exp(np.median(a)))}


def part_b(rng, p, s, k, big_lo=3.0, big_hi=12.0, n=N):
    small, has_big, mag = errors_b(rng, n, k, p, s, big_lo, big_hi)
    big = np.where(has_big, mag, 0.0)
    out = {}
    out["as_is"] = score((small + big).sum(1))
    out["half_small"] = score((small / 2 + big).sum(1))
    out["no_small"] = score(big.sum(1))
    out["no_big"] = score(small.sum(1))
    any_big = has_big.any(1)
    tot = (small + big).sum(1)
    far = np.abs(tot) > L3
    out["share_with_big"] = float(any_big.mean())
    out["share_with_big_formula"] = 1 - (1 - p) ** k
    out["far_with_big"] = float(any_big[far].mean()) if far.any() else 0.0
    out["within2x_given_big"] = float((np.abs(tot[any_big]) <= L2).mean())
    out["within2x_given_nobig"] = float((np.abs(tot[~any_big]) <= L2).mean())
    return out, small, has_big, mag


def r(x, d=4):
    return round(float(x), d)


NAMES = {"as_is": "そのまま", "half_small": "小さな誤差を半分に", "no_small": "小さな誤差を0に（大きな外れは残る）",
         "no_big": "大きな外れをなくす（小さな誤差は残る）"}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # ① 1つだけ M 倍に外す
    A = pd.DataFrame([part_a(rng, M, s) for M in MS for s in SS])
    A = A.round(4)
    A.to_csv(RES / "one_factor_off.csv", index=False)

    # ② 大きな外れがときどき入る（基本）
    b, small, has_big, mag = part_b(np.random.default_rng(SEED + 1), BASE["p"], BASE["s"], BASE["k"])
    fixes = pd.DataFrame([{"fix": k_, "fix_name": NAMES[k_], **{a: r(v) for a, v in b[k_].items()}} for k_ in NAMES])
    fixes.to_csv(RES / "fixes_base.csv", index=False)

    # data：基本の置き方の1,000人分
    m = 1000
    est = np.exp(small[:m] + np.where(has_big[:m], mag[:m], 0.0))
    df = pd.DataFrame(est.round(4), columns=[f"f{i + 1}_ratio" for i in range(K)])
    df.insert(0, "person", np.arange(1, m + 1))
    df["n_big_errors"] = has_big[:m].sum(1)
    df["estimate"] = (TRUE * est.prod(1)).round(1)
    df["ratio"] = est.prod(1).round(4)
    df.to_csv(DATA / "estimators.csv", index=False)

    # 確かめ：大きな外れの確率 p × 小さな誤差 s × 要素の数 k（27通り）
    grid, j = [], 0
    for p in [0.03, 0.10, 0.20]:
        for s in [0.15, 0.25, 0.40]:
            for k in [4, 6, 8]:
                o, *_ = part_b(np.random.default_rng(SEED * 100 + j), p, s, k, n=50_000)
                j += 1
                grid.append({"p": p, "s": s, "k": k, "as_is": r(o["as_is"]["within2x"]), "half_small": r(o["half_small"]["within2x"]),
                             "no_small": r(o["no_small"]["within2x"]), "no_big": r(o["no_big"]["within2x"]),
                             "far_with_big": r(o["far_with_big"]), "share_with_big": r(o["share_with_big"])})
    g = pd.DataFrame(grid)
    g["gain_no_big_pt"] = ((g.no_big - g.as_is) * 100).round(2)
    g["gain_no_small_pt"] = ((g.no_small - g.as_is) * 100).round(2)
    g.to_csv(RES / "grid.csv", index=False)

    a3 = A[(A.M == 3)].set_index("s_others")
    out = {"factors": [{"name": n_, "true": v} for n_, v in FACTORS], "true_answer": r(TRUE, 1), "big_factor": FACTORS[BIG_FACTOR][0],
           "base_setting_b": BASE, "n": N,
           "note": "見込み＝本当の値×exp(誤差)。②の誤差＝s×正規の乱数＋（確率 p で）±log(3〜12倍の一様)",
           "headline": {"M3_s0_within2x_pct": r(a3.loc[0.0, "within2x"] * 100, 2),
                        "M3_s02_within2x_pct": r(a3.loc[0.2, "within2x"] * 100, 2),
                        "M3_s02_median_ratio": r(a3.loc[0.2, "median_ratio"], 3),
                        "M3_s02_p10_ratio": r(a3.loc[0.2, "p10_ratio"], 3), "M3_s02_p90_ratio": r(a3.loc[0.2, "p90_ratio"], 3),
                        "M2_s0_within2x_pct": r(A[(A.M == 2) & (A.s_others == 0)].within2x.iloc[0] * 100, 2),
                        "M2_s02_within2x_pct": r(A[(A.M == 2) & (A.s_others == 0.2)].within2x.iloc[0] * 100, 2),
                        "M10_s03_within2x_pct": r(A[(A.M == 10) & (A.s_others == 0.3)].within2x.iloc[0] * 100, 2),
                        "b_as_is_within2x_pct": r(b["as_is"]["within2x"] * 100, 2),
                        "b_half_small_within2x_pct": r(b["half_small"]["within2x"] * 100, 2),
                        "b_no_small_within2x_pct": r(b["no_small"]["within2x"] * 100, 2),
                        "b_no_big_within2x_pct": r(b["no_big"]["within2x"] * 100, 2),
                        "b_share_with_big_pct": r(b["share_with_big"] * 100, 2),
                        "b_share_with_big_formula_pct": r(b["share_with_big_formula"] * 100, 2),
                        "b_far_with_big_pct": r(b["far_with_big"] * 100, 2),
                        "b_within2x_given_big_pct": r(b["within2x_given_big"] * 100, 2),
                        "b_within2x_given_nobig_pct": r(b["within2x_given_nobig"] * 100, 2),
                        "b_as_is_beyond3x_pct": r(b["as_is"]["beyond3x"] * 100, 2),
                        "b_no_small_beyond3x_pct": r(b["no_small"]["beyond3x"] * 100, 2)},
           "grid_summary": {"n": int(len(g)),
                            "rows_no_big_beats_no_small": int((g.no_big > g.no_small).sum()),
                            "rows_no_small_beats_no_big": g[g.no_small > g.no_big][["p", "s", "k"]].to_dict("records"),
                            "rows_no_small_below_as_is": int((g.no_small < g.as_is).sum()),
                            "rows_no_small_below_as_is_detail": g[g.no_small < g.as_is][["p", "s", "k"]].to_dict("records"),
                            "gain_no_big_min_pt": r(g.gain_no_big_pt.min(), 2), "gain_no_big_max_pt": r(g.gain_no_big_pt.max(), 2),
                            "gain_no_small_min_pt": r(g.gain_no_small_pt.min(), 2), "gain_no_small_max_pt": r(g.gain_no_small_pt.max(), 2),
                            "far_with_big_min": r(g.far_with_big.min()), "far_with_big_max": r(g.far_with_big.max()),
                            "p01_rows_far_with_big_min": r(g[g.p == 0.10].far_with_big.min()),
                            "p01_rows_far_with_big_max": r(g[g.p == 0.10].far_with_big.max())},
           "fixes_base": {k_: {a: r(v) for a, v in b[k_].items()} for k_ in NAMES},
           "one_factor_off": A.to_dict("records")}
    json.dump(out, open(RES / "a1043_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1つを M 倍に外したときの、2倍以内に入る割合（ほかの要素の誤差ごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cl = {0.0: INK, 0.1: GRAY, 0.2: BLUE, 0.3: ORANGE}
    for s, gg in A.groupby("s_others"):
        lab = "ほかの要素は正しい（誤差0）" if s == 0 else f"ほかの要素の誤差 s={s}"
        ax.plot(gg.M, gg.within2x * 100, marker="o", color=cl[s], label=lab)
    ax.set_xscale("log"); ax.set_xticks(MS); ax.set_xticklabels([f"{m:g}倍" for m in MS]); ax.minorticks_off()
    ax.set_ylim(0, 105); ax.set_xlabel("1つの要素の外れ（本当の値の何倍に見込んだか、対数の目盛り）")
    ax.set_ylabel("答えが本当の値の2倍以内に入る割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title(f"3倍外れた要素が1つあると、ほかを正しくしても2倍以内は{a3.loc[0.0, 'within2x']*100:.0f}%")
    save(fig, "a1043_one_off.png", SRC)

    # 図2：基本の置き方で、直し方ごとの2倍以内の割合（0から）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    vals = [b[k_]["within2x"] * 100 for k_ in NAMES]
    y = np.arange(len(vals))[::-1]
    ax.barh(y, vals, color=[GRAY, LIGHT, BLUE, ORANGE])
    for yi, v in zip(y, vals):
        ax.text(v + 1, yi, f"{v:.2f}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(list(NAMES.values()), fontsize=9)
    ax.set_xlim(0, 105); ax.set_xlabel("答えが本当の値の2倍以内に入る割合（%）")
    ax.set_title("基本の置き方では、大きな外れをなくすほうが小さな誤差を0にするより効く（27通り中9通りは逆）", fontsize=11)
    save(fig, "a1043_fixes.png", SRC)

    # 図3：27通りの、2つの直し方の効き目
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    clp = {0.03: GRAY, 0.10: BLUE, 0.20: ORANGE}
    for p, gg in g.groupby("p"):
        ax.scatter(gg.gain_no_small_pt, gg.gain_no_big_pt, color=clp[p], s=30, label=f"大きな外れの確率 {p:g}")
    lo = min(g.gain_no_small_pt.min(), 0) - 2; hi = max(g.gain_no_big_pt.max(), g.gain_no_small_pt.max()) + 3
    ax.plot([lo, hi], [lo, hi], color=INK, lw=.8, ls="--"); ax.text(hi * .55, hi * .47, "効き目が同じ", fontsize=8)
    ax.axhline(0, color=GRAY, lw=.6); ax.axvline(0, color=GRAY, lw=.6)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("小さな誤差を0にしたときの増え（ポイント）"); ax.set_ylabel("大きな外れをなくしたときの増え（ポイント）")
    ax.legend(frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1.0, 0.18))
    ax.set_title("置き方27通り：2倍以内に入る割合の増え")
    save(fig, "a1043_grid.png", SRC)

    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1))
    print(A.to_string()); print(fixes.to_string()); print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
