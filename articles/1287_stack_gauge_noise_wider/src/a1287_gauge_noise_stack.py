"""1287 部品の寸法の記録に測りのばらつきがまざっていると、記録から見込んだ組み立て品の幅は、本当の幅よりどれだけ広く出るのか？（架空のデータ）

架空の引き出しの部品4つ（A〜D）を高さ方向に重ねる。組み立て品の高さ＝4つの部品の寸法の和。
部品ごとの本当の寸法のばらつき（標準偏差）を作成者が置き、記録の値＝本当の寸法＋測りのばらつき。
測りのばらつき＝くり返しのばらつき（毎回ちがう）＋日ごとのずれ（その日に測ったものに共通）。
記録から部品ごとの標準偏差を出し、二乗で足して組み立て品の標準偏差を見込む。
本当の組み立て品の標準偏差（作成者が置いた値を二乗で足したもの）と比べる。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1287
SRC = "架空の引き出しの部品の寸法（作成者が乱数で作成、seed 1287）"
BASE_SD = [0.05, 0.04, 0.06, 0.03]       # 部品A〜Dの本当の標準偏差（mm）
NAMES = ["A", "B", "C", "D"]
NOMINAL = [18.00, 120.00, 18.00, 6.00]   # 名目の寸法（mm）
TOL = 0.25                               # 組み立て品の許容差 ±0.25mm
N_REC = 200                              # 部品1種類あたりの記録の数
DAYS = 20                                # 記録は20日に分けて測る（1日10個）
N_REP = 10                               # 2回測りの確かめに使う部品の数（1種類あたり）
TRIALS = 2000
GRID_TRIALS = 1000
GM = [0.01, 0.02, 0.03, 0.05]            # 測りのばらつき（標準偏差、mm）
SHARES = [0.0, 0.3, 0.6]                 # 測りのばらつきの分散のうち日ごとのずれの割合
NPARTS = [2, 4, 8]


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def out_rate(sd, tol=TOL):
    return 2 * (1 - ncdf(tol / sd))


def sds_for(n):
    return [BASE_SD[i % 4] for i in range(n)]


def trial_batch(rng, sds, gm, share, trials):
    """trials 回分の見込みを返す。
    raw：記録の標準偏差を二乗で足した見込み
    corr_same：同じ日に2回測った差から測りのばらつきを見込んで引いたもの
    corr_diff：別の日に2回測った差から見込んで引いたもの"""
    sr = gm * math.sqrt(1 - share)
    sdd = gm * math.sqrt(share)
    n = len(sds)
    sds = np.array(sds)
    # 記録：trials × 部品の種類 × 200個
    true = rng.normal(0, 1, (trials, n, N_REC)) * sds[None, :, None]
    day = np.repeat(np.arange(DAYS), N_REC // DAYS)
    off = rng.normal(0, sdd, (trials, n, DAYS))[:, :, day] if sdd > 0 else 0.0
    rec = true + off + rng.normal(0, sr, (trials, n, N_REC))
    var_rec = rec.var(axis=2, ddof=1)                      # trials × n
    raw = np.sqrt(var_rec.sum(axis=1))
    # 2回測り：部品の種類ごとに10個を2回。同じ日（日ごとのずれは打ち消し合う）と、部品ごとに別々の2日（日ごとのずれも差に入る）
    d_same = rng.normal(0, sr, (trials, n, N_REP)) - rng.normal(0, sr, (trials, n, N_REP))
    d_diff = (rng.normal(0, sr, (trials, n, N_REP)) - rng.normal(0, sr, (trials, n, N_REP))
              + rng.normal(0, sdd, (trials, n, N_REP)) - rng.normal(0, sdd, (trials, n, N_REP)))
    gm2_same = (d_same ** 2).mean(axis=(1, 2)) / 2         # 全部の種類をまとめて見込む
    gm2_diff = (d_diff ** 2).mean(axis=(1, 2)) / 2
    corr_same = np.sqrt(np.clip(var_rec.sum(axis=1) - n * gm2_same, 0, None))
    corr_diff = np.sqrt(np.clip(var_rec.sum(axis=1) - n * gm2_diff, 0, None))
    return raw, corr_same, corr_diff, rec[0], true[0], day


def summ(x, true_sd):
    r = x / true_sd
    return {"median_ratio": round(float(np.median(r)), 4),
            "p10_ratio": round(float(np.quantile(r, 0.1)), 4),
            "p90_ratio": round(float(np.quantile(r, 0.9)), 4),
            "share_above_true": round(float((r > 1).mean() * 100), 2),
            "share_within_5pct": round(float((np.abs(r - 1) <= 0.05).mean() * 100), 2)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    true_sd = math.sqrt(sum(s * s for s in BASE_SD))

    # 本当の組み立て品：100万個を組んで数える（作りの確かめ）
    asm = sum(rng.normal(0, s, 1_000_000) for s in BASE_SD)
    asm_sd_sim = float(asm.std(ddof=1))
    asm_out_sim = float((np.abs(asm) > TOL).mean() * 100)

    base = {}
    examples = []
    for share in [0.0, 0.6]:
        raw, cs, cd, rec0, true0, day = trial_batch(rng, BASE_SD, 0.03, share, TRIALS)
        gm = 0.03
        meas_asm = math.sqrt(true_sd ** 2 + gm ** 2)         # 組み立て品を1回測った記録の幅（式）
        key = f"share{int(share * 100)}"
        base[key] = {
            "gauge_sd": gm, "day_share_pct": share * 100,
            "true_asm_sd": round(true_sd, 5),
            "formula_raw_ratio": round(math.sqrt(1 + 4 * gm ** 2 / true_sd ** 2), 4),
            "measured_asm_sd": round(meas_asm, 5),
            "measured_asm_ratio": round(meas_asm / true_sd, 4),
            "raw": summ(raw, true_sd), "corr_same_day": summ(cs, true_sd), "corr_diff_day": summ(cd, true_sd),
            "raw_median_sd": round(float(np.median(raw)), 5),
            "true_out_pct": round(out_rate(true_sd) * 100, 3),
            "raw_pred_out_pct_median": round(out_rate(float(np.median(raw))) * 100, 3),
            "corr_same_pred_out_pct_median": round(out_rate(float(np.median(cs))) * 100, 3),
            "corr_diff_pred_out_pct_median": round(out_rate(float(np.median(cd))) * 100, 3),
        }
        for lab, x in [("本当の幅（置いた値）", None), ("組み立て品を1回測った記録", None),
                       ("部品の記録から見込んだ幅", raw), ("同じ日の2回測りで引いた", cs), ("別の日の2回測りで引いた", cd)]:
            if x is None:
                v = true_sd if lab.startswith("本当") else meas_asm
            else:
                v = float(np.median(x))
            examples.append({"day_share_pct": share * 100, "what": lab, "asm_sd_mm": round(v, 5),
                             "ratio_to_true": round(v / true_sd, 4),
                             "pred_out_pct": round(out_rate(v) * 100, 3)})
        if share == 0.0:
            # 1回分の記録を data に置く
            rows = []
            for j, nm in enumerate(NAMES):
                for k in range(N_REC):
                    rows.append({"part": nm, "no": k + 1, "day": int(day[k]) + 1,
                                 "true_mm": round(NOMINAL[j] + float(true0[j, k]), 4),
                                 "record_mm": round(NOMINAL[j] + float(rec0[j, k]), 4)})
            pd.DataFrame(rows).to_csv(DATA / "records_base_one_trial.csv", index=False)
            per_part = []
            for j, nm in enumerate(NAMES):
                per_part.append({"part": nm, "true_sd_set": BASE_SD[j],
                                 "true_sd_sample": round(float(true0[j].std(ddof=1)), 5),
                                 "record_sd_sample": round(float(rec0[j].std(ddof=1)), 5),
                                 "record_sd_formula": round(math.sqrt(BASE_SD[j] ** 2 + gm ** 2), 5),
                                 "ratio_formula": round(math.sqrt(BASE_SD[j] ** 2 + gm ** 2) / BASE_SD[j], 4)})
            pd.DataFrame(per_part).to_csv(RES / "per_part_base.csv", index=False)
    pd.DataFrame(examples).to_csv(RES / "examples.csv", index=False)

    # 確かめ：測りのばらつき4 × 日ごとのずれの割合3 × 部品の数3
    grid = []
    for n in NPARTS:
        sds = sds_for(n)
        tsd = math.sqrt(sum(s * s for s in sds))
        for gm in GM:
            for share in SHARES:
                raw, cs, cd, *_ = trial_batch(rng, sds, gm, share, GRID_TRIALS)
                r, c1, c2 = summ(raw, tsd), summ(cs, tsd), summ(cd, tsd)
                grid.append({"n_parts": n, "gauge_sd": gm, "day_share_pct": share * 100,
                             "true_asm_sd": round(tsd, 5),
                             "formula_raw_ratio": round(math.sqrt(1 + n * gm ** 2 / tsd ** 2), 4),
                             "raw_median_ratio": r["median_ratio"], "raw_p10": r["p10_ratio"], "raw_p90": r["p90_ratio"],
                             "same_median_ratio": c1["median_ratio"], "same_p10": c1["p10_ratio"], "same_p90": c1["p90_ratio"],
                             "diff_median_ratio": c2["median_ratio"], "diff_p10": c2["p10_ratio"], "diff_p90": c2["p90_ratio"],
                             "measured_asm_ratio": round(math.sqrt(tsd ** 2 + gm ** 2) / tsd, 4),
                             "true_out_pct": round(out_rate(tsd) * 100, 3),
                             "raw_pred_out_pct": round(out_rate(float(np.median(raw))) * 100, 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    main_json = {
        "setting": {"parts_sd": BASE_SD, "tol": TOL, "n_records": N_REC, "days": DAYS, "trials": TRIALS,
                    "grid_trials": GRID_TRIALS, "n_repeat_parts": N_REP},
        "true_check": {"true_asm_sd_formula": round(true_sd, 5), "true_asm_sd_sim_1m": round(asm_sd_sim, 5),
                       "true_out_pct_formula": round(out_rate(true_sd) * 100, 3),
                       "true_out_pct_sim_1m": round(asm_out_sim, 3)},
        "base": base,
        "grid_range": {
            "raw_ratio_min": float(g.raw_median_ratio.min()), "raw_ratio_max": float(g.raw_median_ratio.max()),
            "raw_minus_formula_maxabs": round(float((g.raw_median_ratio - g.formula_raw_ratio).abs().max()), 4),
            "same_ratio_share0_min": float(g[g.day_share_pct == 0].same_median_ratio.min()),
            "same_ratio_share0_max": float(g[g.day_share_pct == 0].same_median_ratio.max()),
            "same_ratio_share60_min": float(g[g.day_share_pct == 60].same_median_ratio.min()),
            "same_ratio_share60_max": float(g[g.day_share_pct == 60].same_median_ratio.max()),
            "diff_ratio_min": float(g.diff_median_ratio.min()), "diff_ratio_max": float(g.diff_median_ratio.max()),
            "diff_p10_min": float(g.diff_p10.min()), "diff_p90_max": float(g.diff_p90.max()),
            "measured_asm_ratio_min": float(g.measured_asm_ratio.min()),
            "measured_asm_ratio_max": float(g.measured_asm_ratio.max()),
            "n_settings": int(len(g)),
        },
    }
    with open(RES / "a1287_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：基本の置き方で見込んだ幅（棒、0から）
    ex = pd.DataFrame(examples)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), sharey=True)
    cols = [GRAY, LIGHT, ORANGE, BLUE, GREEN]
    for ax, share in zip(axes, [0.0, 60.0]):
        d = ex[ex.day_share_pct == share]
        ax.bar(range(len(d)), d.asm_sd_mm, color=cols)
        for i, v in enumerate(d.asm_sd_mm):
            ax.text(i, v + 0.002, f"{v:.5f}", ha="center", fontsize=8.5)
        ax.set_xticks(range(len(d)))
        lab = {"本当の幅（置いた値）": "本当の幅\n（置いた値）", "組み立て品を1回測った記録": "組み立て品を\n1回測った\n記録",
               "部品の記録から見込んだ幅": "部品の記録\nから見込んだ", "同じ日の2回測りで引いた": "同じ日の\n2回測りで\n引いた",
               "別の日の2回測りで引いた": "別の日の\n2回測りで\n引いた"}
        ax.set_xticklabels([lab[w] for w in d.what], fontsize=8.5)
        ttl = "日ごとのずれなし" if share == 0 else "測りのばらつきの6割が日ごとのずれ"
        ax.set_title(f"{ttl}（測りのばらつき0.03mm）", fontsize=11)
        ax.set_ylim(0, 0.13)
    axes[0].set_ylabel("組み立て品の高さの標準偏差（mm、2,000回の中央値）")
    fig.suptitle("部品4つの記録から見込んだ幅は、本当の幅より広く出た", fontsize=13)
    save(fig, "a1287_base_widths.png", SRC, y=-0.03)

    # 図2：見込み÷本当（測りのばらつきごと、部品の数ごと）
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for n, c, ls in zip(NPARTS, [ORANGE, BLUE, INK], ["-", "-", ":"]):
        d = g[(g.n_parts == n) & (g.day_share_pct == 0)]
        ax.plot(d.gauge_sd, d.formula_raw_ratio, color=c, lw=1.4, ls=ls, label=f"部品{n}つ（式）")
        ax.scatter(d.gauge_sd, d.raw_median_ratio, color=c, s=28, zorder=3)
        ax.scatter(d.gauge_sd, d.same_median_ratio, color=c, s=28, marker="x", zorder=3)
    ax.axhline(1, color=GRAY, lw=0.8, ls="--")
    ax.set_xlabel("測りのばらつき（標準偏差、mm）")
    ax.set_ylabel("見込んだ幅÷本当の幅（中央値）")
    ax.set_xticks(GM)
    ax.set_title("●記録そのまま（線は式。4つと8つは同じ式）\n×同じ日の2回測りで引いた（日ごとのずれなし）", fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1287_ratio_by_gauge.png", SRC)

    # 図3：外れの割合の見込み（棒、0から）
    d = g[(g.n_parts == 4) & (g.day_share_pct == 0)]
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    x = np.arange(len(d))
    ax.bar(x - 0.2, d.true_out_pct, 0.4, color=GRAY, label="本当の外れの割合（置いた値から式）")
    ax.bar(x + 0.2, d.raw_pred_out_pct, 0.4, color=ORANGE, label="記録から見込んだ外れの割合")
    for i, (a, b) in enumerate(zip(d.true_out_pct, d.raw_pred_out_pct)):
        ax.text(i - 0.2, a + 0.05, f"{a:.3f}%", ha="center", fontsize=8.5)
        ax.text(i + 0.2, b + 0.05, f"{b:.3f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v:.2f}mm" for v in d.gauge_sd])
    ax.set_xlabel("測りのばらつき（部品4つ・日ごとのずれなし）")
    ax.set_ylabel("組み立て品が±0.25mmを外れる割合（%）")
    ax.set_ylim(0, max(d.raw_pred_out_pct) * 1.2)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("記録そのままで見込むと、外れの割合が多く出た", fontsize=12)
    save(fig, "a1287_out_rate.png", SRC)

    print(json.dumps(main_json["base"], ensure_ascii=False, indent=1))
    print(json.dumps(main_json["grid_range"], ensure_ascii=False, indent=1))
    print(json.dumps(main_json["true_check"], ensure_ascii=False))
    print(f"{time.time() - t0:.1f} 秒")


if __name__ == "__main__":
    main()
