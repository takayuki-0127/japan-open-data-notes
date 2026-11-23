"""1048 途中の数字を1桁に丸めて計算すると、答えは何倍まで外れるのか？（架空のデータ）

架空の概算で、掛け算でつなぐ要素の値を作成者が乱数で置き（頭の数字は「対数で一様」＝ベンフォードの形）、
要素ごとに上から1桁（有効数字1桁、四捨五入）に丸めてから掛けた答えと、丸めずに掛けた答えを比べる。
比べる丸め方：有効数字1桁・有効数字2桁・10の累乗だけ（桁だけ残す）。
外れ（何倍）は、丸めた答えが丸めない答えの何倍、または何分の1か（1以上の倍率）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1048
SRC = "架空の概算の要素（作成者が乱数で作成、seed 1048）"
FACT = {"households": 12000, "share_ac": 0.9, "units": 2.2, "rate": 0.08}
N = 200000
KS = [1, 2, 3, 4, 5, 6, 8]
SIG_F = 0.35   # 要素の見込みの誤差（対数の標準偏差）


def round_sig(x, d=1):
    e = np.floor(np.log10(x))
    m = x / 10 ** e                                   # 1以上10未満
    q = np.floor(m * 10 ** (d - 1) + 0.5) / 10 ** (d - 1)   # 四捨五入
    return q * 10 ** e


def round_pow10(x):
    return 10 ** np.floor(np.log10(x) + 0.5)


def mantissa(rng, shape, kind="log"):
    if kind == "log":
        m = 10 ** rng.uniform(0, 1, shape)
    elif kind == "uniform":
        m = rng.uniform(1, 10, shape)
    elif kind == "small_lead":
        m = rng.uniform(1, 3, shape)
    elif kind == "near_1_5":
        m = rng.uniform(1.2, 1.8, shape)
    return m * 10 ** rng.integers(-2, 5, shape).astype(float)


def summarize(ratio):
    lr = np.log(ratio); miss = np.exp(np.abs(lr))
    return {"median_miss_times": round(float(np.median(miss)), 4),
            "p90_miss_times": round(float(np.quantile(miss, .9)), 4),
            "p99_miss_times": round(float(np.quantile(miss, .99)), 4),
            "max_miss_times": round(float(miss.max()), 4),
            "over_1_2_pct": round(float((miss > 1.2).mean()) * 100, 2),
            "over_1_5_pct": round(float((miss > 1.5).mean()) * 100, 2),
            "median_ratio": round(float(np.median(ratio)), 4),
            "geo_mean_ratio": round(float(np.exp(lr.mean())), 4)}


WORST = {"sig1": 1.5, "sig2": 1.05, "pow10": 10 ** 0.5}
METHODS = {"sig1": lambda x: round_sig(x, 1), "sig2": lambda x: round_sig(x, 2), "pow10": round_pow10}
NAMES = {"sig1": "有効数字1桁", "sig2": "有効数字2桁", "pow10": "10の累乗だけ"}


def main():
    rng = np.random.default_rng(SEED)

    # 0) 例：A町のエアコンの掃除の件数
    vals = np.array(list(FACT.values()), float)
    ex = {"factors": FACT, "exact": round(float(vals.prod()), 1), "rounded_values": [float(v) for v in round_sig(vals, 1)],
          "rounded_product": round(float(round_sig(vals, 1).prod()), 1)}
    ex["ratio"] = round(ex["rounded_product"] / ex["exact"], 4)
    ex["miss_times"] = round(ex["exact"] / ex["rounded_product"], 4)

    # 1) 要素の数と丸め方ごとの外れ
    rows = []
    x_all = mantissa(rng, (N, max(KS)))
    for meth, f in METHODS.items():
        r_each = f(x_all) / x_all
        for k in KS:
            ratio = r_each[:, :k].prod(1)
            d = {"method": NAMES[meth], "factors": k, **summarize(ratio),
                 "worst_formula_times": round(WORST[meth] ** k, 4)}
            rows.append(d)
    # 最後の答えも1桁に丸める（4要素）
    prod_r = round_sig(round_sig(x_all[:, :4], 1).prod(1), 1) / x_all[:, :4].prod(1)
    final_also = {"factors": 4, **summarize(prod_r)}
    byk = pd.DataFrame(rows)
    byk.to_csv(RES / "by_factors.csv", index=False)

    # 1要素の丸めの比：頭の数字ごとの最悪
    m = np.linspace(1, 9.9999, 90001)
    r1 = round_sig(m, 1) / m
    one = {"max_up_times": round(float(r1.max()), 4), "max_up_at": round(float(m[r1.argmax()]), 3),
           "max_down_times": round(float(1 / r1.min()), 4), "max_down_at": round(float(m[r1.argmin()]), 3)}

    # 2) 要素の見込みの誤差と比べる（4要素）
    e = np.exp(rng.normal(0, SIG_F, (N, 4)))
    x4 = x_all[:, :4]; est = x4 * e
    err_rows = []
    for nm, ratio in [("見込みの誤差だけ", est.prod(1) / x4.prod(1)),
                      ("見込みの誤差＋有効数字1桁", round_sig(est, 1).prod(1) / x4.prod(1)),
                      ("見込みの誤差＋10の累乗だけ", round_pow10(est).prod(1) / x4.prod(1)),
                      ("有効数字1桁の丸めだけ", round_sig(x4, 1).prod(1) / x4.prod(1))]:
        err_rows.append({"case": nm, **summarize(ratio)})
    err = pd.DataFrame(err_rows)
    err.to_csv(RES / "vs_estimation_error.csv", index=False)

    # 3) 確かめ：頭の数字の分布と、見込みの誤差の大きさ
    s_rows = []
    kinds = {"log": "対数で一様（基本）", "uniform": "1〜10で一様", "small_lead": "1〜3に集まる", "near_1_5": "1.2〜1.8に集まる"}
    for kd, kn in kinds.items():
        xx = mantissa(np.random.default_rng(SEED * 10 + len(kd)), (N, 4), kd)
        rr = round_sig(xx, 1) / xx
        s_rows.append({"what": "頭の数字の分布", "value": kn, **summarize(rr.prod(1))})
    for sf in [0.1, 0.2, 0.35, 0.5]:
        r2 = np.random.default_rng(SEED * 100 + int(sf * 100))
        xx = mantissa(r2, (N, 4)); ee = xx * np.exp(r2.normal(0, sf, (N, 4)))
        a = summarize(ee.prod(1) / xx.prod(1)); b = summarize(round_sig(ee, 1).prod(1) / xx.prod(1))
        s_rows.append({"what": "見込みの誤差（対数の標準偏差）", "value": f"{sf}（誤差だけ）", **a})
        s_rows.append({"what": "見込みの誤差（対数の標準偏差）", "value": f"{sf}（＋1桁に丸め）", **b})
    sens = pd.DataFrame(s_rows)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    pd.DataFrame({"x1": x_all[:2000, 0], "x2": x_all[:2000, 1], "x3": x_all[:2000, 2], "x4": x_all[:2000, 3],
                  "exact_product": x_all[:2000, :4].prod(1),
                  "rounded1_product": round_sig(x_all[:2000, :4], 1).prod(1)}
                 ).to_csv(DATA / "factors_4_2000.csv", index=False, float_format="%.6g")

    s1 = sens[sens.what == "頭の数字の分布"]
    out = {"factor_error_sd_log": SIG_F, "factor_error_times_1sd": round(float(np.exp(SIG_F)), 3), "example_A": ex, "one_factor_sig1": one, "by_factors": byk.to_dict("records"),
           "final_also_rounded_4": final_also, "vs_estimation_error_4": err.to_dict("records"),
           "sensitivity": sens.to_dict("records"),
           "range_lead_digit_4factors": {"p90_miss_times": [float(s1.p90_miss_times.min()), float(s1.p90_miss_times.max())],
                                         "over_1_2_pct": [float(s1.over_1_2_pct.min()), float(s1.over_1_2_pct.max())],
                                         "max_miss_times": [float(s1.max_miss_times.min()), float(s1.max_miss_times.max())]}}
    json.dump(out, open(RES / "a1048_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：要素の数と外れ（有効数字1桁）
    d = byk[byk.method == "有効数字1桁"]
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(d.factors, d.worst_formula_times, color=GRAY, ls="--", marker="o", label="最悪（1.5の要素の数乗、式どおり）")
    ax.plot(d.factors, d.p99_miss_times, color=ORANGE, marker="o", lw=2, label="99%の回はこれ以内")
    ax.plot(d.factors, d.p90_miss_times, color=BLUE, marker="o", lw=2, label="90%の回はこれ以内")
    ax.plot(d.factors, d.median_miss_times, color=GREEN, marker="o", lw=2, label="半分の回はこれ以内")
    for _, r in d.iterrows():
        if r.factors in (4, 8):
            ax.text(r.factors, r.p90_miss_times * 1.12, f"{r.p90_miss_times:.2f}倍", fontsize=9, ha="center", color=BLUE)
    ax.set_yscale("log"); ax.set_yticks([1, 1.2, 1.5, 2, 3, 5, 10, 20]); ax.set_yticklabels(["1", "1.2", "1.5", "2", "3", "5", "10", "20"])
    ax.set_xlabel("掛ける要素の数"); ax.set_ylabel("丸めない答えからの外れ（何倍、対数の目盛り）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("1桁に丸めると最悪は1.5の要素の数乗、ふつうはずっと小さい")
    save(fig, "a1048_by_factors.png", SRC, y=-0.04)

    # 図2：丸め方ごと（4要素）の90%点
    d4 = byk[byk.factors == 4].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    y = np.arange(len(d4))
    ax.hlines(y, 1, d4.worst_formula_times, color=LIGHT, lw=1)
    ax.scatter(d4.median_miss_times, y, color=GREEN, s=45, zorder=3, label="半分の回はこれ以内")
    ax.scatter(d4.p90_miss_times, y, color=BLUE, s=45, zorder=3, label="90%の回はこれ以内")
    ax.scatter(d4.worst_formula_times, y, color=GRAY, marker="s", s=45, zorder=3, label="最悪（式どおり）")
    def _fmt(v):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    for i, r in d4.iterrows():
        if r.p90_miss_times < 1.2:   # 1に近い点は、軸に重ならないよう右に置く
            ax.text(r.worst_formula_times * 1.12, i + 0.32, f"90%：{_fmt(r.p90_miss_times)}倍", ha="left", fontsize=9, color=BLUE)
        else:
            ax.text(r.p90_miss_times, i + 0.32, f"{_fmt(r.p90_miss_times)}倍", ha="center", fontsize=9, color=BLUE)
        ax.text(r.worst_formula_times * 1.08, i - 0.22, f"{_fmt(r.worst_formula_times)}倍", ha="center", fontsize=9, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(d4.method); ax.set_ylim(2.7, -0.6)
    ax.set_xscale("log"); ax.set_xlim(0.9, 200)
    ax.set_xticks([1, 1.2, 1.5, 2, 5, 10, 50, 100]); ax.set_xticklabels(["1", "1.2", "1.5", "2", "5", "10", "50", "100"])
    ax.minorticks_off()
    ax.set_xlabel("丸めない答えからの外れ（何倍、4つの要素を掛けたとき）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title(f"有効数字1桁なら90%の回は{d4.p90_miss_times[0]:.2f}倍以内、桁だけ残すと{d4.p90_miss_times[2]:.2f}倍")
    save(fig, "a1048_methods.png", SRC, y=-0.04)

    # 図3：見込みの誤差と比べる（外れは1倍が「ずれなし」なので、1から始まる対数の目盛りの点で描く）
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    y = np.arange(len(err))
    ax.hlines(y, 1, err.p90_miss_times, color=LIGHT, lw=1)
    ax.scatter(err.median_miss_times, y, color=GREEN, s=45, zorder=3, label="外れの中央値")
    ax.scatter(err.p90_miss_times, y, color=BLUE, s=45, zorder=3, label="90%の回はこれ以内")
    for i, r in err.iterrows():
        ax.text(r.median_miss_times, i - 0.25, f"{r.median_miss_times:.3f}倍", ha="center", fontsize=9, color=GREEN)
        ax.text(r.p90_miss_times * 1.06, i, f"{r.p90_miss_times:.2f}倍", va="center", ha="left", fontsize=9, color=BLUE)
    ax.set_yticks(y); ax.set_yticklabels(err.case); ax.set_ylim(len(err) - 0.4, -0.7)
    ax.set_xscale("log"); ax.set_xlim(1, 25)
    ax.set_xticks([1, 1.2, 1.5, 2, 3, 5, 10, 20]); ax.set_xticklabels(["1", "1.2", "1.5", "2", "3", "5", "10", "20"])
    ax.minorticks_off()
    ax.set_xlabel("本当の答えからの外れ（何倍、対数の目盛り。1倍がずれなし。4つの要素を掛けたとき）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("見込みの誤差（1つ約1.42倍）に比べ、1桁の丸めの足す外れは小さい")
    save(fig, "a1048_vs_error.png", SRC, y=-0.04)
    print(json.dumps({k: out[k] for k in ["example_A", "one_factor_sig1", "final_also_rounded_4", "range_lead_digit_4factors"]}, ensure_ascii=False, indent=1))
    print(byk.to_string()); print(err.to_string()); print(sens.to_string())


if __name__ == "__main__":
    main()
