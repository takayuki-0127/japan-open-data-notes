"""1174 第1希望と第2希望を書ける抽選では、第2希望が当たる見込みは何で決まるのか？（架空のデータ）

作成者が置いた架空の体験講座（A〜Eの5回、枠は100・100・120・150・130の計600）。申し込む人1,000人は、
第1希望と第2希望（第1希望とは別の回）を1つずつ書く。第1希望の割合は A35%・B25%・C20%・D12%・E8%（人数はちょうどこの割合）。
第2希望は、第1希望以外の4回から、第1希望の割合に比例した確率で乱数で選ぶ。
2つの抽選の決まり：
 ① 第1希望を先に：回ごとに第1希望の人の中で抽選し、外れた人だけで、第2希望の回の残った枠を抽選する
 ② 順に割り当て：申し込んだ人をでたらめな順に並べ、前から、第1希望に空きがあれば第1希望、なければ第2希望に空きがあれば第2希望に入れる
(1) 基本の設定で各2,000回抽選し、回ごとに、第1希望の人の当たる見込みと、第1希望に外れた人の第2希望の当たる見込みを数える
(2) 第2希望の見込みを「第1希望で埋まらず残った枠÷第1希望に外れてその回を第2希望に書いた人の数（見込み）」の式と照らす
(3) 確かめ：申し込む人（600・1,000・1,400人）×第1希望の偏り（なし・基本・強い）×2つの決まり＝18通り（各500回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1174
SRC = "架空の体験講座の抽選（作成者が置いた希望の割合と枠からの乱数、seed 1174）"
NAMES = ["A", "B", "C", "D", "E"]
SEATS = np.array([100, 100, 120, 150, 130])
SHARES = {"偏りなし": [0.2, 0.2, 0.2, 0.2, 0.2],
          "基本": [0.35, 0.25, 0.20, 0.12, 0.08],
          "偏り強い": [0.5, 0.25, 0.12, 0.08, 0.05]}
PEOPLE_BASE = 1000
R_BASE, R_GRID = 2000, 500
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def make_people(rng, n, share):
    share = np.array(share)
    cnt = np.round(share * n).astype(int)
    cnt[0] += n - cnt.sum()
    first = np.repeat(np.arange(5), cnt)
    second = np.empty(n, dtype=int)
    for i, f in enumerate(first):
        w = share.copy()
        w[f] = 0
        second[i] = rng.choice(5, p=w / w.sum())
    return first, second


def draw_rule1(rng, first, second):
    n = len(first)
    key = rng.random(n)
    win1 = np.zeros(n, bool)
    left = SEATS.copy()
    for s in range(5):
        idx = np.where(first == s)[0]
        k = min(len(idx), SEATS[s])
        if k:
            win1[idx[np.argsort(key[idx])[:k]]] = True
        left[s] = SEATS[s] - k
    win2 = np.zeros(n, bool)
    key2 = rng.random(n)
    for s in range(5):
        idx = np.where((~win1) & (second == s))[0]
        k = min(len(idx), left[s])
        if k:
            win2[idx[np.argsort(key2[idx])[:k]]] = True
    return win1, win2, left


def draw_rule2(rng, first, second):
    n = len(first)
    order = rng.permutation(n)
    left = SEATS.copy()
    win1 = np.zeros(n, bool)
    win2 = np.zeros(n, bool)
    for i in order:
        f = first[i]
        if left[f] > 0:
            left[f] -= 1
            win1[i] = True
        elif left[second[i]] > 0:
            left[second[i]] -= 1
            win2[i] = True
    return win1, win2


def run(rng, first, second, R, rule):
    n = len(first)
    w1 = np.zeros(n)
    w2 = np.zeros(n)
    lose1 = np.zeros(n)
    lefts = []
    for _ in range(R):
        if rule == 1:
            a, b, left = draw_rule1(rng, first, second)
            lefts.append(left)
        else:
            a, b = draw_rule2(rng, first, second)
        w1 += a
        w2 += b
        lose1 += ~a
    return w1 / R, w2 / R, lose1 / R, (np.array(lefts).mean(axis=0) if lefts else None)


def formula_second(first, second):
    """式：第1希望で残る枠 ÷ 第1希望に外れてその回を第2希望に書いた人の数（見込み）"""
    n1 = np.bincount(first, minlength=5)
    p1 = np.minimum(1, SEATS / np.maximum(n1, 1))
    left = np.maximum(0, SEATS - n1)
    exp_losers = np.array([(1 - p1[first[second == s]]).sum() for s in range(5)])
    return np.where(exp_losers > 0, np.minimum(1, left / np.maximum(exp_losers, 1e-9)), np.nan), left, exp_losers


def session_table(first, second, res1, res2):
    w1a, w2a, l1a, lefta = res1
    w1b, w2b, l1b, _ = res2
    fval, left_f, exp_losers = formula_second(first, second)
    rows = []
    for s in range(5):
        f = first == s
        sc = second == s
        n2 = int(sc.sum())
        rows.append({"session": NAMES[s], "seats": int(SEATS[s]), "first_n": int(f.sum()),
                     "first_ratio": r(f.sum() / SEATS[s], 3), "second_n": n2,
                     "ratio_with_second": r((f.sum() + n2) / SEATS[s], 3),
                     "naive_second_pct": r(min(1, SEATS[s] / n2) * 100, 2),
                     "left_after_first": int(left_f[s]), "left_after_first_sim": r(lefta[s], 2),
                     "second_losers_expected": r(exp_losers[s], 1),
                     "rule1_first_pct": r(w1a[f].mean() * 100, 2),
                     "rule1_second_given_lose_pct": r(w2a[sc].sum() / l1a[sc].sum() * 100, 2),
                     "formula_second_pct": r(fval[s] * 100, 2),
                     "rule2_first_pct": r(w1b[f].mean() * 100, 2),
                     "rule2_second_given_lose_pct": r(w2b[sc].sum() / l1b[sc].sum() * 100, 2)})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    first, second = make_people(rng, PEOPLE_BASE, SHARES["基本"])
    res1 = run(rng, first, second, R_BASE, 1)
    print("rule1", round(time.time() - T0, 1), flush=True)
    res2 = run(rng, first, second, R_BASE, 2)
    print("rule2", round(time.time() - T0, 1), flush=True)
    st = session_table(first, second, res1, res2)
    st.to_csv(RES / "by_session.csv", index=False)
    out["setting"] = {"people": PEOPLE_BASE, "seats": SEATS.tolist(), "seats_total": int(SEATS.sum()),
                      "first_share": SHARES["基本"], "reps": R_BASE}
    out["by_session"] = st.to_dict(orient="records")

    # 組（第1希望×第2希望）ごと
    prow = []
    for f in range(5):
        for s in range(5):
            m = (first == f) & (second == s)
            if m.sum() == 0:
                continue
            prow.append({"first": NAMES[f], "second": NAMES[s], "people": int(m.sum()),
                         "rule1_first_pct": r(res1[0][m].mean() * 100, 2),
                         "rule1_second_pct": r(res1[1][m].mean() * 100, 2),
                         "rule1_any_pct": r((res1[0][m] + res1[1][m]).mean() * 100, 2),
                         "rule2_first_pct": r(res2[0][m].mean() * 100, 2),
                         "rule2_second_pct": r(res2[1][m].mean() * 100, 2),
                         "rule2_any_pct": r((res2[0][m] + res2[1][m]).mean() * 100, 2)})
    pt = pd.DataFrame(prow)
    pt.to_csv(RES / "by_pair.csv", index=False)
    a_first = pt[pt["first"] == "A"]
    out["pairs_first_A"] = {"rule1_any_min": r(a_first.rule1_any_pct.min(), 2), "rule1_any_max": r(a_first.rule1_any_pct.max(), 2),
                            "rule2_any_min": r(a_first.rule2_any_pct.min(), 2), "rule2_any_max": r(a_first.rule2_any_pct.max(), 2)}
    full = st[st.first_ratio >= 1]
    openq = st[st.first_ratio < 1]
    out["headline"] = {
        "full_sessions": full.session.tolist(),
        "full_rule1_second_max_pct": r(full.rule1_second_given_lose_pct.max(), 2),
        "open_sessions": openq.session.tolist(),
        "open_rule1_second_pct": dict(zip(openq.session, openq.rule1_second_given_lose_pct)),
        "open_formula_pct": dict(zip(openq.session, openq.formula_second_pct)),
        "open_naive_pct": dict(zip(openq.session, openq.naive_second_pct)),
        "rule1_placed_pct": r((res1[0] + res1[1]).mean() * 100, 2),
        "rule2_placed_pct": r((res2[0] + res2[1]).mean() * 100, 2),
        "rule1_first_win_pct": r(res1[0].mean() * 100, 2),
        "rule2_first_win_pct": r(res2[0].mean() * 100, 2),
        "max_abs_diff_formula_rule1": r((st.rule1_second_given_lose_pct - st.formula_second_pct).abs().max(), 2)}

    # data：1回分の抽選の例（①）
    a, b, _ = draw_rule1(rng, first, second)
    pd.DataFrame({"person_id": np.arange(1, PEOPLE_BASE + 1), "first": [NAMES[i] for i in first],
                  "second": [NAMES[i] for i in second], "won_first_rule1": a.astype(int),
                  "won_second_rule1": b.astype(int)}).to_csv(DATA / "applicants_example.csv", index=False)

    # (3) 18通り
    grows = []
    for n in [600, 1000, 1400]:
        for sname, share in SHARES.items():
            f_, s_ = make_people(rng, n, share)
            g1 = run(rng, f_, s_, R_GRID, 1)
            g2 = run(rng, f_, s_, R_GRID, 2)
            t = session_table(f_, s_, g1, g2)
            for _, row in t.iterrows():
                grows.append({"people": n, "share": sname, **row.to_dict()})
        print("grid", n, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    gf = grid[grid.first_ratio >= 1]
    go = grid[grid.first_ratio < 1]
    out["grid"] = {"settings": 9, "session_rows": len(grid),
                   "full_rows": len(gf), "full_rule1_second_max_pct": r(gf.rule1_second_given_lose_pct.max(), 2),
                   "full_rule2_second_min_pct": r(gf.rule2_second_given_lose_pct.min(), 2),
                   "full_rule2_second_max_pct": r(gf.rule2_second_given_lose_pct.max(), 2),
                   "open_rows": len(go),
                   "open_rule1_second_min_pct": r(go.rule1_second_given_lose_pct.min(), 2),
                   "open_rule1_second_max_pct": r(go.rule1_second_given_lose_pct.max(), 2),
                   "max_abs_diff_formula_rule1": r((grid.rule1_second_given_lose_pct - grid.formula_second_pct).abs().max(), 2),
                   "corr_naive_vs_rule1": r(np.corrcoef(grid.naive_second_pct, grid.rule1_second_given_lose_pct)[0, 1], 3),
                   "corr_formula_vs_rule1": r(np.corrcoef(grid.formula_second_pct, grid.rule1_second_given_lose_pct)[0, 1], 3),
                   "rule2_first_minus_rule1_first_min": r((grid.rule2_first_pct - grid.rule1_first_pct).min(), 2),
                   "rule2_first_minus_rule1_first_max": r((grid.rule2_first_pct - grid.rule1_first_pct).max(), 2)}

    # 図1：回ごとの第2希望の見込み（①）
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    x = np.arange(5)
    ax.bar(x - 0.2, st.naive_second_pct, width=0.4, color=GRAY, label="枠÷第2希望に書いた人（素朴な読み）")
    ax.bar(x + 0.2, st.rule1_second_given_lose_pct, width=0.4, color=BLUE, label="① 第1希望に外れた人が第2希望で当たる割合")
    ax.scatter(x + 0.2, st.formula_second_pct, color=ORANGE, zorder=3, s=22, label="式：残った枠÷外れて第2希望に書いた人")
    for i, row in st.iterrows():
        ax.text(i - 0.2, row.naive_second_pct + 2.5, f"{row.naive_second_pct:g}", ha="center", fontsize=8)
        ax.text(i + 0.2, row.rule1_second_given_lose_pct + 3.5, f"{row.rule1_second_given_lose_pct:g}", ha="center", fontsize=8, color=BLUE)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{a}（枠{b}）\n第1希望の倍率\n{c:g}倍" for a, b, c in zip(st.session, st.seats, st.first_ratio)], fontsize=9)
    ax.set_ylim(0, 115)
    ax.set_ylabel("第2希望で当たる見込み（%）")
    ax.set_title("第2希望の見込みは、第1希望で残った枠で決まる（①）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1174_by_session.png", SRC)

    # 図2：決まり①と②の比べ
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, col1, col2, ttl in [(axes[0], "rule1_first_pct", "rule2_first_pct", "第1希望で当たる見込み"),
                                (axes[1], "rule1_second_given_lose_pct", "rule2_second_given_lose_pct", "第1希望に外れた人が第2希望で当たる見込み")]:
        ax.bar(x - 0.2, st[col1], width=0.4, color=BLUE, label="① 第1希望を先に")
        ax.bar(x + 0.2, st[col2], width=0.4, color=GREEN, label="② 順に割り当て")
        for i, row in st.iterrows():
            ax.text(i - 0.2, row[col1] + 1.5, f"{row[col1]:g}", ha="center", fontsize=7.5, color=BLUE)
            ax.text(i + 0.2, row[col2] + 1.5, f"{row[col2]:g}", ha="center", fontsize=7.5, color=GREEN)
        ax.set_xticks(x)
        ax.set_xticklabels(st.session)
        ax.set_title(ttl, fontsize=11)
        ax.set_ylim(0, 115)
    axes[0].set_ylabel("%")
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("決まり②では、第2希望の人が空いた回の枠を先に使う", y=1.02)
    save(fig, "a1174_rules.png", SRC)

    # 図3：18通りで、式と数えた値
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    g1 = grid
    ax.scatter(g1.naive_second_pct, g1.rule1_second_given_lose_pct, color=GRAY, s=18, label="横軸＝枠÷第2希望に書いた人")
    ax.scatter(g1.formula_second_pct, g1.rule1_second_given_lose_pct, color=BLUE, s=18, label="横軸＝式（残った枠÷外れて書いた人）")
    ax.plot([0, 100], [0, 100], color=INK, lw=0.8)
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 105)
    ax.set_xlabel("見込みの読み（%）")
    ax.set_ylabel("① 第2希望で当たった割合（%）")
    ax.set_title("9通り×5回：式の読みは数えた値とほぼ重なる（①）", fontsize=12)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1174_grid.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1174_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
