"""1195 決まった文面で答えて1件の時間が縮んだとき、もう一度来る問い合わせはどれだけ増えるのか？（架空のデータ）

架空の会社の問い合わせ窓口。問い合わせ（困りごと1つ）には、決まった文面で答えられる「定型」と、
個別に調べて書く必要がある「込み入った」の2種類がある（作成者が置いた）。
はじめの返事を個別に書く前と、決まった文面を使う後で、
 ・1回の対応あたりの時間（記録から数える「1件の時間」）
 ・困りごと1つあたりの対応の時間の合計
 ・7日以内に同じ人がもう一度来た割合（記録から数える）
 ・解決しないまま来なくなった割合（記録には出ない。作成者だけが知る）
がどう動くかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1195
SRC = "架空の会社の問い合わせ窓口（作成者が置いた問い合わせの種類・対応の時間・解決の確率からの乱数、seed 1195）"
N = 40000                    # 困りごと（はじめの問い合わせ）の数
BASE = {
    "complex_share": 0.3,     # 込み入った問い合わせの割合
    "t_indiv_simple": 10.0,   # 個別に書く時間の平均（分）定型
    "t_indiv_complex": 18.0,  # 同 込み入った
    "t_template": 4.0,        # 決まった文面で答える時間の平均（分）
    "t_followup": 20.0,       # 2回目以降（個別に書く）の時間の平均（分）
    "cv_time": 0.5,
    "p_indiv_simple": 0.92,   # 個別に書いたときに解決する確率
    "p_indiv_complex": 0.80,
    "p_tmpl_simple": 0.92,    # 決まった文面で解決する確率
    "p_tmpl_complex": 0.45,
    "p_followup": 0.85,       # 2回目以降に解決する確率
    "use_on_complex": 0.5,    # 込み入った問い合わせにも決まった文面を使ってしまう割合
    "q_return": 0.7,          # 解決しなかった人がもう一度来る確率（残りは来なくなる）
    "delay_mean_days": 3.0,   # もう一度来るまでの日数の平均（指数分布）
    "window_days": 7,         # 「もう一度来た」と数える日数（記録の数え方）
    "max_contacts": 6,
}
GRID_COMPLEX = [0.1, 0.3, 0.5]
GRID_USE = [0.2, 0.5, 0.8]
GRID_PTC = [0.3, 0.45, 0.6]
GRID_Q = [0.5, 0.7, 0.9]


def r(x, d=4):
    return round(float(x), d)


def gamma_time(rng, mean, cv, n):
    k = 1 / cv ** 2
    return rng.gamma(k, mean / k, n)


def simulate(rng, template, P=BASE, n=N):
    """困りごと n 個を、はじめの問い合わせから解決か来なくなるまで追う"""
    cx = rng.random(n) < P["complex_share"]
    use_t = np.zeros(n, bool)
    if template:
        use_t = (~cx) | (rng.random(n) < P["use_on_complex"])
    # はじめの対応
    t1 = np.where(use_t, gamma_time(rng, P["t_template"], P["cv_time"], n),
                  np.where(cx, gamma_time(rng, P["t_indiv_complex"], P["cv_time"], n),
                           gamma_time(rng, P["t_indiv_simple"], P["cv_time"], n)))
    p1 = np.where(use_t, np.where(cx, P["p_tmpl_complex"], P["p_tmpl_simple"]),
                  np.where(cx, P["p_indiv_complex"], P["p_indiv_simple"]))
    solved = rng.random(n) < p1
    contacts = np.ones(n, int)
    total_t = t1.copy()
    gave_up = np.zeros(n, bool)
    first_gap = np.full(n, np.nan)   # はじめの問い合わせから2回目までの日数
    open_ = ~solved
    all_times = [t1]
    for c in range(2, P["max_contacts"] + 1):
        ret = open_ & (rng.random(n) < P["q_return"])
        gave_up |= open_ & ~ret
        idx = np.where(ret)[0]
        if len(idx) == 0:
            break
        gap = rng.exponential(P["delay_mean_days"], len(idx))
        if c == 2:
            first_gap[idx] = gap
        tt = gamma_time(rng, P["t_followup"], P["cv_time"], len(idx))
        all_times.append(tt)
        total_t[idx] += tt
        contacts[idx] += 1
        ok = rng.random(len(idx)) < P["p_followup"]
        solved[idx[ok]] = True
        open_ = np.zeros(n, bool)
        open_[idx[~ok]] = True
    gave_up |= open_          # 最後まで解決しなかった分も来なくなったとみなす
    times = np.concatenate(all_times)
    return {"complex": cx, "use_template": use_t, "t_first": t1, "total_t": total_t, "contacts": contacts,
            "solved": solved, "gave_up": gave_up, "first_gap": first_gap, "times": times}


def summarize(s, P=BASE):
    w = P["window_days"]
    came_back = ~np.isnan(s["first_gap"])
    return {
        "per_contact_min": s["times"].mean(),                 # 記録の「1件の時間」
        "first_contact_min": s["t_first"].mean(),
        "per_issue_total_min": s["total_t"].mean(),
        "contacts_per_issue": s["contacts"].mean(),
        "recontact_any_pct": 100 * came_back.mean(),
        "recontact_window_pct": 100 * (s["first_gap"] <= w).mean(),   # 7日以内に2回目が来た割合（記録）
        "recontact_after_window_pct": 100 * (came_back & (s["first_gap"] > w)).mean(),
        "gave_up_pct": 100 * s["gave_up"].mean(),
        "solved_pct": 100 * s["solved"].mean(),
        "contacts_total": int(s["contacts"].sum()),
        "followup_contacts": int((s["contacts"] - 1).sum()),
    }


def compare(rng, P=BASE, n=N):
    a = summarize(simulate(rng, False, P, n), P)
    b = summarize(simulate(rng, True, P, n), P)
    return a, b


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res = {"seed": SEED, "base": BASE, "n_issues": N}
    sa = simulate(rng, False)
    sb = simulate(rng, True)
    a, b = summarize(sa), summarize(sb)
    rows = []
    lab = {"per_contact_min": "1回の対応あたりの時間（分、記録の1件の時間）",
           "first_contact_min": "はじめの対応の時間（分）",
           "per_issue_total_min": "困りごと1つあたりの対応の時間の合計（分）",
           "contacts_per_issue": "困りごと1つあたりの対応の回数",
           "recontact_window_pct": "7日以内にもう一度来た割合（%、記録）",
           "recontact_any_pct": "いつかもう一度来た割合（%）",
           "recontact_after_window_pct": "8日以後にもう一度来た割合（%）",
           "gave_up_pct": "解決しないまま来なくなった割合（%、記録に出ない）",
           "solved_pct": "解決した割合（%）",
           "contacts_total": "対応の回数の合計（件）",
           "followup_contacts": "2回目以降の対応の回数（件）"}
    for k, l in lab.items():
        rows.append({"metric": k, "label": l, "before": r(a[k], 2), "after": r(b[k], 2),
                     "change_pct": r(100 * (b[k] / a[k] - 1), 2) if a[k] else None,
                     "diff": r(b[k] - a[k], 2)})
    base_df = pd.DataFrame(rows)
    base_df.to_csv(RES / "before_after_base.csv", index=False)
    res["before_after"] = rows
    # 種類ごと（後）
    tb = []
    for name, m in [("定型", ~sb["complex"]), ("込み入った・文面を使った", sb["complex"] & sb["use_template"]),
                    ("込み入った・個別に書いた", sb["complex"] & ~sb["use_template"])]:
        tb.append({"group": name, "n": int(m.sum()), "first_contact_min": r(sb["t_first"][m].mean(), 3),
                   "recontact_window_pct": r(100 * (sb["first_gap"][m] <= BASE["window_days"]).mean(), 2),
                   "gave_up_pct": r(100 * sb["gave_up"][m].mean(), 2),
                   "per_issue_total_min": r(sb["total_t"][m].mean(), 3)})
    for name, m in [("定型（前）", ~sa["complex"]), ("込み入った（前）", sa["complex"])]:
        tb.append({"group": name, "n": int(m.sum()), "first_contact_min": r(sa["t_first"][m].mean(), 3),
                   "recontact_window_pct": r(100 * (sa["first_gap"][m] <= BASE["window_days"]).mean(), 2),
                   "gave_up_pct": r(100 * sa["gave_up"][m].mean(), 2),
                   "per_issue_total_min": r(sa["total_t"][m].mean(), 3)})
    pd.DataFrame(tb).to_csv(RES / "by_group_base.csv", index=False)
    res["by_group"] = tb
    # 見かけの縮み（1回あたり）と困りごとあたりの縮み
    res["headline"] = {
        "per_contact_change_pct": r(100 * (b["per_contact_min"] / a["per_contact_min"] - 1), 2),
        "per_issue_change_pct": r(100 * (b["per_issue_total_min"] / a["per_issue_total_min"] - 1), 2),
        "recontact_window_before_pct": r(a["recontact_window_pct"], 2),
        "recontact_window_after_pct": r(b["recontact_window_pct"], 2),
        "recontact_ratio": r(b["recontact_window_pct"] / a["recontact_window_pct"], 3),
        "followup_ratio": r(b["followup_contacts"] / a["followup_contacts"], 3),
        "gave_up_before_pct": r(a["gave_up_pct"], 2), "gave_up_after_pct": r(b["gave_up_pct"], 2),
    }
    # 確かめ：81通り
    g = []
    for cs in GRID_COMPLEX:
        for u in GRID_USE:
            for ptc in GRID_PTC:
                for q in GRID_Q:
                    P = dict(BASE, complex_share=cs, use_on_complex=u, p_tmpl_complex=ptc, q_return=q)
                    a2, b2 = compare(rng, P, 20000)
                    g.append({"complex_share": cs, "use_on_complex": u, "p_tmpl_complex": ptc, "q_return": q,
                              "per_contact_change_pct": r(100 * (b2["per_contact_min"] / a2["per_contact_min"] - 1), 2),
                              "per_issue_change_pct": r(100 * (b2["per_issue_total_min"] / a2["per_issue_total_min"] - 1), 2),
                              "recontact_before_pct": r(a2["recontact_window_pct"], 2),
                              "recontact_after_pct": r(b2["recontact_window_pct"], 2),
                              "recontact_diff_pt": r(b2["recontact_window_pct"] - a2["recontact_window_pct"], 2),
                              "gave_up_diff_pt": r(b2["gave_up_pct"] - a2["gave_up_pct"], 2),
                              "solved_diff_pt": r(b2["solved_pct"] - a2["solved_pct"], 2)})
    grid = pd.DataFrame(g)
    grid.to_csv(RES / "grid.csv", index=False)
    gap = grid.per_issue_change_pct - grid.per_contact_change_pct
    res["grid_summary"] = {
        "n": int(len(grid)),
        "per_contact_change_range": [r(grid.per_contact_change_pct.min(), 2), r(grid.per_contact_change_pct.max(), 2)],
        "per_issue_change_range": [r(grid.per_issue_change_pct.min(), 2), r(grid.per_issue_change_pct.max(), 2)],
        "per_issue_increase_count": int((grid.per_issue_change_pct > 0).sum()),
        "per_contact_decrease_count": int((grid.per_contact_change_pct < 0).sum()),
        "recontact_diff_range": [r(grid.recontact_diff_pt.min(), 2), r(grid.recontact_diff_pt.max(), 2)],
        "gave_up_diff_range": [r(grid.gave_up_diff_pt.min(), 2), r(grid.gave_up_diff_pt.max(), 2)],
        "issue_minus_contact_range": [r(gap.min(), 2), r(gap.max(), 2)],
    }
    inc = grid[grid.per_issue_change_pct > 0]
    res["grid_issue_increase_rows"] = inc.to_dict("records")
    # 込み入った割合 × 使う割合ごとの範囲（解決の確率・来る確率の9通り）
    tab = []
    for cs in GRID_COMPLEX:
        for u in GRID_USE:
            d = grid[(grid.complex_share == cs) & (grid.use_on_complex == u)]
            tab.append({"complex_share": cs, "use_on_complex": u,
                        "per_contact_min_pct": r(d.per_contact_change_pct.min(), 2), "per_contact_max_pct": r(d.per_contact_change_pct.max(), 2),
                        "per_issue_min_pct": r(d.per_issue_change_pct.min(), 2), "per_issue_max_pct": r(d.per_issue_change_pct.max(), 2),
                        "recontact_diff_min_pt": r(d.recontact_diff_pt.min(), 2), "recontact_diff_max_pt": r(d.recontact_diff_pt.max(), 2)})
    pd.DataFrame(tab).to_csv(RES / "grid_by_share_use.csv", index=False)
    res["grid_by_share_use"] = tab

    # データ：後の困りごと（はじめの2,000件）
    m = 2000
    pd.DataFrame({"issue": np.arange(m), "complex": sb["complex"][:m].astype(int), "use_template": sb["use_template"][:m].astype(int),
                  "first_contact_min": np.round(sb["t_first"][:m], 2), "contacts": sb["contacts"][:m],
                  "days_to_second": np.round(sb["first_gap"][:m], 2), "total_min": np.round(sb["total_t"][:m], 2),
                  "solved": sb["solved"][:m].astype(int), "gave_up": sb["gave_up"][:m].astype(int)}
                 ).to_csv(DATA / "issues_after_first2000.csv", index=False)

    # 図1 前と後：1回あたりと困りごとあたり
    fig, ax = plt.subplots(figsize=(8, 4.2))
    keys = ["first_contact_min", "per_contact_min", "per_issue_total_min"]
    names = ["はじめの対応の時間", "1回の対応あたり\n（記録の1件の時間）", "困りごと1つあたりの\n対応の時間の合計"]
    x = np.arange(3)
    va = [r(a[k], 2) for k in keys]
    vb = [r(b[k], 2) for k in keys]
    ax.bar(x - 0.2, va, 0.4, color=GRAY, label="前（はじめの返事を個別に書く）")
    ax.bar(x + 0.2, vb, 0.4, color=BLUE, label="後（決まった文面を使う）")
    for xi, v1, v2 in zip(x, va, vb):
        ax.text(xi - 0.2, v1 + 0.3, f"{v1:g}", ha="center", fontsize=9)
        ax.text(xi + 0.2, v2 + 0.3, f"{v2:g}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("分（平均）")
    ax.set_ylim(0, max(va + vb) * 1.2)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("1回あたりの縮みより、困りごとあたりの縮みは少し小さい")
    save(fig, "a1195_time_before_after.png", "出典：" + SRC)

    # 図2 もう一度来た割合と来なくなった割合
    fig, ax = plt.subplots(figsize=(8, 4.2))
    keys = ["recontact_window_pct", "recontact_after_window_pct", "gave_up_pct"]
    names = ["7日以内に\nもう一度来た（記録）", "8日以後に\nもう一度来た", "解決しないまま\n来なくなった（記録に出ない）"]
    va = [r(a[k], 2) for k in keys]
    vb = [r(b[k], 2) for k in keys]
    ax.bar(x - 0.2, va, 0.4, color=GRAY, label="前")
    ax.bar(x + 0.2, vb, 0.4, color=ORANGE, label="後")
    for xi, v1, v2 in zip(x, va, vb):
        ax.text(xi - 0.2, v1 + 0.2, f"{v1:g}%", ha="center", fontsize=9)
        ax.text(xi + 0.2, v2 + 0.2, f"{v2:g}%", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("困りごとに対する割合（%）")
    ax.set_ylim(0, max(va + vb) * 1.25)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("決まった文面を使うと、もう一度来る人も、来なくなる人も増えた")
    save(fig, "a1195_recontact.png", "出典：" + SRC)

    # 図3 81通り：1回あたりの変化と困りごとあたりの変化
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for cs, col in zip(GRID_COMPLEX, [LIGHT, BLUE, INK]):
        d = grid[grid.complex_share == cs]
        ax.scatter(d.per_contact_change_pct, d.per_issue_change_pct, s=22, color=col, label=f"込み入った割合{cs:.0%}")
    lo = min(grid.per_contact_change_pct.min(), grid.per_issue_change_pct.min()) - 3
    hi = max(grid.per_issue_change_pct.max(), 0) + 5
    ax.plot([lo, hi], [lo, hi], color=GRAY, lw=0.8, ls="--")
    ax.text(-12, -16, "同じ割合で縮む線", color=GRAY, fontsize=8, ha="left")
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("1回の対応あたりの時間の変化（%）")
    ax.set_ylabel("困りごと1つあたりの時間の合計の変化（%）")
    ax.set_title("81通りで、困りごとあたりの縮みはいつも1回あたりより小さい")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1195_grid.png", "出典：" + SRC)

    res_out = dict(res)
    with open(RES / "a1195_main.json", "w", encoding="utf-8") as f:
        json.dump(res_out, f, ensure_ascii=False, indent=1)
    print(base_df.to_string())
    print(pd.DataFrame(tb).to_string())
    print(json.dumps(res["grid_summary"], ensure_ascii=False))
    print(pd.DataFrame(tab).to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
