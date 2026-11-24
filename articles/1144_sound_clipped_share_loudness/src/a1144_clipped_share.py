"""1144 上限を超えて切れた部分の割合は、大きさの数字にどう表れるのか？（架空のデータ）

作成者が式と乱数で作った架空の曲（波形、30秒）。音のもとは3種類（雑音に近い音・音程のはっきりした音・打つ音の多い音）。
いちばん大きい点がちょうど上限（振れ幅1.0、0 dB）になるようにそろえてから、音量を g dB 上げ、上限を超えた分は上限で切る。
切れた点の割合と、大きさ（強さの平均を dB にした値）・いちばん大きい点の値・その差・切れて変わった分の強さを比べる。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1144
SRC = "架空の曲の波形（作成者が式と乱数で作成、seed 1144）"
SR = 8000
DUR = 30
N = SR * DUR
MAT = {"noise": "雑音に近い音", "tone": "音程のはっきりした音", "hits": "打つ音の多い音"}


def db(p):
    return 10 * np.log10(np.maximum(p, 1e-30))


KER = np.hanning(11)[1:-1]


def smooth_noise(rng, n):
    """なめらかな雑音（隣どうしの点が近い値になるよう、短い窓でならした乱数。おもに1,000 Hz より下の音）"""
    return np.convolve(rng.standard_normal(n + len(KER)), KER, mode="valid")[:n]


def source(rng, kind, dyn):
    """強さの平均が1の音のもとに、3秒ごとに ±dyn dB の強弱を付け、いちばん大きい点を1.0にそろえる"""
    t = np.arange(N) / SR
    if kind == "noise":
        s = smooth_noise(rng, N)
    elif kind == "tone":
        f = rng.uniform(110, 330)
        s = sum(a * np.sin(2 * np.pi * k * f * t + rng.uniform(0, 6.3)) for k, a in [(1, 1.0), (2, 0.5), (3, 0.3)])
        s = s + 0.15 * smooth_noise(rng, N) / np.sqrt(np.sum(KER ** 2))
    else:
        env = np.zeros(N)
        hits = np.arange(0, N, SR // 4) + rng.integers(0, 200, N // (SR // 4) + 1)[:len(np.arange(0, N, SR // 4))]
        dec = np.exp(-np.arange(int(0.08 * SR)) / (0.02 * SR))
        for h in hits:
            e = min(N, h + len(dec)); env[h:e] += dec[:e - h] * rng.uniform(0.6, 1.0)
        s = smooth_noise(rng, N) * (env + 0.08)
    s = s / np.sqrt(np.mean(s ** 2))
    n_sec = N // (3 * SR)
    lv = np.repeat(rng.uniform(-dyn, dyn, n_sec), 3 * SR) if dyn > 0 else np.zeros(N)
    x = s * 10 ** (lv / 20)
    return x / np.abs(x).max()


def at_gain(x, g):
    xg = x * 10 ** (g / 20)
    y = np.clip(xg, -1.0, 1.0)
    p_x = np.mean(xg ** 2); p_y = np.mean(y ** 2)
    return {"gain_db": g, "clipped_pct": float(np.mean(np.abs(xg) > 1.0) * 100),
            "loud_unclipped_db": float(db(p_x)), "loud_db": float(db(p_y)),
            "shortfall_db": float(db(p_x) - db(p_y)),
            "peak_db": float(db(np.abs(y).max() ** 2)),
            "peak_minus_loud_db": float(db(np.abs(y).max() ** 2) - db(p_y)),
            "changed_part_db": float(db(np.mean((y - xg) ** 2)) - db(p_y))}


def gain_for(x, pct):
    """切れる点の割合が pct% になる音量の上げ幅（点の大きさの順から直接出す）"""
    a = np.sort(np.abs(x))[::-1]
    k = int(round(pct / 100 * len(a)))
    return float(-20 * np.log10(a[k]))


def gauss_formula(c):
    """強さ1の雑音（正規分布）を振れ幅 c で切ったときの強さの平均（式）"""
    phi = math.exp(-c * c / 2) / math.sqrt(2 * math.pi)
    Phi = 0.5 * (1 + math.erf(c / math.sqrt(2)))
    q = 1 - Phi
    return (2 * Phi - 1) - 2 * c * phi + 2 * c * c * q, 2 * q


def main():
    t0 = time.time()

    xs = {k: source(np.random.default_rng(SEED + i), k, 3.0) for i, k in enumerate(MAT)}

    # 1) 音量を0〜15 dB 上げたときの数字（3種類の音）
    rows = []
    for k, x in xs.items():
        for g in np.arange(0, 15.01, 0.5):
            r = at_gain(x, float(g)); r["material"] = MAT[k]; rows.append(r)
    sweep = pd.DataFrame(rows)[["material", "gain_db", "clipped_pct", "loud_unclipped_db", "loud_db", "shortfall_db",
                                "peak_db", "peak_minus_loud_db", "changed_part_db"]].round(4)
    sweep.to_csv(RES / "gain_sweep.csv", index=False)

    # 2) 切れた点の割合ごとの数字（0.1%・1%・5%・10%）
    tg = []
    for k, x in xs.items():
        base = at_gain(x, 0.0)
        for pct in [0.1, 1.0, 5.0, 10.0]:
            g = gain_for(x, pct); r = at_gain(x, g)
            tg.append({"material": MAT[k], "target_clipped_pct": pct, "gain_db": round(g, 2),
                       "clipped_pct": round(r["clipped_pct"], 3),
                       "loud_db": round(r["loud_db"], 2), "loud_gain_db": round(r["loud_db"] - base["loud_db"], 2),
                       "shortfall_db": round(r["shortfall_db"], 3), "peak_minus_loud_db": round(r["peak_minus_loud_db"], 2),
                       "peak_minus_loud_at_0_db": round(base["peak_minus_loud_db"], 2),
                       "changed_part_db": round(r["changed_part_db"], 1)})
    tg = pd.DataFrame(tg)
    tg.to_csv(RES / "by_clipped_share.csv", index=False)

    # 3) 式との照合：強弱を付けない雑音
    xg0 = np.random.default_rng(SEED + 10).standard_normal(N)
    form = []
    for pct in [0.1, 1.0, 5.0, 10.0]:
        a = np.sort(np.abs(xg0))[::-1]; c = a[int(round(pct / 100 * N))]
        y = np.clip(xg0, -c, c)
        sim = float(db(np.mean(xg0 ** 2)) - db(np.mean(y ** 2)))
        p_f, share_f = gauss_formula(float(c))
        form.append({"clipped_pct": pct, "clip_level_in_sd": round(float(c), 3),
                     "shortfall_sim_db": round(sim, 4), "shortfall_formula_db": round(float(-db(p_f)), 4)})
    form = pd.DataFrame(form)
    form.to_csv(RES / "formula_check.csv", index=False)

    # 4) 200曲：大きさの数字から切れた割合が読めるか
    songs = []
    for i in range(200):
        r2 = np.random.default_rng(SEED * 100 + i)
        k = list(MAT)[r2.integers(0, 3)]; dyn = r2.uniform(0, 6); g = r2.uniform(0, 12); trim = r2.uniform(0, 6)
        x = source(r2, k, dyn); r = at_gain(x, g)
        # 切ったあと、曲ごとに 0〜6 dB 下げて仕上げる（いちばん大きい点も下がる）
        songs.append({"song_id": i + 1, "material": MAT[k], "dyn_db": round(dyn, 3), "gain_db": round(g, 3),
                      "trim_db": round(trim, 3),
                      "clipped_pct": round(r["clipped_pct"], 4), "loud_db": round(r["loud_db"] - trim, 3),
                      "peak_db": round(r["peak_db"] - trim, 3), "peak_minus_loud_db": round(r["peak_minus_loud_db"], 3)})
    songs = pd.DataFrame(songs)
    songs.to_csv(DATA / "songs.csv", index=False)
    lo = np.floor(songs.loud_db.median())
    band = songs[(songs.loud_db >= lo) & (songs.loud_db < lo + 1)]
    song_info = {"n_songs": len(songs), "band_loud_from": float(lo), "band_loud_to": float(lo + 1), "band_n": len(band),
                 "band_clipped_min": float(band.clipped_pct.min()), "band_clipped_max": float(band.clipped_pct.max()),
                 "band_ptl_min": float(band.peak_minus_loud_db.min()), "band_ptl_max": float(band.peak_minus_loud_db.max()),
                 "corr_clipped_loud": round(float(np.corrcoef(songs.clipped_pct, songs.loud_db)[0, 1]), 3),
                 "corr_clipped_peak_minus_loud": round(float(np.corrcoef(songs.clipped_pct, songs.peak_minus_loud_db)[0, 1]), 3)}
    by_mat = songs.groupby("material", sort=False).apply(
        lambda g: pd.Series({"n": len(g), "corr_clipped_peak_minus_loud": round(float(np.corrcoef(g.clipped_pct, g.peak_minus_loud_db)[0, 1]), 3),
                             "corr_clipped_loud": round(float(np.corrcoef(g.clipped_pct, g.loud_db)[0, 1]), 3)})).reset_index()
    by_mat.to_csv(RES / "songs_corr_by_material.csv", index=False)
    # 同じ大きさ（1 dB の幅）の中の、切れていない曲と5%以上切れた曲
    song_info["band_unclipped_n"] = int((band.clipped_pct == 0).sum())
    song_info["band_5pct_or_more_n"] = int((band.clipped_pct >= 5).sum())

    # 5) あとから処理したときに、切れた点を数えられるか
    x = xs["noise"]; g = gain_for(x, 1.0)
    xg = x * 10 ** (g / 20); y = np.clip(xg, -1, 1); true_pct = float(np.mean(np.abs(xg) > 1) * 100)
    yu = x.copy()  # 切れていない曲（上げない。いちばん大きい点がちょうど上限）
    rd = np.random.default_rng(SEED + 20)

    def q16(v):
        return np.round(v * 32767) / 32767

    procs = {"そのまま": lambda v: v,
             "16ビットで保存": q16,
             "0.5 dB 下げて16ビットで保存": lambda v: q16(v * 10 ** (-0.5 / 20)),
             "0.5 dB 下げ、ごく小さな雑音（−90 dB）を足して16ビットで保存": lambda v: q16(v * 10 ** (-0.5 / 20) + 10 ** (-90 / 20) * rd.standard_normal(len(v)))}

    def count(v):
        a = np.abs(v); m = a.max()
        c1 = np.mean(a >= 1.0) * 100
        near = a >= 0.999 * m
        c2 = np.mean(near) * 100
        same = np.r_[False, np.diff(v) == 0]
        run = np.zeros(len(v), bool)
        # 同じ値が3点以上続く点（いちばん大きい値の99.9%以上のところだけ）
        eq = same & near
        idx = np.where(eq[1:] & eq[:-1])[0]
        run[idx] = True; run[idx + 1] = True; run[idx + 2] = True
        c3 = np.mean(run & near) * 100
        return round(float(c1), 3), round(float(c2), 3), round(float(c3), 3)

    det = []
    for name, f in procs.items():
        for which, v in [("1%切れた曲", y), ("切れていない曲", yu)]:
            c1, c2, c3 = count(f(v.copy()))
            det.append({"process": name, "song": which, "true_clipped_pct": round(true_pct, 3) if which == "1%切れた曲" else 0.0,
                        "count_at_limit_pct": c1, "count_near_max_pct": c2, "count_flat_run_pct": c3})
    det = pd.DataFrame(det)
    det.to_csv(RES / "detect_after_processing.csv", index=False)

    # 6) 置き方を変えた27通り（音のもと3×強弱の幅3×切れた割合3）
    grid = []
    for i, k in enumerate(MAT):
        for dyn in [0.0, 3.0, 6.0]:
            x = source(np.random.default_rng(SEED * 10 + i * 7 + int(dyn)), k, dyn)
            b = at_gain(x, 0.0)
            for pct in [0.1, 1.0, 5.0]:
                g = gain_for(x, pct); r = at_gain(x, g)
                grid.append({"material": MAT[k], "dyn_db": dyn, "target_clipped_pct": pct, "gain_db": round(g, 2),
                             "loud_gain_db": round(r["loud_db"] - b["loud_db"], 2), "shortfall_db": round(r["shortfall_db"], 3),
                             "changed_part_db": round(r["changed_part_db"], 1),
                             "peak_minus_loud_drop_db": round(b["peak_minus_loud_db"] - r["peak_minus_loud_db"], 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g1 = grid[grid.target_clipped_pct == 1.0]
    gsum = {"grid_n": len(grid),
            "grid1_gain_min": float(g1.gain_db.min()), "grid1_gain_max": float(g1.gain_db.max()),
            "grid1_shortfall_min": float(g1.shortfall_db.min()), "grid1_shortfall_max": float(g1.shortfall_db.max()),
            "grid1_changed_min": float(g1.changed_part_db.min()), "grid1_changed_max": float(g1.changed_part_db.max()),
            "grid1_ptl_drop_min": float(g1.peak_minus_loud_drop_db.min()), "grid1_ptl_drop_max": float(g1.peak_minus_loud_drop_db.max()),
            "grid_all_shortfall_max": float(grid.shortfall_db.max()),
            "grid5_shortfall_min": float(grid[grid.target_clipped_pct == 5.0].shortfall_db.min()),
            "grid5_shortfall_max": float(grid[grid.target_clipped_pct == 5.0].shortfall_db.max())}

    t1 = tg.set_index(["material", "target_clipped_pct"])
    head = {"noise_1pct_gain": float(t1.loc[("雑音に近い音", 1.0), "gain_db"]),
            "noise_1pct_loud_gain": float(t1.loc[("雑音に近い音", 1.0), "loud_gain_db"]),
            "noise_1pct_shortfall": float(t1.loc[("雑音に近い音", 1.0), "shortfall_db"]),
            "noise_1pct_changed": float(t1.loc[("雑音に近い音", 1.0), "changed_part_db"]),
            "noise_10pct_gain": float(t1.loc[("雑音に近い音", 10.0), "gain_db"]),
            "noise_10pct_shortfall": float(t1.loc[("雑音に近い音", 10.0), "shortfall_db"]),
            "formula_maxabs_diff": round(float((form.shortfall_sim_db - form.shortfall_formula_db).abs().max()), 4),
            **song_info, **gsum}
    out = {"headline": head, "by_clipped_share": tg.to_dict("records"), "formula_check": form.to_dict("records"),
           "detect_after_processing": det.to_dict("records"), "songs_corr_by_material": by_mat.to_dict("records")}
    json.dump(out, open(RES / "a1144_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：音量を上げたときの大きさと、切れた点の割合
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    cols = {"雑音に近い音": BLUE, "音程のはっきりした音": ORANGE, "打つ音の多い音": GREEN}
    for m, g in sweep.groupby("material", sort=False):
        axs[0].plot(g.gain_db, g.loud_db - g.loud_db.iloc[0], color=cols[m], lw=1.8, label=m)
        axs[1].plot(g.gain_db, g.clipped_pct, color=cols[m], lw=1.8, label=m)
    axs[0].plot([0, 15], [0, 15], color=GRAY, lw=1, ls="--", label="切れなければ（上げた分だけ）")
    axs[0].set_xlabel("音量を上げた量（dB）"); axs[0].set_ylabel("大きさの増え（dB）"); axs[0].set_ylim(0, 15.5); axs[0].set_xlim(0, 15)
    axs[0].set_title("大きさの数字は、上げた分ほど増えない")
    axs[0].legend(fontsize=8, frameon=False)
    axs[1].set_xlabel("音量を上げた量（dB）"); axs[1].set_ylabel("上限で切れた点の割合（%）"); axs[1].set_ylim(0, None); axs[1].set_xlim(0, 15)
    axs[1].set_title("切れた点の割合")
    fig.tight_layout()
    save(fig, "a1144_gain.png", SRC)

    # 図2：200曲の大きさと切れた割合
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    for m, g in songs.groupby("material", sort=False):
        axs[0].scatter(g.loud_db, g.clipped_pct, s=12, color=cols[m], label=m)
        axs[1].scatter(g.peak_minus_loud_db, g.clipped_pct, s=12, color=cols[m], label=m)
    axs[0].axvspan(lo, lo + 1, color=LIGHT, alpha=0.5, lw=0)
    axs[0].set_xlabel("大きさ（dB）"); axs[0].set_ylabel("上限で切れた点の割合（%）"); axs[0].set_ylim(0, None)
    axs[0].set_title("大きさだけでは、切れた割合は読めない")
    axs[1].set_xlabel("いちばん大きい点と大きさの差（dB）"); axs[1].set_ylim(0, None)
    axs[1].set_title("差の小ささは手がかりだが、音のもとで違う")
    axs[1].set_ylabel("上限で切れた点の割合（%）")
    axs[0].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    save(fig, "a1144_songs.png", SRC)

    # 図3：あとから処理したときの数え方
    fig, ax = plt.subplots(figsize=(9, 4.2))
    d1 = det[det.song == "1%切れた曲"].reset_index(drop=True)
    w = 0.25; xi = np.arange(len(d1))
    for j, (c, name, col) in enumerate([("count_at_limit_pct", "上限ちょうどの点", BLUE),
                                        ("count_near_max_pct", "いちばん大きい値の99.9%以上", ORANGE),
                                        ("count_flat_run_pct", "その中で同じ値が3点以上続く点", GREEN)]):
        ax.bar(xi + (j - 1) * w, d1[c], width=w, color=col, label=name)
        for xx, v in zip(xi + (j - 1) * w, d1[c]):
            ax.text(xx, v + 0.02, f"{v:.3f}", ha="center", fontsize=7)
    ax.axhline(true_pct, color=INK, ls="--", lw=1, label=f"本当に切れた点（{true_pct:.3f}%）")
    ax.set_xticks(xi); ax.set_xticklabels(["そのまま", "16ビットで保存", "0.5 dB 下げて\n16ビットで保存", "0.5 dB 下げ、ごく小さな\n雑音を足して16ビット"], fontsize=9)
    ax.set_ylabel("数えた切れた点の割合（%）"); ax.set_ylim(0, 1.6)
    ax.set_title("1%切れた曲を、あとから処理してから数える（雑音に近い音）")
    ax.legend(fontsize=8, frameon=False, loc="upper center", ncol=2)
    save(fig, "a1144_detect.png", SRC)

    head["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(head, ensure_ascii=False, indent=1))
    print(tg.to_string()); print(form); print(det.to_string()); print(by_mat)


if __name__ == "__main__":
    main()
