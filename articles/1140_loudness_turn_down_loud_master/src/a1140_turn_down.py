"""1140 配信先が決まった大きさまで音量を下げるとき、大きく作った曲は得をするのか？（架空のデータ）

作成者が式と乱数で作った架空の曲（波形、4,000 回/秒、24秒、静かな部分と盛り上がる部分が6秒ずつ交互）を、
いちばん大きい瞬間を上限（0 dB）にそろえた状態から、0〜16 dB「大きく作る」（上限を超えないよう、
超えそうな瞬間だけ音量を下げる＝つぶす処理）。配信先は曲全体の強さの平均（dB、上限を0とした値、重みなし）を測り、
①決まった大きさより大きい曲だけ下げる、②下げるうえに、小さい曲は瞬間の上限まで上げる、の2つの決まりで再生する。
大きく作った曲が、再生したときに大きく作らない同じ曲より大きく聞こえるか（全体の平均・盛り上がる部分・いちばん大きい3秒）を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1140
SRC = "架空の曲（作成者が式と乱数で作成、seed 1140）"
FS = 4000
DUR = 24
SEC = 6                      # 1つの部分の長さ（秒）
BLK = 8                      # つぶす処理の区切り（2ms）
HOLD = 12                    # 前後12区切り（±24ms）の中でいちばん下げた量を使う
KS = [0, 2, 4, 6, 8, 10, 12, 14, 16]
T_BASE = -16.0
TS = [-20.0, -16.0, -12.0]
N_BASE = 500
N_ROB = 300
SETS = {"狭い（2〜6 dB）": (2, 6), "基本（3〜12 dB）": (3, 12), "広い（8〜16 dB）": (8, 16)}
RULES = {"A": "①大きい曲だけ下げる", "B": "②上げ下げする（上げて上限を超える瞬間はつぶす）"}


def r(x, d=2):
    return round(float(x), d)


def make_song(rng, d_lo, d_hi):
    """架空の曲の波形を作り、2msの区切りごとの「いちばん大きい瞬間」と「強さの合計」にまとめる"""
    n = FS * DUR
    t = np.arange(n) / FS
    bpm = rng.uniform(80, 140)
    per = 60 / bpm
    a_hit = rng.uniform(1.5, 4.0)
    tau = rng.uniform(0.04, 0.12)
    env = 1 + a_hit * np.exp(-(t % per) / tau)
    d = rng.uniform(d_lo, d_hi)
    part = (t // SEC).astype(int)             # 0,1,2,3
    chorus = (part % 2 == 1)
    lev = np.where(chorus, 1.0, 10 ** (-d / 20))
    x = rng.standard_normal(n) * env * lev
    x /= np.abs(x).max()                      # いちばん大きい瞬間を上限（0 dB）に
    bp = np.abs(x).reshape(-1, BLK).max(axis=1)
    pw = (x * x).reshape(-1, BLK).sum(axis=1)
    return dict(bp=bp, pw=pw, chorus=chorus[::BLK], d=d)


def limit_gain(bp, gain, k):
    """いまの区切りごとの倍率 gain に、さらに k dB 大きくして上限1を超えそうな区切りだけ下げる（つぶす処理）。
    区切りの中では倍率が一定なので、区切りのいちばん大きい瞬間は bp×倍率 で決まる"""
    g_all = 10 ** (k / 20)
    req = np.minimum(1.0, 1.0 / (bp * gain * g_all))
    return gain * g_all * run_min(req)


def run_min(a):
    """前後 HOLD 区切り（幅25）の中のいちばん小さい値（幅2・4・8・16の最小を重ねて求める）"""
    p = np.pad(a, HOLD, mode="edge")
    m2 = np.minimum(p[:-1], p[1:])
    m4 = np.minimum(m2[:-2], m2[2:])
    m8 = np.minimum(m4[:-4], m4[4:])
    m16 = np.minimum(m8[:-8], m8[8:])
    return np.minimum(m16[:-9], m16[9:])


def db_pow(p):
    return 10 * np.log10(p)


def measure(s, gain):
    p = s["pw"] * gain ** 2
    ch = s["chorus"]
    w = 3 * FS // BLK
    hop = FS // 2 // BLK
    c = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, len(p) - w + 1, hop)
    l3 = db_pow((c[starts + w] - c[starts]) / (w * BLK))
    return dict(Lint=db_pow(p.sum() / (len(p) * BLK)), Lch=db_pow(p[ch].sum() / (ch.sum() * BLK)),
                Lve=db_pow(p[~ch].sum() / ((~ch).sum() * BLK)),
                peak=20 * np.log10((s["bp"] * gain).max()), L3max=l3.max(), L3=l3)


def play_B(s, gain, T):
    """②：決まった大きさより大きければ下げ、小さければ上げる。上げて上限を超える瞬間は配信先がつぶす"""
    m = measure(s, gain)
    if m["Lint"] >= T:
        return gain * 10 ** ((T - m["Lint"]) / 20)
    g = gain
    for _ in range(4):                        # つぶした分だけ届かないので、くり返して合わせる
        m = measure(s, g)
        g = limit_gain(s["bp"], g, T - m["Lint"])
    return g


def simulate(rng, n, d_lo, d_hi, Ts, keep_example=False):
    rows, ex = [], {}
    for i in range(n):
        s = make_song(rng, d_lo, d_hi)
        one = np.ones_like(s["bp"])
        for k in KS:
            gk = limit_gain(s["bp"], one, k) if k else one
            m = measure(s, gk)
            row = dict(song=i, contrast_set_dB=s["d"], k=k, Lint=m["Lint"], Lch=m["Lch"], Lve=m["Lve"],
                       peak=m["peak"], L3max=m["L3max"])
            if keep_example and i == 0:
                ex[("pre", k)] = m["L3"]
            for T in Ts:
                mb = measure(s, play_B(s, gk, T))
                for c in ["Lint", "Lch", "Lve", "L3max", "peak"]:
                    row[f"B{T:.0f}_{c}"] = mb[c]
                if keep_example and i == 0 and T == T_BASE:
                    ex[("B", k)] = mb["L3"]
            rows.append(row)
    return pd.DataFrame(rows), ex


def playback(df, T, rule):
    """再生したときの大きさ（①は下げるだけ、②は上げ下げ、none はそのまま）"""
    out = df.copy()
    if rule == "B":
        for c in ["Lint", "Lch", "Lve", "L3max", "peak"]:
            out[c + "_play"] = df[f"B{T:.0f}_{c}"]
        return out
    g = T - df["Lint"]
    g = np.minimum(g, 0.0) if rule == "A" else g * 0
    for c in ["Lint", "Lch", "Lve", "L3max", "peak"]:
        out[c + "_play"] = df[c] + g
    return out


def compare(df, T, rule, kk=8):
    """kk dB 大きく作った曲と、作らない同じ曲（k=0）の再生したときの差"""
    p = playback(df, T, rule)
    a = p[p.k == 0].set_index("song")
    b = p[p.k == kk].set_index("song")
    dl = b["Lint_play"] - a["Lint_play"]
    dc = b["Lch_play"] - a["Lch_play"]
    d3 = b["L3max_play"] - a["L3max_play"]
    return dict(mean_gain_overall=r(dl.mean()), share_overall_louder_0p5=r((dl > 0.5).mean() * 100, 1),
                mean_gain_chorus=r(dc.mean()), share_chorus_louder_0p5=r((dc > 0.5).mean() * 100, 1),
                share_chorus_quieter_0p5=r((dc < -0.5).mean() * 100, 1),
                mean_gain_loudest3s=r(d3.mean()),
                share_already_above_T_at_k0=r((a["Lint"] > T).mean() * 100, 1))


def main():
    rng = np.random.default_rng(SEED)
    base, ex = simulate(rng, N_BASE, *SETS["基本（3〜12 dB）"], TS, keep_example=True)
    base.round(4).to_csv(DATA / "songs_by_push.csv", index=False)

    # ---- 基本：k ごと ----
    per_k = []
    a0 = base[base.k == 0].set_index("song")
    for k in KS:
        b = base[base.k == k].set_index("song")
        row = dict(k=k, Lint_before=r(b.Lint.mean()), contrast_before=r((b.Lch - b.Lve).mean()),
                   peak_to_avg_before=r((b.peak - b.Lint).mean()),
                   share_above_T=r((b.Lint > T_BASE).mean() * 100, 1))
        for rule in ["A", "B", "none"]:
            pa = playback(base[base.k == k], T_BASE, rule).set_index("song")
            p0 = playback(base[base.k == 0], T_BASE, rule).set_index("song")
            row[f"{rule}_Lint_play"] = r(pa.Lint_play.mean())
            row[f"{rule}_Lch_play"] = r(pa.Lch_play.mean())
            row[f"{rule}_L3max_play"] = r(pa.L3max_play.mean())
            row[f"{rule}_gain_overall_vs_k0"] = r((pa.Lint_play - p0.Lint_play).mean())
            row[f"{rule}_gain_chorus_vs_k0"] = r((pa.Lch_play - p0.Lch_play).mean())
        per_k.append(row)
    per_k = pd.DataFrame(per_k)
    per_k.to_csv(RES / "by_push.csv", index=False)

    # ---- 曲ごと：決まった大きさに届く k、届いたあとの差 ----
    lint0 = a0.Lint
    reach = []
    for s, g in base.groupby("song"):
        gg = g.set_index("k")
        ks = [k for k in KS if gg.loc[k, "Lint"] >= T_BASE]
        reach.append(ks[0] if ks else np.nan)
    reach = pd.Series(reach)
    already = (lint0 > T_BASE)
    cmpA = compare(base, T_BASE, "A")
    cmpB = compare(base, T_BASE, "B")
    cmpN = compare(base, T_BASE, "none")
    # 盛り上がる部分の差を、k=0 ですでに決まった大きさを超えていた曲と、届いていなかった曲に分ける
    pA = playback(base, T_BASE, "A")
    a = pA[pA.k == 0].set_index("song")
    b = pA[pA.k == 8].set_index("song")
    dc = b.Lch_play - a.Lch_play
    dl = b.Lint_play - a.Lint_play
    split = dict(above=dict(n=int(already.sum()), mean_gain_overall=r(dl[already].mean()), mean_gain_chorus=r(dc[already].mean())),
                 below=dict(n=int((~already).sum()), mean_gain_overall=r(dl[~already].mean()), mean_gain_chorus=r(dc[~already].mean())))
    # 何dB大きく作ると、いちばん盛り上がる部分が k=0 より下がり始めるか（①、500曲の平均）
    # ①で盛り上がる部分がいちばん大きくなる k（曲ごと）と、16 dB との差
    pAll = playback(base, T_BASE, "A")
    best_k = pAll.loc[pAll.groupby("song").Lch_play.idxmax(), "k"].reset_index(drop=True)
    piv = pAll.pivot(index="song", columns="k", values="Lch_play")
    loss_16_from_best = (piv[16] - piv.max(axis=1))
    best = dict(median_best_k=r(best_k.median(), 1), share_best_k_le8=r((best_k <= 8).mean() * 100, 1),
                mean_loss_k16_vs_best=r(loss_16_from_best.mean()),
                corr_bestk_reachk=r(np.corrcoef(best_k, reach)[0, 1], 3),
                mean_bestk_minus_reachk=r((best_k - reach).mean(), 2))
    # ①の全体の得は「決まった大きさ−もとの大きさ」を超えない（式どおり）
    bound = np.minimum(np.maximum(T_BASE - lint0, 0), np.inf)
    gainA16 = pAll[pAll.k == 16].set_index("song").Lint_play - pAll[pAll.k == 0].set_index("song").Lint_play
    bound_check = dict(mean_gap_T_minus_L0=r(bound.mean()), mean_gainA_k16=r(gainA16.mean()),
                       max_abs_diff=r((gainA16 - bound).abs().max(), 3))
    # 強弱の差の減り方
    contrast_loss = r(((base[base.k == 8].set_index("song").Lch - base[base.k == 8].set_index("song").Lve)
                       - (a0.Lch - a0.Lve)).mean())

    # ---- 確かめ：曲の強弱の差 × 決まった大きさ × 決まり ----
    grid = []
    rob_sets = {}
    for name, (lo, hi) in SETS.items():
        if name == "基本（3〜12 dB）":
            rob_sets[name] = base
        else:
            rob_sets[name], _ = simulate(rng, N_ROB, lo, hi, TS)
    for name, df in rob_sets.items():
        for T in TS:
            for rule in ["A", "B"]:
                for kk in [8, 16]:
                    c = compare(df, T, rule, kk)
                    grid.append(dict(contrast_set=name, T=T, rule=RULES[rule], push_dB=kk, **c))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    def rng_of(col, sub, kk=8):
        g = grid[(grid.rule == sub) & (grid.push_dB == kk)]
        return [r(g[col].min()), r(g[col].max())]

    main_json = dict(
        setup=dict(fs=FS, dur_sec=DUR, part_sec=SEC, n_base=N_BASE, n_robust_each=N_ROB, target_dB=T_BASE,
                   push_dB=KS, contrast_sets=SETS, measure="曲全体の強さの平均（dB、上限を0とした値、重みなし）"),
        base_k0=dict(Lint_mean=r(lint0.mean()), Lint_p10=r(lint0.quantile(.1)), Lint_p90=r(lint0.quantile(.9)),
                     share_above_T=r(already.mean() * 100, 1)),
        reach_T_k=dict(share_reached_by_16=r(reach.notna().mean() * 100, 1), median_k=r(reach.median(), 1),
                       share_k0=r((reach == 0).mean() * 100, 1)),
        compare_k8_vs_k0=dict(A=cmpA, B=cmpB, none=cmpN),
        best_k_for_chorus_A=best,
        overall_gain_bound_A=bound_check,
        max_peak_after_push_dB=r(base.peak.max(), 4),
        contrast_loss_k8=contrast_loss,
        compare_k16_vs_k0=dict(A=compare(base, T_BASE, "A", 16), B=compare(base, T_BASE, "B", 16)),
        grid_ranges=dict(
            A_mean_gain_overall=rng_of("mean_gain_overall", RULES["A"]),
            A_mean_gain_chorus=rng_of("mean_gain_chorus", RULES["A"]),
            B_mean_gain_overall=rng_of("mean_gain_overall", RULES["B"]),
            B_mean_gain_chorus=rng_of("mean_gain_chorus", RULES["B"]),
            A_share_chorus_quieter=rng_of("share_chorus_quieter_0p5", RULES["A"]),
            B_share_chorus_quieter=rng_of("share_chorus_quieter_0p5", RULES["B"]),
            A_k16_mean_gain_overall=rng_of("mean_gain_overall", RULES["A"], 16),
            A_k16_mean_gain_chorus=rng_of("mean_gain_chorus", RULES["A"], 16),
            B_k16_mean_gain_chorus=rng_of("mean_gain_chorus", RULES["B"], 16),
            B_k16_mean_gain_overall=rng_of("mean_gain_overall", RULES["B"], 16),
            A_k16_minus_k8_chorus=[r((grid[(grid.rule == RULES["A"]) & (grid.push_dB == 16)].mean_gain_chorus.values
                                      - grid[(grid.rule == RULES["A"]) & (grid.push_dB == 8)].mean_gain_chorus.values).min()),
                                   r((grid[(grid.rule == RULES["A"]) & (grid.push_dB == 16)].mean_gain_chorus.values
                                      - grid[(grid.rule == RULES["A"]) & (grid.push_dB == 8)].mean_gain_chorus.values).max())],
            n_combos=int(len(grid) // 2)),
    )
    with open(RES / "a1140_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # ---- 図1：例の1曲、3秒ごとの大きさ（①と②で再生） ----
    e = base[base.song == 0].set_index("k")
    tt = np.arange(len(ex[("pre", 0)])) * 0.5 + 1.5
    cur = dict(t_center_sec=tt)
    for k in [0, 12]:
        cur[f"A_k{k}"] = ex[("pre", k)] + min(0.0, T_BASE - e.loc[k, "Lint"])
        cur[f"B_k{k}"] = ex[("B", k)]
    exdf = pd.DataFrame(cur)
    exdf.round(3).to_csv(DATA / "example_song_3s.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
    for ax, rule in zip(axes, ["A", "B"]):
        for k, col in [(0, BLUE), (12, ORANGE)]:
            y = exdf[f"{rule}_k{k}"]
            lab = "大きく作らない" if k == 0 else "12 dB 大きく作った"
            ax.plot(tt, y, color=col, lw=2, label=f"{lab}（盛り上がる部分の最大 {y.max():.2f} dB）")
        ax.axhline(T_BASE, color=GRAY, ls="--", lw=1)
        ax.text(24.5, T_BASE + 0.25, f"決まった大きさ {T_BASE:.0f} dB", color=GRAY, fontsize=8.5, ha="right")
        for s0 in [6, 18]:
            ax.axvspan(s0, s0 + 6, color=LIGHT, alpha=0.35, lw=0)
        ax.set_title(RULES[rule], fontsize=11)
        ax.set_xlabel("曲の中の時刻（秒、3秒ごとの真ん中）")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=8.5, frameon=False)
    axes[0].set_ylabel("再生したときの3秒ごとの大きさ（dB）")
    lo = min(exdf.drop(columns="t_center_sec").min()) - 1
    axes[0].set_ylim(lo, max(exdf.drop(columns="t_center_sec").max()) + 1.5)
    fig.suptitle("例の1曲：再生のときの大きさ（色の帯は盛り上がる部分）", fontsize=12, y=1.03)
    save(fig, "a1140_example.png", "出典：" + SRC, y=-0.17)
    ex_json = {c: dict(max_3s=r(exdf[c].max()), min_3s=r(exdf[c].min())) for c in exdf.columns if c != "t_center_sec"}
    ex_json["Lint_k0"] = r(e.loc[0, "Lint"])
    ex_json["Lint_k12"] = r(e.loc[12, "Lint"])
    main_json["example_song0"] = ex_json
    with open(RES / "a1140_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # ---- 図2：k ごとの、k=0 との差（①・②・そのまま） ----
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)
    for ax, (col, ttl) in zip(axes, [("gain_overall_vs_k0", "曲全体の平均"), ("gain_chorus_vs_k0", "盛り上がる部分")]):
        ax.plot(per_k.k, per_k["none_" + col], color=GRAY, marker="o", ms=4, label="下げない（そのまま）")
        ax.plot(per_k.k, per_k["A_" + col], color=BLUE, marker="o", ms=4, label=RULES["A"])
        ax.plot(per_k.k, per_k["B_" + col], color=ORANGE, marker="o", ms=4, label=RULES["B"])
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_title(ttl)
        ax.set_xlabel("大きく作った量（dB）")
        ax.set_xticks(KS)
    axes[0].set_ylabel("大きく作らない同じ曲との差\n（dB、500曲の平均）")
    axes[0].legend(fontsize=8.5, frameon=False, loc="upper left")
    fig.suptitle("①の得は決まった大きさに届くまで、②では得がない（基本の置き方、決まった大きさ−16 dB）", fontsize=12, y=1.03)
    save(fig, "a1140_by_push.png", "出典：" + SRC)

    # ---- 図3：確かめ（8 dB 大きく作ったとき、盛り上がる部分の差） ----
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    labels, vals_a, vals_b = [], [], []
    for name in SETS:
        for T in TS:
            g = grid[(grid.contrast_set == name) & (grid["T"] == T)]
            labels.append(f"{name.split('（')[0]}\n{T:.0f} dB")
            vals_a.append(g[(g.rule == RULES["A"]) & (g.push_dB == 16)].mean_gain_chorus.iloc[0])
            vals_b.append(g[(g.rule == RULES["B"]) & (g.push_dB == 16)].mean_gain_chorus.iloc[0])
    xx = np.arange(len(labels))
    ax.bar(xx - 0.2, vals_a, 0.4, color=BLUE, label=RULES["A"])
    ax.bar(xx + 0.2, vals_b, 0.4, color=ORANGE, label=RULES["B"])
    for x, v in zip(xx, vals_a):
        ax.text(x - 0.2, v + (0.08 if v >= 0 else -0.08), f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7)
    for x, v in zip(xx, vals_b):
        ax.text(x + 0.2, v + (0.08 if v >= 0 else -0.08), f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xx)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlabel("曲の強弱の差の置き方（上）と配信先の決まった大きさ（下）")
    ax.set_ylabel("盛り上がる部分の差（dB、\n16 dB 大きく作った曲−作らない曲）")
    ax.set_title("9通り×2つの決まり：16 dB 大きく作ったときの盛り上がる部分の差")
    ax.legend(fontsize=9, frameon=False)
    lo = min(min(vals_a), min(vals_b), 0)
    hi = max(max(vals_a), max(vals_b), 0)
    ax.set_ylim(lo - 0.6, hi + 0.6)
    save(fig, "a1140_robust.png", "出典：" + SRC)


if __name__ == "__main__":
    main()
