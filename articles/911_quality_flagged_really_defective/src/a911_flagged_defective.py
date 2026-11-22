"""911 検査で「不良」と出た品物は、本当に不良なのか？（見逃しと誤検出）（架空のデータ）

架空の工場の部品の長さの検査。本当の長さは平均50.00mmの正規分布、規格は50.00±0.30mm。
測った値は「本当の長さ＋測りの誤差」。測った値が規格の外なら「不良」と判定する。
測りの誤差は、品物ごとに毎回同じ向きに出る分（置き方・反りなど）と、測るたびに変わる分に分けて置く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 911
SRC = "架空の工場の部品の長さの検査（作成者が乱数で作成、seed 911）"
MU, TOL = 50.0, 0.30
BASE_DEFECT, BASE_ME, BASE_SHARE = 0.01, 0.03, 0.0
N_ITEMS = 1_000_000


def sigma_for(defect_rate):
    """規格の外に出る割合が defect_rate になる、本当の長さの標準偏差"""
    return TOL / norm.ppf(1 - defect_rate / 2)


def make(rng, defect_rate, me, share, n=N_ITEMS):
    sp = sigma_for(defect_rate)
    L = rng.normal(MU, sp, n)
    b = rng.normal(0, me * np.sqrt(share), n)          # 品物ごとに毎回同じ向きの誤差
    m1 = L + b + rng.normal(0, me * np.sqrt(1 - share), n)
    m2 = L + b + rng.normal(0, me * np.sqrt(1 - share), n)  # 測り直したときの値
    return L, m1, m2


def out_spec(x):
    return np.abs(x - MU) > TOL


def stats(L, m1, m2):
    d = out_spec(L)
    f1 = out_spec(m1)
    f2 = f1 & out_spec(m2)
    fp = f1 & ~d
    near = np.abs(L - MU) > TOL - 0.05
    return {
        "defect_rate": round(float(d.mean()), 5),
        "flag_rate": round(float(f1.mean()), 5),
        "ppv": round(float(d[f1].mean()), 4),
        "good_to_defect_ratio": round(float((~d).mean() / d.mean()), 2),
        "good_share_of_flagged": round(float((~d)[f1].mean()), 4),
        "miss_rate": round(float((~f1[d]).mean()), 4),
        "accuracy": round(float((f1 == d).mean()), 5),
        "false_pos_per_1000": round(float(fp.mean() * 1000), 3),
        "false_pos_within_0_05mm": round(float(near[fp].mean()), 4),
        "ppv_after_recheck": round(float(d[f2].mean()), 4) if f2.any() else None,
        "miss_rate_after_recheck": round(float((~f2[d]).mean()), 4),
        "good_flagged_after_recheck_per_1000": round(float((f2 & ~d).mean() * 1000), 3),
    }


def ppv_formula(defect_rate, me):
    """数値積分で求めた判定の当たり（品物ごとの誤差なしのとき）"""
    sp = sigma_for(defect_rate)
    x = np.linspace(MU - 8 * sp, MU + 8 * sp, 400001)
    dens = norm.pdf(x, MU, sp)
    pflag = norm.cdf((x - (MU + TOL)) / me) + norm.cdf(((MU - TOL) - x) / me)
    d = out_spec(x)
    tp = np.trapezoid(dens * pflag * d, x)
    fl = np.trapezoid(dens * pflag, x)
    miss = 1 - tp / np.trapezoid(dens * d, x)
    return round(float(tp / fl), 4), round(float(miss), 4)


def main():
    t0 = time.time()
    out = {"settings": {"mean_mm": MU, "tolerance_mm": TOL, "base_defect_rate": BASE_DEFECT,
                        "base_true_sd_mm": round(sigma_for(BASE_DEFECT), 4), "base_measure_sd_mm": BASE_ME,
                        "base_persistent_share": BASE_SHARE, "items_per_setting": N_ITEMS}}
    k = 0
    # 1) 基本の置き方
    k += 1
    L, m1, m2 = make(np.random.default_rng(SEED * 100 + k), BASE_DEFECT, BASE_ME, BASE_SHARE)
    base = stats(L, m1, m2)
    base["formula_ppv"], base["formula_miss"] = ppv_formula(BASE_DEFECT, BASE_ME)
    d, f1 = out_spec(L), out_spec(m1)
    base["per_10000"] = {"flagged": int(round(f1.mean() * 10000)), "true_defect_flagged": int(round((f1 & d).mean() * 10000)),
                         "good_flagged": int(round((f1 & ~d).mean() * 10000)), "defect_missed": int(round((~f1 & d).mean() * 10000)),
                         "defects": int(round(d.mean() * 10000))}
    out["base"] = base
    ex = pd.DataFrame({"part_id": np.arange(1, 5001), "true_length": L[:5000].round(4), "measured1": m1[:5000].round(4),
                       "measured2": m2[:5000].round(4), "true_defect": d[:5000].astype(int),
                       "flagged1": f1[:5000].astype(int), "flagged_after_recheck": (f1 & out_spec(m2))[:5000].astype(int)})
    ex.to_csv(DATA / "parts_example.csv", index=False)

    # 2) 不良率と測りの誤差を変える
    grid = []
    for dr in [0.002, 0.01, 0.05]:
        for me in [0.01, 0.03, 0.06]:
            k += 1
            s = stats(*make(np.random.default_rng(SEED * 100 + k), dr, me, 0.0))
            fp, fm = ppv_formula(dr, me)
            grid.append({"defect_rate_pct": dr * 100, "measure_sd_mm": me, **s, "formula_ppv": fp, "formula_miss": fm})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "by_rate_and_error.csv", index=False)
    out["by_rate_and_error"] = grid
    out["ppv_range"] = [float(g.ppv.min()), float(g.ppv.max())]
    out["accuracy_range"] = [float(g.accuracy.min()), float(g.accuracy.max())]
    out["max_abs_sim_minus_formula_ppv"] = round(float((g.ppv - g.formula_ppv).abs().max()), 4)

    # 3) 測り直し：誤差のうち品物ごとに同じ向きの分の割合を変える
    rc = []
    for share in [0.0, 0.5, 0.9]:
        for me in [0.03, 0.06]:
            k += 1
            s = stats(*make(np.random.default_rng(SEED * 100 + k), BASE_DEFECT, me, share))
            rc.append({"persistent_share": share, "measure_sd_mm": me, **s})
    r = pd.DataFrame(rc)
    r.to_csv(RES / "recheck.csv", index=False)
    out["recheck"] = rc
    json.dump(out, open(RES / "a911_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：「不良」と出た品物の本当の長さ
    fl = out_spec(m1)
    dev = L[fl] - MU
    a = np.abs(dev)
    fig, ax = plt.subplots(figsize=(7.4, 4.1))
    bins = np.linspace(0.15, 0.60, 46)
    ax.hist(a[a <= TOL], bins=bins, color=ORANGE, label="本当は規格の中（良品）")
    ax.hist(a[a > TOL], bins=bins, color=BLUE, label="本当に規格の外（不良）")
    ax.axvline(TOL, color=INK, lw=1, ls="--")
    ax.text(0.16, ax.get_ylim()[1] * .93, "点線：規格の端（±0.30mm）", fontsize=8.5)
    ax.set_xlabel("「不良」と出た品物の、本当の長さの中心からのずれ（mm、上下まとめて）")
    ax.set_ylabel("品物の数（100万個のうち）")
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1.0, 0.85))
    ax.set_title("「不良」と出た良品は、ほとんどが規格の端のすぐ内側")
    save(fig, "a911_flagged_true_length.png", SRC)

    # 図2：不良率と測りの誤差ごとの当たり
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(3); w = .27
    for j, (me, col) in enumerate(zip([0.01, 0.03, 0.06], [LIGHT, BLUE, ORANGE])):
        s = g[g.measure_sd_mm == me]
        ax.bar(x + (j - 1) * w, s.ppv * 100, w, color=col, label=f"測りの誤差 {me}mm")
        for i, v in enumerate(s.ppv):
            ax.text(i + (j - 1) * w, v * 100 + 1.2, f"{v*100:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(["本当の不良率 0.2%", "1%（基本）", "5%"])
    ax.set_ylabel("「不良」と出た品物のうち、本当に不良の割合（%）"); ax.set_ylim(0, 112)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
    ax.set_title("不良が少ない工程ほど、「不良」判定の当たりは下がる")
    save(fig, "a911_ppv_grid.png", SRC)

    # 図3：測り直しの効き方
    s3 = r[r.measure_sd_mm == 0.03]
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    x = np.arange(len(s3)); w = .38
    ax.bar(x - w / 2, s3.ppv * 100, w, color=GRAY, label="1回の判定")
    ax.bar(x + w / 2, s3.ppv_after_recheck * 100, w, color=BLUE, label="「不良」を測り直し、2回とも外なら不良")
    for i, (u, v) in enumerate(zip(s3.ppv, s3.ppv_after_recheck)):
        ax.text(i - w / 2, u * 100 + 1.2, f"{u*100:.0f}%", ha="center", fontsize=8.5)
        ax.text(i + w / 2, v * 100 + 1.2, f"{v*100:.0f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"誤差のうち品物ごとに\n同じ向きの分 {int(v*100)}%" for v in s3.persistent_share])
    ax.set_ylabel("本当に不良の割合（%）"); ax.set_ylim(0, 115)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=2)
    ax.set_title("測り直しは、毎回同じ向きに出る誤差には効きにくい（測りの誤差0.03mm）")
    save(fig, "a911_recheck.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
