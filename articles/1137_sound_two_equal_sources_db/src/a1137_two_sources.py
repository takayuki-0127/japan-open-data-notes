"""1137 同じ大きさの音を2つ重ねると、デシベルの値は2倍になるのか？（架空のデータ）

作成者が式と乱数で作った架空の音（波形、1秒あたり8,000点）を2つずつ重ね、
重ねたあとの大きさが1つのときより何dB上がるかを数える。
大きさ＝波の値の二乗平均（音の強さ）を10×log10 で dB にしたもの（基準の強さを0dBとした値）。
音は3種類：でたらめな雑音・低い音の多い雑音（でたらめな値を16点の幅でならしたもの）・一定の高さの音（1つの高さの波）。
どれも1つで60dBにそろえてから重ねる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1137
SRC = "架空の音（作成者が式と乱数で作成、seed 1137）"
SR = 8000          # 1秒あたりの点の数
DUR = 2.0          # 基本の長さ（秒）
LEVEL = 60.0       # 1つの音の大きさ（dB、作成者が置いた基準の強さを0dBとした値）
N_PAIR = 1000
TYPES = ["でたらめな雑音", "低い音の多い雑音", "一定の高さの音"]
DELAYS_MS = [0, 0.125, 0.25, 0.5, 1, 2, 5, 10, 20]
WINDOWS = [0.01, 0.1, 1.0, 10.0]
RHOS = [0.0, 0.25, 0.5, 0.75, 1.0]
GAPS = [0, 3, 6, 10, 20]


def r(x, d=3):
    return round(float(x), d)


def db(x):
    return 10 * np.log10(np.mean(np.asarray(x) ** 2, axis=-1))


def set_level(x, lv=LEVEL):
    return x * np.sqrt(10 ** (lv / 10) / np.mean(x ** 2, axis=-1, keepdims=True))


def make(rng, kind, n, length):
    """kind 0：でたらめな雑音、1：低い音の多い雑音、2：一定の高さの音（高さ200〜1,000、位相でたらめ）"""
    if kind == 0:
        x = rng.standard_normal((n, length))
    elif kind == 1:
        w = rng.standard_normal((n, length + 15))
        c = np.cumsum(w, axis=1)
        x = (c[:, 15:] - np.concatenate([np.zeros((n, 1)), c[:, :-16]], axis=1)) / 16.0
    else:
        t = np.arange(length) / SR
        f = rng.uniform(200, 1000, (n, 1))
        ph = rng.uniform(0, 2 * np.pi, (n, 1))
        x = np.sin(2 * np.pi * f * t + ph)
    return set_level(x)


def q(a, p):
    return float(np.quantile(a, p))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    L = int(SR * DUR)
    rows, out = [], {"settings": {"sample_rate": SR, "duration_sec": DUR, "single_level_db": LEVEL,
                                  "pairs_per_case": N_PAIR, "types": TYPES, "seed": SEED}}

    # ① 同じ音をそのまま重ねる、② 別々の音を重ねる（種類ごと）
    same, indep = {}, {}
    for k, name in enumerate(TYPES):
        a = make(rng, k, N_PAIR, L)
        b = make(rng, k, N_PAIR, L)
        inc_same = db(a + a) - LEVEL
        inc_ind = db(a + b) - LEVEL
        same[name] = inc_same
        indep[name] = inc_ind
        for i in range(N_PAIR):
            rows.append({"case": "same_copy", "type": name, "pair": i, "increase_db": r(inc_same[i], 4)})
            rows.append({"case": "independent", "type": name, "pair": i, "increase_db": r(inc_ind[i], 4)})

    # ③ 同じ高さの音を、位相（波の山の位置）をでたらめにずらして重ねる
    t = np.arange(L) / SR
    f = rng.uniform(200, 1000, (N_PAIR, 1))
    p1 = rng.uniform(0, 2 * np.pi, (N_PAIR, 1))
    dphi = rng.uniform(0, 2 * np.pi, (N_PAIR, 1))
    a = set_level(np.sin(2 * np.pi * f * t + p1))
    b = set_level(np.sin(2 * np.pi * f * t + p1 + dphi))
    inc_phase = db(a + b) - LEVEL
    inc_phase_formula = 10 * np.log10(np.maximum(2 + 2 * np.cos(dphi[:, 0]), 1e-12))
    for i in range(N_PAIR):
        rows.append({"case": "same_pitch_random_phase", "type": TYPES[2], "pair": i, "increase_db": r(inc_phase[i], 4)})
    # 1つより小さくなる位相の幅は 2π/3〜4π/3（全体の1/3）
    share_below0 = float(np.mean(inc_phase < 0))
    share_above5 = float(np.mean(inc_phase > 5))
    share_below_m10 = float(np.mean(inc_phase < -10))
    mean_power_inc = 10 * np.log10(np.mean(10 ** (inc_phase / 10)))

    def summ(x):
        return {"mean": r(np.mean(x), 3), "median": r(np.median(x), 3), "p05": r(q(x, 0.05), 3), "p95": r(q(x, 0.95), 3),
                "min": r(np.min(x), 3), "max": r(np.max(x), 3)}

    out["same_copy"] = {k: summ(v) for k, v in same.items()}
    out["independent"] = {k: summ(v) for k, v in indep.items()}
    out["formula"] = {"same_copy_db": r(20 * np.log10(2), 3), "independent_db": r(10 * np.log10(2), 3),
                      "phase_share_below0_formula": r(1 / 3, 4)}
    out["same_pitch_random_phase"] = {**summ(inc_phase), "share_below_0db": r(share_below0, 4),
                                      "share_above_5db": r(share_above5, 4), "share_below_minus10db": r(share_below_m10, 4),
                                      "power_average_increase_db": r(mean_power_inc, 3),
                                      "max_abs_diff_to_formula": r(np.max(np.abs(inc_phase - inc_phase_formula)), 4)}

    # ④ 同じ音を少し遅らせて重ねる（200の音の平均）
    n_d = 200
    delay_rows = []
    maxd = int(max(DELAYS_MS) * SR / 1000)
    for k in [0, 1]:
        base = make(rng, k, n_d, L + maxd)
        for d in DELAYS_MS:
            s = int(round(d * SR / 1000))
            x = base[:, maxd:]
            y = base[:, maxd - s:maxd - s + L] if s > 0 else x
            x2, y2 = set_level(x), set_level(y)
            inc = db(x2 + y2) - LEVEL
            delay_rows.append({"type": TYPES[k], "delay_ms": d, "delay_points": s, "mean_increase_db": r(np.mean(inc), 3),
                               "p05": r(q(inc, 0.05), 3), "p95": r(q(inc, 0.95), 3)})
    dly = pd.DataFrame(delay_rows)
    dly.to_csv(RES / "delay.csv", index=False)
    out["delay"] = delay_rows

    # ⑤ 同じ大きさの別々の雑音を N 個重ねる
    nrows = []
    for n in range(1, 11):
        x = make(rng, 0, 200 * n, L).reshape(200, n, L).sum(axis=1)
        inc = db(x) - LEVEL
        nrows.append({"n_sources": n, "mean_increase_db": r(np.mean(inc), 3), "formula_10log10n": r(10 * np.log10(n), 3), "formula_level_db": r(LEVEL + 10 * np.log10(n), 3),
                      "level_if_db_added": r(LEVEL * n, 1), "measured_level_db": r(LEVEL + np.mean(inc), 3)})
    out["n_sources"] = nrows
    pd.DataFrame(nrows).to_csv(RES / "n_sources.csv", index=False)

    # 確かめ1：測る長さを変える（別々のでたらめな雑音、各300組）
    wrows = []
    for w in WINDOWS:
        Lw = int(SR * w)
        inc = []
        for _ in range(3):
            a = make(rng, 0, 100, Lw)
            b = make(rng, 0, 100, Lw)
            inc.append(db(a + b) - LEVEL)
        inc = np.concatenate(inc)
        wrows.append({"window_sec": w, "mean": r(np.mean(inc), 3), "p05": r(q(inc, 0.05), 3), "p95": r(q(inc, 0.95), 3),
                      "min": r(np.min(inc), 3), "max": r(np.max(inc), 3)})
    out["window_check"] = wrows
    pd.DataFrame(wrows).to_csv(RES / "window_check.csv", index=False)

    # 確かめ2：2つの音が一部だけ同じ（共通の部分の割合 ρ）
    rrows = []
    for rho in RHOS:
        c = make(rng, 0, 300, L)
        u = make(rng, 0, 300, L)
        v = make(rng, 0, 300, L)
        a = set_level(np.sqrt(rho) * c + np.sqrt(1 - rho) * u)
        b = set_level(np.sqrt(rho) * c + np.sqrt(1 - rho) * v)
        inc = db(a + b) - LEVEL
        rrows.append({"shared_share": rho, "mean_increase_db": r(np.mean(inc), 3), "formula": r(10 * np.log10(2 + 2 * rho), 3),
                      "p05": r(q(inc, 0.05), 3), "p95": r(q(inc, 0.95), 3)})
    out["shared_check"] = rrows
    out["shared_check_max_abs_diff_to_formula"] = r(max(abs(x["mean_increase_db"] - x["formula"]) for x in rrows), 3)
    pd.DataFrame(rrows).to_csv(RES / "shared_check.csv", index=False)

    # 確かめ3：2つめの音が小さいとき（別々のでたらめな雑音）
    grows = []
    for g in GAPS:
        a = make(rng, 0, 300, L)
        b = set_level(make(rng, 0, 300, L), LEVEL - g)
        inc = db(a + b) - LEVEL
        grows.append({"second_quieter_by_db": g, "mean_increase_db": r(np.mean(inc), 3),
                      "formula": r(10 * np.log10(1 + 10 ** (-g / 10)), 3)})
    out["gap_check"] = grows
    pd.DataFrame(grows).to_csv(RES / "gap_check.csv", index=False)

    summary = []
    for name in TYPES:
        summary.append({"case": "①同じ音をそのまま", "type": name, **summ(same[name])})
    for name in TYPES:
        summary.append({"case": "②別々の音", "type": name, **summ(indep[name])})
    summary.append({"case": "③同じ高さで位相がでたらめ", "type": TYPES[2], **summ(inc_phase)})
    pd.DataFrame(summary).to_csv(RES / "summary.csv", index=False)
    pd.DataFrame(rows).to_csv(DATA / "pairs.csv", index=False)

    # ---- 図 ----
    # 図1：重ね方ごとの上がり幅（中央値と5〜95%）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    labels = ["①同じ音を\nそのまま", "②別々の\nでたらめな雑音", "②別々の\n低い音の多い雑音", "③同じ高さ・\n位相がでたらめ", "④低い音の多い雑音を\n20ミリ秒遅らせて"]
    d20 = dly[(dly.type == TYPES[1]) & (dly.delay_ms == 20)].iloc[0]
    meds = [np.median(same[TYPES[0]]), np.median(indep[TYPES[0]]), np.median(indep[TYPES[1]]), np.median(inc_phase), d20.mean_increase_db]
    lo = [q(same[TYPES[0]], .05), q(indep[TYPES[0]], .05), q(indep[TYPES[1]], .05), q(inc_phase, .05), d20.p05]
    hi = [q(same[TYPES[0]], .95), q(indep[TYPES[0]], .95), q(indep[TYPES[1]], .95), q(inc_phase, .95), d20.p95]
    cols = [ORANGE, BLUE, BLUE, GRAY, LIGHT]
    xs = np.arange(len(labels))
    ax.bar(xs, meds, color=cols, width=0.6)
    ax.errorbar(xs, meds, yerr=[np.array(meds) - np.array(lo), np.array(hi) - np.array(meds)], fmt="none", ecolor=INK, capsize=4, lw=1)
    for x, m in zip(xs, meds):
        ax.text(x + 0.33, m + 0.15, f"{m:.3f}", ha="left", va="bottom", fontsize=9)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("1つのときから上がった大きさ（dB）")
    ax.set_ylim(min(lo) - 1, 8)
    ax.set_title("同じ大きさの音を2つ重ねても、dBは2倍にならない\n（棒は中央値、線は5〜95%の範囲。60dBの音2つで120dBにはならない）")
    save(fig, "a1137_ways.png", SRC)

    # 図2：③の上がり幅の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.hist(np.clip(inc_phase, -30, None), bins=np.arange(-30, 6.5, 1.0), color=GRAY, edgecolor="white")
    ax.axvline(0, color=ORANGE, lw=1.5)
    ax.text(-0.5, ax.get_ylim()[1] * 0.9, f"1つより小さくなった組 {share_below0*100:.1f}%", ha="right", color=ORANGE, fontsize=10)
    ax.set_xlabel("1つのときから上がった大きさ（dB、−30以下は−30にまとめた）")
    ax.set_ylabel("組の数（1,000組のうち）")
    ax.set_title("同じ高さの音を位相がでたらめなまま重ねると\n3割ほどは1つのときより小さくなった（式では3分の1）")
    save(fig, "a1137_phase_hist.png", SRC)

    # 図3：遅らせ方と上がり幅
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for k, c in [(0, BLUE), (1, ORANGE)]:
        s = dly[dly.type == TYPES[k]]
        ax.plot(np.arange(len(DELAYS_MS)), s.mean_increase_db, marker="o", color=c, label=TYPES[k])
    ax.axhline(10 * np.log10(2), color=GRAY, ls="--", lw=1)
    ax.text(len(DELAYS_MS) - 1, 10 * np.log10(2) + 0.3, "+3.01（別々の音と同じ）", ha="right", color=GRAY, fontsize=9)
    ax.set_xticks(np.arange(len(DELAYS_MS)))
    ax.set_xticklabels([str(d) for d in DELAYS_MS])
    ax.set_xlabel("2つめを遅らせた時間（ミリ秒、目盛りは等間隔ではない）")
    ax.set_ylabel("1つのときから上がった大きさ（dB）")
    ax.set_ylim(0, 7)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.85))
    ax.set_title("同じ音を少し遅らせて重ねると、+6.02から+3.01に近づく\n（200の音の平均）")
    save(fig, "a1137_delay.png", SRC)

    out["run_sec"] = r(time.time() - t0, 1)
    out.pop("run_sec")
    with open(RES / "a1137_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ["same_copy", "independent", "same_pitch_random_phase"]}, ensure_ascii=False, indent=1))
    print(dly.to_string()); print(pd.DataFrame(nrows).to_string()); print(pd.DataFrame(wrows).to_string())
    print(pd.DataFrame(rrows).to_string()); print(pd.DataFrame(grows).to_string())
    print("sec", time.time() - t0)


if __name__ == "__main__":
    main()
