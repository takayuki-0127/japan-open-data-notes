"""974 欠けている割合が何%を超えると、結果は読めなくなるのか？（架空のデータ）

架空の会社の利用者アンケート（満足／不満の2択）。本当の満足の割合を作成者が置き、答えなかった人の割合（欠けの割合）と、
不満な人が満足な人の何倍答えにくいか（答えにくさの比）を変えて、答えた人だけで出した満足の割合がどれだけずれるかを数える。
「読める」は作成者が置いた物差し：調査を作り直した回の95%で、ずれが±5ポイント以内。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 974
SRC = "架空の会社の利用者アンケート（作成者が乱数で作成、seed 974）"
P_TRUE = 0.60                    # 本当の満足の割合
KS = [1.0, 1.25, 1.5, 2.0, 3.0]  # 不満な人の答えない確率 ÷ 満足な人の答えない確率
NS = [200, 500, 1000, 3000]      # 聞いた人数
MS = np.round(np.arange(0, 0.601, 0.01), 2)   # 欠けの割合（答えなかった人の割合）
REPS = 20000
TOL = 0.05                       # 読める：95%の回で、ずれが±5ポイント以内
KLAB = {1.0: "1倍（でたらめに欠ける）", 1.25: "1.25倍", 1.5: "1.5倍", 2.0: "2倍", 3.0: "3倍"}


def rates(m, k, p):
    """欠けの割合が m、答えにくさの比が k のときの、満足な人・不満な人の答えない確率"""
    r1 = m / (p + (1 - p) * k)
    return r1, min(k * r1, 1.0)


def bias_formula(m, k, p):
    r1, r0 = rates(m, k, p)
    if m >= 1:
        return np.nan
    return p * (1 - r1) / (p * (1 - r1) + (1 - p) * (1 - r0)) - p


def simulate(rng, n, m, k, p, reps=REPS):
    r1, r0 = rates(m, k, p)
    sat = rng.binomial(n, p, reps)
    a1 = rng.binomial(sat, 1 - r1)
    a0 = rng.binomial(n - sat, 1 - r0)
    tot = a1 + a0
    est = np.where(tot > 0, a1 / np.maximum(tot, 1), np.nan)
    return est - p, tot


def threshold(errs_by_m, tol):
    """0%から順に見て、初めて「95%の回で±tol以内」を満たさなくなる1つ前の欠けの割合（満たさない場合は −1）"""
    last = -1.0
    for m, e in errs_by_m:
        if np.nanquantile(np.abs(e), 0.95) <= tol + 1e-12:
            last = m
        else:
            break
    return last


def main():
    rng = np.random.default_rng(SEED)
    rows, thr = [], []
    for p in [P_TRUE, 0.80]:
        for n in NS:
            for k in KS:
                eb = []
                for m in MS:
                    if rates(m, k, p)[1] >= 1.0:
                        continue
                    e, tot = simulate(rng, n, m, k, p)
                    eb.append((m, e))
                    rows.append({"本当の満足の割合": p, "聞いた人数": n, "答えにくさの比": k, "欠けの割合": m,
                                 "ずれの平均（ポイント）": round(float(np.nanmean(e)) * 100, 3),
                                 "ずれの式の値（ポイント）": round(bias_formula(m, k, p) * 100, 3),
                                 "ずれの絶対値の95%点（ポイント）": round(float(np.nanquantile(np.abs(e), .95)) * 100, 3),
                                 "±5ポイント以内の回の割合": round(float((np.abs(e) <= 0.05 + 1e-12).mean()), 4),
                                 "答えた人数の平均": round(float(tot.mean()), 1)})
                thr.append({"本当の満足の割合": p, "聞いた人数": n, "答えにくさの比": k,
                            "読める欠けの割合の上限（±5ポイント）": threshold(eb, 0.05),
                            "読める欠けの割合の上限（±3ポイント）": threshold(eb, 0.03),
                            "でたらめに欠けるときの式の上限（±5ポイント）":
                                (lambda v: round(v, 3) if v >= 0 else -1.0)(1 - (1.96 / 0.05) ** 2 * p * (1 - p) / n) if k == 1.0 else None})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "error_grid.csv", index=False)
    thr = pd.DataFrame(thr)
    thr.to_csv(RES / "readable_limit.csv", index=False)

    # 2) 2年の比べ：本当の満足の割合は2年とも60%。1年目の欠け10%、2年目の欠けを変える（各1,000人）
    two = []
    for k in KS:
        for m2 in [0.10, 0.20, 0.30, 0.40, 0.50]:
            e1, _ = simulate(rng, 1000, 0.10, k, P_TRUE)
            e2, _ = simulate(rng, 1000, m2, k, P_TRUE)
            ch = (e2 - e1) * 100
            two.append({"答えにくさの比": k, "1年目の欠け": 0.10, "2年目の欠け": m2,
                        "見かけの変化の平均（ポイント）": round(float(ch.mean()), 3),
                        "式の値（ポイント）": round((bias_formula(m2, k, P_TRUE) - bias_formula(0.10, k, P_TRUE)) * 100, 3),
                        "見かけの変化が+5ポイント以上の回の割合": round(float((ch >= 5).mean()), 4),
                        "見かけの変化の絶対値が5ポイント以上の回の割合": round(float((np.abs(ch) >= 5).mean()), 4)})
    two = pd.DataFrame(two)
    two.to_csv(RES / "two_years.csv", index=False)

    # 3) 答えた人の満足が60%・欠け30%のとき、答えにくさの比ごとの本当の満足の割合（式から逆算）
    back = {}
    for k in KS:
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if mid + bias_formula(0.30, k, mid) < 0.60:
                lo = mid
            else:
                hi = mid
        back[KLAB[k]] = round(mid * 100, 2)

    # 例の1回分（1,000人、欠け30%、答えにくさ2倍）
    r1, r0 = rates(0.30, 2.0, P_TRUE)
    re = np.random.default_rng(SEED + 1)
    sat = re.random(1000) < P_TRUE
    ans = re.random(1000) >= np.where(sat, r1, r0)
    pd.DataFrame({"person_id": np.arange(1, 1001), "satisfied_true": sat.astype(int), "answered": ans.astype(int),
                  "answer": np.where(ans, np.where(sat, "満足", "不満"), "")}).to_csv(DATA / "survey_example.csv", index=False)
    ex = {"answered": int(ans.sum()), "true_share": round(float(sat.mean()) * 100, 2),
          "answered_share": round(float(sat[ans].mean()) * 100, 2)}

    g = grid[grid["本当の満足の割合"] == P_TRUE]
    b1000 = g[g["聞いた人数"] == 1000]
    pick = {}
    for k in KS:
        for m in [0.10, 0.30, 0.50]:
            r = b1000[(b1000["答えにくさの比"] == k) & (np.isclose(b1000["欠けの割合"], m))]
            if len(r):
                pick[f"{KLAB[k]}・欠け{int(round(m * 100))}%"] = {
                    "bias": float(r["ずれの平均（ポイント）"].iloc[0]),
                    "bias_formula": float(r["ずれの式の値（ポイント）"].iloc[0]),
                    "abs_err_p95": float(r["ずれの絶対値の95%点（ポイント）"].iloc[0]),
                    "share_within_5": float(r["±5ポイント以内の回の割合"].iloc[0])}
    th = thr[thr["本当の満足の割合"] == P_TRUE]
    out = {"setup": {"p_true": P_TRUE, "ks": KS, "ns": NS, "m_grid": "0〜60%（1%きざみ）", "reps": REPS,
                     "rule": "調査を作り直した回の95%で、ずれが±5ポイント以内なら読める（作成者が置いた物差し）"},
           "n1000_selected": pick,
           "max_abs_diff_sim_vs_formula_points": round(float((grid["ずれの平均（ポイント）"]
                                                              - grid["ずれの式の値（ポイント）"]).abs().max()), 3),
           "readable_limit_p60": th.drop(columns=["本当の満足の割合"]).to_dict("records"),
           "readable_limit_p80": thr[thr["本当の満足の割合"] == 0.8].drop(columns=["本当の満足の割合"]).to_dict("records"),
           "limit_range_k_gt1_n500plus": {
               str(pp): {"min": float(thr[(thr["本当の満足の割合"] == pp) & (thr["答えにくさの比"] > 1) & (thr["聞いた人数"] >= 500)]
                                     ["読める欠けの割合の上限（±5ポイント）"].min()),
                         "max": float(thr[(thr["本当の満足の割合"] == pp) & (thr["答えにくさの比"] > 1) & (thr["聞いた人数"] >= 500)]
                                     ["読める欠けの割合の上限（±5ポイント）"].max())} for pp in [P_TRUE, 0.8]},
           "two_years_n1000": two.to_dict("records"),
           "observed60_missing30_true_share_by_k": back,
           "example_survey": ex}
    json.dump(out, open(RES / "a974_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cols = {1.0: INK, 1.25: LIGHT, 1.5: BLUE, 2.0: ORANGE, 3.0: "#9b3d1a"}
    # 図1：1,000人のとき、欠けの割合とずれの95%点
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    for k in KS:
        d = b1000[b1000["答えにくさの比"] == k]
        ax.plot(d["欠けの割合"] * 100, d["ずれの絶対値の95%点（ポイント）"], color=cols[k], lw=1.8, label=f"不満な人の答えにくさ {KLAB[k]}")
    ax.axhline(5, color=GRAY, lw=1, ls="--"); ax.text(60, 5.3, "±5ポイント", color=GRAY, fontsize=9, ha="right")
    ax.set_xlabel("答えなかった人の割合（%）"); ax.set_ylabel("ずれの大きさの95%点（ポイント、20,000回）")
    ax.set_ylim(0, 20); ax.set_xlim(0, 60)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("同じ欠けの割合でも、答えにくさに差があるとずれは早く大きくなる（1,000人）", fontsize=11.5)
    save(fig, "a974_error_by_missing.png", SRC)

    # 図2：読める欠けの割合の上限（人数×答えにくさの比）
    mat = th.pivot(index="答えにくさの比", columns="聞いた人数", values="読める欠けの割合の上限（±5ポイント）")
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    v = mat.values * 100
    ax.imshow(np.where(v < 0, np.nan, v), cmap="Blues", vmin=0, vmax=70, aspect="auto")
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            t = "0%でも\n読めない" if v[i, j] < 0 else ("60%（調べた上限）\nでも読める" if v[i, j] >= 60 else f"{v[i, j]:.0f}%まで")
            ax.text(j, i, t, ha="center", va="center", fontsize=9, color=INK if (v[i, j] < 40) else "white")
    ax.set_xticks(range(len(mat.columns))); ax.set_xticklabels([f"{c:,}人" for c in mat.columns])
    ax.set_yticks(range(len(mat.index))); ax.set_yticklabels([KLAB[k] for k in mat.index])
    ax.set_xlabel("聞いた人数"); ax.set_ylabel("不満な人の答えにくさ")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("「95%の回でずれ±5ポイント以内」を保てる欠けの割合の上限（本当の満足60%）", fontsize=11)
    save(fig, "a974_readable_limit.png", SRC)

    # 図3：2年の比べ（本当は変わらない）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    for k in KS:
        d = two[two["答えにくさの比"] == k]
        ax.plot(d["2年目の欠け"] * 100, d["見かけの変化の平均（ポイント）"], "o-", color=cols[k], lw=1.6, label=KLAB[k])
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("2年目に答えなかった人の割合（%、1年目は10%）"); ax.set_ylabel("満足の割合の見かけの変化（ポイント）")
    ax.legend(frameon=False, fontsize=8.5, title="不満な人の答えにくさ", title_fontsize=8.5, loc="upper left")
    ax.set_title("本当は変わらないのに、答えない人が増えると満足が増えたように見える（各年1,000人）", fontsize=11)
    save(fig, "a974_two_years.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
