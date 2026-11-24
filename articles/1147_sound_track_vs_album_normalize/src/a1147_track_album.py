"""1147 曲ごとに大きさをそろえる再生と、アルバム全体でそろえる再生では、曲どうしの強弱の差はどう残るのか？（架空のデータ）

作成者が置いた架空のアルバム（1枚10曲）の、曲ごとの大きさ（dB）・長さ・いちばん大きい瞬間（ピーク）から、
3つの再生のしかたで実際に鳴る大きさを計算し、作り手が置いた曲どうしの強弱の差がどれだけ残るかを数える。
・そのまま：何もしない
・曲ごと：曲ごとに、目標の大きさ（−14dB）との差だけ上げ下げする
・アルバムごと：アルバム全体の大きさ（曲の長さで重みを付けた二乗平均の dB）と目標の差だけ、全曲を同じだけ上げ下げする
上げるときは、ピークが−1dB を超えない分までしか上げない（基本）。下げるときは目標まで下げる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1147
SRC = "架空のアルバムの曲の大きさ（作成者が置いた値からの乱数、seed 1147）"
N_ALB = 300
N_TRK = 10
TARGET = -14.0
CEIL = -1.0
LOUD_MAX = -4.0
MODES = ["そのまま", "曲ごと", "アルバムごと"]


def r(x, d=3):
    return round(float(x), d)


def q(a, p):
    return float(np.quantile(a, p))


def make_albums(rng, n_alb, spread_sd=3.0, crest_lo=8.0, crest_hi=20.0):
    """作り手が置いた曲どうしの差（offset）と、アルバムの作りの大きさ（master）から曲の大きさを作る"""
    master = rng.uniform(-18, -8, n_alb)
    off = rng.normal(0, spread_sd, (n_alb, N_TRK))
    off = off - off.mean(axis=1, keepdims=True)
    loud = master[:, None] + off
    loud = loud - np.maximum(0, loud.max(axis=1, keepdims=True) - LOUD_MAX)   # いちばん大きい曲が−4dBを超えるアルバムは全体を下げる
    dur = rng.uniform(150, 330, (n_alb, N_TRK))
    crest = rng.uniform(crest_lo, crest_hi, (n_alb, N_TRK))
    peak = np.minimum(loud + crest, -0.1)          # ピークは0dBを超えない（超える分は作るときに抑えたと置く）
    return {"master": master, "off": off, "loud": loud, "dur": dur, "peak": peak}


def album_level(loud, dur):
    return 10 * np.log10(np.sum(dur * 10 ** (loud / 10), axis=1) / np.sum(dur, axis=1))


def cap_raise(g, room):
    """下げるときはそのまま。上げるときは、ピークが上限を超えない分（room、0未満なら0）まで"""
    return np.where(g > 0, np.minimum(g, np.maximum(room, 0)), g)


def play(a, mode, target=TARGET, ceil=CEIL, limit=True):
    loud, peak = a["loud"], a["peak"]
    if mode == "そのまま":
        g = np.zeros_like(loud)
    elif mode == "曲ごと":
        g = target - loud
        if limit:
            g = cap_raise(g, ceil - peak)
    else:
        al = album_level(loud, a["dur"])
        g = np.repeat((target - al)[:, None], N_TRK, axis=1)
        if limit:
            g = cap_raise(g, np.repeat((ceil - peak.max(axis=1))[:, None], N_TRK, axis=1))
    return loud + g, g


def retained(played, off):
    """アルバムの中の差がどれだけ残るか：鳴る大きさの最大−最小 ÷ 作り手の差の最大−最小、と、作り手の差への傾き"""
    rng_p = played.max(axis=1) - played.min(axis=1)
    rng_o = off.max(axis=1) - off.min(axis=1)
    pc = played - played.mean(axis=1, keepdims=True)
    slope = np.sum(pc * off, axis=1) / np.sum(off * off, axis=1)
    return rng_p / rng_o, slope


def corr_rows(x, y):
    xc = x - x.mean(axis=1, keepdims=True)
    yc = y - y.mean(axis=1, keepdims=True)
    den = np.sqrt(np.sum(xc ** 2, axis=1) * np.sum(yc ** 2, axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        c = np.sum(xc * yc, axis=1) / den
    return c


def shuffle_stats(rng, played, n_list=2000, length=20):
    flat = played.ravel()
    idx = rng.integers(0, flat.size, (n_list, length))
    p = flat[idx]
    jumps = np.abs(np.diff(p, axis=1))
    return {"sd_in_list_db": r(np.mean(p.std(axis=1))), "mean_jump_db": r(jumps.mean()),
            "share_jump_over_6db": r(np.mean(jumps > 6), 4)}


def summarize(a, label, rng, target=TARGET, limit=True):
    rows = []
    for m in MODES:
        p, g = play(a, m, target=target, limit=limit)
        ret, slope = retained(p, a["off"])
        c = corr_rows(p, a["off"])
        rel = (p - p.mean(axis=1, keepdims=True)) - a["off"]
        within_sd = p.std(axis=1)
        row = {"case": label, "mode": m, "limit_peak": limit,
               "mean_range_retained": r(np.mean(ret), 4), "mean_slope_on_intended": r(np.mean(slope), 4),
               "mean_corr_with_intended": r(np.nanmean(c), 4) if np.isfinite(c).any() else None,
               "mean_abs_error_vs_intended_db": r(np.mean(np.abs(rel))),
               "mean_within_album_sd_db": r(np.mean(within_sd)),
               "share_tracks_below_target_by_3db": r(np.mean(p < target - 3), 4),
               "share_tracks_limited": r(np.mean(np.abs(g - (target - a["loud"])) > 1e-9), 4) if m == "曲ごと" else None,
               "mean_played_db": r(np.mean(p))}
        row.update({f"shuffle_{k}": v for k, v in shuffle_stats(rng, p).items()})
        rows.append(row)
    return rows


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"settings": {"albums": N_ALB, "tracks_per_album": N_TRK, "target_db": TARGET, "peak_ceiling_db": CEIL,
                        "master_range_db": [-18, -8], "loudest_track_max_db": LOUD_MAX, "intended_spread_sd_db": 3.0, "crest_range_db": [8, 20],
                        "duration_sec_range": [150, 330], "seed": SEED}}
    a = make_albums(rng, N_ALB)
    al = album_level(a["loud"], a["dur"])

    # 曲のデータ
    recs = []
    p_tr, g_tr = play(a, "曲ごと")
    p_al, g_al = play(a, "アルバムごと")
    p_tr0, _ = play(a, "曲ごと", limit=False)
    p_al0, _ = play(a, "アルバムごと", limit=False)
    for i in range(N_ALB):
        for j in range(N_TRK):
            recs.append({"album": i, "track": j + 1, "intended_offset_db": r(a["off"][i, j]), "loudness_db": r(a["loud"][i, j]),
                         "duration_sec": r(a["dur"][i, j], 1), "peak_db": r(a["peak"][i, j]),
                         "played_track_mode_db": r(p_tr[i, j]), "played_album_mode_db": r(p_al[i, j])})
    pd.DataFrame(recs).to_csv(DATA / "tracks.csv", index=False)

    # ① 基本：ピークの上限あり／なし
    main_rows = summarize(a, "基本", rng, limit=True) + summarize(a, "基本", rng, limit=False)
    mdf = pd.DataFrame(main_rows)
    mdf.to_csv(RES / "by_mode.csv", index=False)
    out["by_mode"] = main_rows

    # 曲ごと（上限あり）で残った差は、作り手の差か、ピークの余裕か
    head = CEIL - a["peak"]                                       # ピークまでの余裕
    rel_tr = p_tr - p_tr.mean(axis=1, keepdims=True)
    head_c = head - head.mean(axis=1, keepdims=True)
    lim = np.abs(g_tr - (TARGET - a["loud"])) > 1e-9
    out["track_mode_detail"] = {
        "share_tracks_limited": r(lim.mean(), 4),
        "share_albums_with_any_limited": r(lim.any(axis=1).mean(), 4),
        "corr_played_rel_with_intended_all": r(np.corrcoef(rel_tr.ravel(), a["off"].ravel())[0, 1], 4),
        "corr_played_rel_with_headroom_all": r(np.corrcoef(rel_tr.ravel(), head_c.ravel())[0, 1], 4),
        "limited_mean_shortfall_db": r(np.mean((TARGET - p_tr)[lim])),
        "quietest_intended_track_played_below_target_share": r(np.mean(
            (TARGET - p_tr)[np.arange(N_ALB), np.argmin(a["off"], axis=1)] > 1e-9), 4),
    }
    out["album_mode_detail"] = {
        "share_albums_limited": r(np.mean(np.abs(g_al[:, 0] - (TARGET - al)) > 1e-9), 4),
        "mean_album_shortfall_db_if_limited": r(np.mean((TARGET - al - g_al[:, 0])[np.abs(g_al[:, 0] - (TARGET - al)) > 1e-9])),
        "album_level_mean_db": r(al.mean()),
        "album_level_minus_mean_of_track_db": r(np.mean(al - a["loud"].mean(axis=1))),
        "album_level_minus_mean_of_track_max_db": r(np.max(al - a["loud"].mean(axis=1))),
    }

    # 例のアルバム1枚（作り手の差の幅が中くらいで、曲ごとで上限にかかる曲があるもの）
    rng_o = a["off"].max(axis=1) - a["off"].min(axis=1)
    cand = np.where(lim.sum(axis=1) >= 2)[0]
    ex = int(cand[np.argmin(np.abs(rng_o[cand] - np.median(rng_o)))])
    ex_rows = []
    for j in np.argsort(a["off"][ex]):
        ex_rows.append({"track": int(j + 1), "intended_offset_db": r(a["off"][ex, j]), "loudness_db": r(a["loud"][ex, j]),
                        "peak_db": r(a["peak"][ex, j]), "played_none_db": r(a["loud"][ex, j]),
                        "played_track_mode_db": r(p_tr[ex, j]), "played_album_mode_db": r(p_al[ex, j]),
                        "played_track_mode_no_limit_db": r(p_tr0[ex, j])})
    pd.DataFrame(ex_rows).to_csv(RES / "example_album.csv", index=False)
    out["example_album"] = {"album": ex, "album_level_db": r(al[ex]), "album_mode_gain_db": r(g_al[ex, 0]),
                            "played_album_mode_range_db": r(p_al[ex].max() - p_al[ex].min()),
                            "intended_range_db": r(a["off"][ex].max() - a["off"][ex].min()), "tracks": ex_rows}

    # 確かめ：作り手の差の大きさ×目標の大きさ×ピークの余裕の27通り（各300枚）
    grid = []
    for sd in [1.5, 3.0, 5.0]:
        for tg in [-18.0, -14.0, -10.0]:
            for (clo, chi, cname) in [(6.0, 12.0, "小さい（6〜12dB）"), (8.0, 20.0, "基本（8〜20dB）"), (12.0, 24.0, "大きい（12〜24dB）")]:
                b = make_albums(rng, N_ALB, spread_sd=sd, crest_lo=clo, crest_hi=chi)
                ptr, gtr = play(b, "曲ごと", target=tg)
                pal, gal = play(b, "アルバムごと", target=tg)
                rt, st = retained(ptr, b["off"])
                ra, sa = retained(pal, b["off"])
                ctr = corr_rows(ptr, b["off"])
                limt = np.abs(gtr - (tg - b["loud"])) > 1e-9
                alb = album_level(b["loud"], b["dur"])
                lima = np.abs(gal[:, 0] - (tg - alb)) > 1e-9
                grid.append({"intended_spread_sd_db": sd, "target_db": tg, "crest": cname,
                             "track_mode_range_retained": r(rt.mean(), 4), "track_mode_slope": r(st.mean(), 4),
                             "track_mode_corr": r(np.nanmean(ctr), 4), "track_mode_share_limited": r(limt.mean(), 4),
                             "album_mode_range_retained": r(ra.mean(), 4), "album_mode_share_albums_limited": r(lima.mean(), 4),
                             "album_mode_share_below_target_3db": r(np.mean(pal < tg - 3), 4),
                             "track_mode_share_below_target_3db": r(np.mean(ptr < tg - 3), 4)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    out["grid_summary"] = {"n": len(g),
                           "track_slope_min": r(g.track_mode_slope.min(), 4), "track_slope_max": r(g.track_mode_slope.max(), 4),
                           "track_range_min": r(g.track_mode_range_retained.min(), 4), "track_range_max": r(g.track_mode_range_retained.max(), 4),
                           "track_limited_min": r(g.track_mode_share_limited.min(), 4), "track_limited_max": r(g.track_mode_share_limited.max(), 4),
                           "album_range_min": r(g.album_mode_range_retained.min(), 4), "album_range_max": r(g.album_mode_range_retained.max(), 4),
                           "album_limited_min": r(g.album_mode_share_albums_limited.min(), 4),
                           "album_limited_max": r(g.album_mode_share_albums_limited.max(), 4),
                           "album_below3_min": r(g.album_mode_share_below_target_3db.min(), 4),
                           "album_below3_max": r(g.album_mode_share_below_target_3db.max(), 4)}

    # ---- 図 ----
    # 図1：例のアルバム
    exd = pd.DataFrame(ex_rows)
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    xs = np.arange(len(exd))
    for col, c, mk, lab in [("played_none_db", GRAY, "o", "そのまま"), ("played_track_mode_db", ORANGE, "s", "曲ごとにそろえる"),
                            ("played_album_mode_db", BLUE, "D", "アルバムごとにそろえる")]:
        ax.plot(xs, exd[col], color=c, marker=mk, label=lab)
    ax.axhline(TARGET, color=INK, ls="--", lw=0.8)
    ax.text(len(exd) - 0.6, TARGET + 0.2, "目標 −14dB", ha="right", va="bottom", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{t}曲目" for t in exd.track], fontsize=8.5)
    ax.set_xlabel("曲（作り手が置いた大きさの小さい順）")
    ax.set_ylabel("鳴る大きさ（dB）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("曲ごとにそろえると、作り手の強弱がほぼ消える\n（例のアルバム1枚。曲ごとで目標まで上げられない曲はピークの上限による）")
    save(fig, "a1147_example.png", SRC)

    # 図2：アルバムの中の差がどれだけ残るか（作り手の差への傾き、上限あり）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    m1 = mdf[mdf.limit_peak]
    m0 = mdf[~mdf.limit_peak]
    w = 0.38
    ax.bar(xs := np.arange(3), m1.mean_slope_on_intended, width=w, color=BLUE, label="ピークが−1dBを超えない分まで上げる")
    ax.bar(xs + w, m0.mean_slope_on_intended, width=w, color=LIGHT, label="上限なしで上げる")
    for x, v in zip(xs, m1.mean_slope_on_intended):
        ax.text(x, v + 0.02, f"{v:.4f}", ha="center", fontsize=9)
    for x, v in zip(xs + w, m0.mean_slope_on_intended):
        ax.text(x, v + 0.02, f"{v:.4f}", ha="center", fontsize=9)
    ax.set_xticks(xs + w / 2)
    ax.set_xticklabels(MODES)
    ax.set_ylim(0, 1.25)
    ax.set_ylabel("作り手の差のうち残った割合\n（作り手の差1dBあたりの鳴る差）", fontsize=10, linespacing=1.4)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("アルバムごとなら作り手の差はそのまま残り、曲ごとではほぼ消える\n（300枚の平均。1は作り手の差がそのまま残ること）")
    save(fig, "a1147_retained.png", SRC)

    # 図3：曲をまぜて流したとき（アルバムをまたいだ20曲）の、となりの曲との差
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    vals = [m1[m1["mode"] == m]["shuffle_mean_jump_db"].iloc[0] for m in MODES]
    ax.bar(np.arange(3), vals, color=[GRAY, ORANGE, BLUE], width=0.55)
    for x, v in enumerate(vals):
        ax.text(x, v + 0.1, f"{v:.3f}dB", ha="center", fontsize=10)
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(MODES)
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_ylabel("となりの曲との大きさの差（dB、平均）")
    ax.set_title("いろいろなアルバムの曲をまぜて流すと、アルバムごとでも差が残る\n（20曲の並びを2,000回、ピークの上限あり）")
    save(fig, "a1147_shuffle.png", SRC)

    with open(RES / "a1147_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    pd.set_option("display.width", 250)
    print(mdf.to_string()); print(json.dumps({k: out[k] for k in ["track_mode_detail", "album_mode_detail", "grid_summary"]}, ensure_ascii=False, indent=1))
    print(exd.to_string()); print(g.to_string())
    print("sec", time.time() - t0)


if __name__ == "__main__":
    main()
