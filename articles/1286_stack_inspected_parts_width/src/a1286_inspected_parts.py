"""1286 検査で規格外を除いた部品だけを組むと、組み立て品のばらつきは、除く前の部品の標準偏差から見込んだ幅より狭くなるのか？（架空のデータ）

架空の引き出し。5つの部品の寸法を足した長さを見る。部品の寸法のずれは正規分布で標準偏差0.10mm（除く前）、
平均のずれ delta。部品の規格は ±L（基本 0.15mm＝標準偏差の1.5倍）。検査で規格の外と測られた部品は除き、残りだけで組む。
検査の測りには、ばらつき e（基本0）がまざることがある（測った値で合否を決め、組むのは本当の寸法）。
見込みの3つの置き方：
  (a) 除く前の標準偏差で二乗の足し算
  (b) 規格の幅を標準偏差の3倍と見て（L/3）二乗の足し算
  (c) 規格の中で平らに散らばると見て（L/√3）二乗の足し算
組み立て品の許容差は、部品の規格を二乗で足した ±√5×L と、そのまま足した ±5L。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1286
SRC = "架空の引き出しの部品の寸法のシミュレーション（作成者が乱数で作成、seed 1286）"
SIG = 0.10
BASE = {"n": 5, "L": 1.5, "delta": 0.0, "e": 0.0}
N_ASM = 1_000_000
N_ASM_GRID = 400_000
LS = [1.0, 1.5, 2.0, 3.0]
DELTAS = [0.0, 0.5, 1.0]
ES = [0.0, 0.25, 0.5]


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def npdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def trunc_formula(L, delta):
    """測りのばらつきがないとき、規格 ±L で切った正規（平均 delta、標準偏差1）の平均と標準偏差（式）"""
    a, b = -L - delta, L - delta
    Z = ncdf(b) - ncdf(a)
    m = (npdf(a) - npdf(b)) / Z
    v = 1 + (a * npdf(a) - b * npdf(b)) / Z - m * m
    return delta + m, math.sqrt(v), Z


def parts(rng, need, L, delta, e):
    """規格に通った部品を need 個作る（標準偏差1の単位）。通った割合も返す"""
    out = []
    got, made = 0, 0
    while got < need:
        k = int((need - got) * 1.3) + 1000
        x = rng.normal(delta, 1, k)
        meas = x + (rng.normal(0, e, k) if e > 0 else 0.0)
        ok = np.abs(meas) <= L
        out.append(x[ok]); got += int(ok.sum()); made += k
    x = np.concatenate(out)[:need]
    return x, got / made


def setting(rng, n, L, delta, e, n_asm, keep=False):
    x, pass_rate = parts(rng, n * n_asm, L, delta, e)
    h = x.reshape(n_asm, n).sum(1)
    sd_part = float(x.std())
    sd_h = float(h.std())
    T_rss = math.sqrt(n) * L
    T_worst = n * L
    pred_a = math.sqrt(n) * 1.0
    pred_b = math.sqrt(n) * L / 3
    pred_c = math.sqrt(n) * L / math.sqrt(3)
    fm, fs, fz = trunc_formula(L, delta)
    r = {"n_parts": n, "spec_L_sd": L, "spec_L_mm": round(L * SIG, 4), "mean_shift_sd": delta, "meas_error_sd": e,
         "tol_rss_mm": round(T_rss * SIG, 4), "tol_worst_mm": round(T_worst * SIG, 4),
         "pass_rate_pct": round(100 * pass_rate, 2), "pass_rate_formula_no_meas_error_pct": round(100 * trunc_formula(L, delta)[2], 2),
         "part_sd_after_mm": round(sd_part * SIG, 4), "part_sd_after_formula_mm": round(fs * SIG, 4),
         "asm_mean_mm": round(float(h.mean()) * SIG, 4), "asm_sd_mm": round(sd_h * SIG, 4),
         "pred_a_before_mm": round(pred_a * SIG, 4), "pred_b_spec_div3_mm": round(pred_b * SIG, 4), "pred_c_flat_mm": round(pred_c * SIG, 4),
         "ratio_to_a": round(sd_h / pred_a, 4), "ratio_to_b": round(sd_h / pred_b, 4), "ratio_to_c": round(sd_h / pred_c, 4),
         "ratio_to_hard_cut_formula": round(sd_h / (math.sqrt(n) * fs), 4),
         "out_rss_pct": round(100 * float((np.abs(h) > T_rss).mean()), 3),
         "out_rss_if_b_pct": round(100 * 2 * (1 - ncdf(3)), 3),
         "out_rss_if_a_pct": round(100 * 2 * (1 - ncdf(T_rss / pred_a)), 3),
         "out_worst_pct": round(100 * float((np.abs(h) > T_worst).mean()), 4),
         "part_outside_spec_pct": round(100 * float((np.abs(x) > L).mean()), 3)}
    return (r, h, x) if keep else r


def main():
    rng = np.random.default_rng(SEED)
    n, L, d, e = BASE["n"], BASE["L"], BASE["delta"], BASE["e"]
    base, h, x = setting(rng, n, L, d, e, N_ASM, keep=True)
    # 除く前の組み立て品（比べるため）
    h0 = rng.normal(0, 1, (N_ASM, n)).sum(1)
    base["before_asm_sd_mm"] = round(float(h0.std()) * SIG, 4)
    base["before_out_rss_pct"] = round(100 * float((np.abs(h0) > math.sqrt(n) * L).mean()), 3)
    base["before_out_worst_pct"] = round(100 * float((np.abs(h0) > n * L).mean()), 4)
    pd.DataFrame({"part_dev_mm": (x[:2000] * SIG).round(4)}).to_csv(DATA / "example_passed_parts.csv", index=False)
    pd.DataFrame({"assembly_dev_mm": (h[:2000] * SIG).round(4)}).to_csv(DATA / "example_assemblies.csv", index=False)

    # 部品の数
    base_row = {k_: v for k_, v in base.items() if not k_.startswith("before_")}
    by_n = pd.DataFrame([base_row if nn == n else setting(rng, nn, L, d, e, N_ASM_GRID) for nn in [2, 3, 5, 8, 12]])
    by_n.to_csv(RES / "by_n_parts.csv", index=False)
    # 36通り
    grid = pd.DataFrame([base_row if (LL, dd, ee) == (L, d, e) else setting(rng, n, LL, dd, ee, N_ASM_GRID)
                         for LL in LS for dd in DELTAS for ee in ES])
    grid.to_csv(RES / "grid.csv", index=False)

    g0 = grid[grid.meas_error_sd == 0]
    main_json = {
        "setting": {"n_parts": n, "sd_before_mm": SIG, "spec_L_mm": L * SIG, "assemblies": N_ASM, "grid_assemblies": N_ASM_GRID, "seed": SEED},
        "base": base,
        "grid_range": {
            "ratio_to_a_min": float(grid.ratio_to_a.min()), "ratio_to_a_max": float(grid.ratio_to_a.max()),
            "ratio_to_b_min": float(grid.ratio_to_b.min()), "ratio_to_b_max": float(grid.ratio_to_b.max()),
            "out_rss_min_pct": float(grid.out_rss_pct.min()), "out_rss_max_pct": float(grid.out_rss_pct.max()),
            "out_worst_max_pct_no_meas_error": float(g0.out_worst_pct.max()),
            "out_worst_max_pct_with_meas_error": float(grid[grid.meas_error_sd > 0].out_worst_pct.max()),
            "max_abs_diff_hard_cut_formula_no_meas_error": round(float((g0.ratio_to_hard_cut_formula - 1).abs().max()), 4),
            "n_settings_ratio_to_b_over_1": int((grid.ratio_to_b > 1).sum()), "n_settings": int(len(grid)),
        },
    }
    with open(RES / "a1286_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：部品と組み立て品の分布
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    ax = axes[0]
    xs = np.linspace(-0.4, 0.4, 401)
    ax.hist(x * SIG, bins=np.arange(-0.4, 0.401, 0.01), density=True, color=LIGHT, edgecolor="white", label="検査に通った部品")
    ax.plot(xs, [npdf(v / SIG) / SIG for v in xs], color=GRAY, ls="--", lw=1, label="除く前（標準偏差0.10mm）")
    ax.vlines([-L * SIG, L * SIG], 0, 4.9, color=ORANGE, lw=1)
    ax.set_title("部品1つ（規格 ±0.15mm で除いた後）", fontsize=11)
    ax.set_xlabel("ずれ（mm）"); ax.set_ylabel("密度"); ax.set_ylim(0, 6.4)
    ax.legend(fontsize=8, frameon=False, loc="upper center", ncol=2)
    ax = axes[1]
    xs = np.linspace(-0.8, 0.8, 401)
    ax.hist(h * SIG, bins=np.arange(-0.8, 0.801, 0.02), density=True, color=LIGHT, edgecolor="white", label="通った部品5つで組んだ")
    for sd_, c_, lab in [(base["pred_a_before_mm"], GRAY, "見込み(a) 除く前の標準偏差"), (base["pred_b_spec_div3_mm"], ORANGE, "見込み(b) 規格÷3 を標準偏差と見る")]:
        ax.plot(xs, [npdf(v / sd_) / sd_ for v in xs], color=c_, ls="--", lw=1.2, label=lab)
    ax.vlines([-math.sqrt(n) * L * SIG, math.sqrt(n) * L * SIG], 0, 2.6, color=INK, lw=0.8)
    ax.text(math.sqrt(n) * L * SIG, 1.1, " 許容差\n ±0.3354mm", fontsize=8)
    ax.set_title("組み立て品（部品5つの合計）", fontsize=11)
    ax.set_xlabel("ずれ（mm）"); ax.set_ylim(0, 4.6)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    save(fig, "a1286_hist.png", SRC, y=-0.03)

    # 図2：規格の幅と、標準偏差の比（測りのばらつきなし・平均のずれなし）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    gg = grid[(grid.mean_shift_sd == 0) & (grid.meas_error_sd == 0)]
    xs_ = np.arange(len(gg))
    ax.bar(xs_ - 0.2, gg.ratio_to_a, 0.4, color=GRAY, label="(a) 除く前の標準偏差から見込んだ幅に対して")
    ax.bar(xs_ + 0.2, gg.ratio_to_b, 0.4, color=BLUE, label="(b) 規格÷3 を標準偏差と見た幅に対して")
    for xx, v in zip(xs_ - 0.2, gg.ratio_to_a):
        ax.text(xx, v + 0.03, f"{v:g}", ha="center", fontsize=8)
    for xx, v in zip(xs_ + 0.2, gg.ratio_to_b):
        ax.text(xx, v + 0.03, f"{v:g}", ha="center", fontsize=8)
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_xticks(xs_, [f"±{v * SIG:.2f}mm\n（標準偏差の{v:g}倍）" for v in gg.spec_L_sd])
    ax.set_xlabel("部品の規格の幅")
    ax.set_ylabel("組み立て品の標準偏差 ÷ 見込み")
    ax.set_ylim(0, 2.1)
    ax.set_title("除いた後の組み立て品の幅と、2つの見込みの比（平均のずれ・測りのばらつきなし）", fontsize=11.5)
    ax.legend(fontsize=8.5, frameon=False, loc="upper right")
    save(fig, "a1286_ratio_by_spec.png", SRC, y=-0.1)

    # 図3：測りのばらつきと、許容差の外に出る割合（規格±0.15mm）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    gl = grid[grid.spec_L_sd == L]
    for j, dd in enumerate(DELTAS):
        g_ = gl[gl.mean_shift_sd == dd]
        xx = np.arange(len(ES)) + (j - 1) * 0.26
        ax.bar(xx, g_.out_rss_pct, 0.26, color=[BLUE, GREEN, ORANGE][j], label=f"平均のずれ {dd * SIG:.2f}mm")
        for a_, v in zip(xx, g_.out_rss_pct):
            ax.text(a_, v + 0.4, f"{v:g}", ha="center", fontsize=7.5)
    ax.set_xticks(np.arange(len(ES)), [f"測りのばらつき {v * SIG:.3f}mm" for v in ES])
    ax.set_ylabel("許容差 ±0.3354mm の外に出た組み立て品（%）")
    ax.set_ylim(0, 48)
    ax.set_title("規格 ±0.15mm で除いた部品5つ：許容差の外に出た割合")
    ax.legend(fontsize=9, frameon=False, loc="upper center", ncol=3)
    save(fig, "a1286_out_meas_error.png", SRC)
    print(json.dumps(main_json, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
