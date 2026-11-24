"""1188 よくある質問のページを増やして問い合わせが減ったとき、減ったのは解決した人か、あきらめた人か？（架空のデータ）

作成者が置いた架空の会社の窓口。1か月に困りごとを持つ人は20,000人。困りごとの種類は200種類で、
多い順に k 番目の種類の出やすさは 1/k^a（基本 a=1.0）。よくある質問のページは、多い種類から順に1種類1ページで作る（P ページなら上位 P 種類を扱う）。
1人ひとりは、
  1) 確率 L（基本0.6）で、まずよくある質問のページを見る。見ない人は問い合わせる
  2) 見た人のうち、自分の種類のページがあれば、確率 f(P)=0.9×(10/P)^b で、そのページにたどり着く（基本 b=0.1。ページが増えるほど探しにくい）
  3) たどり着いた人は確率 0.8 で解決する（問い合わせない）
  4) 解決しなかった人（ページがない・たどり着けない・読んでも解決しない）は、確率 g(P)=0.2+g1×log2(P/10) であきらめる（基本 g1=0.06。探す手間が増えるほどあきらめやすい）。あきらめなかった人は問い合わせる
同じ人の乱数を、ページの数を変えても使い回す（どのページの数でも同じ人たちで比べる）。
窓口から見える数：
  ① 問い合わせの件数の減り（10ページのときから）を、すべてページで解決した人とみなす
  ② ページを見て問い合わせなかった人（＝解決した人＋あきらめた人）を、解決した人とみなす
  ③ ページの下の「解決しましたか」：解決した人は30%が「はい」、たどり着いたが解決しなかった人は30%が「いいえ」、
     ほかのページで止まった人（ページがない・たどり着けない）は10%が「いいえ」と答える。
     「はい」÷（「はい」＋「いいえ」）×ページを見た人 を解決した人とみなす
ページの数 10・20・40・80・160・320 を各300回。確かめとして b（0・0.1・0.2・0.3）×g1（0・0.03・0.06・0.09）×L（0.4・0.6・0.8）×a（0.7・1.0・1.3）＝144通り（各30回）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1188
SRC = "架空の会社の問い合わせ窓口（作成者が置いた困りごとの種類・ページの見つけやすさ・あきらめやすさからの乱数、seed 1188）"
N, T = 20000, 200
PAGES = [10, 20, 40, 80, 160, 320]
SOLVE = 0.8
ANS_SOLVED, ANS_FOUND_FAIL, ANS_OTHER = 0.3, 0.3, 0.1
R_MAIN, R_GRID = 300, 30
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def f_find(P, b):
    return 0.9 * (10 / P) ** b


def g_give(P, g1):
    return 0.2 + g1 * np.log2(P / 10)


def one_run(rng, b=0.1, g1=0.06, L=0.6, a=1.0, keep=False):
    w = 1 / np.arange(1, T + 1) ** a
    typ = rng.choice(T, size=N, p=w / w.sum())       # 0 がいちばん多い種類
    u_look, u_find, u_solve, u_give, u_ans = rng.random((5, N))
    look = u_look < L
    out = []
    for P in PAGES:
        covered = typ < P
        found = look & covered & (u_find < f_find(P, b))
        solved = found & (u_solve < SOLVE)
        fail = look & ~solved
        gave = fail & (u_give < g_give(P, g1))
        inquire = ~look | (fail & ~gave)
        found_fail = found & ~solved
        other = look & ~found
        yes = (solved & (u_ans < ANS_SOLVED)).sum()
        no = (found_fail & (u_ans < ANS_FOUND_FAIL)).sum() + (other & (u_ans < ANS_OTHER)).sum()
        out.append({"pages": P, "inquiries": int(inquire.sum()), "solved": int(solved.sum()), "gave_up": int(gave.sum()),
                    "looked": int(look.sum()), "looked_no_inquiry": int((look & ~inquire).sum()),
                    "yes": int(yes), "no": int(no),
                    "est_by_button": float(yes / max(yes + no, 1) * look.sum()),
                    "coverage": float(covered.mean())})
    df = pd.DataFrame(out)
    base = df.iloc[0]
    df["drop_from_10"] = base.inquiries - df.inquiries
    df["solved_up_from_10"] = df.solved - base.solved
    df["gave_up_from_10"] = df.gave_up - base.gave_up
    if keep:
        P = 80
        covered = typ < P
        found = look & covered & (u_find < f_find(P, b))
        solved = found & (u_solve < SOLVE)
        fail = look & ~solved
        gave = fail & (u_give < g_give(P, g1))
        inquire = ~look | (fail & ~gave)
        state = np.where(solved, "解決", np.where(gave, "あきらめた", "問い合わせ"))
        return df, pd.DataFrame({"person_id": np.arange(1, N + 1), "type_rank": typ + 1, "looked_page": look.astype(int),
                                 "found_page": found.astype(int), "result_80pages": state})
    return df


def steps_of(df):
    s = []
    for i in range(1, len(df)):
        p0, p1 = df.iloc[i - 1], df.iloc[i]
        d = p0.inquiries - p1.inquiries
        s.append({"step": f"{int(p0.pages)}→{int(p1.pages)}", "inq_drop": d,
                  "solved_part": p1.solved - p0.solved, "gave_up_part": p1.gave_up - p0.gave_up})
    return pd.DataFrame(s)


def main():
    rng = np.random.default_rng(SEED)
    _, ex = one_run(np.random.default_rng(SEED + 1), keep=True)
    ex.to_csv(DATA / "people_example.csv", index=False)

    runs = [one_run(rng) for _ in range(R_MAIN)]
    allp = pd.concat([d.assign(run=i) for i, d in enumerate(runs)])
    byp = allp.groupby("pages").mean(numeric_only=True).drop(columns="run").reset_index()
    byp["true_solved_share_of_drop"] = np.where(byp.drop_from_10 > 0, byp.solved_up_from_10 / byp.drop_from_10.replace(0, np.nan), np.nan)
    byp["metric2_over_true_solved"] = byp.looked_no_inquiry / byp.solved
    byp["metric3_over_true_solved"] = byp.est_by_button / byp.solved
    byp["find_prob"] = [f_find(P, 0.1) for P in byp.pages]
    byp["give_prob"] = [g_give(P, 0.06) for P in byp.pages]
    byp = byp.round(4)
    byp.to_csv(RES / "by_pages.csv", index=False)

    st_all = pd.concat([steps_of(d) for d in runs])
    st = st_all.groupby("step", sort=False).mean().reset_index()
    st["gave_up_share"] = st.gave_up_part / st.inq_drop
    # 段ごとの減りのうち、あきらめた人の割合の10〜90%（回ごと）
    st_all["share"] = st_all.gave_up_part / st_all.inq_drop.replace(0, np.nan)
    q = st_all.groupby("step", sort=False).share.quantile([0.1, 0.9]).unstack().reset_index()
    st["gave_up_share_p10"] = q[0.1].values
    st["gave_up_share_p90"] = q[0.9].values
    st = st.round(4)
    st.to_csv(RES / "steps.csv", index=False)

    # 確かめ 144通り
    rows = []
    for b in [0, 0.1, 0.2, 0.3]:
        for g1 in [0, 0.03, 0.06, 0.09]:
            for L in [0.4, 0.6, 0.8]:
                for a in [0.7, 1.0, 1.3]:
                    ds = [one_run(rng, b, g1, L, a) for _ in range(R_GRID)]
                    m = pd.concat(ds).groupby("pages").mean(numeric_only=True)
                    sm = pd.concat([steps_of(d) for d in ds]).groupby("step", sort=False).mean()
                    tot_drop = m.loc[320, "drop_from_10"]
                    last = sm.loc["160→320"]
                    rows.append({"find_decline_b": b, "give_up_rise_g1": g1, "look_L": L, "skew_a": a,
                                 "drop_10_to_320": r(tot_drop, 1),
                                 "drop_share_10_to_320": r(tot_drop / m.loc[10, "inquiries"]),
                                 "gave_up_share_10_to_320": r(m.loc[320, "gave_up_from_10"] / tot_drop) if tot_drop > 0 else None,
                                 "drop_160_to_320": r(last.inq_drop, 1),
                                 "gave_up_share_160_to_320": r(last.gave_up_part / last.inq_drop) if last.inq_drop > 0 else None,
                                 "metric2_over_true_solved_320": r(m.loc[320, "looked_no_inquiry"] / m.loc[320, "solved"]),
                                 "metric3_over_true_solved_320": r(m.loc[320, "est_by_button"] / m.loc[320, "solved"]),
                                 "solved_change_160_to_320": r(last.solved_part, 1), "gave_up_change_160_to_320": r(last.gave_up_part, 1),
                                 "solved_change_10_to_320": r(m.loc[320, "solved_up_from_10"], 1), "gave_up_change_10_to_320": r(m.loc[320, "gave_up_from_10"], 1),
                                 "inquiries_fall_every_step": bool((np.diff(m.inquiries.values) < 0).all()),
                                 "true_solved_peak_pages": int(m.solved.idxmax())})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    ctrl = g[(g.find_decline_b == 0) & (g.give_up_rise_g1 == 0)]
    harm = g[(g.find_decline_b > 0) | (g.give_up_rise_g1 > 0)]
    both = g[(g.find_decline_b > 0) & (g.give_up_rise_g1 > 0)]
    fall = g[g.drop_160_to_320 > 0]
    robust = {
        "n": int(len(g)),
        "control_gave_up_share_10_320_min": r(ctrl.gave_up_share_10_to_320.min()),
        "control_gave_up_share_10_320_max": r(ctrl.gave_up_share_10_to_320.max()),
        "control_n": int(len(ctrl)),
        "n_inq_down_10_320": int((g.drop_10_to_320 > 0).sum()),
        "n_inq_down_solved_down_10_320": int(((g.drop_10_to_320 > 0) & (g.solved_change_10_to_320 < 0)).sum()),
        "n_inq_down_solved_up_10_320": int(((g.drop_10_to_320 > 0) & (g.solved_change_10_to_320 > 0)).sum()),
        "n_inq_down_gave_up_up_10_320": int(((g.drop_10_to_320 > 0) & (g.gave_up_change_10_to_320 > 0)).sum()),
        "n_last_step_inq_down": int(len(fall)),
        "n_last_step_inq_down_solved_down": int((fall.solved_change_160_to_320 < 0).sum()),
        "both_n": int(len(both)),
        "both_n_last_step_inq_down": int((both.drop_160_to_320 > 0).sum()),
        "both_n_last_step_inq_down_solved_down": int(((both.drop_160_to_320 > 0) & (both.solved_change_160_to_320 < 0)).sum()),
        "control_n_last_step_inq_down_solved_down": int(((ctrl.drop_160_to_320 > 0) & (ctrl.solved_change_160_to_320 < 0)).sum()),
        "drop_share_10_320_min": r(g.drop_share_10_to_320.min()), "drop_share_10_320_max": r(g.drop_share_10_to_320.max()),
        "n_inquiries_fall_every_step": int(g.inquiries_fall_every_step.sum()),
        "metric2_min": r(g.metric2_over_true_solved_320.min()), "metric2_max": r(g.metric2_over_true_solved_320.max()),
        "metric2_control_min": r(ctrl.metric2_over_true_solved_320.min()), "metric2_control_max": r(ctrl.metric2_over_true_solved_320.max()),
        "metric3_min": r(g.metric3_over_true_solved_320.min()), "metric3_max": r(g.metric3_over_true_solved_320.max()),
        "peak_pages_counts": g.true_solved_peak_pages.value_counts().sort_index().to_dict(),
        "metric2_by_b_g1": g.groupby(["find_decline_b", "give_up_rise_g1"]).metric2_over_true_solved_320.agg(["min", "max"]).round(4).reset_index().to_dict("records"),
    }
    robust["peak_pages_counts"] = {str(k): int(v) for k, v in robust["peak_pages_counts"].items()}

    bp = byp.set_index("pages")
    sts = st.set_index("step")
    headline = {
        "inq_10": r(bp.loc[10, "inquiries"], 1), "inq_320": r(bp.loc[320, "inquiries"], 1),
        "drop_10_320": r(bp.loc[320, "drop_from_10"], 1),
        "drop_10_320_pct": r(bp.loc[320, "drop_from_10"] / bp.loc[10, "inquiries"] * 100, 2),
        "solved_part_10_320": r(bp.loc[320, "solved_up_from_10"], 1), "gave_part_10_320": r(bp.loc[320, "gave_up_from_10"], 1),
        "gave_share_10_320_pct": r(bp.loc[320, "gave_up_from_10"] / bp.loc[320, "drop_from_10"] * 100, 2),
        "step_first_gave_share_pct": r(sts.loc["10→20", "gave_up_share"] * 100, 2),
        "step_last_gave_share_pct": r(sts.loc["160→320", "gave_up_share"] * 100, 2),
        "solved_peak_pages": int(bp.solved.idxmax()),
        "metric2_over_true_320": r(bp.loc[320, "metric2_over_true_solved"]),
        "metric3_over_true_320": r(bp.loc[320, "metric3_over_true_solved"]),
    }
    out = {"settings": {"people_per_month": N, "types": T, "skew_a": 1.0, "look_L": 0.6, "find": "0.9×(10/P)^0.1",
                        "solve_if_found": SOLVE, "give_up": "0.2+0.06×log2(P/10)", "pages": PAGES,
                        "answer_rates": {"solved_yes": ANS_SOLVED, "found_not_solved_no": ANS_FOUND_FAIL, "other_no": ANS_OTHER},
                        "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
           "headline": headline,
           "example_one_month_80pages": {"looked": int(ex.looked_page.sum()), "found": int(ex.found_page.sum()),
                                         **{k: int(v) for k, v in ex.result_80pages.value_counts().items()}},
           "robust": robust}
    with open(RES / "a1188_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：段ごとの減りの中身
    fig, ax = plt.subplots(figsize=(7.8, 4.5))
    x = np.arange(len(st))
    sp = st.solved_part.clip(lower=0)
    ax.bar(x, sp, 0.6, color=BLUE, label="解決した人が増えた分")
    ax.bar(x, st.gave_up_part, 0.6, bottom=sp, color=ORANGE, label="あきらめた人が増えた分")
    neg = st.solved_part.clip(upper=0)
    ax.bar(x, neg, 0.6, color=LIGHT, label="解決した人が減った分（ページが見つけにくくなった）")
    for xi, row in zip(x, st.itertuples()):
        ax.text(xi, sp.iloc[xi] + row.gave_up_part + 40, f"問い合わせ −{row.inq_drop:,.1f}\n解決 {row.solved_part:+,.1f}\nあきらめ {row.gave_up_part:+,.1f}",
                ha="center", va="bottom", fontsize=8)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x, [f"{s}ページ" for s in st.step])
    ax.set_xlabel("よくある質問のページの数（ふやす前→ふやした後）")
    ax.set_ylabel("1か月の人数（300回の平均）")
    top = (sp + st.gave_up_part).max()
    ax.set_ylim(min(neg.min() * 1.3, 0), top * 1.5)
    ax.set_title("ページをふやした分の問い合わせの減り：160→320では解決した人が減った")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1188_steps.png", SRC)

    # 図2：窓口から見える数と本当の解決
    fig, ax = plt.subplots(figsize=(7.8, 4.5))
    xp = np.arange(len(byp))
    ax.plot(xp, byp.solved, marker="o", color=INK, label="本当に解決した人（作成者が置いた値から数えた）")
    ax.plot(xp, byp.looked_no_inquiry, marker="s", color=ORANGE, label="②ページを見て問い合わせなかった人")
    ax.plot(xp, byp.est_by_button, marker="^", color=GREEN, label="③「解決しましたか」の「はい」の割合×見た人")
    ax.plot(xp, byp.inquiries, marker="D", color=GRAY, ls="--", label="問い合わせの件数")
    ax.set_xticks(xp, [f"{p}" for p in byp.pages])
    ax.set_xlabel("よくある質問のページの数")
    ax.set_ylabel("1か月の人数（300回の平均）")
    ax.set_ylim(0, max(byp.inquiries.max(), byp.looked_no_inquiry.max()) * 1.15)
    ax.set_title("②は増え続けたが、本当に解決した人は160→320ページで減った")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    save(fig, "a1188_metrics.png", SRC)

    # 図3：144通り、10→320ページの解決の増えとあきらめの増え
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    cols = {0: GRAY, 0.1: BLUE, 0.2: GREEN, 0.3: ORANGE}
    base_inq = g.drop_10_to_320 / g.drop_share_10_to_320
    xs_all = g.solved_change_10_to_320 / base_inq * 100
    ys_all = g.gave_up_change_10_to_320 / base_inq * 100
    for bb, c in cols.items():
        m_ = g.find_decline_b == bb
        ax.scatter(xs_all[m_], ys_all[m_], s=16, color=c, alpha=0.85, label=f"探しにくさの増え b={bb:g}")
    lo = min(xs_all.min(), ys_all.min()) - 3
    hi = max(xs_all.max(), ys_all.max()) + 3
    t = np.linspace(lo, hi, 10)
    ax.plot(t, -t, color=INK, lw=0.8, ls="--", label="点線より右上：問い合わせが減った")
    ax.axvline(0, color=INK, lw=0.6)
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_xlim(lo, hi)
    ax.set_ylim(min(ys_all.min() - 3, -hi * 0.2), ys_all.max() + 6)
    ax.set_xlabel("解決した人の増え（10ページのときの問い合わせに対する%）")
    ax.set_ylabel("あきらめた人の増え（同じく%）")
    ax.set_title("144通りの置き方：10→320ページで、何が問い合わせを減らしたか")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1188_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(robust, ensure_ascii=False)[:1500], round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
