"""970 「答えなかった人」は、答えた人と同じなのか？（架空のデータ）

架空のサービスの利用者8,000人の全員に満足アンケートを送る。1回目の案内で答える人、
催促（2回目の案内）のあとに答える人、最後まで答えない人に分かれる。
利用年数（3区分）は台帳で全員分かる。満足しているかどうかは作成者が全員分置く（答えない人の分も）。
答えるかどうかの決まり方を2つ置く：
  A「答えにくさが続いている」：満足している人ほど答えやすく、人ごとの答えやすさは1回目と催促で同じ。
  B「答えない人は別の理由」：Aに加えて、利用者の30%は忙しくてほとんど答えない人で、満足している割合がほかの人より30ポイント高い。
答えなかった人の満足は、ふつうは見えない。ここでは作成者が置いたので数えられる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 970
SRC = "架空のサービスの利用者アンケート（作成者が乱数で作成、seed 970）"
N = 8000
REPS = 300
TENURE_SHARE = np.array([0.30, 0.40, 0.30])        # 1年未満・1〜3年・3年以上
SAT_BY_TENURE = np.array([0.50, 0.60, 0.70])        # 満足している割合
TENURE_LOGIT = np.array([-0.3, 0.0, 0.3])           # 利用年数が長いほど答えやすい
SAT_ODDS = 1.8                                      # 満足している人の答えやすさ（オッズの倍率）
U_SD = 1.0                                          # 人ごとの答えやすさの散らばり
R1, R_CUM = 0.25, 0.40                              # 1回目の回答率、催促後までの回答率（ねらい）
BUSY_SHARE, BUSY_SAT_DIFF, BUSY_SHIFT = 0.30, 0.30, -3.0
TENURE_LAB = ["1年未満", "1〜3年", "3年以上"]


def logistic(x):
    return 1 / (1 + np.exp(-x))


def make_people(rng, n, scen, busy_share=BUSY_SHARE, busy_diff=BUSY_SAT_DIFF):
    ten = rng.choice(3, size=n, p=TENURE_SHARE)
    busy = (rng.random(n) < busy_share) if scen == "B" else np.zeros(n, bool)
    # 忙しい人とほかの人の満足の割合の差を busy_diff に置き、全体の満足の割合はAと同じにそろえる
    p_sat = SAT_BY_TENURE[ten] + (np.where(busy, 1 - busy_share, -busy_share) * busy_diff if scen == "B" else 0.0)
    sat = rng.random(n) < np.clip(p_sat, 0.01, 0.99)
    u = rng.normal(0, U_SD, n) + np.where(busy, BUSY_SHIFT, 0.0)
    return ten, busy, sat, u


def score(ten, sat, u, odds):
    return TENURE_LOGIT[ten] + np.log(odds) * sat + u


def calib(scen, odds, r1, r_cum, **kw):
    """1回目の回答率 r1、催促後までの回答率 r_cum になる切片 a1・a2 を大きな標本で決める"""
    rng = np.random.default_rng(SEED * 7)
    ten, busy, sat, u = make_people(rng, 300000, scen, **kw)
    s = score(ten, sat, u, odds)

    def solve(f, target):
        lo, hi = -20.0, 20.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if f(mid) > target:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    a1 = solve(lambda a: logistic(a + s).mean(), r1)
    p1 = logistic(a1 + s)
    a2 = solve(lambda a: (p1 + (1 - p1) * logistic(a + s)).mean(), r_cum)
    return a1, a2


def survey(rng, scen, odds, a1, a2, n=N, **kw):
    ten, busy, sat, u = make_people(rng, n, scen, **kw)
    s = score(ten, sat, u, odds)
    w1 = rng.random(n) < logistic(a1 + s)
    w2 = (~w1) & (rng.random(n) < logistic(a2 + s))
    non = ~(w1 | w2)
    return ten, busy, sat, w1, w2, non


def estimates(ten, sat, w1, w2, non):
    resp = w1 | w2
    o = {"true": sat.mean(), "wave1": sat[w1].mean(), "wave2": sat[w2].mean(), "respondents": sat[resp].mean(),
         "nonrespondents": sat[non].mean(), "rate1": w1.mean(), "rate_cum": resp.mean()}
    # 利用年数で重み（台帳の区分の割合で、区分ごとの回答者の満足の割合を合わせる）
    share = np.bincount(ten, minlength=3) / len(ten)
    by = np.array([sat[resp & (ten == t)].mean() for t in range(3)])
    o["weighted_tenure"] = float((share * by).sum())
    # 答えなかった人を催促後の回答者と同じと置く
    o["late_as_non"] = (sat[w1].sum() + sat[w2].sum() + non.sum() * sat[w2].mean()) / len(sat)
    # 台帳から見える：回答者と全員の利用年数の構成の差（最大のポイント差）
    share_r = np.bincount(ten[resp], minlength=3) / resp.sum()
    o["tenure_gap_max_pt"] = float(np.abs(share_r - share).max() * 100)
    return o


def run(seed0, reps, scen, odds=SAT_ODDS, r1=R1, r_cum=R_CUM, **kw):
    a1, a2 = calib(scen, odds, r1, r_cum, **kw)
    rows = [estimates(*[x for i, x in enumerate(survey(np.random.default_rng(seed0 + r), scen, odds, a1, a2, **kw)) if i != 1])
            for r in range(reps)]
    d = pd.DataFrame(rows)
    for c in ["respondents", "weighted_tenure", "late_as_non", "wave1"]:
        d[c + "_err_pt"] = (d[c] - d["true"]) * 100
    d["non_minus_resp_pt"] = (d.nonrespondents - d.respondents) * 100
    d["non_minus_wave2_pt"] = (d.nonrespondents - d.wave2) * 100
    return d, a1, a2


def r4(x):
    return round(float(x), 4)


def main():
    t0 = time.time()
    res = {"setting": {"people": N, "reps": REPS, "tenure_share": TENURE_SHARE.tolist(),
                       "satisfied_by_tenure": SAT_BY_TENURE.tolist(), "tenure_logit": TENURE_LOGIT.tolist(),
                       "satisfied_odds": SAT_ODDS, "u_sd": U_SD, "target_rate_wave1": R1, "target_rate_cum": R_CUM,
                       "B_busy_share": BUSY_SHARE, "B_busy_sat_diff": BUSY_SAT_DIFF, "B_busy_shift": BUSY_SHIFT,
                       "true_satisfied_formula": float((TENURE_SHARE * SAT_BY_TENURE).sum())}}

    # 1) 例の1回分（data、シナリオB）
    a1, a2 = calib("B", SAT_ODDS, R1, R_CUM)
    ten, busy, sat, w1, w2, non = survey(np.random.default_rng(SEED), "B", SAT_ODDS, a1, a2)
    wave = np.where(w1, "1回目", np.where(w2, "催促後", "答えない"))
    pd.DataFrame({"person_id": np.arange(1, N + 1), "tenure": np.array(TENURE_LAB)[ten], "busy": busy.astype(int),
                  "satisfied_true": sat.astype(int), "answered": wave}).to_csv(DATA / "survey_example_B.csv", index=False)

    # 2) A と B（各300回）
    main_rows, sims = [], {}
    for scen in ["A", "B"]:
        d, a1, a2 = run(SEED * 1000 + (0 if scen == "A" else 50000), REPS, scen)
        sims[scen] = d
        row = {"scenario": scen, "a1": r4(a1), "a2": r4(a2)}
        for c in ["true", "wave1", "wave2", "respondents", "nonrespondents", "weighted_tenure", "late_as_non",
                  "rate1", "rate_cum", "respondents_err_pt", "weighted_tenure_err_pt", "late_as_non_err_pt",
                  "wave1_err_pt", "non_minus_resp_pt", "non_minus_wave2_pt", "tenure_gap_max_pt"]:
            row[c] = r4(d[c].mean())
        for c in ["respondents_err_pt", "late_as_non_err_pt"]:
            row[c + "_p10"] = r4(d[c].quantile(.1))
            row[c + "_p90"] = r4(d[c].quantile(.9))
        main_rows.append(row)
    pd.DataFrame(main_rows).to_csv(RES / "scenarios.csv", index=False)
    res["scenarios"] = main_rows

    # 3) 確かめ：A は満足の答えやすさ × 回答率、B は忙しい人の満足の差 × 割合（各100回）
    grid, k = [], 0
    for odds in [1.0, 1.4, 1.8, 3.0]:
        for r1, rc in [(0.12, 0.20), (0.25, 0.40), (0.40, 0.60)]:
            d, _, _ = run(SEED * 5000 + k * 1000, 100, "A", odds=odds, r1=r1, r_cum=rc)
            k += 1
            grid.append({"scenario": "A", "satisfied_odds": odds, "rate_cum_target": rc, "busy_share": 0.0, "busy_sat_diff": 0.0,
                         **{c: r4(d[c].mean()) for c in ["rate_cum", "true", "wave1", "wave2", "nonrespondents",
                                                         "respondents_err_pt", "weighted_tenure_err_pt", "late_as_non_err_pt",
                                                         "non_minus_resp_pt", "non_minus_wave2_pt"]}})
    for bs in [0.15, 0.30, 0.45]:
        for bd in [-0.15, 0.0, 0.15, 0.30, 0.45]:
            d, _, _ = run(SEED * 6000 + k * 1000, 100, "B", busy_share=bs, busy_diff=bd)
            k += 1
            grid.append({"scenario": "B", "satisfied_odds": SAT_ODDS, "rate_cum_target": R_CUM, "busy_share": bs, "busy_sat_diff": bd,
                         **{c: r4(d[c].mean()) for c in ["rate_cum", "true", "wave1", "wave2", "nonrespondents",
                                                         "respondents_err_pt", "weighted_tenure_err_pt", "late_as_non_err_pt",
                                                         "non_minus_resp_pt", "non_minus_wave2_pt"]}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness.csv", index=False)
    gA, gB = grid[grid.scenario == "A"], grid[grid.scenario == "B"]
    gA1 = gA[gA.satisfied_odds > 1]
    res["robustness"] = {
        "combos": int(len(grid)),
        "A_non_minus_resp_pt_range_odds_gt1": [r4(gA1.non_minus_resp_pt.min()), r4(gA1.non_minus_resp_pt.max())],
        "A_respondents_err_pt_range_odds_gt1": [r4(gA1.respondents_err_pt.min()), r4(gA1.respondents_err_pt.max())],
        "A_late_as_non_err_pt_range_odds_gt1": [r4(gA1.late_as_non_err_pt.min()), r4(gA1.late_as_non_err_pt.max())],
        "A_late_as_non_abs_smaller_than_resp_all_odds_gt1": bool((gA1.late_as_non_err_pt.abs() < gA1.respondents_err_pt.abs()).all()),
        "A_odds1_respondents_err_pt_range": [r4(gA[gA.satisfied_odds == 1].respondents_err_pt.min()),
                                             r4(gA[gA.satisfied_odds == 1].respondents_err_pt.max())],
        "B_non_minus_wave2_pt_range": [r4(gB.non_minus_wave2_pt.min()), r4(gB.non_minus_wave2_pt.max())],
        "B_late_as_non_err_pt_range": [r4(gB.late_as_non_err_pt.min()), r4(gB.late_as_non_err_pt.max())],
        "B_respondents_err_pt_range": [r4(gB.respondents_err_pt.min()), r4(gB.respondents_err_pt.max())],
        "B_combos_late_as_non_worse_than_resp": int((gB.late_as_non_err_pt.abs() > gB.respondents_err_pt.abs()).sum()),
        "B_combos": int(len(gB)),
        "B_combos_non_above_resp": int((gB.non_minus_resp_pt > 0).sum()),
        "combos_wave1_above_wave2": int((grid.wave1 > grid.wave2).sum()),
        "B_combos_wave1_above_wave2": int((gB.wave1 > gB.wave2).sum()),
        "A_combos_odds_gt1": int(len(gA1)),
    }

    m = {r["scenario"]: r for r in main_rows}
    # 図1：1回目・催促後・答えない人の満足の割合
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.6), sharey=True)
    for ax, scen, ttl in [(axes[0], "A", "A：答えにくさが続いている"), (axes[1], "B", "B：利用者の30%は忙しくてほぼ答えない人\n（満足がほかの人より30ポイント高い）")]:
        r = m[scen]
        labs = ["1回目に答えた", "催促後に答えた", "答えなかった\n（ふつうは見えない）"]
        vals = [r["wave1"] * 100, r["wave2"] * 100, r["nonrespondents"] * 100]
        bars = ax.bar(labs, vals, color=[BLUE, LIGHT, ORANGE])
        for b_, v, tc in zip(bars, vals, ["white", INK, "white"]):
            ax.text(b_.get_x() + b_.get_width() / 2, 6, f"{v:.1f}%", ha="center", va="bottom", fontsize=11, color=tc)
        ax.axhline(r["true"] * 100, color=INK, ls="--", lw=1, label=f"全員の本当の割合 {r['true']*100:.1f}%")
        ax.legend(fontsize=9, frameon=False, loc="upper right")
        ax.set_title(ttl, fontsize=11)
        ax.set_ylim(0, 85)
    axes[0].set_ylabel("満足している人の割合（%）")
    fig.suptitle("催促後に答えた人は、答えなかった人の代わりになるか", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a970_waves.png", SRC + "。利用者8,000人を300回作り直した平均。回答率は1回目25%・催促後まで40%")

    # 図2：見積もりの外れ（A・B）
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    labs = ["1回目の回答者だけ", "回答者そのまま", "利用年数で重み", "答えなかった人を\n催促後の回答者と同じと置く"]
    keys = ["wave1_err_pt", "respondents_err_pt", "weighted_tenure_err_pt", "late_as_non_err_pt"]
    x = np.arange(len(labs))
    for j, (scen, c) in enumerate([("A", BLUE), ("B", ORANGE)]):
        vals = [m[scen][k_] for k_ in keys]
        bb = ax.bar(x + (j - 0.5) * 0.38, vals, 0.36, color=c, label="A：答えにくさが続いている" if scen == "A" else "B：答えない人に忙しい人")
        for b_, v in zip(bb, vals):
            ax.text(b_.get_x() + b_.get_width() / 2, v + (0.3 if v >= 0 else -0.3), f"{v:+.1f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9.5)
    ax.set_ylabel("満足の割合の外れ（ポイント）")
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    ax.set_ylim(min(-3.0, ax.get_ylim()[0] - 0.8), ax.get_ylim()[1] + 0.5)
    ax.set_title("催促後の回答者で埋めると、Aでは外れが少し縮み、この置き方のBでは外れが広がる", fontsize=12)
    save(fig, "a970_estimates.png", SRC + "。300回の平均。外れ＝見積もり－全員の本当の割合")

    # 図3：確かめ（B：忙しい人の満足の差 × 割合）
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    for bs, c, mk in [(0.15, LIGHT, "o"), (0.30, BLUE, "s"), (0.45, INK, "^")]:
        d = gB[gB.busy_share == bs].sort_values("busy_sat_diff")
        ax.plot(d.busy_sat_diff * 100, d.respondents_err_pt, marker=mk, color=c, label=f"忙しい人が利用者の{bs*100:.0f}%（実線・点線とも）")
        ax.plot(d.busy_sat_diff * 100, d.late_as_non_err_pt, marker=mk, color=c, ls="--")
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xticks([-15, 0, 15, 30, 45])
    ax.set_xlabel("忙しい人とほかの人の、満足している割合の差（ポイント）")
    ax.set_ylabel("満足の割合の外れ（ポイント）")
    ax.legend(fontsize=8.5, frameon=False, loc="lower left")
    ax.set_title("答えない理由が別にあると、催促後の回答者で埋めたほうが外れる置き方がある\n（実線：回答者そのまま、点線：答えなかった人を催促後の回答者と同じと置く）", fontsize=11.5)
    save(fig, "a970_robustness_B.png", SRC + "。各100回の平均。全員の満足の割合は60%前後にそろえた")

    res["run_sec"] = round(time.time() - t0, 1)
    with open(RES / "a970_main.json", "w", encoding="utf-8") as f:
        json.dump({k_: v for k_, v in res.items() if k_ != "run_sec"}, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
