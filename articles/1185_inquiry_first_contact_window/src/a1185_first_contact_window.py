"""1185 1回で解決した割合は、何日以内に同じ人から再び来なければ解決と数えるかで、どれだけ変わるのか？（架空のデータ）

作成者が置いた架空の会社の問い合わせ窓口。お客さん8,000人が、1年に平均2件の「用件」をでたらめな時刻に持ちこむ。
用件の種類は5つ。1回の対応で用件が本当に片づく確率は70%（どの回でも同じ）。片づかなかったとき、
20%はあきらめて二度と来ず、80%は同じ種類の用件でまた来る（再び来るまでの日数は中央値3日、対数で散らばる）。
「1回で解決した割合」を、ある対応のあと w 日以内に同じ人から問い合わせが来なければ解決、と数える。
(1) 窓 w を 1〜60日に変え、本当の割合（作りどおりで約70%）とのずれを数える。来た問い合わせを
    「種類を問わず数える」と「同じ種類だけ数える」の2つで比べる
(2) ずれを「片づいていないのに解決と数えた分」と「片づいたのに未解決と数えた分」に分ける
(3) 確かめ：新しい用件の数3通り×再び来るまでの日数3通り×あきらめる割合3通りの27通り
"""
import json
from math import erf, log, sqrt, exp
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1185
SRC = "架空の会社の問い合わせ窓口（作成者が置いた用件・解決の確率・再び来るまでの日数からの乱数、seed 1185）"
N_PEOPLE = 8000
P_SOLVE = 0.70
TYPE_SHARE = np.array([0.35, 0.25, 0.2, 0.12, 0.08])
EVAL_DAYS, MAX_W = 365, 60
WINDOWS = [1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60]
FINE_W = np.arange(1, 61)
BASE = {"issues_per_year": 2.0, "return_median_days": 3.0, "give_up": 0.2}
GRID_RATE = [0.5, 2.0, 6.0]
GRID_DELAY = [1.0, 3.0, 10.0]
GRID_GIVE = [0.1, 0.2, 0.4]
SIGMA = 1.0
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def simulate(rng, rate, med, give):
    span = EVAL_DAYS + MAX_W
    n_iss = rng.poisson(rate * span / 365, N_PEOPLE)
    person = np.repeat(np.arange(N_PEOPLE), n_iss)
    t = rng.random(len(person)) * span
    typ = rng.choice(len(TYPE_SHARE), len(person), p=TYPE_SHARE)
    P, T, Y, S, F, I, B = [], [], [], [], [], [], []
    alive = np.arange(len(person))
    cur_t = t.copy()
    first = True
    for _ in range(30):
        if len(alive) == 0:
            break
        solved = rng.random(len(alive)) < P_SOLVE
        P.append(person[alive]); T.append(cur_t[alive]); Y.append(typ[alive]); S.append(solved)
        F.append(np.full(len(alive), first)); I.append(alive)
        back = (~solved) & (rng.random(len(alive)) >= give)
        B.append(back)
        nxt = alive[back]
        cur_t[nxt] = cur_t[nxt] + np.exp(np.log(med) + SIGMA * rng.standard_normal(len(nxt)))
        alive = nxt[cur_t[nxt] < span]
        first = False
    df = pd.DataFrame({"person": np.concatenate(P), "t": np.concatenate(T), "type": np.concatenate(Y),
                       "solved": np.concatenate(S), "first": np.concatenate(F), "issue": np.concatenate(I),
                       "returns": np.concatenate(B)})
    df = df.sort_values(["person", "t"]).reset_index(drop=True)
    same_p = df.person.values[1:] == df.person.values[:-1]
    gap_any = np.full(len(df), np.inf)
    gap_any[:-1][same_p] = df.t.values[1:][same_p] - df.t.values[:-1][same_p]
    nxt_issue = np.full(len(df), -1)
    nxt_issue[:-1][same_p] = df.issue.values[1:][same_p]
    df["gap_any"] = gap_any
    df["next_is_same_issue"] = nxt_issue == df.issue.values
    d2 = df.sort_values(["person", "type", "t"])
    same_pt = (d2.person.values[1:] == d2.person.values[:-1]) & (d2.type.values[1:] == d2.type.values[:-1])
    g2 = np.full(len(d2), np.inf)
    g2[:-1][same_pt] = d2.t.values[1:][same_pt] - d2.t.values[:-1][same_pt]
    df.loc[d2.index, "gap_same"] = g2
    return df[df.t < EVAL_DAYS].reset_index(drop=True)


def measure(df, w, col="gap_any"):
    return float((df[col].values > w).mean())


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"people": N_PEOPLE, "p_solve": P_SOLVE, "type_share": TYPE_SHARE.tolist(),
                       "eval_days": EVAL_DAYS, "extra_days_after": MAX_W, "return_sigma_log": SIGMA, **BASE}}
    df = simulate(rng, BASE["issues_per_year"], BASE["return_median_days"], BASE["give_up"])
    true = df.solved.mean()
    out["base"] = {"contacts": len(df), "people_with_contact": int(df.person.nunique()),
                   "true_pct": r(true * 100, 2), "first_contacts": int(df["first"].sum())}
    rows = []
    for w in WINDOWS:
        m_any = measure(df, w)
        m_same = measure(df, w, "gap_same")
        counted = df.gap_any.values > w
        over = ((~df.solved.values) & counted).mean()     # 片づいていないのに解決と数えた
        under = (df.solved.values & ~counted).mean()      # 片づいたのに未解決と数えた
        over_giveup = ((~df.solved.values) & counted & ~df.returns.values).mean()
        counted_s = df.gap_same.values > w
        under_s = (df.solved.values & ~counted_s).mean()
        over_s = ((~df.solved.values) & counted_s).mean()
        # 式での見込み（種類を問わず）：片づかず w 日以内に戻る分と、片づいたが w 日以内に別件が来る分
        Fw = 0.5 * (1 + erf((log(w) - log(BASE["return_median_days"])) / (SIGMA * sqrt(2))))
        lam = BASE["issues_per_year"] / 365
        f_any = P_SOLVE * exp(-lam * w) + (1 - P_SOLVE) * (1 - (1 - BASE["give_up"]) * Fw) * exp(-lam * w)
        rows.append({"window_days": w, "measured_any_pct": r(m_any * 100, 2), "measured_same_type_pct": r(m_same * 100, 2),
                     "true_pct": r(true * 100, 2), "gap_any_pt": r((m_any - true) * 100, 2),
                     "gap_same_type_pt": r((m_same - true) * 100, 2),
                     "over_unsolved_counted_pct": r(over * 100, 2), "over_giveup_part_pct": r(over_giveup * 100, 2),
                     "over_late_return_part_pct": r((over - over_giveup) * 100, 2),
                     "under_solved_not_counted_pct": r(under * 100, 2),
                     "over_same_type_pct": r(over_s * 100, 2), "under_same_type_pct": r(under_s * 100, 2),
                     "formula_any_pct": r(f_any * 100, 2)})
    win = pd.DataFrame(rows)
    win.to_csv(RES / "by_window.csv", index=False)
    out["by_window"] = rows
    fine_any = np.array([measure(df, w) for w in FINE_W])
    fine_same = np.array([measure(df, w, "gap_same") for w in FINE_W])
    out["closest_window"] = {"any_days": int(FINE_W[np.argmin(abs(fine_any - true))]),
                             "any_gap_pt": r((fine_any[np.argmin(abs(fine_any - true))] - true) * 100, 2),
                             "same_type_days": int(FINE_W[np.argmin(abs(fine_same - true))]),
                             "same_type_gap_pt": r((fine_same[np.argmin(abs(fine_same - true))] - true) * 100, 2)}
    out["base"]["max_formula_diff_pt"] = r((win.measured_any_pct - win.formula_any_pct).abs().max(), 2)
    print("base", round(time.time() - T0, 1), flush=True)

    # data：1か月分の例
    ex = df[df.t < 30].copy()
    ex["day"] = ex.t.round(3)
    ex[["person", "day", "type", "solved", "gap_any", "gap_same"]].assign(
        person=lambda d: d.person + 1, type=lambda d: d["type"].map(lambda k: "種類" + "ABCDE"[k]),
        solved=lambda d: d.solved.astype(int),
        gap_any=lambda d: d.gap_any.replace(np.inf, np.nan).round(3),
        gap_same=lambda d: d.gap_same.replace(np.inf, np.nan).round(3)).to_csv(
        DATA / "contacts_first30days.csv", index=False)

    # (3) 27通り
    grows = []
    for rate in GRID_RATE:
        for med in GRID_DELAY:
            for give in GRID_GIVE:
                d = simulate(rng, rate, med, give)
                tr = d.solved.mean()
                fa = np.array([measure(d, w) for w in FINE_W])
                fs = np.array([measure(d, w, "gap_same") for w in FINE_W])
                ia, is_ = int(np.argmin(abs(fa - tr))), int(np.argmin(abs(fs - tr)))
                grows.append({"issues_per_year": rate, "return_median_days": med, "give_up": give,
                              "true_pct": r(tr * 100, 2),
                              "measured_any_w7_pct": r(fa[6] * 100, 2), "gap_any_w7_pt": r((fa[6] - tr) * 100, 2),
                              "measured_any_w30_pct": r(fa[29] * 100, 2), "gap_any_w30_pt": r((fa[29] - tr) * 100, 2),
                              "measured_same_w7_pct": r(fs[6] * 100, 2), "gap_same_w7_pt": r((fs[6] - tr) * 100, 2),
                              "closest_any_days": int(FINE_W[ia]), "closest_any_gap_pt": r((fa[ia] - tr) * 100, 2),
                              "closest_same_days": int(FINE_W[is_]), "closest_same_gap_pt": r((fs[is_] - tr) * 100, 2)})
        print("grid", rate, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid),
                   "gap_any_w7_min": grid.gap_any_w7_pt.min(), "gap_any_w7_max": grid.gap_any_w7_pt.max(),
                   "gap_any_w30_min": grid.gap_any_w30_pt.min(), "gap_any_w30_max": grid.gap_any_w30_pt.max(),
                   "gap_same_w7_min": grid.gap_same_w7_pt.min(), "gap_same_w7_max": grid.gap_same_w7_pt.max(),
                   "closest_any_days_min": int(grid.closest_any_days.min()),
                   "closest_any_days_max": int(grid.closest_any_days.max()),
                   "closest_any_abs_gap_max": r(grid.closest_any_gap_pt.abs().max(), 2),
                   "w7_over_settings": int((grid.gap_any_w7_pt > 0).sum()),
                   "w30_under_settings": int((grid.gap_any_w30_pt < 0).sum()),
                   "no_window_within_1pt": int((grid.closest_any_gap_pt.abs() > 1).sum()),
                   "closest_any_at_upper_60": int((grid.closest_any_days == 60).sum()),
                   "closest_same_days_min": int(grid.closest_same_days.min()),
                   "closest_same_at_upper_60": int((grid.closest_same_days == 60).sum())}
    g7 = win.set_index("window_days")
    out["headline"] = {"true_pct": out["base"]["true_pct"],
                       "w1_any_pct": g7.loc[1, "measured_any_pct"], "w7_any_pct": g7.loc[7, "measured_any_pct"],
                       "w30_any_pct": g7.loc[30, "measured_any_pct"], "w60_any_pct": g7.loc[60, "measured_any_pct"],
                       "w1_to_w60_span_pt": r(g7.loc[1, "measured_any_pct"] - g7.loc[60, "measured_any_pct"], 2),
                       "w7_same_pct": g7.loc[7, "measured_same_type_pct"],
                       "w30_same_pct": g7.loc[30, "measured_same_type_pct"]}

    # 図1：窓と見かけの割合
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.plot(win.window_days, win.measured_any_pct, "o-", color=BLUE, label="見かけ（種類を問わず、また来たら未解決）")
    ax.plot(win.window_days, win.measured_same_type_pct, "s-", color=GREEN, label="見かけ（同じ種類で来たら未解決）")
    ax.axhline(true * 100, color=ORANGE, ls="--", lw=1.3, label=f"本当の割合 {true * 100:.2f}%（作りどおり）")
    for w in [1, 7, 30, 60]:
        v = g7.loc[w, "measured_any_pct"]
        ax.text(w, v - 3.2, f"{v:g}", ha="center", fontsize=8, color=BLUE)
    ax.set_xscale("log")
    ax.set_xticks(WINDOWS)
    ax.set_xticklabels([str(w) for w in WINDOWS])
    ax.set_xlabel("この日数以内に同じ人から来なければ「解決」と数える（日）")
    ax.set_ylabel("1回で解決した割合（%）")
    ax.set_ylim(0, 100)
    ax.set_title("窓が短いと高く、長いと低く出る")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1185_window.png", SRC)

    # 図2：ずれの中身
    sel = win[win.window_days.isin([1, 3, 7, 14, 30, 60])].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    x = np.arange(len(sel))
    ax.bar(x - 0.27, sel.over_giveup_part_pct, width=0.27, color=GRAY, label="片づかず、あきらめた（解決と数えた）")
    ax.bar(x, sel.over_late_return_part_pct, width=0.27, color=BLUE, label="片づかず、窓より遅く来た（解決と数えた）")
    ax.bar(x + 0.27, sel.under_solved_not_counted_pct, width=0.27, color=ORANGE, label="片づいたのに、窓の中に別件が来た（未解決と数えた）")
    for i, row in sel.iterrows():
        for dx, v in [(-0.27, row.over_giveup_part_pct), (0, row.over_late_return_part_pct), (0.27, row.under_solved_not_counted_pct)]:
            ax.text(i + dx, v + 0.4, f"{v:g}", ha="center", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{w}日" for w in sel.window_days])
    ax.set_ylim(0, max(sel.over_giveup_part_pct.max(), sel.over_late_return_part_pct.max(), sel.under_solved_not_counted_pct.max()) * 1.35)
    ax.set_ylabel("すべての対応に占める割合（%）")
    ax.set_title("数え違いの中身（種類を問わず数えたとき）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center")
    save(fig, "a1185_errors.png", SRC)

    # 図3：27通りで、いちばん近い窓
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    cols = {0.1: GRAY, 0.2: BLUE, 0.4: GREEN}
    labels = []
    j = 0
    for rate in GRID_RATE:
        for med in GRID_DELAY:
            for t_, give in enumerate(GRID_GIVE):
                v = grid[(grid.issues_per_year == rate) & (grid.return_median_days == med) & (grid.give_up == give)].closest_any_days.iloc[0]
                ax.bar(j + (t_ - 1) * 0.27, v, width=0.27, color=cols[give], label=f"あきらめる {int(give * 100)}%" if j == 0 else None)
                ax.text(j + (t_ - 1) * 0.27, v + 0.6, f"{v}", ha="center", fontsize=7)
            labels.append(f"用件{rate:g}件\n戻り{med:g}日")
            j += 1
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylim(0, grid.closest_any_days.max() * 1.2)
    ax.set_ylabel("本当の割合にいちばん近い窓（日、60日は調べた上限）", fontsize=9.5)
    ax.set_xlabel("新しい用件の数（1人1年あたり）と、再び来るまでの日数（中央値）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    ax.set_title("「ちょうどよい窓」は置き方で変わる（種類を問わず数えたとき）", pad=26)
    save(fig, "a1185_grid.png", SRC, y=-0.1)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1185_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
