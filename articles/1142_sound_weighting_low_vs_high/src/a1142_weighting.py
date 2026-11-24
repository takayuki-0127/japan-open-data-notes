"""1142 低い音と高い音では、同じデシベルでも、測り方の重み付けしだいで大きさの数字がどれだけ違うのか？（架空のデータ）

大きさの数字を出すとき、高さ（周波数）ごとに重みを掛けてから足す測り方がある。3つの重みを置く：
  ①重みなし
  ②低い音を大きく下げる重み（広く使われる重み付けの1つの形を式で写したもの）
  ③低い音を少しだけ下げ、高い音を少し上げる重み（広く使われる別の重み付けの形に似せて作成者が置いた式）
1つの高さの音（式どおり）、作成者が乱数で作った架空の曲1,000曲（高さごとの強さの配分）で、
重みなしでは同じ大きさの曲が、重みを付けるとどれだけ違うか、順位がどれだけ入れかわるか、
低い音を足したとき配信先がどれだけ下げるかを数える。高さごとの強さの計算は、波形を作って測った値と照らし合わせる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1142
SRC = "架空の音と曲（作成者が式と乱数で作成、seed 1142）"
FB = 1000 * 2.0 ** (np.arange(-15, 12) / 3)          # 帯の真ん中の高さ（31.5〜12,700）
N_SONG = 1000
L_SET = -16.0                                        # 重みなしでそろえる大きさ
BUMP_C, BUMP_W = 60.0, 0.6                           # 低い音のふくらみ（真ん中の高さ・幅（オクターブ））
BASS_ADD = 6.0                                       # 確かめで足す低い音（125 以下の帯に +6 dB）
W3_HP, W3_SH, W3_SF = 38.0, 4.0, 1500.0              # ③の低い側の下げ始め・高い側の上げ幅・上げ始め
NAMES = {"w0": "①重みなし", "w1": "②低い音を大きく下げる重み", "w2": "③低い音を少し下げ高い音を少し上げる重み"}


def r(x, d=2):
    return round(float(x), d)


def w1(f):
    f = np.asarray(f, float)
    ra = (12194.0 ** 2 * f ** 4) / ((f ** 2 + 20.6 ** 2) * np.sqrt((f ** 2 + 107.7 ** 2) * (f ** 2 + 737.9 ** 2)) * (f ** 2 + 12194.0 ** 2))
    return 20 * np.log10(ra) + 2.0


def w2(f, hp=W3_HP, sh=W3_SH, sf=W3_SF):
    f = np.asarray(f, float)
    return 10 * np.log10(f ** 4 / (f ** 4 + hp ** 4)) + sh * f ** 2 / (f ** 2 + sf ** 2)


def wdb(name, f, **kw):
    if name == "w0":
        return np.zeros_like(np.asarray(f, float))
    return w1(f) if name == "w1" else w2(f, **kw)


def level(band_db, wts):
    return 10 * np.log10((10 ** ((band_db + wts) / 10)).sum(axis=-1))


def make_songs(rng, n, bump_c=BUMP_C):
    oct_ = np.log2(np.maximum(FB, 125) / 1000)            # 125 より低い帯は傾きを止める（低い側は平ら）
    tilt = rng.uniform(-4.5, -1.5, n)
    bass = rng.uniform(0, 12, n)
    bright = rng.uniform(-3, 6, n)
    spec = (tilt[:, None] * oct_[None, :]
            + bass[:, None] * np.exp(-np.log2(FB / bump_c) ** 2 / (2 * BUMP_W ** 2))[None, :]
            + bright[:, None] * np.exp(-np.log2(FB / 5000) ** 2 / (2 * 0.7 ** 2))[None, :]
            + rng.normal(0, 1.5, (n, len(FB))))
    spec += L_SET - level(spec, 0)[:, None]               # 重みなしで −16 dB にそろえる
    return spec, tilt, bass, bright


def rank_corr(a, b):
    return np.corrcoef(pd.Series(a).rank(), pd.Series(b).rank())[0, 1]


def analyse(spec, bass, kw=None):
    kw = kw or {}
    L = {k: level(spec, wdb(k, FB, **(kw if k == "w2" else {}))) for k in NAMES}
    d1, d2 = L["w1"] - L["w0"], L["w2"] - L["w0"]
    n = len(spec)
    top = max(1, n // 10)
    t1 = set(np.argsort(-L["w1"])[:top])
    t2 = set(np.argsort(-L["w2"])[:top])
    boosted = spec.copy()
    boosted[:, FB <= 130] += BASS_ADD
    up = {k: (level(boosted, wdb(k, FB, **(kw if k == "w2" else {}))) - L[k]) for k in NAMES}
    return L, dict(
        d1_mean=r(d1.mean()), d1_p10_p90=[r(np.quantile(d1, .1)), r(np.quantile(d1, .9))], d1_min_max=[r(d1.min()), r(d1.max())],
        d1_spread_p90_p10=r(np.quantile(d1, .9) - np.quantile(d1, .1)),
        d2_mean=r(d2.mean()), d2_p10_p90=[r(np.quantile(d2, .1)), r(np.quantile(d2, .9))], d2_min_max=[r(d2.min()), r(d2.max())],
        d2_spread_p90_p10=r(np.quantile(d2, .9) - np.quantile(d2, .1)),
        w1_minus_w2_spread_p90_p10=r(np.quantile(L["w1"] - L["w2"], .9) - np.quantile(L["w1"] - L["w2"], .1)),
        corr_d1_bass=r(np.corrcoef(d1, bass)[0, 1], 3), corr_d2_bass=r(np.corrcoef(d2, bass)[0, 1], 3),
        rankcorr_w1_w2=r(rank_corr(L["w1"], L["w2"]), 3),
        top10pct_overlap_w1_w2_pct=r(len(t1 & t2) / top * 100, 1),
        bass_add_up={k: r(v.mean()) for k, v in up.items()},
        bass_add_up_w0_range=[r(up["w0"].min()), r(up["w0"].max())],
        bass_add_up_w1_range=[r(up["w1"].min()), r(up["w1"].max())],
        bass_add_up_w2_range=[r(up["w2"].min()), r(up["w2"].max())],
    ), up


def wave_check(rng, spec_rows):
    """波形を作って測った大きさと、帯ごとの計算を照らし合わせる"""
    fs, dur = 32000, 4
    n = fs * dur
    f = np.fft.rfftfreq(n, 1 / fs)
    lo, hi = FB * 2 ** (-1 / 6), FB * 2 ** (1 / 6)
    out = []
    for spec in spec_rows:
        mag = np.zeros_like(f)
        for b in range(len(FB)):
            m = (f >= lo[b]) & (f < hi[b])
            mag[m] = np.sqrt(10 ** (spec[b] / 10) / m.sum())
        X = mag * np.exp(1j * rng.uniform(0, 2 * np.pi, len(f)))
        x = np.fft.irfft(X, n)
        x *= np.sqrt(10 ** (level(spec, 0) / 10) / np.mean(x ** 2))   # 重みなしの大きさに合わせる
        Xw = np.fft.rfft(x)
        row = {}
        for k in NAMES:
            wf = np.where(f > 0, wdb(k, np.maximum(f, 1e-9)), -np.inf) if k != "w0" else np.zeros_like(f)
            y = np.fft.irfft(Xw * 10 ** (wf / 20), n)
            row[k] = (10 * np.log10(np.mean(y ** 2)), level(spec, wdb(k, FB)))
        out.append(row)
    # 1つの高さの音
    tones = []
    for f0 in [63.0, 1000.0, 8000.0]:
        t = np.arange(n) / fs
        x = np.sqrt(2) * np.sin(2 * np.pi * f0 * t)   # 重みなし 0 dB
        Xw = np.fft.rfft(x)
        for k in ["w1", "w2"]:
            wf = np.where(f > 0, wdb(k, np.maximum(f, 1e-9)), -np.inf)
            y = np.fft.irfft(Xw * 10 ** (wf / 20), n)
            tones.append(abs(10 * np.log10(np.mean(y ** 2)) - wdb(k, f0)))
    diffs = [abs(a - b) for row in out for (a, b) in row.values()]
    return dict(n_songs=len(out), max_abs_diff_song_dB=r(max(diffs), 3), max_abs_diff_tone_dB=r(max(tones), 4))


def main():
    rng = np.random.default_rng(SEED)

    # ---- 1つの高さの音（式どおり） ----
    tones = pd.DataFrame(dict(freq=np.round(FB, 1), w0=0.0, w1=np.round(w1(FB), 2), w2=np.round(w2(FB), 2)))
    tones["w1_minus_w2"] = (tones.w1 - tones.w2).round(2)
    tones.to_csv(RES / "tones.csv", index=False)
    pick = {}
    for f0 in [31.5, 63, 125, 250, 1000, 4000, 8000]:
        pick[str(f0)] = dict(w1=r(w1(f0)), w2=r(w2(f0)), w1_minus_w2=r(w1(f0) - w2(f0)))

    # ---- 架空の曲 ----
    spec, tilt, bass, bright = make_songs(rng, N_SONG)
    L, res, up = analyse(spec, bass)
    songs = pd.DataFrame(dict(song=np.arange(N_SONG), tilt_db_per_oct=tilt, bass_bump_db=bass, bright_bump_db=bright,
                              L_w0=L["w0"], L_w1=L["w1"], L_w2=L["w2"],
                              up_bass6_w0=up["w0"], up_bass6_w1=up["w1"], up_bass6_w2=up["w2"]))
    songs.round(3).to_csv(DATA / "songs_levels.csv", index=False)
    pd.DataFrame(spec.round(3), columns=[f"band_{f:.0f}" for f in FB]).assign(song=np.arange(N_SONG)).to_csv(
        DATA / "songs_bands.csv", index=False)

    # 低い音のふくらみの大きさで分けたとき（0〜4 dB と 8〜12 dB）
    lo_b, hi_b = bass < 4, bass >= 8
    by_bass = dict(low_bass=dict(n=int(lo_b.sum()), d1=r((L["w1"] - L["w0"])[lo_b].mean()), d2=r((L["w2"] - L["w0"])[lo_b].mean())),
                   high_bass=dict(n=int(hi_b.sum()), d1=r((L["w1"] - L["w0"])[hi_b].mean()), d2=r((L["w2"] - L["w0"])[hi_b].mean())))

    # 配信先が③でそろえたとき、②で測った大きさの散らばり
    after_w2 = L["w1"] - L["w2"]

    # ---- 波形での照らし合わせ ----
    wc = wave_check(rng, spec[:5])

    # ---- 確かめ：低い音のふくらみの高さ × ③の上げ幅 × ③の下げ始め（27通り） ----
    grid = []
    for bc in [40.0, 60.0, 100.0]:
        sp_g, _, b_g, _ = make_songs(rng, 500, bump_c=bc)
        for sh in [2.0, 4.0, 6.0]:
            for hp in [25.0, 38.0, 60.0]:
                _, rg, _ = analyse(sp_g, b_g, dict(hp=hp, sh=sh))
                grid.append(dict(bump_center=bc, w2_shelf_db=sh, w2_highpass=hp,
                                 d1_spread=rg["d1_spread_p90_p10"], d2_spread=rg["d2_spread_p90_p10"],
                                 w1_minus_w2_spread=rg["w1_minus_w2_spread_p90_p10"],
                                 rankcorr_w1_w2=rg["rankcorr_w1_w2"], top10_overlap_pct=rg["top10pct_overlap_w1_w2_pct"],
                                 bass6_up_w0=rg["bass_add_up"]["w0"], bass6_up_w1=rg["bass_add_up"]["w1"], bass6_up_w2=rg["bass_add_up"]["w2"]))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gr = {c: [r(grid[c].min()), r(grid[c].max())] for c in grid.columns if c not in ("bump_center", "w2_shelf_db", "w2_highpass")}
    gr["n_w1_spread_gt_w2_spread"] = int((grid.d1_spread > grid.d2_spread).sum())
    gr["by_bump_center"] = {f"{bc:.0f}": dict(rankcorr=[r(g.rankcorr_w1_w2.min(), 3), r(g.rankcorr_w1_w2.max(), 3)],
                                              top10_overlap_pct=[r(g.top10_overlap_pct.min(), 1), r(g.top10_overlap_pct.max(), 1)])
                            for bc, g in grid.groupby("bump_center")}
    gr["w1_at_bump_centers"] = {f"{bc:.0f}": r(w1(bc)) for bc in [40.0, 60.0, 100.0]}
    gr["w2_at_bump_centers_base"] = {f"{bc:.0f}": r(w2(bc)) for bc in [40.0, 60.0, 100.0]}
    gr["n_d1_spread_gt_d2_spread"] = int((grid.d1_spread > grid.d2_spread).sum())
    gr["n_bass6_w0_gt_w2_gt_w1"] = int(((grid.bass6_up_w0 > grid.bass6_up_w2) & (grid.bass6_up_w2 > grid.bass6_up_w1)).sum())

    main_json = dict(
        setup=dict(bands_center=[r(f, 1) for f in FB], n_songs=N_SONG, level_unweighted=L_SET, bass_bump_center=BUMP_C,
                   bass_bump_width_oct=BUMP_W, bass_add_db=BASS_ADD, bass_add_bands_upto=130,
                   w3=dict(highpass=W3_HP, shelf_db=W3_SH, shelf_freq=W3_SF), names=NAMES),
        tones=pick,
        tones_range=dict(w1=[r(w1(FB).min()), r(w1(FB).max())], w2=[r(w2(FB).min()), r(w2(FB).max())]),
        songs=res, songs_by_bass=by_bass,
        w1_level_when_w2_equal=dict(p10=r(np.quantile(after_w2, .1)), p90=r(np.quantile(after_w2, .9)),
                                    spread=r(np.quantile(after_w2, .9) - np.quantile(after_w2, .1))),
        wave_check=wc, grid_ranges=gr, n_grid=int(len(grid)),
    )
    with open(RES / "a1142_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # ---- 図1：重みの形（1つの高さの音、式どおり） ----
    ff = np.geomspace(20, 16000, 400)
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    ax.plot(ff, np.zeros_like(ff), color=GRAY, lw=2, label=NAMES["w0"])
    ax.plot(ff, w1(ff), color=BLUE, lw=2, label=NAMES["w1"])
    ax.plot(ff, w2(ff), color=ORANGE, lw=2, label=NAMES["w2"])
    for f0, va in [(63, "top"), (1000, "bottom"), (8000, "top")]:
        for fn, col in [(w1, BLUE), (w2, ORANGE)]:
            v = float(fn(f0))
            ax.plot([f0], [v], "o", color=col, ms=5)
        ax.annotate(f"{f0:,} の音\n②{w1(f0):.2f}・③{w2(f0):.2f}", (f0, float(w1(f0))), textcoords="offset points",
                    xytext=(8, -28 if f0 == 63 else (10 if f0 == 1000 else -30)), fontsize=8.5)
    ax.set_xscale("log")
    ax.set_xticks([31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000])
    ax.set_xticklabels(["31.5", "63", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"])
    ax.set_xlabel("音の高さ（1秒あたりの振動の回数）")
    ax.set_ylabel("重み（dB）：重みなしとの差")
    ax.set_title("同じ dB の音でも、重みしだいで大きさの数字が変わる（式どおり）")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    ax.set_ylim(-45, 8)
    save(fig, "a1142_weights.png", "出典：" + SRC + "。②は広く使われる重み付けの形を式で写したもの、③は作成者が置いた式")

    # ---- 図2：重みなしで同じ大きさの曲を重みで測ると ----
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].scatter(bass, L["w1"] - L["w0"], s=6, color=BLUE, alpha=0.5, label=NAMES["w1"])
    axes[0].scatter(bass, L["w2"] - L["w0"], s=6, color=ORANGE, alpha=0.5, label=NAMES["w2"])
    axes[0].axhline(0, color=INK, lw=0.8)
    axes[0].set_xlabel("置いた低い音のふくらみ（dB）")
    axes[0].set_ylabel("重みを付けた大きさ−重みなし（dB）")
    axes[0].set_title("1,000曲（重みなしではどれも −16 dB）", fontsize=11)
    axes[0].legend(fontsize=8, frameon=False, markerscale=3, loc="lower left")
    axes[1].scatter(L["w2"], L["w1"], s=6, color=GRAY, alpha=0.6)
    top = N_SONG // 10
    t1 = np.argsort(-L["w1"])[:top]
    t2 = np.argsort(-L["w2"])[:top]
    both = np.intersect1d(t1, t2)
    axes[1].scatter(L["w2"][t1], L["w1"][t1], s=8, color=BLUE, label="②で上位1割")
    axes[1].scatter(L["w2"][t2], L["w1"][t2], s=8, color=ORANGE, label="③で上位1割")
    axes[1].scatter(L["w2"][both], L["w1"][both], s=10, color=GREEN, label=f"両方で上位1割（{len(both)}曲）")
    axes[1].set_xlabel("③で測った大きさ（dB）")
    axes[1].set_ylabel("②で測った大きさ（dB）")
    axes[1].set_title("どちらの重みで測るかで、上位が入れかわる", fontsize=11)
    axes[1].legend(fontsize=8, frameon=False, markerscale=2, loc="lower right")
    save(fig, "a1142_songs.png", "出典：" + SRC)

    # ---- 図3：低い音を +6 dB 足したときの上がり（＝配信先が下げる量） ----
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    keys = list(NAMES)
    vals = [res["bass_add_up"][k] for k in keys]
    cols = [GRAY, BLUE, ORANGE]
    ax.bar(range(3), vals, 0.55, color=cols)
    for i, v in enumerate(vals):
        rng_k = res[f"bass_add_up_{keys[i]}_range"]
        ax.text(i, v + 0.08, f"{v:.2f}\n（1,000曲で {rng_k[0]:.2f}〜{rng_k[1]:.2f}）", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["①重みなし", "②低い音を\n大きく下げる重み", "③低い音を少し下げ\n高い音を少し上げる重み"], fontsize=9)
    ax.set_ylabel("大きさの上がり（dB、1,000曲の平均）")
    ax.set_ylim(0, max(vals) * 1.45)
    ax.set_title("低い音（130 以下の帯）を +6 dB 足すと、大きさの数字はどれだけ上がるか")
    save(fig, "a1142_bass_add.png", "出典：" + SRC)


if __name__ == "__main__":
    main()
