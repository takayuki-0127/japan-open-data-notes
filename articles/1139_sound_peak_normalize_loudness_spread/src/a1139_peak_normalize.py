"""1139 いちばん大きい瞬間の値で音量をそろえると、曲ごとの聞いた大きさはどれだけばらつくのか？（架空のデータ）

作成者が式と乱数で作った架空の曲（波形、1秒あたり4,000点、20〜60秒に縮めたもの）120曲を、
①いちばん大きい瞬間の値（波の値の絶対値の最大）を−1dBにそろえる、
②曲全体の平均の強さ（波の値の二乗平均）を−20dBにそろえる、の2つでそろえ、
そろえたあとの「平均の強さ」と「いちばん大きい瞬間の値」のばらつきを数える。
この記事では、聞いた大きさの代わりに、曲全体の平均の強さ（dB）を物差しにする（作成者が置いた物差し）。
dB は、波の値の1を0dBとした値。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1139
SRC = "架空の曲（作成者が式と乱数で作成、seed 1139）"
SR = 4000
N_SONG = 120
PEAK_TARGET = -1.0
AVG_TARGET = -20.0
LEN_RANGE = (20, 60)
STYLES = {  # 打つ音の多さ（1秒あたり）・打つ音の高さ（下地の平均の強さより何dB上か）・区間ごとの強弱の幅（dB）
    "狭い": {"hits": (0, 1), "hit_db": (6, 12), "dyn": (0, 6)},
    "基本": {"hits": (0, 3), "hit_db": (6, 20), "dyn": (0, 12)},
    "広い": {"hits": (0, 4), "hit_db": (6, 30), "dyn": (0, 18)},
}
CLICK_SHARES = [0.0, 0.1, 0.3]
CLICK_DB = 6.0           # はみ出した1点の高さ（その曲のいちばん大きい瞬間より何dB上か）
LENGTHS = [10, 60, 300]  # 長さの確かめ（秒）


def r(x, d=3):
    return round(float(x), d)


def db_pow(x):
    return 10 * np.log10(np.mean(x ** 2))


def db_peak(x):
    return 20 * np.log10(np.max(np.abs(x)))


def smooth_noise(rng, n, width=8):
    w = rng.standard_normal(n + width - 1)
    c = np.concatenate([[0.0], np.cumsum(w)])
    return (c[width:] - c[:-width]) / np.sqrt(width)


def make_song(rng, style, length=None):
    st = STYLES[style]
    if length is None:
        length = rng.uniform(*LEN_RANGE)
    n = int(length * SR)
    base = smooth_noise(rng, n)
    base /= np.sqrt(np.mean(base ** 2))
    # 8秒ごとの区間の強弱
    dyn = rng.uniform(*st["dyn"])
    nb = n // (8 * SR) + 1
    lv = rng.uniform(-dyn / 2, dyn / 2, nb)
    env = np.repeat(10 ** (lv / 20), 8 * SR)[:n]
    x = base * env
    # 打つ音（0.05秒で消える音）
    rate = rng.uniform(*st["hits"])
    hit_db = rng.uniform(*st["hit_db"])
    n_hit = rng.poisson(rate * length)
    hl = int(0.05 * SR)
    decay = np.exp(-np.arange(hl) / (0.012 * SR))
    for pos in rng.integers(0, n - hl, n_hit):
        burst = rng.standard_normal(hl) * decay * 10 ** (hit_db / 20) * env[pos]
        x[pos:pos + hl] += burst
    # 全体の大きさは −20dB 前後に置く（作成のときの音量はでたらめ）
    x *= 10 ** ((rng.uniform(-26, -14) - db_pow(x)) / 20)
    return x, {"length_sec": length, "dyn_db": dyn, "hits_per_sec": rate, "hit_db": hit_db}


def add_click(rng, x):
    y = x.copy()
    pos = rng.integers(0, len(y))
    y[pos] = np.max(np.abs(x)) * 10 ** (CLICK_DB / 20)
    return y


def measure_set(rng, style, click_share, n=N_SONG, keep=False):
    rows = []
    for i in range(n):
        x, info = make_song(rng, style)
        clicked = rng.random() < click_share
        if clicked:
            x = add_click(rng, x)
        pk, av = db_peak(x), db_pow(x)
        crest = pk - av
        rows.append({"song": i + 1, **{k: r(v, 3) for k, v in info.items()}, "stray_click": int(clicked),
                     "peak_db": r(pk, 3), "avg_db": r(av, 3), "peak_minus_avg_db": r(crest, 3),
                     "avg_after_peak_norm_db": r(PEAK_TARGET - crest, 3),
                     "peak_after_avg_norm_db": r(AVG_TARGET + crest, 3)})
    return pd.DataFrame(rows)


def spread(s):
    return {"sd": r(s.std(ddof=0)), "max_minus_min": r(s.max() - s.min()), "p10": r(s.quantile(.1)), "p90": r(s.quantile(.9)),
            "p90_minus_p10": r(s.quantile(.9) - s.quantile(.1)), "min": r(s.min()), "max": r(s.max()), "median": r(s.median())}


def main():
    rng = np.random.default_rng(SEED)
    out = {"settings": {"sample_rate": SR, "songs": N_SONG, "length_sec": list(LEN_RANGE), "peak_target_db": PEAK_TARGET,
                        "avg_target_db": AVG_TARGET, "styles": STYLES, "click_db": CLICK_DB, "hit_length_sec": 0.05, "seed": SEED}}

    # ---- 基本：曲の作り方「基本」、はみ出した1点なし ----
    base = measure_set(rng, "基本", 0.0)
    base.to_csv(DATA / "songs_base.csv", index=False)
    before = base.avg_db
    after_peak = base.avg_after_peak_norm_db
    peak_after_avg = base.peak_after_avg_norm_db
    out["base"] = {"avg_before_any_norm": spread(before),
                   "avg_after_peak_norm": spread(after_peak),
                   "peak_before_any_norm": spread(base.peak_db),
                   "peak_after_avg_norm": spread(peak_after_avg),
                   "share_peak_over_0db_after_avg_norm": r((peak_after_avg > 0).mean(), 4),
                   "n_peak_over_0db_after_avg_norm": int((peak_after_avg > 0).sum()),
                   "avg_after_avg_norm_sd": 0.0,
                   "corr_avg_after_peak_norm_vs_hits": r(np.corrcoef(after_peak, base.hits_per_sec * 10 ** (base.hit_db / 20))[0, 1], 3),
                   "loudest_minus_quietest_songs": {
                       "loudest": base.loc[after_peak.idxmax(), ["song", "hits_per_sec", "hit_db", "dyn_db", "peak_minus_avg_db"]].to_dict(),
                       "quietest": base.loc[after_peak.idxmin(), ["song", "hits_per_sec", "hit_db", "dyn_db", "peak_minus_avg_db"]].to_dict()}}

    # ---- はみ出した1点が入った曲（同じ曲に1点だけ足す） ----
    one = []
    for i in range(N_SONG):
        x, _ = make_song(rng, "基本")
        y = add_click(rng, x)
        one.append({"song": i + 1, "avg_after_peak_norm_db": r(PEAK_TARGET - (db_peak(x) - db_pow(x)), 3),
                    "avg_after_peak_norm_with_click_db": r(PEAK_TARGET - (db_peak(y) - db_pow(y)), 3)})
    one = pd.DataFrame(one)
    one["drop_db"] = (one.avg_after_peak_norm_db - one.avg_after_peak_norm_with_click_db).round(3)
    one.to_csv(RES / "one_click.csv", index=False)
    out["one_click"] = {"drop_mean": r(one.drop_db.mean()), "drop_min": r(one.drop_db.min()), "drop_max": r(one.drop_db.max()),
                        "formula": r(CLICK_DB, 2)}

    # ---- 長さ：同じ作り方（打つ音なし・強弱なし）で長さだけ変える ----
    lrows = []
    for L in LENGTHS:
        vals = []
        for _ in range(40):
            n = int(L * SR)
            x = smooth_noise(rng, n)
            vals.append(PEAK_TARGET - (db_peak(x) - db_pow(x)))
        vals = np.array(vals)
        lrows.append({"length_sec": L, "avg_after_peak_norm_mean": r(vals.mean()), "min": r(vals.min()), "max": r(vals.max())})
    out["length_check"] = lrows
    out["length_check_quieter_300_vs_10_db"] = r(lrows[0]["avg_after_peak_norm_mean"] - lrows[-1]["avg_after_peak_norm_mean"])
    pd.DataFrame(lrows).to_csv(RES / "length_check.csv", index=False)

    # ---- 確かめ：曲の作り方3つ×はみ出した1点の入る割合3つ ----
    grid = []
    for style in STYLES:
        for cs in CLICK_SHARES:
            d = base if (style == "基本" and cs == 0.0) else measure_set(rng, style, cs)
            sp = spread(d.avg_after_peak_norm_db)
            grid.append({"style": style, "click_share": cs, "sd_after_peak_norm": sp["sd"], "p10_p90_after_peak_norm": sp["p90_minus_p10"],
                         "range_after_peak_norm": sp["max_minus_min"], "sd_before_norm": r(d.avg_db.std(ddof=0)),
                         "share_peak_over_0db_after_avg_norm": r((d.peak_after_avg_norm_db > 0).mean(), 4)})
    dg = pd.DataFrame(grid)
    dg.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"cases": len(grid), "sd_min": r(dg.sd_after_peak_norm.min()), "sd_max": r(dg.sd_after_peak_norm.max()),
                   "range_min": r(dg.range_after_peak_norm.min()), "range_max": r(dg.range_after_peak_norm.max()),
                   "p10_p90_min": r(dg.p10_p90_after_peak_norm.min()), "p10_p90_max": r(dg.p10_p90_after_peak_norm.max()),
                   "over0_share_min": r(dg.share_peak_over_0db_after_avg_norm.min(), 4),
                   "over0_share_max": r(dg.share_peak_over_0db_after_avg_norm.max(), 4)}

    summ = pd.DataFrame([
        {"case": "そろえる前", "avg_sd": spread(before)["sd"], "avg_range": spread(before)["max_minus_min"],
         "peak_sd": spread(base.peak_db)["sd"], "peak_range": spread(base.peak_db)["max_minus_min"]},
        {"case": "①いちばん大きい瞬間を−1dBに", "avg_sd": spread(after_peak)["sd"], "avg_range": spread(after_peak)["max_minus_min"],
         "peak_sd": 0.0, "peak_range": 0.0},
        {"case": "②平均の強さを−20dBに", "avg_sd": 0.0, "avg_range": 0.0,
         "peak_sd": spread(peak_after_avg)["sd"], "peak_range": spread(peak_after_avg)["max_minus_min"]},
    ])
    summ.to_csv(RES / "summary.csv", index=False)
    with open(RES / "a1139_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1, default=float)

    # ---- 図 ----
    # 図1：曲ごとの平均の強さ（そろえる前・①・②）
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    jit = np.random.default_rng(0).uniform(-0.18, 0.18, N_SONG)
    cols3 = [GRAY, BLUE, ORANGE]
    vals3 = [before, after_peak, pd.Series(np.full(N_SONG, AVG_TARGET))]
    labs3 = ["そろえる前\n（作るときの音量はでたらめ）", "①いちばん大きい瞬間を\n−1dBにそろえた", "②平均の強さを\n−20dBにそろえた"]
    for j, (v, c) in enumerate(zip(vals3, cols3)):
        ax.scatter(j + jit, v, s=10, color=c, alpha=0.8)
        ax.text(j + 0.25, float(v.median()), (f"幅 {float(v.max() - v.min()):.3f}dB\n標準偏差 {float(v.std(ddof=0)):.3f}dB" + ("\n（作りどおり）" if j == 2 else "")), fontsize=8.5, va="center")
    ax.set_xticks(range(3))
    ax.set_xticklabels(labs3, fontsize=9)
    ax.set_xlim(-0.5, 2.9)
    ax.set_ylabel("曲全体の平均の強さ（dB）")
    sp = out["base"]["avg_after_peak_norm"]
    ax.set_title(f"いちばん大きい瞬間でそろえても、平均の強さは\n{sp['min']:.3f}〜{sp['max']:.3f}dBに散らばった（120曲、点は1曲）")
    save(fig, "a1139_after_peak_norm.png", SRC)

    # 図2：平均の強さを−20dBにそろえたときのいちばん大きい瞬間
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.arange(np.floor(peak_after_avg.min()) - 1, np.ceil(peak_after_avg.max()) + 1.01, 1.0)
    ax.hist(peak_after_avg, bins=bins, color=GRAY, edgecolor="white")
    ax.hist(peak_after_avg[peak_after_avg > 0], bins=bins, color=ORANGE, edgecolor="white")
    ax.axvline(0, color=ORANGE, lw=1.2)
    ax.text(0.02, 0.95, f"0dB（波の上限）を超えた曲\n{out['base']['n_peak_over_0db_after_avg_norm']}曲（{out['base']['share_peak_over_0db_after_avg_norm']*100:.2f}%）",
            color=ORANGE, fontsize=9, va="top", transform=ax.transAxes)
    ax.set_xlabel("平均の強さを−20dBにそろえたときの、いちばん大きい瞬間の値（dB）")
    ax.set_ylabel("曲の数")
    ax.set_title("平均の強さでそろえると、今度はいちばん大きい瞬間が散らばる")
    save(fig, "a1139_peak_after_avg_norm.png", SRC)

    # 図3：9通りのばらつき（標準偏差）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    w = 0.26
    for j, (cs, col) in enumerate(zip(CLICK_SHARES, [BLUE, LIGHT, ORANGE])):
        s = dg[dg.click_share == cs]
        xs = np.arange(len(STYLES)) + (j - 1) * w
        ax.bar(xs, s.sd_after_peak_norm, width=w, color=col, label=f"はみ出した1点の入る曲 {int(cs*100)}%")
        for x, v in zip(xs, s.sd_after_peak_norm):
            ax.text(x, v + 0.05, f"{v:.3f}", ha="center", fontsize=7.5)
    ax.set_xticks(np.arange(len(STYLES)))
    ax.set_xticklabels([f"曲の作り方：{k}" for k in STYLES])
    ax.set_ylabel("①でそろえたあとの平均の強さの\n標準偏差（dB）")
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("①でそろえたあとのばらつきは、曲の作り方と\nはみ出した1点で変わる（各120曲）")
    save(fig, "a1139_grid.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print(dg.to_string())


if __name__ == "__main__":
    main()
