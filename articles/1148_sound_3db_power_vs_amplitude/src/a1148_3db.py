"""1148 「3dB 上げる」は、音の強さで見るか波の振れ幅で見るかで、何倍の変化になるのか？（架空のデータ）

作成者が式と乱数で作った架空の音（波形、1秒あたり8,000点）を「3dB 上げ」、
音の強さ（波の値の二乗平均）と波の振れ幅（二乗平均の平方根・いちばん大きい瞬間）が何倍になったかを数える。
dB の値は、強さの比なら 10×log10、振れ幅の比なら 20×log10 で表す。
① 全体を同じだけ上げる、② 上限（±1）で切れるとき、③ 低い音の部分だけ上げるとき、の3つ。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1148
SRC = "架空の音（作成者が式と乱数で作成、seed 1148）"
SR = 8000
DUR = 4.0
UP = 3.0
SPLIT_HZ = 500


def r(x, d=4):
    return round(float(x), d)


def q(a, p):
    return float(np.quantile(a, p))


def pw(x):
    return np.mean(x ** 2, axis=-1)


def make(rng, kind, n, length):
    t = np.arange(length) / SR
    if kind == "でたらめな雑音":
        x = rng.standard_normal((n, length))
    elif kind == "一定の高さの音":
        f = rng.uniform(200, 1000, (n, 1))
        x = np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi, (n, 1)))
    else:  # 架空の曲：雑音に、0.5秒ごとの強い音と1秒ごとに変わる大きさを掛けたもの
        env = np.ones((n, length))
        ph = np.mod(t[None, :] - rng.uniform(0, 0.5, (n, 1)), 0.5)
        env = env * (1 + 10 ** (rng.uniform(0, 12, (n, 1)) / 10) * np.exp(-ph / 0.04))
        blocks = 10 ** (rng.normal(0, 2, (n, int(DUR) + 1)) / 10)
        env = env * blocks[:, (t // 1).astype(int)]
        x = rng.standard_normal((n, length)) * np.sqrt(env)
    return x


def to_peak(x, peak_db):
    return x * (10 ** (np.asarray(peak_db) / 20) / np.max(np.abs(x), axis=-1)).reshape(-1, 1)


def bands(rng, n, length):
    """でたらめな雑音を、1秒に500回までの振動（低い音）と、それより速い振動（高い音）にきっちり分ける"""
    w = rng.standard_normal((n, length))
    F = np.fft.rfft(w, axis=1)
    f = np.fft.rfftfreq(length, 1 / SR)
    lo = np.fft.irfft(F * (f <= SPLIT_HZ), n=length, axis=1)
    hi = np.fft.irfft(F * (f > SPLIT_HZ), n=length, axis=1)
    lo /= np.sqrt(pw(lo))[:, None]
    hi /= np.sqrt(pw(hi))[:, None]
    return lo, hi


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    L = int(SR * DUR)
    g = 10 ** (UP / 20)
    out = {"settings": {"sample_rate": SR, "duration_sec": DUR, "up_db": UP, "split_hz": SPLIT_HZ, "seed": SEED}}

    # 式：dB と、強さの比・振れ幅の比
    frows = []
    for d in [1, 3, 6, 10, 20]:
        frows.append({"db": d, "power_ratio": r(10 ** (d / 10)), "amplitude_ratio": r(10 ** (d / 20))})
    out["formula_table"] = frows
    pd.DataFrame(frows).to_csv(RES / "formula_table.csv", index=False)
    # 「3dB＝2倍」を重ねたときのずれ
    srows = []
    for k in [1, 2, 5, 10, 20]:
        srows.append({"times_3db": k, "total_db": 3 * k, "power_ratio": r(10 ** (0.3 * k), 3), "two_to_k": 2 ** k,
                      "power_ratio_over_two_to_k": r(10 ** (0.3 * k) / 2 ** k)})
    out["stack_3db"] = srows
    pd.DataFrame(srows).to_csv(RES / "stack_3db.csv", index=False)

    # ① 全体を3dB上げる（3種類×300、上限なし）
    rows1 = []
    for kind in ["でたらめな雑音", "一定の高さの音", "架空の曲"]:
        x = make(rng, kind, 300, L)
        y = x * g
        pr = pw(y) / pw(x)
        ar = np.sqrt(pr)
        pk = np.max(np.abs(y), axis=1) / np.max(np.abs(x), axis=1)
        ma = np.mean(np.abs(y), axis=1) / np.mean(np.abs(x), axis=1)
        rows1.append({"type": kind, "power_ratio": r(pr.mean()), "rms_amplitude_ratio": r(ar.mean()), "peak_ratio": r(pk.mean()),
                      "mean_abs_ratio": r(ma.mean()), "all_within_1e-12_of_formula": bool(max(np.abs(pr - 10 ** 0.3).max(), np.abs(pk - g).max(), np.abs(ma - g).max()) < 1e-12)})
    out["whole_gain"] = rows1
    pd.DataFrame(rows1).to_csv(RES / "whole_gain.csv", index=False)
    # 読み違え：「3dB＝2倍」を振れ幅に当てる／「振れ幅1.413倍」を強さに当てる
    out["misread"] = {"amplitude_x2_db": r(20 * np.log10(2), 3), "amplitude_x2_power_ratio": 4,
                      "power_x1413_db": r(10 * np.log10(g), 3), "power_x2_amplitude_ratio": r(np.sqrt(2))}

    # ② 上限（±1）で切れるとき：架空の曲200曲。いちばん大きい瞬間を −6〜−0.1dB（一様）に置いてから3dB上げる
    n2 = 200
    peaks = rng.uniform(-6, -0.1, n2)
    x = to_peak(make(rng, "架空の曲", n2, L), peaks)
    y = np.clip(x * g, -1, 1)
    p_inc = 10 * np.log10(pw(y) / pw(x))
    pk_ratio = np.max(np.abs(y), axis=1) / np.max(np.abs(x), axis=1)
    clip_share = np.mean(np.abs(x * g) > 1, axis=1)
    songs = pd.DataFrame({"song": np.arange(n2), "peak_before_db": np.round(peaks, 3), "power_increase_db": np.round(p_inc, 4),
                          "power_ratio": np.round(10 ** (p_inc / 10), 4), "peak_ratio": np.round(pk_ratio, 4),
                          "clipped_point_share": np.round(clip_share, 6)})
    songs.to_csv(DATA / "songs_clip.csv", index=False)
    cl = peaks > -UP
    out["clip"] = {"songs": n2, "share_songs_clipped": r(cl.mean()), "share_songs_not_clipped": r(1 - cl.mean()),
                   "not_clipped_power_ratio_mean": r(np.mean(10 ** (p_inc[~cl] / 10))),
                   "not_clipped_power_increase_db_mean": r(p_inc[~cl].mean()), "not_clipped_peak_ratio_mean": r(pk_ratio[~cl].mean()),
                   "clipped_power_increase_db_mean": r(p_inc[cl].mean()), "clipped_power_increase_db_min": r(p_inc[cl].min()),
                   "clipped_power_ratio_mean": r(np.mean(10 ** (p_inc[cl] / 10))),
                   "clipped_peak_ratio_mean": r(pk_ratio[cl].mean()), "clipped_peak_ratio_min": r(pk_ratio[cl].min()),
                   "clipped_point_share_mean": r(clip_share[cl].mean(), 6), "clipped_point_share_max": r(clip_share[cl].max(), 6),
                   "peak_ratio_db_clipped_mean": r(np.mean(20 * np.log10(pk_ratio[cl])), 3)}
    # 置いた音の種類で、切れたときの強さの上がり方（いちばん大きい瞬間を−1dBにして3dB上げる、各200）
    crows = []
    for kind in ["でたらめな雑音", "一定の高さの音", "架空の曲"]:
        for pdb in [-2.0, -1.0, -0.1]:
            xx = to_peak(make(rng, kind, 200, L), np.full(200, pdb))
            yy = np.clip(xx * g, -1, 1)
            inc = 10 * np.log10(pw(yy) / pw(xx))
            crows.append({"type": kind, "peak_before_db": pdb, "power_increase_db_mean": r(inc.mean(), 3),
                          "power_ratio_mean": r(np.mean(10 ** (inc / 10))), "peak_ratio_mean": r(np.mean(np.max(np.abs(yy), 1) / np.max(np.abs(xx), 1))),
                          "clipped_point_share_mean": r(np.mean(np.abs(xx * g) > 1), 6)})
    out["clip_by_type"] = crows
    pd.DataFrame(crows).to_csv(RES / "clip_by_type.csv", index=False)

    # ③ 低い音の部分だけ3dB上げる（低い音の強さの割合 s、各200）
    brows = []
    for s in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        lo, hi = bands(rng, 200, L)
        x = np.sqrt(s) * lo + np.sqrt(1 - s) * hi
        for up in [1.0, 3.0, 6.0]:
            y = np.sqrt(s) * lo * 10 ** (up / 20) + np.sqrt(1 - s) * hi
            inc = 10 * np.log10(pw(y) / pw(x))
            pk = np.max(np.abs(y), 1) / np.max(np.abs(x), 1)
            brows.append({"low_share": s, "up_db": up, "power_increase_db_mean": r(inc.mean(), 3),
                          "formula_db": r(10 * np.log10(1 + s * (10 ** (up / 10) - 1)), 3),
                          "power_ratio_mean": r(np.mean(10 ** (inc / 10))),
                          "peak_ratio_mean": r(pk.mean()), "peak_ratio_p05": r(q(pk, .05)), "peak_ratio_p95": r(q(pk, .95))})
    b = pd.DataFrame(brows)
    b.to_csv(RES / "low_band.csv", index=False)
    out["low_band"] = brows
    b3 = b[b.up_db == 3.0]
    out["low_band_summary"] = {"up3_power_increase_db_min": r(b3.power_increase_db_mean.min(), 3),
                               "up3_power_increase_db_max": r(b3.power_increase_db_mean.max(), 3),
                               "max_abs_diff_formula_db": r(np.max(np.abs(b.power_increase_db_mean - b.formula_db)), 3),
                               "up3_peak_ratio_min": r(b3.peak_ratio_mean.min()), "up3_peak_ratio_max": r(b3.peak_ratio_mean.max()),
                               "all27_power_increase_db_min": r(b.power_increase_db_mean.min(), 3),
                               "all27_power_increase_db_max": r(b.power_increase_db_mean.max(), 3)}

    # ---- 図 ----
    # 図1：dB と、強さの比・振れ幅の比（式）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    dd = np.linspace(0, 10, 201)
    ax.plot(dd, 10 ** (dd / 10), color=ORANGE, label="強さの比\n＝10^(dB÷10)")
    ax.plot(dd, 10 ** (dd / 20), color=BLUE, label="振れ幅の比\n＝10^(dB÷20)")
    for d, c in [(3, GRAY), (6, GRAY)]:
        ax.axvline(d, color=c, ls=":", lw=1)
    ax.plot([3, 3, 6, 6], [10 ** 0.3, 10 ** 0.15, 10 ** 0.6, 10 ** 0.3], "o", color=INK, ms=4)
    ax.text(3.15, 10 ** 0.3 + 0.15, f"+3dB：強さ {10**0.3:.4f}倍", fontsize=9, va="bottom")
    ax.text(3.15, 10 ** 0.15 - 0.15, f"振れ幅 {10**0.15:.4f}倍", fontsize=9, va="top")
    ax.text(6.15, 10 ** 0.6, f"+6dB：強さ {10**0.6:.4f}倍", fontsize=9, va="center")
    ax.text(6.15, 10 ** 0.3 - 0.15, f"振れ幅 {10**0.3:.4f}倍", fontsize=9, va="top")
    ax.set_xlabel("上げた大きさ（dB）")
    ax.set_ylabel("何倍になったか")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10.5)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.set_title("同じ「3dB 上げる」でも、強さでは1.9953倍、振れ幅では1.4125倍\n（式どおり。架空の音3種類で測っても同じ値になった）")
    save(fig, "a1148_formula.png", SRC)

    # 図2：上限で切れるとき（200曲）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.scatter(peaks, 10 ** (p_inc / 10), s=14, color=ORANGE, label="強さの比")
    ax.scatter(peaks, pk_ratio, s=14, color=BLUE, marker="s", label="いちばん大きい瞬間の振れ幅の比")
    ax.axvline(-UP, color=GRAY, ls=":", lw=1)
    ax.text(-UP + 0.05, 0.15, "この右は上限（±1）で切れる", fontsize=9, color=GRAY)
    ax.set_xlabel("上げる前のいちばん大きい瞬間（dB、0が上限）")
    ax.set_ylabel("3dB 上げたあと何倍になったか")
    ax.set_ylim(0, 2.3)
    ax.legend(frameon=False, loc="lower left", fontsize=9, bbox_to_anchor=(0, 0.12))
    ax.set_title("上限で切れると、振れ幅の比は1倍近くまで下がるが、強さの比はほぼ2倍のまま\n（架空の曲200曲。3dB上げて±1を超えた分を切った）")
    save(fig, "a1148_clip.png", SRC)

    # 図3：低い音の部分だけ上げる
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for up, c in [(1.0, LIGHT), (3.0, BLUE), (6.0, ORANGE)]:
        s_ = b[b.up_db == up]
        ax.plot(s_.low_share * 100, s_.power_increase_db_mean, marker="o", color=c, label=f"低い音だけ{up:g}dB上げる")
        ax.axhline(up, color=c, ls=":", lw=1)
    ax.set_xlabel("低い音（1秒に500回までの振動）が強さに占める割合（%）")
    ax.set_ylabel("全体の強さが上がった大きさ（dB）")
    ax.set_ylim(0, 6.5)
    ax.set_xlim(0, 100)
    ax.legend(frameon=False, loc="upper left", fontsize=9, bbox_to_anchor=(0, 0.9))
    ax.set_title("一部だけ3dB上げても、全体は3dB上がらない\n（点線は上げた大きさ。各200の音の平均で、式どおり）")
    save(fig, "a1148_low_band.png", SRC)

    with open(RES / "a1148_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows1).to_string()); print(out["misread"]); print(json.dumps(out["clip"], ensure_ascii=False, indent=1))
    print(pd.DataFrame(crows).to_string()); print(b.to_string()); print(out["low_band_summary"]); print(pd.DataFrame(srows).to_string())
    print("sec", time.time() - t0)


if __name__ == "__main__":
    main()
