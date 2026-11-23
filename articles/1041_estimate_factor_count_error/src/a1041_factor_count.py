"""1041 掛け算でつなぐ要素が増えるほど、概算はどれだけ外れやすくなるのか？（架空のデータ）

架空のA町の「自転車の修理の依頼件数（年）」を、要素の掛け算で概算する。
本当の値（8つの要素と答え）は作成者が置き、見込む人ごとに要素の見込みの誤差を乱数で与える。
見込む要素の数を1〜8個に変えて、答えが本当の値の何倍に外れるかを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1041
SRC = "架空のA町の概算（作成者が乱数で作成、seed 1041）"
# 本当の要素（作成者が置いた値）。掛けると本当の件数になる
FACTORS = [("人口", 30000), ("1÷世帯の人数", 1 / 2.5), ("自転車を持つ世帯の割合", 0.6), ("1世帯の台数", 1.5),
           ("1台が年に修理の要る回数", 0.5), ("自分で直さず店に頼む割合", 0.6), ("町内の店を選ぶ割合", 0.7),
           ("1回の依頼で数える件数", 1.2)]
TRUE = float(np.prod([v for _, v in FACTORS]))
BASE = {"s": 0.4, "rho": 0.0, "b": 0.0}
N_PEOPLE = 200_000
L2 = math.log(2)


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def log_errors(rng, n, k, s, rho, b):
    """n人 × k要素の、見込みの対数の誤差。rho：同じ人の要素どうしに共通する誤差の割合、b：要素ごとの片寄り"""
    z_person = rng.standard_normal((n, 1))
    z = rng.standard_normal((n, k))
    return b + s * (math.sqrt(rho) * z_person + math.sqrt(1 - rho) * z)


def summarize(tot, k, s, rho, b):
    a = np.abs(tot)
    mu, sd = k * b, s * math.sqrt(k * (1 + (k - 1) * rho))
    f_within2 = phi((L2 - mu) / sd) - phi((-L2 - mu) / sd)
    return {"k": k, "within2x": float((a <= L2).mean()), "within2x_formula": f_within2,
            "within3x": float((a <= math.log(3)).mean()), "beyond10x": float((a > math.log(10)).mean()),
            "median_miss_factor": float(np.exp(np.median(a))), "p90_miss_factor": float(np.exp(np.quantile(a, 0.9))),
            "median_ratio": float(np.exp(np.median(tot))), "over_share": float((tot > 0).mean()),
            "sd_log": float(tot.std()), "sd_log_formula": sd}


def run(rng, s, rho, b, n=N_PEOPLE, ks=range(1, 9)):
    e = log_errors(rng, n, 8, s, rho, b)
    cum = np.cumsum(e, axis=1)
    return [summarize(cum[:, k - 1], k, s, rho, b) for k in ks], e


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    cases = {"base": BASE, "corr": dict(BASE, rho=0.3), "bias": dict(BASE, b=0.1)}
    names = {"base": "誤差は要素ごとに別々（基本）", "corr": "同じ人の要素に共通の誤差（rho=0.3）",
             "bias": "要素ごとに1.105倍の片寄り（b=0.1）"}
    rows, e_base = [], None
    for key, kw in cases.items():
        res, e = run(rng, **kw)
        if key == "base":
            e_base = e
        for x in res:
            rows.append({"case": key, "case_name": names[key], **{k_: (r(v) if isinstance(v, float) else v) for k_, v in x.items()}})
    byk = pd.DataFrame(rows)
    byk.to_csv(RES / "by_factor_count.csv", index=False)

    # data：基本の置き方の1,000人分（8要素の見込み÷本当の値と、掛けた答え）
    sub = np.exp(e_base[:1000])
    df = pd.DataFrame(sub.round(4), columns=[f"f{i + 1}_ratio" for i in range(8)])
    df.insert(0, "person", np.arange(1, 1001))
    df["estimate_k8"] = (TRUE * sub.prod(1)).round(1)
    df["ratio_k8"] = sub.prod(1).round(4)
    df.to_csv(DATA / "estimators_k8.csv", index=False)

    # 幅の付け方：要素ごとの90%の幅（本当の値の何倍以内）と、掛けた答えの90%の幅
    s = BASE["s"]
    width = []
    bk = byk[byk.case == "base"].set_index("k")
    for k in range(1, 9):
        width.append({"k": k, "each_factor_90_factor": r(math.exp(1.645 * s), 3),
                      "product_90_factor_sim": r(bk.loc[k, "p90_miss_factor"], 3),
                      "product_90_factor_formula": r(math.exp(1.645 * s * math.sqrt(k)), 3),
                      "multiply_widths_factor": r(math.exp(1.645 * s) ** k, 2)})
    wd = pd.DataFrame(width)
    wd.to_csv(RES / "range_width.csv", index=False)

    # 確かめ：要素1つの誤差 s × 共通の誤差 rho × 片寄り b（27通り）
    grid, j = [], 0
    for s_ in [0.2, 0.4, 0.6]:
        for rho in [0.0, 0.3, 0.6]:
            for b in [0.0, 0.1, 0.2]:
                res, _ = run(np.random.default_rng(SEED * 100 + j), s_, rho, b, n=50_000)
                j += 1
                d = {x["k"]: x for x in res}
                below = [x["k"] for x in res if x["within2x"] < 0.5]
                grid.append({"s": s_, "rho": rho, "b": b, "within2x_k1": r(d[1]["within2x"]), "within2x_k2": r(d[2]["within2x"]),
                             "within2x_k4": r(d[4]["within2x"]), "within2x_k8": r(d[8]["within2x"]),
                             "within2x_k8_formula": r(d[8]["within2x_formula"]),
                             "median_miss_k8": r(d[8]["median_miss_factor"], 3),
                             "first_k_below_50pct": int(below[0]) if below else 0})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    B = bk
    C = byk[byk.case == "corr"].set_index("k")
    Bi = byk[byk.case == "bias"].set_index("k")
    out = {"factors": [{"name": n_, "true": v} for n_, v in FACTORS], "true_answer": r(TRUE, 1),
           "base_setting": BASE, "n_people": N_PEOPLE,
           "note": "見込み＝本当の値×exp(誤差)。誤差＝b＋s×(√rho×人ごとの共通の乱数＋√(1−rho)×要素ごとの乱数)。k個目までを見込み、残りは本当の値を使う",
           "headline": {"each_factor_within2x_pct": r(B.loc[1, "within2x"] * 100, 2),
                        "k8_within2x_pct": r(B.loc[8, "within2x"] * 100, 2),
                        "k8_within2x_formula_pct": r(B.loc[8, "within2x_formula"] * 100, 2),
                        "k4_within2x_pct": r(B.loc[4, "within2x"] * 100, 2),
                        "k8_median_miss": r(B.loc[8, "median_miss_factor"], 2),
                        "k8_p90_miss": r(B.loc[8, "p90_miss_factor"], 2),
                        "k8_beyond10x_pct": r(B.loc[8, "beyond10x"] * 100, 2),
                        "corr_k8_within2x_pct": r(C.loc[8, "within2x"] * 100, 2),
                        "bias_k8_within2x_pct": r(Bi.loc[8, "within2x"] * 100, 2),
                        "bias_k8_median_ratio": r(Bi.loc[8, "median_ratio"], 3),
                        "bias_k8_over_share_pct": r(Bi.loc[8, "over_share"] * 100, 2),
                        "each_factor_90_factor": r(math.exp(1.645 * s), 2),
                        "k8_product_90_formula": r(math.exp(1.645 * s * math.sqrt(8)), 2),
                        "k8_multiply_widths": r(math.exp(1.645 * s) ** 8, 1)},
           "formula_check_max_abs_diff_within2x_pt": r((byk.within2x - byk.within2x_formula).abs().max() * 100, 2),
           "grid_summary": {"n": int(len(g)),
                            "k8_within2x_min": r(g.within2x_k8.min()), "k8_within2x_max": r(g.within2x_k8.max()),
                            "k1_within2x_min": r(g.within2x_k1.min()), "k1_within2x_max": r(g.within2x_k1.max()),
                            "drop_k1_to_k8_min_pt": r(((g.within2x_k1 - g.within2x_k8) * 100).min(), 2),
                            "drop_k1_to_k8_max_pt": r(((g.within2x_k1 - g.within2x_k8) * 100).max(), 2),
                            "n_k8_below_k1": int((g.within2x_k8 < g.within2x_k1).sum()),
                            "n_below50_by_k8": int((g.first_k_below_50pct > 0).sum()),
                            "s02_rho0_b0_k8": r(g[(g.s == 0.2) & (g.rho == 0) & (g.b == 0)].within2x_k8.iloc[0]),
                            "s06_rho06_b02_k8": r(g[(g.s == 0.6) & (g.rho == 0.6) & (g.b == 0.2)].within2x_k8.iloc[0]),
                            "formula_max_abs_diff_k8_pt": r((g.within2x_k8 - g.within2x_k8_formula).abs().max() * 100, 2)},
           "by_factor_count": byk.to_dict("records"), "range_width": wd.to_dict("records")}
    json.dump(out, open(RES / "a1041_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：要素の数と、2倍以内に入る割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cl = {"base": BLUE, "corr": ORANGE, "bias": GREEN}
    for key in cases:
        d = byk[byk.case == key]
        ax.plot(d.k, d.within2x * 100, marker="o", color=cl[key], label=names[key])
    d = byk[byk.case == "base"]
    for x_, y_ in zip(d.k, d.within2x * 100):
        ax.text(x_ + 0.12, y_ + 1.5, f"{y_:.1f}%", fontsize=8, color=BLUE)
    ax.set_ylim(0, 100); ax.set_xticks(range(1, 9))
    ax.set_xlabel("見込んで掛ける要素の数"); ax.set_ylabel("答えが本当の値の2倍以内に入る割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title(f"要素1つなら{B.loc[1, 'within2x']*100:.2f}%が2倍以内でも、8つ掛けると{B.loc[8, 'within2x']*100:.2f}%")
    save(fig, "a1041_within2x.png", SRC)

    # 図2：答えの分布（本当の値の何倍か、対数の目盛り）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cum = np.cumsum(e_base, axis=1)
    bins = np.linspace(-1.6, 1.6, 81)
    for k, c in [(1, GRAY), (4, BLUE), (8, ORANGE)]:
        ax.hist(cum[:, k - 1] / math.log(10), bins=bins, histtype="step", lw=1.6, color=c, density=True, label=f"要素{k}つ")
    for v in [-math.log10(2), math.log10(2)]:
        ax.axvline(v, color=INK, lw=.8, ls="--")
    ticks = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20]
    ax.set_xticks([math.log10(t) for t in ticks]); ax.set_xticklabels([f"{t:g}倍" for t in ticks])
    ax.set_yticks([]); ax.set_xlabel("概算の答え÷本当の値（対数の目盛り。点線は1/2倍と2倍）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("要素が増えると、答えの散らばりは横に広がる")
    save(fig, "a1041_spread.png", SRC)

    # 図3：27通りの、要素1つと8つの2倍以内の割合
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = np.arange(len(g))
    ax.bar(x - 0.2, g.within2x_k1 * 100, 0.4, color=LIGHT, label="要素1つ")
    ax.bar(x + 0.2, g.within2x_k8 * 100, 0.4, color=ORANGE, label="要素8つ")
    ax.set_xticks(x); ax.set_xticklabels([f"{a}/{b}/{c}" for a, b, c in zip(g.s, g.rho, g.b)], rotation=90, fontsize=7)
    ax.set_ylim(0, 105); ax.set_ylabel("2倍以内に入る割合（%）")
    ax.set_xlabel("要素1つの誤差 s ／ 共通の誤差 rho ／ 片寄り b")
    ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=2)
    ax.set_title("置き方27通り：どの通りでも、8つ掛けると2倍以内は減る")
    save(fig, "a1041_grid.png", SRC, y=-0.1)

    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1))
    print(byk.to_string()); print(wd.to_string()); print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
