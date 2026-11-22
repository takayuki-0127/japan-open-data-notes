"""931 分野ごとの足切りがあると、合格率はどう変わるのか？（架空のデータ）

架空の社内資格試験。3つの分野（A 40問・B 40問・C 20問、1問1点）からなり、合計が6割以上で合格。
「足切り」ありでは、さらにどの分野も4割以上が要る。受験者ごとに分野ごとの本当の実力（何度も受けたときの平均の正答率）を
置き、分野どうしの実力は相関 ρ で結びつく。足切りで合格率がどれだけ下がるか、足切りで落ちた人は本当にその分野が
足切りより下なのか（1回の点の振れで落ちたのか）を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import beta as beta_dist, norm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 931
SRC = "架空の社内資格試験（作成者が乱数で作成、seed 931）"
MEAN, SD, DAY = 55.0, 13.0, 3.0      # 分野ごとの実力の平均・標準偏差、当日の調子の振れ（点）
BASE = {"items": (40, 40, 20), "rho": 0.6, "sec_cut": 0.40, "total_cut": 0.60}
NAMES = ["A", "B", "C"]
N_BASE = 2_000_000
N_GRID = 400_000
MIN_N = 200          # これより少ない人数の割合は出さない（空欄）


def ab(mean, sd):
    k = mean * (1 - mean) / sd ** 2 - 1
    return mean * k, (1 - mean) * k


_A, _B = ab(MEAN / 100, SD / 100)
_U = np.linspace(0, 1, 200_001)
_Q = beta_dist.ppf(_U, _A, _B)          # ベータ分布の分位点の表（細かい目盛りで引いて線で補う）


def abilities(rng, n, rho):
    """分野ごとの実力（0〜1）。正規の相関 rho をベータ分布の形に写す（ガウス・コピュラ）"""
    c = np.full((3, 3), rho); np.fill_diagonal(c, 1.0)
    z = rng.standard_normal((n, 3)) @ np.linalg.cholesky(c).T
    return np.interp(norm.cdf(z), _U, _Q)


def sit(rng, p, items):
    """1回受けたときの分野ごとの得点。当日の調子は3分野に同じだけ効く"""
    q = np.clip(p + rng.normal(0, DAY / 100, (len(p), 1)), 0, 1)
    return np.stack([rng.binomial(m, q[:, k]) for k, m in enumerate(items)], 1)


def rules(x, items, sec_cut, total_cut):
    items = np.asarray(items)
    tcut = int(np.ceil(total_cut * items.sum() - 1e-9))
    scut = np.ceil(sec_cut * items - 1e-9).astype(int)
    total_ok = x.sum(1) >= tcut
    sec_fail = x < scut
    return total_ok, sec_fail, tcut, scut


def run(rng, n, items, rho, sec_cut, total_cut, keep=False):
    items = tuple(items)
    p = abilities(rng, n, rho)
    x = sit(rng, p, items)
    x2 = sit(rng, p, items)
    total_ok, sec_fail, tcut, scut = rules(x, items, sec_cut, total_cut)
    full = total_ok & ~sec_fail.any(1)
    removed = total_ok & sec_fail.any(1)
    weak = p < sec_cut                                     # 本当にその分野が足切りより下
    true_total = (p * np.asarray(items)).sum(1) / sum(items) * 100
    # 落とされた分野がすべて本当は足切り以上＝振れだけで落ちた
    fluke = removed & ~(sec_fail & weak).any(1)
    t2, f2, *_ = rules(x2, items, sec_cut, total_cut)
    full2 = t2 & ~f2.any(1)
    tw = total_ok & weak.any(1)
    o = {"items_A": items[0], "items_B": items[1], "items_C": items[2], "rho": rho, "sec_cut": sec_cut,
         "total_cut": total_cut, "total_cut_pts": tcut, "sec_cut_A": int(scut[0]), "sec_cut_B": int(scut[1]),
         "sec_cut_C": int(scut[2]),
         "pass_total_only": float(total_ok.mean()), "pass_with_cutoff": float(full.mean()),
         "drop_pt": float((total_ok.mean() - full.mean()) * 100),
         "removed_share_of_total_pass": float(removed.sum() / total_ok.sum()),
         "n_removed": int(removed.sum()), "n_total_pass_weak": int(tw.sum()),
         "removed_fluke_share": float(fluke.sum() / removed.sum()) if removed.sum() >= MIN_N else None,
         "removed_true_total_ge_cut": float((true_total[removed] >= total_cut * 100).mean()) if removed.sum() >= MIN_N else None,
         "removed_true_total_mean": float(true_total[removed].mean()) if removed.sum() >= MIN_N else None,
         "full_true_total_mean": float(true_total[full].mean()),
         "removed_pass_next_time": float(full2[removed].mean()) if removed.sum() >= MIN_N else None,
         "full_pass_next_time": float(full2[full].mean()),
         "weak_any_share_all": float(weak.any(1).mean()),
         "total_pass_weak_share": float(tw.sum() / total_ok.sum()),
         "total_pass_weak_caught": float((tw & removed).sum() / tw.sum()) if tw.sum() >= MIN_N else None,
         "full_pass_weak_share": float((full & weak.any(1)).sum() / full.sum())}
    for k, nm in enumerate(NAMES):
        o[f"removed_by_{nm}"] = float((removed & sec_fail[:, k]).sum() / removed.sum()) if removed.sum() >= MIN_N else None
        m = removed & sec_fail[:, k]
        o[f"removed_by_{nm}_true_ge_cut"] = float((p[m, k] >= sec_cut).mean()) if m.any() else None
    if keep:
        return o, p, x, total_ok, sec_fail, removed, full
    return o


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base, p, x, total_ok, sec_fail, removed, full = run(rng, N_BASE, keep=True, **BASE)

    # 合計で受かった人のうち、本当の C の実力ごとに C で足切りされる割合（C の問題数を変えて）
    curve = []
    for items_c in [10, 20, 40]:
        r = np.random.default_rng(SEED * 10 + items_c)
        items = (40, 40, items_c)
        pp = abilities(r, 600_000, BASE["rho"])
        xx = sit(r, pp, items)
        tok, sf, *_ = rules(xx, items, BASE["sec_cut"], BASE["total_cut"])
        tc = pp[:, 2] * 100
        for lo in range(26, 60, 2):
            m = tok & (tc >= lo) & (tc < lo + 2)
            if m.sum() >= 200:
                curve.append({"items_C": items_c, "true_C_from": lo, "true_C_to": lo + 2, "n_total_pass": int(m.sum()),
                              "cut_by_C": float(sf[m, 2].mean())})
    curve = pd.DataFrame(curve).round(4)
    curve.to_csv(RES / "cut_by_true_C.csv", index=False)

    # 確かめ：相関 × 足切りの高さ × C の問題数（27通り、各40万人）
    grid = []
    for i, rho in enumerate([0.3, 0.6, 0.9]):
        for j, sc in enumerate([0.30, 0.40, 0.50]):
            for k, ic in enumerate([10, 20, 40]):
                grid.append(run(np.random.default_rng(SEED * 100 + i * 9 + j * 3 + k), N_GRID, (40, 40, ic), rho, sc, 0.60))
    grid = pd.DataFrame(grid).round(4)
    grid.to_csv(RES / "robustness.csv", index=False)

    # data：最初の5,000人
    tt = (p * np.array(BASE["items"])).sum(1) / 100 * 100
    pd.DataFrame({"person": np.arange(1, 5001), "true_A": np.round(p[:5000, 0] * 100, 2),
                  "true_B": np.round(p[:5000, 1] * 100, 2), "true_C": np.round(p[:5000, 2] * 100, 2),
                  "score_A": x[:5000, 0], "score_B": x[:5000, 1], "score_C": x[:5000, 2],
                  "total": x[:5000].sum(1), "pass_total_only": total_ok[:5000].astype(int),
                  "pass_with_cutoff": full[:5000].astype(int)}).to_csv(DATA / "exam_sample_5000.csv", index=False)

    rnd = lambda d: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}
    rng_of = lambda c: [float(grid[c].min()), float(grid[c].max()), int(grid[c].notna().sum())]
    out = {"settings": {**{k: v for k, v in BASE.items()}, "mean_pts": MEAN, "sd_pts": SD, "day_pts": DAY,
                        "n_people": N_BASE, "n_grid": N_GRID, "seed": SEED},
           "base": rnd(base),
           "grid27_ranges": {c: rng_of(c) for c in ["drop_pt", "removed_share_of_total_pass", "removed_fluke_share",
                                                   "removed_true_total_ge_cut", "removed_pass_next_time",
                                                   "total_pass_weak_caught", "full_pass_weak_share"]},
           "grid_sec_cut_0_4_ranges": {c: [float(grid[grid.sec_cut == 0.4][c].min()), float(grid[grid.sec_cut == 0.4][c].max()),
                                           int(grid[grid.sec_cut == 0.4][c].notna().sum())]
                                       for c in ["drop_pt", "removed_fluke_share", "total_pass_weak_caught", "removed_pass_next_time",
                                                 "removed_share_of_total_pass"]},
           "range_note": "[最小, 最大, 値のある通りの数]。足切りで落ちた人などが200人未満の通りは空欄にして範囲に入れない"}
    json.dump(out, open(RES / "a931_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

    # 図1：合格率と、足切りで落ちた人の中身
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 3.9), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axs[0]
    v = [base["pass_total_only"] * 100, base["pass_with_cutoff"] * 100]
    ax.bar([0, 1], v, color=[LIGHT, BLUE], width=.6)
    for i, y in enumerate(v):
        ax.text(i, y + 0.6, f"{y:.1f}%", ha="center", fontsize=10)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["合計6割だけ", "合計6割＋\nどの分野も4割"])
    ax.set_ylabel("合格率（%）"); ax.set_ylim(0, 45)
    ax.set_title(f"足切りで合格率は{base['drop_pt']:.1f}ポイント下がる", fontsize=10.5)
    ax = axs[1]
    fl = base["removed_fluke_share"] * 100
    ax.barh([0], [fl], color=ORANGE, height=.5, label="落ちた分野の本当の実力は4割以上（振れで落ちた）")
    ax.barh([0], [100 - fl], left=[fl], color=GRAY, height=.5, label="本当に4割より下の分野があった")
    ax.text(fl / 2, 0, f"{fl:.1f}%", ha="center", va="center", color="white", fontsize=11)
    ax.text(fl + (100 - fl) / 2, 0, f"{100-fl:.1f}%", ha="center", va="center", color="white", fontsize=11)
    ax.set_xlim(0, 100); ax.set_yticks([]); ax.set_xlabel("足切りで落ちた人の内訳（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    ax.set_ylim(-0.6, 0.6)
    ax.set_title("合計は足りたのに足切りで落ちた人", fontsize=10.5)
    fig.suptitle("A 40問・B 40問・C 20問、分野どうしの実力の相関0.6と置いた場合（200万人）", fontsize=11)
    fig.tight_layout()
    save(fig, "a931_pass_and_removed.png", SRC)

    # 図2：本当の C の実力ごとに、C で足切りされる割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    for ic, col in [(10, ORANGE), (20, BLUE), (40, GREEN)]:
        s = curve[curve.items_C == ic]
        ax.plot((s.true_C_from + 1), s.cut_by_C * 100, "o-", ms=3.5, color=col, label=f"C {ic}問")
    ax.axvline(40, color=GRAY, lw=.8, ls=":")
    ax.text(40.5, 92, "足切り（4割）", fontsize=9, color=GRAY)
    ax.set_xlabel("C の本当の実力（点、100点満点に直した値）"); ax.set_ylabel("C で足切りされる割合（%）")
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("合計で受かった人のうち、C で足切りされる割合（各60万人）", fontsize=11)
    save(fig, "a931_cut_by_true_C.png", SRC)

    # 図3：確かめ（相関と足切りの高さ、C の問題数）
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 3.9))
    g = grid[grid.items_C == 20]
    for sc, col in [(0.3, GREEN), (0.4, BLUE), (0.5, ORANGE)]:
        s = g[g.sec_cut == sc].sort_values("rho")
        axs[0].plot(s.rho, s.drop_pt, "o-", color=col, label=f"足切り {sc*10:.0f}割")
    axs[0].set_xlabel("分野どうしの実力の相関"); axs[0].set_ylabel("合格率の下がり（ポイント）")
    axs[0].set_title("合格率の下がり（C 20問）", fontsize=10.5); axs[0].set_xticks([0.3, 0.6, 0.9])
    axs[0].legend(frameon=False, fontsize=8.5)
    g = grid[grid.sec_cut == 0.4]
    for rho, col in [(0.3, GREEN), (0.6, BLUE), (0.9, ORANGE)]:
        s = g[g.rho == rho].sort_values("items_C")
        axs[1].plot(s.items_C, s.removed_fluke_share * 100, "o-", color=col, label=f"相関 {rho}")
    axs[1].set_xlabel("C の問題数"); axs[1].set_ylabel("足切りで落ちた人のうち、\n振れで落ちた人の割合（%）", linespacing=1.6)
    axs[1].set_xticks([10, 20, 40]); axs[1].set_ylim(0, 100)
    axs[1].set_title("振れで落ちた人の割合（足切り4割）", fontsize=10.5)
    axs[1].legend(frameon=False, fontsize=8.5, loc="lower left")
    axs[1].text(40, 3, "相関0.9・C 40問は、落ちた人が\n200人未満のため点を置かない", fontsize=8, color=GRAY, ha="right")
    fig.suptitle("置き方を変えると（各40万人）", fontsize=11)
    fig.tight_layout()
    save(fig, "a931_robustness.png", SRC)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
