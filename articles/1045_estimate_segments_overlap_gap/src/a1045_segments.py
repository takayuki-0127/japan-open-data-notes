"""1045 区分に分けて足し合わせると、重なりと抜けで合計はどれだけずれるのか？（架空のデータ）

架空のA町（10,000世帯）で、架空の「まとめ買いの定期便」を使う世帯の数を概算する。
「車を持たない世帯」「在宅で働く人がいる世帯」などの区分ごとに、区分の世帯数×区分の中で使う割合を出して足す。
区分は重なる（1つの世帯が2つ以上の区分に入る）し、どの区分にも入らない世帯もある。
正しい答え（使う世帯の数）は作成者が置く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1045
SRC = "架空のA町の定期便（作成者が乱数で作成、seed 1045）"
N_HH = 10_000
SEGS = ["車を持たない", "在宅で働く人がいる", "集合住宅の3階以上", "近くにスーパーがない", "ペットがいる", "週末にまとめて料理する"]
PREV = np.array([0.30, 0.25, 0.35, 0.20, 0.20, 0.15])
LIFT = np.array([0.15, 0.12, 0.08, 0.15, 0.06, 0.10])   # その区分に入ると使う確率がこれだけ上乗せ（掛け算の形で重ねる）
BASE = {"n_seg": 4, "rho": 0.3, "p0": 0.04}
N_SURVEY = 200          # 区分ごとに聞く世帯の数（区分の中の使う割合を調べる）
N_TOWN = 200
N_TOWN_GRID = 60


def r(x, k=4):
    return round(float(x), k)


def norm_ppf(p):
    """正規分布の分位点（scipy を使わずに、二分法で求める）"""
    from math import erf, sqrt
    lo, hi = -10.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 0.5 * (1 + erf(mid / sqrt(2))) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


THR = np.array([norm_ppf(1 - p) for p in PREV])


def make_town(rng, n_seg, rho, p0):
    k = len(SEGS)
    cov = np.full((k, k), rho) + np.eye(k) * (1 - rho)
    z = rng.multivariate_normal(np.zeros(k), cov, N_HH, method="cholesky")
    f = z > THR
    p_use = 1 - (1 - p0) * np.prod(np.where(f, 1 - LIFT, 1.0), axis=1)
    use = rng.random(N_HH) < p_use
    return f[:, :n_seg], use


def estimate(rng, f, use):
    """区分ごとの概算と、その内訳"""
    T = use.sum()
    k_h = f.sum(1)
    size = f.sum(0)
    true_rate = np.array([use[f[:, j]].mean() for j in range(f.shape[1])])
    # 区分の中で N_SURVEY 世帯に聞いて使う割合を出す
    survey_rate = np.array([use[rng.choice(np.flatnonzero(f[:, j]), N_SURVEY, replace=False)].mean()
                            for j in range(f.shape[1])])
    a_exact = (size * true_rate).sum()                 # 割合が正しく分かっていても
    a_survey = (size * survey_rate).sum()               # 割合を聞き取りで出す
    none = k_h == 0
    rate_none = use[rng.choice(np.flatnonzero(none), N_SURVEY, replace=False)].mean() if none.sum() >= N_SURVEY else use[none].mean()
    b_survey = a_survey + none.sum() * rate_none        # 「どこにも入らない」区分を足す
    # 優先順で1つの区分だけに入れる（左の区分を優先）＋どこにも入らない区分
    first = np.where(none, -1, np.argmax(f, axis=1))
    c = 0.0
    for j in range(-1, f.shape[1]):
        idx = np.flatnonzero(first == j)
        c += len(idx) * use[rng.choice(idx, min(N_SURVEY, len(idx)), replace=False)].mean()
    over = (np.maximum(k_h - 1, 0) * use).sum()
    gap = (none & use).sum()
    return {"T": int(T), "A_exact": a_exact / T, "A_survey": a_survey / T, "B_survey": b_survey / T, "C_survey": c / T,
            "overlap": over / T, "gap": gap / T, "size_sum_over_N": size.sum() / N_HH,
            "none_share": none.mean(), "multi_share": (k_h >= 2).mean(), "users_mean_k": k_h[use].mean(),
            "all_mean_k": k_h.mean()}


def run(seed, n_town, n_seg, rho, p0):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_town):
        f, use = make_town(rng, n_seg, rho, p0)
        rows.append(estimate(rng, f, use))
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    f, use = make_town(rng, len(SEGS), BASE["rho"], BASE["p0"])
    hh = pd.DataFrame(f.astype(int), columns=[f"seg{j+1}" for j in range(len(SEGS))])
    hh.insert(0, "household_id", np.arange(1, N_HH + 1)); hh["use"] = use.astype(int)
    hh.to_csv(DATA / "households_town1.csv", index=False)

    base = run(SEED * 10, N_TOWN, **BASE)
    base.round(5).to_csv(DATA / "towns_base.csv", index_label="town")
    m = base.mean()

    # 区分の数を変えると（ほかは基本）
    by_n = []
    for n in range(1, len(SEGS) + 1):
        d = run(SEED * 20 + n, N_TOWN_GRID, n, BASE["rho"], BASE["p0"]).mean()
        by_n.append({"n_seg": n, "A_exact": r(d.A_exact), "overlap_pct": r(d.overlap * 100, 2), "gap_pct": r(d.gap * 100, 2),
                     "size_sum_over_N": r(d.size_sum_over_N), "users_mean_k": r(d.users_mean_k)})
    by_n = pd.DataFrame(by_n)
    by_n.to_csv(RES / "by_n_segments.csv", index=False)

    # 27通り
    rows = []
    gi = 0
    for n in [2, 4, 6]:
        for rho in [0.0, 0.3, 0.6]:
            for p0 in [0.02, 0.04, 0.08]:
                d = run(SEED * 100 + gi, N_TOWN_GRID, n, rho, p0)
                mm = d.mean()
                rows.append({"n_seg": n, "rho": rho, "p0": p0, "A_exact": r(mm.A_exact), "A_survey": r(mm.A_survey),
                             "A_survey_p10": r(d.A_survey.quantile(.1)), "A_survey_p90": r(d.A_survey.quantile(.9)),
                             "B_survey": r(mm.B_survey), "C_survey": r(mm.C_survey),
                             "C_survey_p10": r(d.C_survey.quantile(.1)), "C_survey_p90": r(d.C_survey.quantile(.9)),
                             "overlap_pct": r(mm.overlap * 100, 2), "gap_pct": r(mm.gap * 100, 2),
                             "size_sum_over_N": r(mm.size_sum_over_N), "users_mean_k": r(mm.users_mean_k)})
                gi += 1
    g = pd.DataFrame(rows)
    g.to_csv(RES / "grid.csv", index=False)
    g["A_off"] = (g.A_exact - 1).abs()
    cancel = g[(g.A_off < 0.1) & (g.overlap_pct > 15) & (g.gap_pct > 15)]

    methods = pd.DataFrame([
        {"method": "①区分ごとに足す（割合は正しく分かっている）", "mean": r(m.A_exact, 2),
         "p10": r(base.A_exact.quantile(.1), 2), "p90": r(base.A_exact.quantile(.9), 2)},
        {"method": "②区分ごとに足す（割合は200世帯に聞いて出す）", "mean": r(m.A_survey, 2),
         "p10": r(base.A_survey.quantile(.1), 2), "p90": r(base.A_survey.quantile(.9), 2)},
        {"method": "③②に「どこにも入らない」区分を足す", "mean": r(m.B_survey, 2),
         "p10": r(base.B_survey.quantile(.1), 2), "p90": r(base.B_survey.quantile(.9), 2)},
        {"method": "④重ならないように1つの区分にだけ入れる＋どこにも入らない区分", "mean": r(m.C_survey, 2),
         "p10": r(base.C_survey.quantile(.1), 2), "p90": r(base.C_survey.quantile(.9), 2)}])
    methods.to_csv(RES / "methods.csv", index=False)

    pct = lambda x: r(x * 100, 2)
    out = {
        "headline": {
            "true_users_mean": r(base["T"].mean(), 1), "true_users_share_pct": pct(base["T"].mean() / N_HH),
            "A_exact_mean": r(m.A_exact, 2), "A_survey_mean": r(m.A_survey, 2),
            "A_survey_p10": r(base.A_survey.quantile(.1), 2), "A_survey_p90": r(base.A_survey.quantile(.9), 2),
            "overlap_pct": pct(m.overlap), "gap_pct": pct(m.gap),
            "formula_A_exact": r(1 + m.overlap - m.gap, 4), "A_exact_mean_4": r(m.A_exact, 4),
            "users_mean_k": r(m.users_mean_k, 2), "none_share_pct": pct(m.none_share), "multi_share_pct": pct(m.multi_share),
            "size_sum_over_N": r(m.size_sum_over_N, 2),
            "B_survey_mean": r(m.B_survey, 2), "C_survey_mean": r(m.C_survey, 2),
            "C_survey_p10": r(base.C_survey.quantile(.1), 2), "C_survey_p90": r(base.C_survey.quantile(.9), 2),
            "fig_once_1dp": r(100 - m.gap * 100, 1), "fig_overlap_1dp": r(m.overlap * 100, 1), "fig_gap_1dp": r(m.gap * 100, 1),
            "grid_A_min": r(g.A_exact.min(), 2), "grid_A_max": r(g.A_exact.max(), 2),
            "grid_overlap_min_pct": r(g.overlap_pct.min(), 2), "grid_overlap_max_pct": r(g.overlap_pct.max(), 2),
            "grid_gap_min_pct": r(g.gap_pct.min(), 2), "grid_gap_max_pct": r(g.gap_pct.max(), 2),
            "grid_C_min": r(g.C_survey.min(), 2), "grid_C_max": r(g.C_survey.max(), 2),
            "grid_B_min": r(g.B_survey.min(), 2), "grid_B_max": r(g.B_survey.max(), 2),
            "grid_cancel_n": int(len(cancel)), "grid_within10_n": int((g.A_off < 0.1).sum()),
            "A_minus_1": r(m.A_exact - 1, 2),
            "grid_size_sum_min": r(g.size_sum_over_N.min(), 2), "grid_size_sum_max": r(g.size_sum_over_N.max(), 2),
            "grid_A_over_size_sum_corr": r(np.corrcoef(g.A_exact, g.size_sum_over_N)[0, 1], 3),
            "grid_users_k_minus_size_sum_min": r((g.users_mean_k - g.size_sum_over_N).min(), 2),
            "grid_users_k_minus_size_sum_max": r((g.users_mean_k - g.size_sum_over_N).max(), 2),
        },
        "cancel_cases": cancel.drop(columns="A_off").to_dict("records"),
        "methods": methods.to_dict("records"),
        "by_n_segments": by_n.to_dict("records"),
        "constants": {"households": N_HH, "segments": SEGS, "prevalence": PREV.tolist(), "lift": LIFT.tolist(),
                      **BASE, "n_survey": N_SURVEY, "n_town": N_TOWN, "n_town_grid": N_TOWN_GRID},
        "grid_n": int(len(g)),
    }
    json.dump(out, open(RES / "a1045_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：内訳（基本、200町の平均、正しい件数を100とする）
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    once, ov, gp = 100 - m.gap * 100, m.overlap * 100, m.gap * 100
    ax.barh(1, once, color=BLUE, height=0.5)
    ax.barh(1, gp, left=once, color="white", edgecolor=GRAY, hatch="//", height=0.5)
    ax.text(once / 2, 1, f"どれかの区分に入る {once:.1f}", ha="center", va="center", color="white", fontsize=9)
    ax.text(once + gp + 2, 1, f"どの区分にも入らない（抜け）{gp:.1f}", ha="left", va="center", color=INK, fontsize=8.5)
    ax.barh(0, once, color=BLUE, height=0.5)
    ax.barh(0, ov, left=once, color=ORANGE, height=0.5)
    ax.text(once / 2, 0, f"1回目に数えた分 {once:.1f}", ha="center", va="center", color="white", fontsize=9)
    ax.text(once + ov / 2, 0, f"重なりで2回目以降に数えた分 +{ov:.1f}", ha="center", va="center", color="white", fontsize=8.5)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["4つの区分の合計", "正しい件数（使う世帯）"]); ax.set_xlim(0, 200)
    ax.set_xlabel("正しい件数を100としたときの大きさ（200町の平均）")
    ax.set_title(f"区分の合計は正しい件数の{m.A_exact:.2f}倍：重なりで足しすぎ、抜けで足りない")
    save(fig, "a1045_breakdown.png", SRC, y=-0.07)

    # 図2：やり方ごと
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    lab = ["①区分ごとに足す\n（割合は正しい）", "②区分ごとに足す\n（割合は聞き取り）", "③②＋どこにも\n入らない区分", "④1つの区分にだけ\n入れる＋その他"]
    mv = methods["mean"].values
    y = np.arange(4)[::-1]
    ax.barh(y, mv, color=[ORANGE, ORANGE, LIGHT, BLUE], height=0.55)
    ax.errorbar(mv, y, xerr=[mv - methods.p10.values, methods.p90.values - mv], fmt="none", ecolor=INK, lw=1, capsize=3)
    for yi, v in zip(y, mv):
        ax.text(0.03, yi, f"{v:.2f}倍", va="center", color="white", fontsize=9)
    ax.axvline(1, color=INK, lw=1, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9); ax.set_xlim(0, 2.3)
    ax.set_xlabel("概算 ÷ 正しい件数（棒は200町の平均、線は10〜90%の範囲）")
    ax.set_title("重ならないように区分を切ると、合計は正しい件数に戻る")
    save(fig, "a1045_methods.png", SRC, y=-0.05)

    # 図3：27通りの重なりと抜け
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    mk = {2: "o", 4: "s", 6: "^"}
    for n in [2, 4, 6]:
        q = g[g.n_seg == n]
        sc = ax.scatter(q.overlap_pct, q.gap_pct, c=q.A_exact, cmap="coolwarm", norm=TwoSlopeNorm(vcenter=1.0, vmin=0.5, vmax=3.2), marker=mk[n], s=55,
                        edgecolor=INK, lw=0.4, label=f"区分{n}つ")
    xl, yl = g.overlap_pct.max() * 1.08, 50
    ax.plot([0, yl], [0, yl], color=GRAY, lw=1, ls="--")
    ax.text(yl * 1.02, yl * 0.93, "この線の上では\n合計がちょうど合う", color=GRAY, fontsize=8.5)
    ax.set_xlim(0, xl); ax.set_ylim(0, yl)
    ax.set_xlabel("重なりで2回目以降に数えた分（正しい件数に対する%）")
    ax.set_ylabel("どの区分にも入らず抜けた分（%）")
    cb = fig.colorbar(sc, ax=ax); cb.set_label("区分の合計 ÷ 正しい件数")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_aspect("auto")
    ax.set_title("27通り：合計が合って見えても、重なりと抜けが打ち消し合っていることがある", fontsize=11)
    save(fig, "a1045_grid.png", SRC)
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(by_n); print(methods)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
