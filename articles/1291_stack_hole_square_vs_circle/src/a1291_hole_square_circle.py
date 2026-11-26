"""1291 穴の位置のずれを縦と横の許容差で四角に決めると、中心からの距離で丸く決めたときと比べて、合格と外れはどれだけ入れかわるのか？（架空のデータ）

架空の棚板にあけるねじの穴。穴の中心の、狙った位置からのずれ（横 x・縦 y、mm）。
  四角の決まり：|x|≦0.1 かつ |y|≦0.1（縦と横の許容差 ±0.1mm）
  丸の決まり  ：中心からの距離 √(x²+y²)≦r。r は3つ
      四角の中に収まる丸（r=0.1）、四角と同じ面積の丸（r=0.2/√π）、四角の角を通る丸（r=0.1×√2）
ずれの置き方：基本は x・y とも平均0・同じ標準偏差 σ でたがいに関係なし。
確かめ：縦と横で標準偏差が違う（1:2）、横に0.03mm片寄る、斜めに片寄る（x・y とも0.02mm）、x と y が一緒に動く（関係の強さ0.5）。
穴は100万個ずつ乱数で作る。基本の置き方の合格の割合は式でも出す。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1291
SRC = "架空の棚板の穴の位置（作成者が乱数で作成、seed 1291）"
A = 0.1
CIRCLES = {"inner": A, "same_area": 2 * A / math.sqrt(math.pi), "corner": A * math.sqrt(2)}
CIRCLE_JA = {"inner": "四角の中に収まる丸", "same_area": "四角と同じ面積の丸", "corner": "四角の角を通る丸"}
SIGMAS = [0.03, 0.04, 0.05, 0.06, 0.07]
BASE_SIGMA = 0.05
PATTERNS = ["base", "unequal", "shift_x", "shift_diag", "corr"]
PATTERN_JA = {"base": "基本（縦横同じ・片寄りなし）", "unequal": "縦と横の標準偏差が1:2", "shift_x": "横に0.03mm片寄る",
              "shift_diag": "斜めに片寄る（縦横0.02mm）", "corr": "縦と横が一緒に動く（0.5）"}
N = 1_000_000


def Phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def holes(rng, pattern, s, n=N):
    if pattern == "unequal":            # 2つの分散の和を基本とそろえる
        sx, sy = s * math.sqrt(2 / 5), s * math.sqrt(8 / 5)
        return rng.normal(0, sx, n), rng.normal(0, sy, n)
    x = rng.normal(0, s, n); y = rng.normal(0, s, n)
    if pattern == "shift_x":
        x = x + 0.03
    elif pattern == "shift_diag":
        x = x + 0.02; y = y + 0.02
    elif pattern == "corr":
        rho = 0.5
        y = rho * x + math.sqrt(1 - rho * rho) * y
    return x, y


def classify(x, y, rad):
    sq = (np.abs(x) <= A) & (np.abs(y) <= A)
    ci = (x * x + y * y) <= rad * rad
    return sq, ci


def r(v, k=2):
    return float(round(v, k))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    for pattern in PATTERNS:
        sig_list = SIGMAS if pattern == "base" else [BASE_SIGMA]
        for s in sig_list:
            x, y = holes(rng, pattern, s)
            for ck, rad in CIRCLES.items():
                sq, ci = classify(x, y, rad)
                row = dict(pattern=PATTERN_JA[pattern], sigma_mm=s, circle=CIRCLE_JA[ck], radius_mm=r(rad, 4),
                           square_pass_pct=r(sq.mean() * 100), circle_pass_pct=r(ci.mean() * 100),
                           square_only_pct=r((sq & ~ci).mean() * 100), circle_only_pct=r((~sq & ci).mean() * 100),
                           swap_pct=r((sq != ci).mean() * 100))
                fail_sq = (~sq).sum(); fail_ci = (~ci).sum()
                row["swap_share_of_square_fail_pct"] = r((~sq & ci).sum() / fail_sq * 100) if fail_sq else None
                row["swap_share_of_circle_fail_pct"] = r((sq & ~ci).sum() / fail_ci * 100) if fail_ci else None
                if pattern == "base":
                    row["square_pass_pct_formula"] = r((2 * Phi(A / s) - 1) ** 2 * 100)
                    row["circle_pass_pct_formula"] = r((1 - math.exp(-rad * rad / (2 * s * s))) * 100)
                rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "cases.csv", index=False)

    # data：基本 σ=0.05mm の穴5,000個
    rng_d = np.random.default_rng(SEED + 1)
    x, y = holes(rng_d, "base", BASE_SIGMA, 5000)
    dist = np.sqrt(x * x + y * y)
    pd.DataFrame(dict(hole_id=np.arange(1, 5001), dx_mm=x.round(4), dy_mm=y.round(4), dist_mm=dist.round(4),
                      square_pass=((np.abs(x) <= A) & (np.abs(y) <= A)).astype(int),
                      same_area_circle_pass=(dist <= CIRCLES["same_area"]).astype(int),
                      corner_circle_pass=(dist <= CIRCLES["corner"]).astype(int))).to_csv(DATA / "holes_base_005.csv", index=False)

    sqd = (np.abs(x) <= A) & (np.abs(y) <= A)
    scatter_counts = {CIRCLE_JA[k]: dict(square_only=int((sqd & (dist > CIRCLES[k])).sum()),
                                         circle_only=int((~sqd & (dist <= CIRCLES[k])).sum())) for k in ["same_area", "corner"]}
    base = tab[tab.pattern == PATTERN_JA["base"]]
    b5 = base[base.sigma_mm == BASE_SIGMA]
    rob = tab[tab.sigma_mm == BASE_SIGMA]
    main_json = dict(
        setting=dict(square_tol_mm=A, radii_mm={CIRCLE_JA[k]: r(v, 4) for k, v in CIRCLES.items()}, n_holes=N,
                     base_sigma_mm=BASE_SIGMA, sigmas_mm=SIGMAS),
        base_sigma005=b5.to_dict(orient="records"),
        base_swap_range_by_circle={c: [float(base[base.circle == c].swap_pct.min()), float(base[base.circle == c].swap_pct.max())]
                                   for c in CIRCLE_JA.values()},
        robust_sigma005=rob.to_dict(orient="records"),
        robust_swap_range_by_circle={c: [float(rob[rob.circle == c].swap_pct.min()), float(rob[rob.circle == c].swap_pct.max())]
                                     for c in CIRCLE_JA.values()},
        scatter_5000_counts=scatter_counts,
        max_abs_diff_formula_sim_pct=r(max((base.square_pass_pct - base.square_pass_pct_formula).abs().max(),
                                           (base.circle_pass_pct - base.circle_pass_pct_formula).abs().max())),
    )
    with open(RES / "a1291_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：穴5,000個と四角・丸
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 5.0))
    for ax, ck in zip(axes, ["same_area", "corner"]):
        rad = CIRCLES[ck]
        sq = (np.abs(x) <= A) & (np.abs(y) <= A); ci = dist <= rad
        ax.scatter(x[sq & ci], y[sq & ci], s=3, color=LIGHT, label="どちらでも合格")
        ax.scatter(x[~sq & ~ci], y[~sq & ~ci], s=3, color=GRAY, label="どちらでも外れ")
        ax.scatter(x[sq & ~ci], y[sq & ~ci], s=9, color=ORANGE, label=f"四角だけ合格（{(sq & ~ci).sum()}個）")
        ax.scatter(x[~sq & ci], y[~sq & ci], s=9, color=GREEN, label=f"丸だけ合格（{(~sq & ci).sum()}個）")
        ax.add_patch(Rectangle((-A, -A), 2 * A, 2 * A, fill=False, color=INK, lw=1.2))
        ax.add_patch(Circle((0, 0), rad, fill=False, color=BLUE, lw=1.4, ls="--"))
        ax.set_xlim(-0.22, 0.22); ax.set_ylim(-0.22, 0.22); ax.set_aspect("equal")
        ax.set_xlabel("横のずれ（mm）"); ax.set_ylabel("縦のずれ（mm）")
        ax.set_title(f"{CIRCLE_JA[ck]}（半径{rad:.4f}mm）", fontsize=11)
        ax.legend(frameon=False, fontsize=8, loc="upper left", markerscale=2)
    fig.suptitle("穴5,000個（ずれの標準偏差0.05mm）：実線は四角、点線は丸", fontsize=12)
    save(fig, "a1291_scatter.png", SRC, y=0.0)

    # 図2：σごとの入れかわり（基本）
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    w = 0.26
    cols = [ORANGE, BLUE, GREEN]
    for j, c in enumerate(CIRCLE_JA.values()):
        sub = base[base.circle == c]
        xs = np.arange(len(SIGMAS)) + (j - 1) * w
        ax.bar(xs, sub.swap_pct.values, width=w, color=cols[j], label=c)
        for xx, v in zip(xs, sub.swap_pct.values):
            ax.text(xx, v + 0.15, f"{v}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(np.arange(len(SIGMAS))); ax.set_xticklabels([f"{s}mm" for s in SIGMAS])
    ax.set_xlabel("ずれの標準偏差（縦・横とも）"); ax.set_ylabel("合格と外れが入れかわる穴（%）")
    ax.set_ylim(0, base.swap_pct.max() * 1.18)
    ax.set_title("四角で決めたときと丸で決めたときで、判定が入れかわる穴")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1291_swap_by_sigma.png", SRC)

    # 図3：確かめ（σ=0.05mm、ずれの置き方5つ）
    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    pats = [PATTERN_JA[p] for p in PATTERNS]
    for j, c in enumerate(CIRCLE_JA.values()):
        sub = rob[rob.circle == c].set_index("pattern").loc[pats]
        xs = np.arange(len(pats)) + (j - 1) * w
        ax.bar(xs, sub.swap_pct.values, width=w, color=cols[j], label=c)
        for xx, v in zip(xs, sub.swap_pct.values):
            ax.text(xx, v + 0.15, f"{v}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(np.arange(len(pats))); ax.set_xticklabels([p.replace("（", "\n（") for p in pats], fontsize=8.5)
    ax.set_ylabel("合格と外れが入れかわる穴（%）")
    ax.set_ylim(0, rob.swap_pct.max() * 1.2)
    ax.set_title("ずれの置き方を変えると（標準偏差0.05mm）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1291_robust.png", SRC, y=-0.06)

    print(tab.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
