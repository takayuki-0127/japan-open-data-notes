"""1290 箱の内のりと板の幅のすきまで、入らない割合は部品ごとの外れの割合から見込めるのか？（架空のデータ）

架空の家具の引き出し：箱の内のり（内側の幅）と、中に入れる板の幅。
  箱の内のり：規格 300.0±0.5mm（299.5〜300.5mm）
  板の幅    ：規格 299.0±0.5mm（298.5〜299.5mm）→ 規格の真ん中どうしのすきまは1.0mm
すきま＝箱の内のり−板の幅。すきまがマイナスなら板は入らない。
部品ごとの外れの割合（規格の外に出る割合）を同じにそろえ、外れ方を4つ置いて、入らない割合を比べる。
  ばらつき     ：平均は規格の真ん中。標準偏差を外れの割合に合わせる
  狭い側へずれる：平均がすきまの狭くなる側へ0.2mmずれる（箱は小さく、板は大きく）。標準偏差を外れの割合に合わせる
  広い側へずれる：平均がすきまの広くなる側へ0.2mmずれる
  まれに大きくずれる：ふだんは標準偏差0.1mm、まれに標準偏差0.6mmの品がまざる。まざる割合を外れの割合に合わせる
入らない割合は式（すきまの平均と標準偏差から出す）で出し、100万組を乱数で組んで確かめる。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1290
SRC = "架空の引き出しの箱と板の寸法（作成者が乱数で作成、seed 1290）"
TOL = 0.5
BOX_NOM = 300.0
SHIFT = 0.2
NARROW, WIDE = 0.1, 0.6
PS = [0.001, 0.01, 0.05]
GAPS = [0.6, 1.0, 1.4]
MODES = ["spread", "tight_shift", "loose_shift", "rare_wide"]
MODE_JA = {"spread": "ばらつき", "tight_shift": "狭い側へずれる", "loose_shift": "広い側へずれる", "rare_wide": "まれに大きくずれる"}
N_SIM = 1_000_000


def Phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def out_rate(comps, nom):
    lo, hi = nom - TOL, nom + TOL
    return sum(w * (Phi((lo - m) / s) + 1 - Phi((hi - m) / s)) for w, m, s in comps)


def bisect(f, a, b, target, it=200):
    """f は単調。f(x)=target の x を返す"""
    fa = f(a) - target
    for _ in range(it):
        c = (a + b) / 2
        fc = f(c) - target
        if (fc > 0) == (fa > 0):
            a, fa = c, fc
        else:
            b = c
    return (a + b) / 2


def part_comps(mode, p, nom, tight_dir):
    """tight_dir：すきまが狭くなる向き（箱は−1、板は+1）"""
    if mode == "spread":
        s = bisect(lambda s: out_rate([(1, nom, s)], nom), 0.01, 2.0, p)
        return [(1.0, nom, s)]
    if mode in ("tight_shift", "loose_shift"):
        m = nom + SHIFT * tight_dir * (1 if mode == "tight_shift" else -1)
        s = bisect(lambda s: out_rate([(1, m, s)], nom), 0.01, 2.0, p)
        return [(1.0, m, s)]
    q = bisect(lambda q: out_rate([(1 - q, nom, NARROW), (q, nom, WIDE)], nom), 0.0, 1.0, p)
    return [(1 - q, nom, NARROW), (q, nom, WIDE)]


def fail_formula(box, board):
    tot = 0.0
    for wa, ma, sa in box:
        for wb, mb, sb in board:
            tot += wa * wb * Phi((0 - (ma - mb)) / math.sqrt(sa * sa + sb * sb))
    return tot


def gap_mean_sd(box, board):
    ma = sum(w * m for w, m, s in box); mb = sum(w * m for w, m, s in board)
    va = sum(w * (s * s + m * m) for w, m, s in box) - ma * ma
    vb = sum(w * (s * s + m * m) for w, m, s in board) - mb * mb
    return ma - mb, math.sqrt(va + vb)


def draw(rng, comps, n):
    if len(comps) == 1:
        w, m, s = comps[0]
        return rng.normal(m, s, n)
    u = rng.random(n)
    (w1, m1, s1), (w2, m2, s2) = comps
    return np.where(u < w1, rng.normal(m1, s1, n), rng.normal(m2, s2, n))


def simulate(rng, box, board, gap_nom, n=N_SIM):
    board_nom = BOX_NOM - gap_nom
    a = draw(rng, box, n); b = draw(rng, board, n)
    g = a - b
    a_in = np.abs(a - BOX_NOM) <= TOL
    b_in = np.abs(b - board_nom) <= TOL
    fail = g < 0
    return dict(sim_fail=fail.mean(), sim_box_out=1 - a_in.mean(), sim_board_out=1 - b_in.mean(),
                sim_fail_both_in=(fail & a_in & b_in).mean(),
                sim_fail_given_one_out=fail[~(a_in & b_in)].mean() if (~(a_in & b_in)).any() else 0.0), g


def r(x, k=4):
    return float(round(x, k))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # ① すきまの規格どおり（1.0mm）で、部品ごとの外れの割合と外れ方を両方の部品でそろえた12通り
    rows, gaps_keep = [], {}
    for p in PS:
        for mode in MODES:
            box = part_comps(mode, p, BOX_NOM, -1)
            board = part_comps(mode, p, BOX_NOM - 1.0, +1)
            sim, g = simulate(rng, box, board, 1.0)
            mu, sd = gap_mean_sd(box, board)
            rows.append(dict(part_out_pct=p * 100, mode=MODE_JA[mode], gap_mean_mm=r(mu), gap_sd_mm=r(sd),
                             fail_per_million_formula=r(fail_formula(box, board) * 1e6, 2),
                             fail_per_million_sim=r(sim["sim_fail"] * 1e6, 0),
                             fail_per_million_from_gap_mean_sd=r(Phi(-mu / sd) * 1e6, 2),
                             box_out_pct_sim=r(sim["sim_box_out"] * 100), board_out_pct_sim=r(sim["sim_board_out"] * 100),
                             both_out_per_million=r(p * p * 1e6, 2), either_out_per_million=r((1 - (1 - p) ** 2) * 1e6, 2),
                             fail_both_in_per_million_sim=r(sim["sim_fail_both_in"] * 1e6, 0),
                             box_sd_mm=r(box[-1][2] if mode != "rare_wide" else NARROW),
                             rare_share_pct=r(box[1][0] * 100) if mode == "rare_wide" else None))
            if p == 0.01 and mode in ("spread", "tight_shift"):
                gaps_keep[mode] = g[:200_000]
    main_tab = pd.DataFrame(rows)
    main_tab.to_csv(RES / "main_cases.csv", index=False)

    # ② 確かめ：すきま 0.6・1.0・1.4mm × 外れの割合3つ × 箱と板の外れ方 4×4＝16組（式）
    grid = []
    for gap in GAPS:
        for p in PS:
            for mb in MODES:
                for mp in MODES:
                    box = part_comps(mb, p, BOX_NOM, -1)
                    board = part_comps(mp, p, BOX_NOM - gap, +1)
                    grid.append(dict(gap_nominal_mm=gap, part_out_pct=p * 100, box_mode=MODE_JA[mb], board_mode=MODE_JA[mp],
                                     fail_per_million_formula=r(fail_formula(box, board) * 1e6, 2)))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gsum = grid.groupby(["gap_nominal_mm", "part_out_pct"]).fail_per_million_formula.agg(["min", "max"]).reset_index()
    gsum.columns = ["gap_nominal_mm", "part_out_pct", "fail_per_million_min", "fail_per_million_max"]
    gsum.to_csv(RES / "grid_summary.csv", index=False)

    # ③ すきま0.6mm（許容差の和1.0mmより狭い）で、両方が規格の中でも入らない組（外れの割合1%、外れ方を両方でそろえる）
    narrow = []
    for mode in MODES:
        box = part_comps(mode, 0.01, BOX_NOM, -1)
        board = part_comps(mode, 0.01, BOX_NOM - 0.6, +1)
        sim, _ = simulate(rng, box, board, 0.6)
        narrow.append(dict(mode=MODE_JA[mode], fail_per_million_formula=r(fail_formula(box, board) * 1e6, 2),
                           fail_per_million_sim=r(sim["sim_fail"] * 1e6, 0),
                           fail_both_in_per_million_sim=r(sim["sim_fail_both_in"] * 1e6, 0),
                           share_of_fail_both_in_pct=r(sim["sim_fail_both_in"] / sim["sim_fail"] * 100, 2) if sim["sim_fail"] > 0 else None))
    narrow = pd.DataFrame(narrow)
    narrow.to_csv(RES / "gap06_both_in.csv", index=False)

    # data：外れの割合1%・ばらつきの組を5,000組
    rng_d = np.random.default_rng(SEED + 1)
    box = part_comps("spread", 0.01, BOX_NOM, -1); board = part_comps("spread", 0.01, BOX_NOM - 1.0, +1)
    a = draw(rng_d, box, 5000); b = draw(rng_d, board, 5000)
    pd.DataFrame(dict(pair_id=np.arange(1, 5001), box_inner_mm=a.round(4), board_width_mm=b.round(4),
                      gap_mm=(a - b).round(4))).to_csv(DATA / "pairs_spread_1pct.csv", index=False)

    m1 = main_tab[main_tab.part_out_pct == 1.0]
    main_json = dict(
        setting=dict(box_spec="300.0±0.5mm", board_spec="299.0±0.5mm", nominal_gap_mm=1.0, shift_mm=SHIFT,
                     narrow_sd_mm=NARROW, wide_sd_mm=WIDE, n_pairs_sim=N_SIM),
        main_cases=main_tab.to_dict(orient="records"),
        max_abs_diff_formula_sim_per_million=r((main_tab.fail_per_million_formula - main_tab.fail_per_million_sim).abs().max(), 2),
        grid_summary=gsum.to_dict(orient="records"),
        gap06_both_in=narrow.to_dict(orient="records"),
    )
    with open(RES / "a1290_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：外れの割合1%で、外れ方ごとの入らない割合
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    xs = np.arange(len(m1))
    vals = m1.fail_per_million_formula.values
    ax.bar(xs, vals, color=[BLUE, ORANGE, GREEN, GRAY], width=0.6)
    for x, v in zip(xs, vals):
        ax.text(x, max(v, 130) + 30, f"{v:,.2f}組", ha="center", va="bottom", fontsize=10)
    ax.axhline(100, color=INK, lw=1, ls="--")
    ax.text(2.0, 330, "点線：両方とも外れる組 100組", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels(m1["mode"].values)
    ax.set_ylim(0, 2900); ax.set_ylabel("板が入らない組（100万組あたり）")
    ax.set_title("箱も板も外れの割合1%：外れ方ごとの入らない割合（すきま1.0mm）")
    save(fig, "a1290_fail_by_mode.png", SRC)

    # 図2：すきまの分布（ばらつき と 狭い側へずれる）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    bins = np.linspace(-0.4, 2.0, 121)
    ax.hist(gaps_keep["spread"], bins=bins, color=BLUE, alpha=0.55, label="ばらつき")
    ax.hist(gaps_keep["tight_shift"], bins=bins, color=ORANGE, alpha=0.55, label="狭い側へずれる")
    ax.axvline(0, color=INK, lw=1.2)
    ax.text(-0.03, ax.get_ylim()[1] * 0.9, "ここより左は入らない", ha="right", fontsize=9)
    ax.set_xlabel("すきま（mm）"); ax.set_ylabel("組の数（20万組のうち）")
    ax.set_title("箱も板も外れの割合1%のときのすきまの分布")
    ax.legend(frameon=False)
    save(fig, "a1290_gap_hist.png", SRC)

    # 図3：確かめ。すきま×外れの割合ごとの、16組の入らない割合の最小〜最大（対数の目盛り）
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    colors = {0.6: ORANGE, 1.0: BLUE, 1.4: GREEN}
    for j, gap in enumerate(GAPS):
        sub = gsum[gsum.gap_nominal_mm == gap]
        x = np.arange(len(PS)) + (j - 1) * 0.22
        lo = sub["fail_per_million_min"].clip(lower=1e-4).values; hi = sub["fail_per_million_max"].values
        ax.vlines(x, lo, hi, color=colors[gap], lw=5, label=f"すきま {gap}mm")
    ax.set_yscale("log"); ax.set_ylim(1e-4, 1e8)
    ax.set_xticks(np.arange(len(PS))); ax.set_xticklabels([f"部品ごとの外れ {p*100:g}%" for p in PS])
    ax.set_ylabel("入らない組（100万組あたり、対数の目盛り）")
    ax.set_title("外れの割合が同じでも、外れ方16組で入らない割合はこれだけ動く")
    ax.legend(frameon=False, loc="upper left", ncol=3)
    ax.text(0.01, 0.84, "下の端（0.0001組）まで届く線は、最小がそれより小さい（ほぼ0組）", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=8.5, color=INK)
    save(fig, "a1290_grid_range.png", SRC)

    print(main_tab.to_string())
    print(gsum.to_string()); print(narrow.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
