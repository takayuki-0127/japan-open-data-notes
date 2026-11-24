"""1146 短い区間ごとに測った大きさの最大値は、区間の長さでどう変わるのか？（架空のデータ）

作成者が式と乱数で作った架空の曲（波形、1秒あたり2,000点、長さ120秒）の大きさを、
長さ w 秒の区間ごとに測り（区間の中の波の値の二乗平均を 10×log10 で dB にしたもの）、
区間を0.01秒ずつずらしたときの最大値が、曲全体の大きさから何dB上に出るかを数える。
曲は「でたらめな雑音×大きさの形」。大きさの形は、①部分ごとの大きさ（8〜20秒ごとに上下）と、
②0.5秒ごとの短い強い音（強さ・長さを曲ごとに置く）の掛け合わせ。どの曲も全体の大きさを−20dBにそろえる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1146
SRC = "架空の曲（作成者が式と乱数で作成、seed 1146）"
SR = 2000                 # 1秒あたりの点の数
BLK = 20                  # 0.01秒＝20点（区間をずらす刻み）
DUR = 120.0               # 曲の長さ（秒）
LEVEL = -20.0             # 曲全体の大きさ（dB）
WINDOWS = [0.05, 0.1, 0.4, 1.0, 3.0, 10.0, 30.0]
N_SONG = 200
BEAT = 0.5                # 短い強い音の間隔（秒）


def r(x, d=3):
    return round(float(x), d)


def q(a, p):
    return float(np.quantile(a, p))


def envelope(rng, n, burst_db, burst_len, sec_sd):
    """大きさの形（二乗の値、平均を1にそろえる前）"""
    t = np.arange(n) / SR
    # ① 部分ごとの大きさ：8〜20秒ごとに区切り、各部分の上下は平均0・標準偏差 sec_sd dB
    sec = np.zeros(n)
    s = 0.0
    while s < DUR:
        e = s + rng.uniform(8, 20)
        sec[(t >= s) & (t < e)] = rng.normal(0, sec_sd) if sec_sd > 0 else 0.0
        s = e
    # ② 0.5秒ごとの短い強い音：始まりで地の音より burst_db 上、長さ burst_len 秒で 1/e に弱まる
    if burst_db > 0:
        start = rng.uniform(0, BEAT)
        ph = np.mod(t - start, BEAT)
        add = 10 ** (burst_db / 10) * np.exp(-ph / burst_len)
    else:
        add = np.zeros(n)
    return 10 ** (sec / 10) * (1 + add)


def make_song(rng, burst_db, burst_len, sec_sd, dur=DUR):
    n = int(SR * dur)
    p = envelope(rng, n, burst_db, burst_len, sec_sd) if dur == DUR else None
    if p is None:
        p = np.ones(n)
    x = rng.standard_normal(n) * np.sqrt(p)
    return x * np.sqrt(10 ** (LEVEL / 10) / np.mean(x ** 2))


def block_power(x):
    return np.mean(x.reshape(-1, BLK) ** 2, axis=1)


def win_levels(bp, w, hop_blocks=1):
    """長さ w 秒の区間ごとの大きさ（dB）。hop_blocks ブロックずつずらす"""
    k = int(round(w * SR / BLK))
    c = np.concatenate([[0.0], np.cumsum(bp)])
    m = (c[k:] - c[:-k]) / k
    m = m[::hop_blocks]
    return 10 * np.log10(m)


def whole(x):
    return 10 * np.log10(np.mean(x ** 2))


def ranks(a):
    o = np.argsort(a, kind="stable")
    rk = np.empty(len(a))
    rk[o] = np.arange(len(a))
    return rk


def rank_corr(a, b):
    return float(np.corrcoef(ranks(a), ranks(b))[0, 1])


def flip_share(a, b):
    """曲の組のうち、a で大きいほうと b で大きいほうが入れかわる割合"""
    da = a[:, None] - a[None, :]
    db_ = b[:, None] - b[None, :]
    iu = np.triu_indices(len(a), 1)
    return float(np.mean(da[iu] * db_[iu] < 0))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"settings": {"sample_rate": SR, "step_sec": BLK / SR, "duration_sec": DUR, "whole_level_db": LEVEL,
                        "windows_sec": WINDOWS, "songs": N_SONG, "beat_sec": BEAT, "seed": SEED,
                        "burst_db_range": [0, 12], "burst_len_sec_range": [0.02, 0.06], "section_sd_db_range": [0, 4]}}

    # ① 例の2曲：A＝短い強い音なし・部分ごとの上下が大きい、B＝上下なし・短い強い音が強い
    ex = {"A（部分ごとの上下が大きい）": (0.0, 0.04, 4.0), "B（短い強い音が強い）": (12.0, 0.03, 0.0)}
    ex_rows, ex_trace = [], {}
    for name, (bd, bl, sd) in ex.items():
        x = make_song(rng, bd, bl, sd)
        bp = block_power(x)
        for w in WINDOWS:
            lv = win_levels(bp, w)
            ex_rows.append({"song": name, "window_sec": w, "max_db": r(lv.max(), 3), "max_minus_whole_db": r(lv.max() - whole(x), 3)})
        ex_trace[name] = {w: win_levels(bp, w) for w in [0.4, 3.0]}
    exd = pd.DataFrame(ex_rows)
    exd.to_csv(RES / "example_two_songs.csv", index=False)
    out["example_two_songs"] = ex_rows

    # ② 架空の曲200曲：強い音の強さ0〜12dB、長さ0.02〜0.06秒、部分ごとの上下0〜4dB（それぞれ一様）
    par = np.column_stack([rng.uniform(0, 12, N_SONG), rng.uniform(0.02, 0.06, N_SONG), rng.uniform(0, 4, N_SONG)])
    mx = np.zeros((N_SONG, len(WINDOWS)))
    mx_nonover = np.zeros((N_SONG, 2))
    for i in range(N_SONG):
        x = make_song(rng, *par[i])
        bp = block_power(x)
        for j, w in enumerate(WINDOWS):
            mx[i, j] = win_levels(bp, w).max() - LEVEL
        for j, w in enumerate([0.4, 3.0]):
            k = int(round(w * SR / BLK))
            mx_nonover[i, j] = win_levels(bp, w, hop_blocks=k).max() - LEVEL
    songs = pd.DataFrame({"song": np.arange(N_SONG), "burst_db": np.round(par[:, 0], 3), "burst_len_sec": np.round(par[:, 1], 4),
                          "section_sd_db": np.round(par[:, 2], 3)})
    for j, w in enumerate(WINDOWS):
        songs[f"max_{w}s_minus_whole_db"] = np.round(mx[:, j], 3)
    songs["max_0.4s_no_overlap_minus_whole_db"] = np.round(mx_nonover[:, 0], 3)
    songs["max_3.0s_no_overlap_minus_whole_db"] = np.round(mx_nonover[:, 1], 3)
    songs.to_csv(DATA / "songs.csv", index=False)

    by_w = []
    for j, w in enumerate(WINDOWS):
        v = mx[:, j]
        by_w.append({"window_sec": w, "mean_max_minus_whole_db": r(v.mean()), "median": r(np.median(v)), "p05": r(q(v, .05)),
                     "p95": r(q(v, .95)), "min": r(v.min()), "max": r(v.max())})
    pd.DataFrame(by_w).to_csv(RES / "by_window.csv", index=False)
    out["by_window"] = by_w
    j04, j3 = WINDOWS.index(0.4), WINDOWS.index(3.0)
    j01, j10, j005 = WINDOWS.index(0.1), WINDOWS.index(10.0), WINDOWS.index(0.05)
    out["songs200"] = {
        "mean_gap_0.4s_minus_3s_db": r(np.mean(mx[:, j04] - mx[:, j3])),
        "rank_corr_0.4s_vs_3s": r(rank_corr(mx[:, j04], mx[:, j3]), 4),
        "rank_corr_0.1s_vs_10s": r(rank_corr(mx[:, j01], mx[:, j10]), 4),
        "pair_flip_share_0.4s_vs_3s": r(flip_share(mx[:, j04], mx[:, j3]), 4),
        "pair_flip_share_0.1s_vs_10s": r(flip_share(mx[:, j01], mx[:, j10]), 4),
        "mean_gap_0.05s_minus_3s_db": r(np.mean(mx[:, j005] - mx[:, j3])),
        "rank_corr_0.05s_vs_3s": r(rank_corr(mx[:, j005], mx[:, j3]), 4),
        "pair_flip_share_0.05s_vs_3s": r(flip_share(mx[:, j005], mx[:, j3]), 4),
        "corr_burst_db_vs_max0.05": r(np.corrcoef(par[:, 0], mx[:, j005])[0, 1], 4),
        "share_songs_max0.05_above_3s_by_3db": r(np.mean(mx[:, j005] - mx[:, j3] > 3), 4),
        "top10_overlap_0.4s_vs_3s": int(len(set(np.argsort(-mx[:, j04])[:10]) & set(np.argsort(-mx[:, j3])[:10]))),
        "corr_burst_db_vs_max0.4": r(np.corrcoef(par[:, 0], mx[:, j04])[0, 1], 4),
        "corr_section_sd_vs_max3": r(np.corrcoef(par[:, 2], mx[:, j3])[0, 1], 4),
        "corr_burst_db_vs_max3": r(np.corrcoef(par[:, 0], mx[:, j3])[0, 1], 4),
        "corr_section_sd_vs_max0.4": r(np.corrcoef(par[:, 2], mx[:, j04])[0, 1], 4),
        "nonoverlap_lower_0.4s_mean_db": r(np.mean(mx[:, j04] - mx_nonover[:, 0])),
        "nonoverlap_lower_0.4s_max_db": r(np.max(mx[:, j04] - mx_nonover[:, 0])),
        "nonoverlap_lower_3s_mean_db": r(np.mean(mx[:, j3] - mx_nonover[:, 1])),
        "nonoverlap_lower_3s_max_db": r(np.max(mx[:, j3] - mx_nonover[:, 1])),
    }

    # ③ 大きさの形がない一様な雑音：でたらめさだけで最大値は上に出る。曲の長さでも変わる
    steady = []
    for dur in [30.0, 120.0, 480.0]:
        vals = {w: [] for w in WINDOWS}
        for _ in range(20):
            n = int(SR * dur)
            x = rng.standard_normal(n)
            x = x * np.sqrt(10 ** (LEVEL / 10) / np.mean(x ** 2))
            bp = block_power(x)
            for w in WINDOWS:
                if w < dur:
                    vals[w].append(win_levels(bp, w).max() - LEVEL)
        for w in WINDOWS:
            if vals[w]:
                steady.append({"duration_sec": dur, "window_sec": w, "mean_max_minus_whole_db": r(np.mean(vals[w]))})
    pd.DataFrame(steady).to_csv(RES / "steady_noise.csv", index=False)
    out["steady_noise"] = steady

    # 確かめ：強い音の強さの上限・長さ・部分ごとの上下の上限を変えた27通り（各40曲。強さは0〜上限、長さは置いた値の0.5〜1.5倍、上下は0〜上限で一様）
    grid = []
    for bd in [6.0, 12.0, 18.0]:
        for bl in [0.02, 0.05, 0.1]:
            for sd in [1.0, 3.0, 5.0]:
                m = np.zeros((40, len(WINDOWS)))
                for i in range(40):
                    x = make_song(rng, rng.uniform(0, bd), bl * rng.uniform(0.5, 1.5), rng.uniform(0, sd))
                    bp = block_power(x)
                    for j, w in enumerate(WINDOWS):
                        m[i, j] = win_levels(bp, w).max() - LEVEL
                grid.append({"burst_db": bd, "burst_len_sec": bl, "section_sd_db": sd,
                             "mean_max_0.4s": r(m[:, j04].mean()), "mean_max_3s": r(m[:, j3].mean()),
                             "mean_gap_0.4s_minus_3s": r(np.mean(m[:, j04] - m[:, j3])),
                             "rank_corr_0.4s_vs_3s": r(rank_corr(m[:, j04], m[:, j3]), 4),
                             "pair_flip_share_0.4s_vs_3s": r(flip_share(m[:, j04], m[:, j3]), 4),
                             "mean_gap_0.05s_minus_3s": r(np.mean(m[:, j005] - m[:, j3])),
                             "pair_flip_share_0.05s_vs_3s": r(flip_share(m[:, j005], m[:, j3]), 4)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    out["grid_summary"] = {"n": len(g), "gap_min": r(g["mean_gap_0.4s_minus_3s"].min()),
                           "gap_max": r(g["mean_gap_0.4s_minus_3s"].max()),
                           "flip_min": r(g["pair_flip_share_0.4s_vs_3s"].min(), 4), "flip_max": r(g["pair_flip_share_0.4s_vs_3s"].max(), 4),
                           "rank_corr_min": r(g["rank_corr_0.4s_vs_3s"].min(), 4), "rank_corr_max": r(g["rank_corr_0.4s_vs_3s"].max(), 4),
                           "n_gap_positive": int((g["mean_gap_0.4s_minus_3s"] > 0).sum()),
                           "gap005_min": r(g["mean_gap_0.05s_minus_3s"].min()), "gap005_max": r(g["mean_gap_0.05s_minus_3s"].max()),
                           "flip005_min": r(g["pair_flip_share_0.05s_vs_3s"].min(), 4), "flip005_max": r(g["pair_flip_share_0.05s_vs_3s"].max(), 4)}

    # ---- 図 ----
    # 図1：例の曲Bの、0.4秒と3秒の区間で測った大きさ（はじめの20秒）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    nm = "B（短い強い音が強い）"
    for w, c in [(0.4, ORANGE), (3.0, BLUE)]:
        lv = ex_trace[nm][w]
        tt = (np.arange(len(lv)) * BLK / SR) + w
        sel = tt <= 20
        ax.plot(tt[sel], lv[sel], color=c, lw=1.2, label=f"{w:g}秒の区間（区間の終わりの時刻に描く）")
    ax.axhline(LEVEL, color=GRAY, ls="--", lw=1, label="曲全体の大きさ（−20dB）")
    ax.set_xlabel("曲の始めからの時間（秒、はじめの20秒）")
    ax.set_ylabel("区間ごとの大きさ（dB）")
    ax.set_xlim(0, 20)
    lv04 = ex_trace[nm][0.4][: int(20 * SR / BLK)]
    ax.set_ylim(lv04.min() - 1.6, lv04.max() + 0.3)
    ax.legend(frameon=False, loc="lower right", fontsize=9, ncol=2)
    ax.set_title("同じ曲でも、短い区間で測ると細かく上下する\n（例の曲B：0.5秒ごとの強い音が地の音より12dB上）")
    save(fig, "a1146_trace.png", SRC)

    # 図2：区間の長さと最大値（200曲の中央値と5〜95%、例の2曲）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    xs = np.arange(len(WINDOWS))
    bw = pd.DataFrame(by_w)
    ax.fill_between(xs, bw.p05, bw.p95, color=LIGHT, alpha=0.6, label="200曲の5〜95%")
    ax.plot(xs, bw["median"], color=GRAY, marker="o", label="200曲の中央値")
    for (name, c) in zip(ex.keys(), [BLUE, ORANGE]):
        s = exd[exd.song == name]
        ax.plot(xs, s.max_minus_whole_db, color=c, marker="s", label=f"例の曲{name}")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{w:g}" for w in WINDOWS])
    ax.set_xlabel("区間の長さ（秒、目盛りは等間隔ではない）")
    ax.set_ylabel("最大値 − 曲全体の大きさ（dB）")
    ax.set_ylim(0, max(bw.p95.max(), exd.max_minus_whole_db.max()) + 1.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("区間を短くするほど、最大値は曲全体より上に出る\n（どの曲も全体は−20dBにそろえた。例の2曲は区間の長さで上下が入れかわる）")
    save(fig, "a1146_by_window.png", SRC)

    # 図3：0.4秒・0.05秒と3秒の最大値（200曲の散らばり）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.4), sharex=True, sharey=True)
    for ax, j, key in [(axes[0], j04, "0.4s"), (axes[1], j005, "0.05s")]:
        sc = ax.scatter(mx[:, j3], mx[:, j], c=par[:, 0], cmap="Blues", vmin=0, vmax=12, s=14, edgecolor=GRAY, linewidth=0.3)
        fs = out["songs200"][f"pair_flip_share_{key}_vs_3s"]
        ax.set_title(f"{key[:-1]}秒と3秒：曲の組の{fs*100:.2f}%で入れかわった", fontsize=11)
        ax.set_xlabel("3秒の区間で測った最大値 − 曲全体（dB）")
        ax.set_xlim(0, mx[:, j3].max() + 0.5)
        ax.set_ylim(0, max(mx[:, j04].max(), mx[:, j005].max()) + 0.5)
    axes[0].set_ylabel("短い区間で測った最大値 − 曲全体（dB）")
    cb = fig.colorbar(sc, ax=axes)
    cb.set_label("0.5秒ごとの強い音の強さ（dB）")
    fig.suptitle("区間の長さを変えると、どちらの曲の最大値が大きいかが入れかわる（200曲）", y=1.02)
    save(fig, "a1146_scatter.png", SRC)

    with open(RES / "a1146_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(exd.to_string()); print(bw.to_string()); print(json.dumps(out["songs200"], ensure_ascii=False, indent=1))
    print(pd.DataFrame(steady).to_string()); print(g.to_string()); print(out["grid_summary"])
    print("sec", time.time() - t0)


if __name__ == "__main__":
    main()
