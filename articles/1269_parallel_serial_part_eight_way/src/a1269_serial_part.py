"""1269 処理を8つに分けて同時に動かしても8倍速くならないのは、分けられない部分がどれだけあるときか？（架空のデータ）

作成者が置いた架空のアプリの「1回の処理」（1つで動かすと600秒）。
処理は「分けられない部分」（はじめの読み込みの準備・最後のまとめ。割合 s）と「分けられる部分」からなる。
分けられる部分は64個の小さな単位からなり、k 個に同じ数ずつ分けて同時に動かす。
  単位の時間は平均1の右に長い乱数（ばらつき j）×（分けられる部分の時間÷64）。j=0 なら単位はすべて同じ長さ。
  k 個で動かした時間＝分けられない部分＋いちばん遅い1つの分。
  1回ごとの測るときの振れ：時間全体に、対数で標準偏差 sigma の振れを掛ける。
① 式：単位がそろうとき、k 個で何倍速くなるかは 1÷（s＋（1−s）÷k）。
② 時間の内訳：1つのときの割合 s と、8つで動かしたときの割合は違う。
③ 1つ・2つ・4つで測った時間から s を見込み、8つで何倍になるかを見込むと、どれだけ外れるか（乱数）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1269
SRC = "架空のアプリの1回の処理（作成者が置いた分けられない部分の割合と単位の時間からの乱数、seed 1269）"
T = 600.0
UNITS = 64
BASE = dict(s=0.05, sigma=0.03, j=0.5, reps=3)


def formula(s, k):
    return 1.0 / (s + (1.0 - s) / k)


def unit_draw(rng, shape, j):
    if j == 0:
        return np.ones(shape)
    sl = np.sqrt(np.log(1 + j ** 2))
    return rng.lognormal(-sl ** 2 / 2, sl, shape)          # 平均1・ばらつき（標準偏差÷平均）j


def run_time(rng, n, s, k, j, sigma):
    """n 回分の、k 個で動かした時間（秒）"""
    u = unit_draw(rng, (n, UNITS), j) * (1 - s) * T / UNITS
    parts = u.reshape(n, k, UNITS // k).sum(2)
    t = s * T + parts.max(1)
    if sigma > 0:
        t = t * rng.lognormal(0, sigma, n)
    return t


def expected_time(rng, s, k, j, n=100000):
    return float(run_time(rng, n, s, k, j, 0.0).mean())


def estimate(rng, n, s, j, sigma, reps):
    """1・2・4個で reps 回ずつ測り、中央値から s を見込む。8個の見込みを返す"""
    med = {}
    for k in [1, 2, 4]:
        tt = np.stack([run_time(rng, n, s, k, j, sigma) for _ in range(reps)], 1)
        med[k] = np.median(tt, 1)
    num = np.zeros(n); den = 0.0
    for k in [2, 4]:
        y = med[k] / med[1]
        num += (y - 1 / k) * (1 - 1 / k)
        den += (1 - 1 / k) ** 2
    sh = np.clip(num / den, 0, 1)
    return sh, formula(sh, 8), med


def main():
    t0 = time.time()

    # ① 式：分けられない部分の割合と、何倍速くなるか
    srows = []
    for s in [0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]:
        srows.append({"serial_share": s, "speedup_k2": round(formula(s, 2), 3), "speedup_k4": round(formula(s, 4), 3),
                      "speedup_k8": round(formula(s, 8), 3), "speedup_k16": round(formula(s, 16), 3), "speedup_k64": round(formula(s, 64), 3),
                      "upper_limit": (round(1 / s, 3) if s > 0 else None), "time_k8_sec": round(T / formula(s, 8), 1)})
    st = pd.DataFrame(srows)
    st.to_csv(RES / "speedup_formula.csv", index=False)
    thr = [{"target_speedup_k8": x, "serial_share_at_most": round((8 / x - 1) / 7, 4)} for x in [7, 6, 5, 4, 3, 2]]
    pd.DataFrame(thr).to_csv(RES / "threshold_k8.csv", index=False)

    # ② 時間の内訳：1つのときの割合と、8つで動かしたときの割合
    sh_rows = []
    for s in [0.02, 0.05, 0.10, 1 / 7]:
        s8 = s / (s + (1 - s) / 8)
        true16 = formula(s, 16)
        wrong16 = formula(s8, 16) / formula(s8, 1) * 1.0          # 8つのときの内訳を、1つのときの内訳とみなして式に入れる
        # 8つのときの内訳をそのまま「s」とみなすと、8つ→16個の伸びの見込みは formula(s8,16)/formula(s8,8)
        true_8to16 = formula(s, 16) / formula(s, 8)
        wrong_8to16 = formula(s8, 16) / formula(s8, 8)
        sh_rows.append({"serial_share_k1": round(s, 4), "serial_share_in_k8_time": round(s8, 4),
                        "speedup_k16_true": round(true16, 3), "speedup_k16_if_k8_share_used": round(wrong16, 3),
                        "k8_to_k16_gain_true": round(true_8to16, 3), "k8_to_k16_gain_if_k8_share_used_as_k1": round(wrong_8to16, 3)})
    sh = pd.DataFrame(sh_rows)
    sh.to_csv(RES / "share_in_time.csv", index=False)
    # 8つのときの内訳を「8つの時間を1とした割合」で読み、そこから16個を見込むのが正しいやり方：16個の時間＝s8＋(1−s8)÷2
    for r in sh_rows:
        s8 = r["serial_share_in_k8_time"]
        r["k8_to_k16_gain_from_k8_share_correct"] = round(1 / (s8 + (1 - s8) / 2), 3)
    sh = pd.DataFrame(sh_rows)
    sh.to_csv(RES / "share_in_time.csv", index=False)

    # 単位がそろうとき（j=0）の乱数の確かめ：式と同じになるはず（作りどおり）
    chk = {}
    for s in [0.05, 0.10]:
        e8 = expected_time(np.random.default_rng([SEED, 9, int(s * 100)]), s, 8, 0.0, n=1000)
        chk[str(s)] = {"sim_speedup_k8": round(T / e8, 4), "formula": round(formula(s, 8), 4)}

    # ③ 基本の置き方：1・2・4つで3回ずつ測って見込む（2,000回）
    N = 2000
    s, sigma, j, reps = BASE["s"], BASE["sigma"], BASE["j"], BASE["reps"]
    rng = np.random.default_rng([SEED, 1])
    sh_hat, pred8, med = estimate(rng, N, s, j, sigma, reps)
    e1 = expected_time(np.random.default_rng([SEED, 2, 1]), s, 1, j)
    e8 = expected_time(np.random.default_rng([SEED, 2, 8]), s, 8, j)
    actual8 = e1 / e8
    err = pred8 / actual8 - 1
    base = {"true_serial_share": s, "formula_speedup_k8": round(formula(s, 8), 3), "actual_speedup_k8": round(actual8, 3),
            "actual_vs_formula_pct": round((actual8 / formula(s, 8) - 1) * 100, 2),
            "expected_time_k1": round(e1, 1), "expected_time_k8": round(e8, 1),
            "est_serial_share_median": round(float(np.median(sh_hat)), 4),
            "est_serial_share_p10_p90": [round(float(np.quantile(sh_hat, 0.1)), 4), round(float(np.quantile(sh_hat, 0.9)), 4)],
            "pred_speedup_k8_median": round(float(np.median(pred8)), 3),
            "pred_speedup_k8_p10_p90": [round(float(np.quantile(pred8, 0.1)), 3), round(float(np.quantile(pred8, 0.9)), 3)],
            "pred_error_median_pct": round(float(np.median(err)) * 100, 2),
            "pred_error_p10_p90_pct": [round(float(np.quantile(err, 0.1)) * 100, 2), round(float(np.quantile(err, 0.9)) * 100, 2)],
            "share_within_10pct": round(float(np.mean(np.abs(err) <= 0.10)), 4),
            "share_pred_too_high": round(float(np.mean(err > 0)), 4)}
    pd.DataFrame({"trial": np.arange(200), "t1_median": med[1][:200].round(2), "t2_median": med[2][:200].round(2),
                  "t4_median": med[4][:200].round(2), "est_serial_share": sh_hat[:200].round(4),
                  "pred_speedup_k8": pred8[:200].round(3)}).to_csv(DATA / "measurements_base.csv", index=False)

    # 見込んだ s を本当の分けられない部分と読んで、本当の部分を半分（5%→2.5%）に減らしたとき
    half = s / 2
    e1h = expected_time(np.random.default_rng([SEED, 7, 1]), half, 1, j)
    e8h = expected_time(np.random.default_rng([SEED, 7, 8]), half, 8, j)
    sh_med = float(np.median(sh_hat))
    improve = {"true_serial_share_after": half, "est_share_before_median": round(sh_med, 4),
               "believed_share_after": round(sh_med - (s - half), 4),
               "believed_speedup_k8_after": round(formula(sh_med - (s - half), 8), 3),
               "believed_gain_vs_before": round(formula(sh_med - (s - half), 8) / formula(sh_med, 8), 4),
               "formula_speedup_k8_after_true_share": round(formula(half, 8), 3),
               "actual_speedup_k8_after": round(e1h / e8h, 3),
               "actual_gain_vs_before": round((e1h / e8h) / actual8, 4)}

    # 単位の時間のばらつきだけで、分けられない部分があるように見える（s=0）
    ghost = []
    for jj in [0, 0.25, 0.5, 1.0]:
        shg, p8g, _ = estimate(np.random.default_rng([SEED, 3, int(jj * 100)]), N, 0.0, jj, 0.0, 1)
        a8 = expected_time(np.random.default_rng([SEED, 4, int(jj * 100), 1]), 0.0, 1, jj) / expected_time(np.random.default_rng([SEED, 4, int(jj * 100), 8]), 0.0, 8, jj)
        ghost.append({"unit_cv": jj, "true_serial_share": 0.0, "est_serial_share_median": round(float(np.median(shg)), 4),
                      "pred_speedup_k8_median": round(float(np.median(p8g)), 3), "actual_speedup_k8": round(a8, 3)})
    gh = pd.DataFrame(ghost)
    gh.to_csv(RES / "variation_looks_serial.csv", index=False)

    # 測る回数（基本の置き方で1・3・10回）
    rep_rows = []
    for rr in [1, 3, 10]:
        shr, p8r, _ = estimate(np.random.default_rng([SEED, 1] if rr == 3 else [SEED, 5, rr]), N, s, j, sigma, rr)   # 3回は基本と同じ乱数
        er = p8r / actual8 - 1
        rep_rows.append({"reps": rr, "pred_speedup_k8_median": round(float(np.median(p8r)), 3),
                         "pred_error_p10_pct": round(float(np.quantile(er, 0.1)) * 100, 2), "pred_error_p90_pct": round(float(np.quantile(er, 0.9)) * 100, 2),
                         "share_within_10pct": round(float(np.mean(np.abs(er) <= 0.10)), 4)})
    rp = pd.DataFrame(rep_rows)
    rp.to_csv(RES / "by_reps.csv", index=False)

    # ④ 確かめ：本当の s×測るときの振れ×単位のばらつき（27通り、各2,000回、3回ずつ測る）
    grid = []
    for gs in [0.02, 0.05, 0.10]:
        for gsig in [0.01, 0.03, 0.05]:
            for gj in [0, 0.5, 1.0]:
                tag = [SEED, 6, int(gs * 100), int(gsig * 100), int(gj * 10)]
                if (gs, gsig, gj) == (s, sigma, j):          # 基本と同じ乱数（基本の値と同じになる）
                    shg, p8g, a8 = sh_hat, pred8, actual8
                else:
                    shg, p8g, _ = estimate(np.random.default_rng(tag), N, gs, gj, gsig, 3)
                    a8 = expected_time(np.random.default_rng(tag + [1]), gs, 1, gj) / expected_time(np.random.default_rng(tag + [8]), gs, 8, gj)
                eg = p8g / a8 - 1
                grid.append({"true_serial_share": gs, "sigma": gsig, "unit_cv": gj, "formula_speedup_k8": round(formula(gs, 8), 3),
                             "actual_speedup_k8": round(a8, 3), "est_serial_share_median": round(float(np.median(shg)), 4),
                             "pred_speedup_k8_median": round(float(np.median(p8g)), 3),
                             "pred_error_p10_pct": round(float(np.quantile(eg, 0.1)) * 100, 2),
                             "pred_error_median_pct": round(float(np.median(eg)) * 100, 2),
                             "pred_error_p90_pct": round(float(np.quantile(eg, 0.9)) * 100, 2),
                             "share_within_10pct": round(float(np.mean(np.abs(eg) <= 0.10)), 4)})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    robust = {"settings": int(len(gr)),
              "actual_speedup_k8_range": [float(gr.actual_speedup_k8.min()), float(gr.actual_speedup_k8.max())],
              "actual_below_formula_pct_range": [round(float((gr.actual_speedup_k8 / gr.formula_speedup_k8 - 1).min() * 100), 2),
                                                 round(float((gr.actual_speedup_k8 / gr.formula_speedup_k8 - 1).max() * 100), 2)],
              "pred_error_p10_range": [float(gr.pred_error_p10_pct.min()), float(gr.pred_error_p10_pct.max())],
              "pred_error_p90_range": [float(gr.pred_error_p90_pct.min()), float(gr.pred_error_p90_pct.max())],
              "pred_error_median_range": [float(gr.pred_error_median_pct.min()), float(gr.pred_error_median_pct.max())],
              "share_within_10pct_range": [float(gr.share_within_10pct.min()), float(gr.share_within_10pct.max())],
              "share_within_10pct_by_sigma": {str(g): [float(gr[gr.sigma == g].share_within_10pct.min()), float(gr[gr.sigma == g].share_within_10pct.max())] for g in [0.01, 0.03, 0.05]},
              "share_within_10pct_by_s": {str(g): [float(gr[gr.true_serial_share == g].share_within_10pct.min()), float(gr[gr.true_serial_share == g].share_within_10pct.max())] for g in [0.02, 0.05, 0.10]},
              "est_serial_share_by_unit_cv": {str(g): [float(gr[gr.unit_cv == g].est_serial_share_median.min()), float(gr[gr.unit_cv == g].est_serial_share_median.max())] for g in [0, 0.5, 1.0]},
              "actual_speedup_by_unit_cv": {str(g): [float(gr[gr.unit_cv == g].actual_speedup_k8.min()), float(gr[gr.unit_cv == g].actual_speedup_k8.max())] for g in [0, 0.5, 1.0]}}

    out = {"formula_threshold_k8": thr, "share_in_time": sh_rows, "sim_check_equal_units": chk, "base": base, "halve_serial_part": improve,
           "variation_looks_serial": ghost, "by_reps": rep_rows, "robust": robust,
           "setup": {"T1_sec": T, "units": UNITS, **BASE, "trials": N, "measure_k": [1, 2, 4], "expected_time_runs": 100000}}
    json.dump(out, open(RES / "a1269_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：分けられない部分の割合と、何倍速くなるか（式）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    ss = np.linspace(0, 0.5, 501)
    for k, c in [(4, LIGHT), (8, BLUE), (16, INK)]:
        ax.plot(ss * 100, formula(ss, k), color=c, lw=2, label=(f"{k}つで動かす" if k < 10 else f"{k}個で動かす"))
    for x, sv in [(6, (8 / 6 - 1) / 7), (4, 1 / 7)]:
        ax.plot([sv * 100], [x], "o", color=ORANGE)
        ax.annotate(f"8つで{x}倍：分けられない部分 {sv*100:.2f}%", (sv * 100, x), xytext=(sv * 100 + 3, x + 1.6), fontsize=9,
                    arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8))
    ax.set_xlim(0, 50); ax.set_ylim(0, 16.5)
    ax.set_xlabel("分けられない部分の割合（1つで動かしたときの時間のうち、%）")
    ax.set_ylabel("1つのときの何倍速くなるか")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("分けられない部分が14.29%で、8つでも4倍（式どおり）", fontsize=12)
    save(fig, "a1269_formula.png", SRC)

    # 図2：時間の内訳。1つのときの割合と、8つで動かしたときの割合
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    xs = np.arange(len(sh_rows))
    ax.bar(xs - 0.2, sh.serial_share_k1 * 100, 0.4, color=LIGHT, label="1つで動かしたときの時間のうち")
    ax.bar(xs + 0.2, sh.serial_share_in_k8_time * 100, 0.4, color=ORANGE, label="8つで動かしたときの時間のうち")
    for i, r in sh.iterrows():
        ax.text(i - 0.2, r.serial_share_k1 * 100 + 1.2, f"{r.serial_share_k1*100:.2f}%", ha="center", fontsize=8.5)
        ax.text(i + 0.2, r.serial_share_in_k8_time * 100 + 1.2, f"{r.serial_share_in_k8_time*100:.2f}%", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"処理{c}" for c in "ABCD"])
    ax.set_ylim(0, 70); ax.set_ylabel("分けられない部分が占める割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("同じ処理でも、8つで動かした時間の内訳では分けられない部分が大きく見える（式どおり）", fontsize=10.5)
    save(fig, "a1269_share.png", SRC)

    # 図3：27通りの見込みの外れ（10〜90%）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    gx = np.arange(len(gr))
    ax.vlines(gx, gr.pred_error_p10_pct, gr.pred_error_p90_pct, color=BLUE, lw=3, label="見込みの外れの10〜90%の範囲")
    ax.plot(gx, gr.pred_error_median_pct, "o", color=INK, ms=4, label="中央値")
    ax.axhline(0, color=GRAY, lw=0.8)
    for kk in [9, 18]:
        ax.axvline(kk - 0.5, color=GRAY, lw=0.8, ls=":")
    top = float(gr.pred_error_p90_pct.max())
    for kk, g in enumerate([2, 5, 10]):
        ax.text(kk * 9 + 4, top + 4, f"本当の分けられない部分{g}%", ha="center", fontsize=8.5)
    ax.set_xticks(gx); ax.set_xticklabels([f"{int(a*100)}" for a in gr.sigma], fontsize=7)
    ax.set_xlabel("27通り（下の数字は測るときの振れ%。同じ数字の中は単位の時間のばらつき0・0.5・1.0の順）", fontsize=8.5)
    ax.set_ylim(float(gr.pred_error_p10_pct.min()) - 5, top + 9)
    ax.set_ylabel("8つで何倍かの見込みの外れ（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    ax.set_title("1・2・4つで3回ずつ測って見込む8つの速さは、振れとばらつきで外れる", fontsize=11.5)
    save(fig, "a1269_grid.png", SRC, y=-0.2)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(st); print(sh); print(gr)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
