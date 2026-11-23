"""1049 要素どうしが関係しているとき、別々に見込んで掛けると何がずれるのか？（架空のデータ）

架空の A町（12,000世帯、戸建て45%・集合住宅55%）。世帯ごとにエアコンの台数（1〜6台）と、
1台あたり1年に掃除を頼む確率を置き、2つを世帯の中で相関させる（基本：相関0.4、潜在の値どうし）。
本当の件数＝世帯ごとに頼んだ台数の合計（作成者が乱数で作る）。
概算：①世帯数×1世帯あたりの台数の平均×世帯ごとの「頼んだ割合」の平均（別々に見込んで掛ける）
      ②世帯数×台数の平均×台数で重みを付けた割合（＝頼んだ台数÷台数の合計）
      ③戸建て・集合住宅の区分ごとに①を作って足す
後半：1人が3つの要素を見込むときの誤差どうしの相関と、「独立」と置いて作った90%の幅の当たり。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1049
SRC = "架空の A町の世帯と架空の概算（作成者が乱数で作成、seed 1049）"
N_HH = 12000
SHARE_HOUSE = 0.45
BASE = dict(rho=0.4, gap=1.0, sig_p=0.6)
UNITS_MU = {"house": 2.8, "apt": 1.6}
P_MU = {"house": 0.10, "apt": 0.06}
SIG_N = 0.35
SIG_F = 0.35        # 後半：要素ごとの見込みの誤差（対数の標準偏差）
Z90 = 1.6448536


def town(rng, rho=0.4, gap=1.0, sig_p=0.6, n=N_HH):
    house = rng.random(n) < SHARE_HOUSE
    z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], n)
    # gap：区分どうしの違いの大きさ（0＝同じ、1＝基本、2＝基本の2倍、対数の上で）
    mid_n = np.sqrt(UNITS_MU["house"] * UNITS_MU["apt"]); mid_p = np.sqrt(P_MU["house"] * P_MU["apt"])
    mu_n = np.where(house, mid_n * (UNITS_MU["house"] / mid_n) ** gap, mid_n * (UNITS_MU["apt"] / mid_n) ** gap)
    mu_p = np.where(house, mid_p * (P_MU["house"] / mid_p) ** gap, mid_p * (P_MU["apt"] / mid_p) ** gap)
    units = np.clip(np.round(mu_n * np.exp(SIG_N * z[:, 0] - SIG_N ** 2 / 2)), 1, 6).astype(int)
    p = np.clip(mu_p * np.exp(sig_p * z[:, 1] - sig_p ** 2 / 2), 0, 0.9)
    req = rng.binomial(units, p)
    return pd.DataFrame({"house": house.astype(int), "units": units, "p": p, "requests": req})


def estimates(df):
    true = int(df.requests.sum())
    share = df.requests / df.units
    sep = len(df) * df.units.mean() * share.mean()
    w = len(df) * df.units.mean() * (df.requests.sum() / df.units.sum())
    seg = sum(len(g) * g.units.mean() * (g.requests / g.units).mean() for _, g in df.groupby("house"))
    # 式：平均(台数×割合)＝平均(台数)×平均(割合)＋共分散
    cov = float(np.cov(df.units, share, ddof=0)[0, 1])
    formula = 1 / (1 + cov / (df.units.mean() * share.mean()))
    return {"true": true, "separate": sep, "weighted": w, "by_type": seg,
            "ratio_separate": sep / true, "ratio_weighted": w / true, "ratio_by_type": seg / true,
            "ratio_formula": formula,
            "corr_units_share": float(np.corrcoef(df.units, share)[0, 1]),
            "corr_units_p": float(np.corrcoef(df.units, df.p)[0, 1])}


def main():
    rng = np.random.default_rng(SEED)
    df = town(rng, **BASE)
    df.round({"p": 4}).to_csv(DATA / "households.csv", index_label="household")
    base = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in estimates(df).items()}
    base["mean_units"] = round(float(df.units.mean()), 4)
    base["mean_share_household"] = round(float((df.requests / df.units).mean()), 4)
    base["share_unit_weighted"] = round(float(df.requests.sum() / df.units.sum()), 4)
    base["mean_units_by_type"] = {("戸建て" if k else "集合住宅"): round(float(v), 3) for k, v in df.groupby("house").units.mean().items()}
    base["share_by_type"] = {("戸建て" if k else "集合住宅"): round(float(g.requests.sum() / g.units.sum()), 4) for k, g in df.groupby("house")}

    # 1) 町を作り直して100回（基本の置き方）
    reps = pd.DataFrame([estimates(town(np.random.default_rng(SEED * 1000 + r), **BASE)) for r in range(100)])
    rep_sum = {c: [round(float(reps[c].min()), 4), round(float(reps[c].mean()), 4), round(float(reps[c].max()), 4)]
               for c in ["ratio_separate", "ratio_weighted", "ratio_by_type"]}

    # 2) 関係の置き方を変える（相関5×区分の違い3×割合の散らばり3＝45通り）
    rows = []
    for rho in [-0.5, -0.25, 0.0, 0.25, 0.5]:
        for gap in [0.0, 1.0, 2.0]:
            for sp in [0.3, 0.6, 0.9]:
                e = estimates(town(np.random.default_rng(SEED * 10 + int((rho + 1) * 100) * 100 + int(gap * 10) + int(sp * 10)), rho, gap, sp))
                rows.append({"rho": rho, "gap": gap, "sig_p": sp, **{k: round(v, 4) for k, v in e.items() if k != "true"},
                             "true": e["true"]})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid_45.csv", index=False)
    g0 = grid[grid.rho == 0]
    sep_err = (grid.ratio_separate - 1).abs(); seg_err = (grid.ratio_by_type - 1).abs()
    grid_sum = {"separate_range": [float(grid.ratio_separate.min()), float(grid.ratio_separate.max())],
                "by_type_range": [float(grid.ratio_by_type.min()), float(grid.ratio_by_type.max())],
                "weighted_range": [float(grid.ratio_weighted.min()), float(grid.ratio_weighted.max())],
                "formula_max_absdiff": round(float((grid.ratio_separate - grid.ratio_formula).abs().max()), 6),
                "rho0_separate_range": [float(g0.ratio_separate.min()), float(g0.ratio_separate.max())],
                "by_type_smaller_count": int((seg_err < sep_err).sum()),
                "by_type_shrink_median_pct": round(float(np.median((1 - seg_err / sep_err)[sep_err > 0.005])) * 100, 1),
                "n": int(len(grid))}

    # 3) 後半：見込みの誤差どうしの相関と、独立と置いた90%の幅
    w_rows = []
    for r in [-0.3, 0.0, 0.3, 0.5, 0.8]:
        c = np.full((3, 3), r); np.fill_diagonal(c, 1)
        e = rng.multivariate_normal(np.zeros(3), c * SIG_F ** 2, 200000).sum(1)
        half = Z90 * SIG_F * np.sqrt(3)
        need = float(np.quantile(np.abs(e), .9))
        w_rows.append({"error_corr": r, "independent_90_times": round(float(np.exp(half)), 3),
                       "coverage_pct": round(float((np.abs(e) <= half).mean()) * 100, 2),
                       "coverage_formula_pct": round(float(_cov_formula(half / (SIG_F * np.sqrt(3 + 6 * r)))) * 100, 2),
                       "needed_90_times": round(float(np.exp(need)), 3),
                       "needed_formula_times": round(float(np.exp(Z90 * SIG_F * np.sqrt(3 + 6 * r))), 3)})
    width = pd.DataFrame(w_rows)
    width.to_csv(RES / "width_by_error_corr.csv", index=False)

    out = {"base": base, "reps100_min_mean_max": rep_sum, "grid45": grid_sum, "width": width.to_dict("records"),
           "settings": {"households": N_HH, "share_house": SHARE_HOUSE, **BASE, "units_mu": UNITS_MU, "p_mu": P_MU,
                        "sig_units": SIG_N, "sig_factor_error": SIG_F, "factor_error_times_1sd": round(float(np.exp(SIG_F)), 3)}}
    json.dump(out, open(RES / "a1049_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：基本の町での3つの概算
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    names = ["① 別々に（世帯ごとの平均どうし）", "② 台数で重みを付けた割合", "③ 区分ごとに①を作って足す"]
    vals = [base["separate"], base["weighted"], base["by_type"]]
    ax.barh(names, vals, color=[ORANGE, BLUE, LIGHT])
    ax.axvline(base["true"], color=INK, lw=1, ls="--")
    ax.text(base["true"], -0.68, f"本当の件数 {base['true']:,}件", ha="center", fontsize=9)
    for i, v in enumerate(vals):
        ax.text(max(v, base["true"]) + 40, i, f"{v:,.0f}件（{v / base['true']:.3f}倍）", va="center", fontsize=9)
    ax.invert_yaxis(); ax.set_xlim(0, max(vals) * 1.35); ax.set_ylim(2.5, -0.85)
    ax.set_xlabel("1年に頼まれるエアコンの掃除の件数（台）")
    ax.set_title("台数の多い世帯ほど頼みやすいと、別々に掛けた概算は少なく出る")
    save(fig, "a1049_three_ways.png", SRC, y=-0.04)

    # 図2：相関と①のずれ（区分の違い・散らばりごと）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for gap, c in [(0.0, GRAY), (1.0, BLUE), (2.0, ORANGE)]:
        d = grid[(grid.gap == gap) & (grid.sig_p == 0.6)]
        ax.plot(d.rho, d.ratio_separate, marker="o", color=c, lw=2, label=f"① 区分の違い {['なし', '基本', '基本の2倍'][int(gap)]}")
        d3 = grid[(grid.gap == gap) & (grid.sig_p == 0.6)]
        ax.plot(d3.rho, d3.ratio_by_type, marker="s", color=c, lw=1, ls="--", alpha=.8)
    ax.plot([], [], color=INK, ls="--", marker="s", lw=1, label="③ 区分ごと（破線）")
    ax.axhline(1, color=INK, lw=.8)
    ax.set_xlabel("世帯の中での、台数と頼みやすさの相関（置いた値）")
    ax.set_ylabel("概算÷本当の件数（倍）"); ax.set_ylim(0.6, 1.25)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("関係の向きでずれの向きが決まる（破線は区分ごとの③、割合の散らばり0.6）")
    save(fig, "a1049_by_rho.png", SRC, y=-0.04)

    # 図3：見込みの誤差の相関と、独立と置いた90%の幅の当たり
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    lab = [f"{r:g}" for r in width.error_corr]
    ax.bar(lab, width.coverage_pct, color=[LIGHT, GRAY, BLUE, BLUE, ORANGE])
    for i, v in enumerate(width.coverage_pct):
        ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9)
    ax.axhline(90, color=INK, lw=.8, ls="--"); ax.text(4.45, 91, "90%", fontsize=9, ha="right")
    ax.set_ylim(0, 105); ax.set_xlabel("3つの要素の見込みの誤差どうしの相関")
    ax.set_ylabel("本当の値が幅に入った割合（%）")
    ax.set_title(f"誤差が同じ向きにそろうと、独立と置いた90%の幅（×÷{width.independent_90_times[0]:.2f}倍）は狭すぎる")
    save(fig, "a1049_width.png", SRC, y=-0.04)
    print(json.dumps({k: out[k] for k in ["base", "reps100_min_mean_max", "grid45"]}, ensure_ascii=False, indent=1))
    print(width.to_string())


def _cov_formula(z):
    from math import erf, sqrt
    return erf(z / sqrt(2))


if __name__ == "__main__":
    main()
