"""1141 音をつぶして大きくする処理をかけると、平均の大きさと強弱の幅はどう入れかわるのか？（架空のデータ）

作成者が式と乱数で作った架空の曲（波形、4,000 回/秒、24秒、静かな部分と盛り上がる部分が6秒ずつ交互）に、
「大きいところだけ音量を下げる処理」（つぶす処理）をかけ、いちばん大きい瞬間を上限（0 dB）にそろえ直す。
つぶす処理は、区切り（2ms）ごとの強さを前後の幅 W でならした大きさが、しきい値を超えた分を 1−1/r の割合で下げる。
W（速さ）と r（つぶす強さ）を変え、平均の大きさの上がりと、強弱の幅（瞬間の幅・区間の幅）の減りを数える。
いちばん大きい瞬間を上限にそろえるので、
  平均の大きさの上がり ＝ 瞬間の幅（いちばん大きい瞬間−いちばん大きい3秒）の減り ＋ 区間の幅（いちばん大きい3秒−平均）の減り
が式どおりに成り立つ。どちらの幅が減るかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1141
SRC = "架空の曲（作成者が式と乱数で作成、seed 1141）"
FS = 4000
DUR = 24
SEC = 6
BLK = 8                                   # 2ms の区切り
SPEEDS = {"10ミリ秒": 5, "100ミリ秒": 50, "1秒": 500, "3秒": 1500}   # ならす幅（区切りの数）
RATIOS = [1, 1.5, 2, 3, 4, 8, 20]
R_BASE = 4
TH_BASE = 0.0
THS = [-6.0, 0.0, 6.0]
N_BASE = 300
N_ROB = 200
SETS = {"狭い（2〜6 dB）": (2, 6), "基本（3〜12 dB）": (3, 12), "広い（8〜16 dB）": (8, 16)}


def r(x, d=2):
    return round(float(x), d)


def make_song(rng, d_lo, d_hi):
    n = FS * DUR
    t = np.arange(n) / FS
    per = 60 / rng.uniform(80, 140)
    a_hit = rng.uniform(1.5, 4.0)
    tau = rng.uniform(0.04, 0.12)
    env = 1 + a_hit * np.exp(-(t % per) / tau)
    d = rng.uniform(d_lo, d_hi)
    chorus = ((t // SEC).astype(int) % 2 == 1)
    lev = np.where(chorus, 1.0, 10 ** (-d / 20))
    x = rng.standard_normal(n) * env * lev
    x /= np.abs(x).max()
    return dict(bp=np.abs(x).reshape(-1, BLK).max(axis=1), pw=(x * x).reshape(-1, BLK).sum(axis=1),
                chorus=chorus[::BLK], d=d)


def db(p):
    return 10 * np.log10(p)


def smooth(p, w):
    """前後の幅 w 区切りでならした強さ（端は折り返し）"""
    h = w // 2
    q = np.pad(p, (h, w - h), mode="reflect")
    c = np.concatenate([[0.0], np.cumsum(q)])
    return (c[w:] - c[:-w])[:len(p)] / w


def squash(s, w, ratio, th_off):
    """つぶす処理の倍率（区切りごと）。そのあと、いちばん大きい瞬間を上限1にそろえ直す"""
    lev = db(smooth(s["pw"], w) / BLK)
    lint0 = db(s["pw"].sum() / (len(s["pw"]) * BLK))
    over = np.maximum(lev - (lint0 + th_off), 0)
    g = 10 ** (-(1 - 1 / ratio) * over / 20)
    return g / (s["bp"] * g).max()


def measure(s, gain):
    p = s["pw"] * gain ** 2
    ch = s["chorus"]
    w = 3 * FS // BLK
    hop = FS // 2 // BLK
    c = np.concatenate([[0.0], np.cumsum(p)])
    st = np.arange(0, len(p) - w + 1, hop)
    l3 = db((c[st + w] - c[st]) / (w * BLK))
    lint = db(p.sum() / (len(p) * BLK))
    peak = 20 * np.log10((s["bp"] * gain).max())
    return dict(Lint=lint, peak=peak, inst=peak - l3.max(), sect=l3.max() - lint,
                range3s=np.percentile(l3, 95) - np.percentile(l3, 10),
                contrast=db(p[ch].sum() / ch.sum()) - db(p[~ch].sum() / (~ch).sum()), L3=l3)


def run_set(rng, n, d_lo, d_hi, ths, ratios, keep_example=False):
    rows, ex = [], {}
    for i in range(n):
        s = make_song(rng, d_lo, d_hi)
        m0 = measure(s, np.ones_like(s["bp"]))
        for th in ths:
            for sp, w in SPEEDS.items():
                for ra in ratios:
                    m = measure(s, squash(s, w, ra, th)) if ra != 1 else m0
                    rows.append(dict(song=i, contrast_set_dB=s["d"], th_off=th, speed=sp, ratio=ra,
                                     gain_avg=m["Lint"] - m0["Lint"],
                                     loss_inst=m0["inst"] - m["inst"], loss_sect=m0["sect"] - m["sect"],
                                     loss_range3s=m0["range3s"] - m["range3s"],
                                     loss_contrast=m0["contrast"] - m["contrast"],
                                     Lint=m["Lint"], inst=m["inst"], sect=m["sect"], range3s=m["range3s"],
                                     contrast=m["contrast"]))
                    if keep_example and i == 0 and th == TH_BASE and ra in (1, R_BASE):
                        g = squash(s, w, ra, th) if ra != 1 else np.ones_like(s["bp"])
                        ex[(sp, ra)] = (s, g)
    return pd.DataFrame(rows), ex


def main():
    rng = np.random.default_rng(SEED)
    base, ex = run_set(rng, N_BASE, *SETS["基本（3〜12 dB）"], [TH_BASE], RATIOS, keep_example=True)
    base.round(4).to_csv(DATA / "songs_squash.csv", index=False)

    # 恒等式の確かめ：平均の上がり＝瞬間の幅の減り＋区間の幅の減り
    ident = (base.gain_avg - base.loss_inst - base.loss_sect).abs().max()

    cols = ["gain_avg", "loss_inst", "loss_sect", "loss_range3s", "loss_contrast", "Lint", "inst", "sect", "range3s", "contrast"]
    tab = base.groupby(["speed", "ratio"], sort=False)[cols].mean().reset_index()
    tab.round(3).to_csv(RES / "by_speed_ratio.csv", index=False)

    # 1 dB 上げるごとに減る量（r を変えた直線の傾き、曲をまとめて）
    slopes = {}
    for sp in SPEEDS:
        b = base[(base.speed == sp) & (base.ratio > 1)]
        slopes[sp] = dict(contrast_per_dB=r(np.polyfit(b.gain_avg, b.loss_contrast, 1)[0], 3),
                          range3s_per_dB=r(np.polyfit(b.gain_avg, b.loss_range3s, 1)[0], 3),
                          inst_per_dB=r(np.polyfit(b.gain_avg, b.loss_inst, 1)[0], 3))

    # 曲ごとの範囲（r=4）
    b4 = base[base.ratio == R_BASE]
    q = {sp: dict(gain_avg_p10_p90=[r(v.gain_avg.quantile(.1)), r(v.gain_avg.quantile(.9))],
                  loss_contrast_p10_p90=[r(v.loss_contrast.quantile(.1)), r(v.loss_contrast.quantile(.9))])
         for sp, v in b4.groupby("speed", sort=False)}

    # 同じくらい平均を上げたとき（+3〜+5 dB の組）に、どちらの幅が減ったか
    mid = base[(base.ratio > 1) & (base.gain_avg >= 3) & (base.gain_avg <= 5)]
    mid_tab = mid.groupby("speed", sort=False)[["gain_avg", "loss_inst", "loss_sect", "loss_contrast", "loss_range3s"]].mean()
    mid_n = mid.groupby("speed", sort=False).size()

    # ---- 確かめ：強弱の差×しきい値（9通り、r=4、各速さ） ----
    rob = []
    for name, (lo, hi) in SETS.items():
        if name == "基本（3〜12 dB）":
            df, _ = run_set(rng, N_ROB, lo, hi, THS, [1, R_BASE])
        else:
            df, _ = run_set(rng, N_ROB, lo, hi, THS, [1, R_BASE])
        df = df[df.ratio == R_BASE]
        g = df.groupby(["th_off", "speed"], sort=False)[["gain_avg", "loss_inst", "loss_sect", "loss_contrast", "loss_range3s"]].mean().reset_index()
        g["contrast_set"] = name
        rob.append(g)
    rob = pd.concat(rob, ignore_index=True)
    rob.round(3).to_csv(RES / "grid.csv", index=False)

    def rr(sp, col):
        v = rob[rob.speed == sp][col]
        return [r(v.min()), r(v.max())]

    # 速い（10ミリ秒）と遅い（3秒）のどちらで部分の差の減りが大きいか（9通りすべてで）
    fast = rob[rob.speed == "10ミリ秒"].set_index(["contrast_set", "th_off"])
    slow = rob[rob.speed == "3秒"].set_index(["contrast_set", "th_off"])
    n_slow_more_contrast = int((slow.loss_contrast > fast.loss_contrast).sum())
    n_fast_more_inst = int((fast.loss_inst > slow.loss_inst).sum())

    t4 = tab[tab.ratio == R_BASE].set_index("speed")
    t20 = tab[tab.ratio == 20].set_index("speed")
    orig = base[base.ratio == 1].drop_duplicates("song")
    main_json = dict(
        setup=dict(fs=FS, dur_sec=DUR, part_sec=SEC, n_base=N_BASE, n_robust_each=N_ROB, speeds_ms={k: v * 2 for k, v in SPEEDS.items()},
                   ratios=RATIOS, ratio_base=R_BASE, threshold_offset_base=TH_BASE, threshold_offsets=THS, contrast_sets=SETS),
        original=dict(Lint=r(orig.Lint.mean()), inst=r(orig.inst.mean()), sect=r(orig.sect.mean()),
                      range3s=r(orig.range3s.mean()), contrast=r(orig.contrast.mean())),
        identity_max_abs_error_dB=float(f"{ident:.2e}"),
        ratio4={sp: dict(gain_avg=r(t4.loc[sp, "gain_avg"]), loss_inst=r(t4.loc[sp, "loss_inst"]), loss_sect=r(t4.loc[sp, "loss_sect"]),
                         loss_range3s=r(t4.loc[sp, "loss_range3s"]), loss_contrast=r(t4.loc[sp, "loss_contrast"]),
                         **q[sp]) for sp in SPEEDS},
        ratio20={sp: dict(gain_avg=r(t20.loc[sp, "gain_avg"]), loss_inst=r(t20.loc[sp, "loss_inst"]),
                          loss_contrast=r(t20.loc[sp, "loss_contrast"]), contrast_after=r(t20.loc[sp, "contrast"])) for sp in SPEEDS},
        slopes_per_dB=slopes,
        gain3to5={sp: dict(n=int(mid_n.get(sp, 0)), **{c: r(mid_tab.loc[sp, c]) for c in mid_tab.columns}) for sp in mid_tab.index},
        grid=dict(n_combos=9,
                  loss_inst={sp: rr(sp, "loss_inst") for sp in SPEEDS},
                  loss_range3s={sp: rr(sp, "loss_range3s") for sp in SPEEDS},
                  gain_avg={sp: rr(sp, "gain_avg") for sp in SPEEDS},
                  loss_contrast={sp: rr(sp, "loss_contrast") for sp in SPEEDS},
                  n_slow_loses_more_contrast_than_fast=n_slow_more_contrast,
                  n_fast_loses_more_inst_than_slow=n_fast_more_inst,
                  n_fast_gains_more_avg_than_slow=int((fast.gain_avg > slow.gain_avg).sum()),
                  n_slow_gain_below_1dB=int((slow.gain_avg < 1).sum()),
                  n_slow_contrast_loss_over_1dB=int((slow.loss_contrast > 1).sum()),
                  slow_acting=dict(  # 1秒・3秒で部分の差が0.5 dB 以上縮んだ組（しきい値 −6・0 dB）
                      n=int((rob[rob.speed.isin(["1秒", "3秒"])].loss_contrast > 0.5).sum()),
                      gain_avg=[r(rob[rob.speed.isin(["1秒", "3秒"]) & (rob.loss_contrast > 0.5)].gain_avg.min()),
                                r(rob[rob.speed.isin(["1秒", "3秒"]) & (rob.loss_contrast > 0.5)].gain_avg.max())],
                      loss_contrast=[r(rob[rob.speed.isin(["1秒", "3秒"]) & (rob.loss_contrast > 0.5)].loss_contrast.min()),
                                     r(rob[rob.speed.isin(["1秒", "3秒"]) & (rob.loss_contrast > 0.5)].loss_contrast.max())]),
                  th_plus6_slow_all_zero=bool((rob[(rob.th_off == 6) & rob.speed.isin(["1秒", "3秒"])].gain_avg.abs() < 1e-9).all())),
    )

    # ---- 図1：例の1曲、0.1秒ごとの大きさ ----
    s, g1 = ex[("10ミリ秒", 1)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
    tb = np.arange(len(s["pw"]) // 50) * 0.1 + 0.05
    exrows = dict(t_sec=tb)
    for ax, sp in zip(axes, ["10ミリ秒", "3秒"]):
        _, g = ex[(sp, R_BASE)]
        for gg, col, lab in [(g1, GRAY, "つぶす前"), (g, ORANGE if sp == "3秒" else BLUE, f"ならす幅{sp}でつぶした後")]:
            p = (s["pw"] * gg ** 2).reshape(-1, 50).sum(axis=1) / (50 * BLK)
            pk = 20 * np.log10((s["bp"] * gg).reshape(-1, 50).max(axis=1))
            ax.plot(tb, db(p), color=col, lw=1.2, label=lab + "：0.1秒ごとの大きさ")
            ax.plot(tb, pk, color=col, lw=0.8, ls=":", label=lab + "：0.1秒ごとのいちばん大きい瞬間")
            exrows[f"{'before' if gg is g1 else sp}_level"] = db(p)
            exrows[f"{'before' if gg is g1 else sp}_peak"] = pk
        for s0 in [6, 18]:
            ax.axvspan(s0, s0 + 6, color=LIGHT, alpha=0.3, lw=0)
        ax.set_title(f"ならす幅 {sp}（つぶす強さ r＝{R_BASE}）", fontsize=11)
        ax.set_xlabel("曲の中の時刻（秒）")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=8, frameon=False)
    axes[0].set_ylabel("大きさ（dB、上限を0とした値）")
    fig.suptitle("例の1曲：速くつぶすと平均が上がり、遅くつぶすと平均は上がらず部分の差だけ縮む（色の帯は盛り上がる部分）", fontsize=12, y=1.04)
    save(fig, "a1141_example.png", "出典：" + SRC, y=-0.28)
    pd.DataFrame(exrows).round(3).to_csv(DATA / "example_song_100ms.csv", index=False)
    ex_m = {}
    for key in [("10ミリ秒", 1), ("10ミリ秒", R_BASE), ("3秒", R_BASE)]:
        mm = measure(*ex[key])
        ex_m["before" if key[1] == 1 else key[0]] = dict(Lint=r(mm["Lint"]), inst=r(mm["inst"]), sect=r(mm["sect"]), contrast=r(mm["contrast"]))
    main_json["example_song0"] = ex_m

    # ---- 図2：r=4 の平均の上がりと幅の減り ----
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    sps = list(SPEEDS)
    xi = np.arange(len(sps))
    items = [("gain_avg", "平均の大きさの上がり", BLUE), ("loss_inst", "瞬間の幅の減り", GREEN),
             ("loss_contrast", "盛り上がる−静かな部分の差の減り", ORANGE)]
    for j, (c, lab, col) in enumerate(items):
        v = [t4.loc[sp, c] for sp in sps]
        ax.bar(xi + (j - 1) * 0.26, v, 0.26, color=col, label=lab)
        for x, vv in zip(xi, v):
            ax.text(x + (j - 1) * 0.26, vv + (0.06 if vv >= 0 else -0.06), f"{vv:.2f}", ha="center",
                    va="bottom" if vv >= 0 else "top", fontsize=8)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xi)
    ax.set_xticklabels([f"ならす幅\n{sp}" for sp in sps])
    ax.set_ylabel("dB（300曲の平均）")
    ax.set_ylim(-0.7, 6.2)
    ax.set_title(f"つぶす強さ r＝{R_BASE}：平均が上がるのは瞬間の幅が減ったときだけ")
    ax.legend(fontsize=8.5, frameon=False, loc="upper right")
    save(fig, "a1141_split.png", "出典：" + SRC)

    # ---- 図3：盛り上がる部分と静かな部分の差の減り（r を変えて） ----
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
    colors = {"10ミリ秒": BLUE, "100ミリ秒": GREEN, "1秒": GRAY, "3秒": ORANGE}
    for sp in sps:
        t = tab[tab.speed == sp]
        axes[0].plot(t.gain_avg, t.loss_contrast, marker="o", ms=4, color=colors[sp], label=f"ならす幅 {sp}")
        g = rob[rob.speed == sp]
        axes[1].scatter(g.gain_avg, g.loss_contrast, color=colors[sp], s=22, label=f"ならす幅 {sp}")
    axes[0].set_title("基本：つぶす強さ r＝1〜20", fontsize=11)
    axes[1].set_title(f"確かめ9通り（r＝{R_BASE}）", fontsize=11)
    for ax in axes:
        ax.set_xlabel("平均の大きさの上がり（dB）")
        ax.set_xlim(left=-0.3)
        ax.axvline(0, color=INK, lw=0.6)
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("盛り上がる−静かな部分の差の減り（dB）")
    axes[0].legend(fontsize=8.5, frameon=False)
    fig.suptitle("遅くつぶすと、平均はほとんど上がらないまま部分の差が縮む", fontsize=12, y=1.02)
    save(fig, "a1141_contrast.png", "出典：" + SRC)

    with open(RES / "a1141_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
