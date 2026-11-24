"""1176 2人1組の申し込みは、1人での申し込みより当たりやすいのか、当たりにくいのか？（架空のデータ）

作成者が置いた架空の催し（座席の抽選）で、1人の申し込みと2人1組の申し込みをまぜて抽選する。
2人1組は、当たれば2席を使う（2人そろって当たるか、そろって外れるか）。
抽選の決まりは2つ。
  ①1組を1口：申し込み1件を1口として、でたらめな順に並べ、前から席を割り当てる。
    残りが1席のときに組が来たら、その組は飛ばして次の1人の申し込みに割り当てる。
  ②人数分の口：2人1組は2口として引く（1人を引いたら、その人の組がまとめて当たる）。席の割り当ては①と同じ。
(1) 基本：席200、申し込む人2,000人（人数で数えた倍率10倍）、組で申し込む人の割合40%。各4,000回の抽選
(2) 2人が別々に1人ずつ申し込んだとき（2人そろって当たる・どちらかが当たる）と、組で申し込んだとき
(3) 確かめ：組の割合（10・40・70%）×倍率（2・5・10・30倍）×席（10・200）の24通り×2つの決まり
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1176
SRC = "架空の催しの座席の抽選（作成者が置いた申し込みと乱数、seed 1176）"
T0 = time.time()
RULES = {"entry": "①1組を1口", "people": "②人数分の口"}


def r(x, d=4):
    return round(float(x), d)


def make_entries(people, pair_share):
    n_pair = int(round(people * pair_share / 2))
    n_solo = people - 2 * n_pair
    size = np.concatenate([np.ones(n_solo, np.int64), np.full(n_pair, 2, np.int64)])
    return size, n_solo, n_pair


def draw(rng, size, seats, rule, reps, chunk=500):
    """各回の当たり（reps×申し込み件数の真偽）を返す"""
    E = len(size)
    w = size.astype(float) if rule == "people" else np.ones(E)
    outs = []
    for s in range(0, reps, chunk):
        m = min(chunk, reps - s)
        key = rng.exponential(1.0, (m, E)) / w  # 小さい順に引く（口の数に比例して先に来やすい）
        order = np.argsort(key, axis=1)
        sz = size[order]
        cs = np.cumsum(sz, axis=1)
        acc = cs <= seats
        used = np.where(acc, cs, 0).max(axis=1)
        left1 = (seats - used) == 1
        cand = (sz == 1) & (~acc)
        has = cand.any(axis=1)
        first = np.argmax(cand, axis=1)
        rows = np.where(left1 & has)[0]
        acc[rows, first[rows]] = True
        win = np.zeros((m, E), bool)
        np.put_along_axis(win, order, acc, axis=1)
        outs.append(win)
    return np.vstack(outs)


def summarize(win, size, n_solo, seats):
    solo = win[:, :n_solo]
    pair = win[:, n_solo:]
    p_solo = solo.mean()
    p_pair = pair.mean() if pair.shape[1] else float("nan")
    k = (n_solo // 2) * 2
    a, b = solo[:, 0:k:2], solo[:, 1:k:2]
    seats_used = (win * size).sum(axis=1)
    return {"p_solo_person_pct": p_solo * 100, "p_pair_person_pct": p_pair * 100,
            "pair_over_solo": p_pair / p_solo if p_solo > 0 else float("nan"),
            "two_solo_both_pct": (a & b).mean() * 100, "two_solo_any_pct": (a | b).mean() * 100,
            "seats_used_mean": seats_used.mean(), "seats_empty_share": (seats_used < seats).mean()}


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    S, PEOPLE, Q, REPS = 200, 2000, 0.4, 4000
    size, n_solo, n_pair = make_entries(PEOPLE, Q)
    out["setting"] = {"seats": S, "people": PEOPLE, "pair_share_people": Q, "solo_entries": n_solo,
                      "pair_entries": n_pair, "entries": n_solo + n_pair, "reps": REPS,
                      "ratio_by_people": r(PEOPLE / S, 3), "ratio_by_entries": r((n_solo + n_pair) / S, 3),
                      "seats_over_people_pct": r(S / PEOPLE * 100, 3)}
    base = {}
    rows = []
    wins_first = {}
    for rule, name in RULES.items():
        win = draw(rng, size, S, rule, REPS)
        sm = summarize(win, size, n_solo, S)
        # 回ごとの組の人の当たり÷1人の当たり（ばらつき）
        per = win[:, n_solo:].mean(axis=1) / win[:, :n_solo].mean(axis=1)
        sm["pair_over_solo_p05"], sm["pair_over_solo_p95"] = np.percentile(per, [5, 95])
        sm = {k: r(v, 3 if k.endswith("_pct") else 4) for k, v in sm.items()}
        base[rule] = sm
        rows.append({"rule": name, **sm})
        wins_first[rule] = win[0]
        print(rule, round(time.time() - T0, 1), flush=True)
    out["base"] = base
    pd.DataFrame(rows).to_csv(RES / "base_rules.csv", index=False)
    # 式：①では1口あたりの見込みがほぼ同じなので、1人あたり＝席÷人数
    out["formula_entry_rule_person_pct"] = r(S / PEOPLE * 100, 3)
    out["formula_two_solo_both_entry_pct"] = r((S / PEOPLE) ** 2 * 100, 3)
    out["formula_two_solo_any_entry_pct"] = r((1 - (1 - S / PEOPLE) ** 2) * 100, 3)

    # data：1回目の抽選の申し込みと当たり
    pd.DataFrame({"entry_id": np.arange(1, len(size) + 1), "people": size,
                  "win_rule_entry": wins_first["entry"].astype(int),
                  "win_rule_people": wins_first["people"].astype(int)}).to_csv(DATA / "entries_draw1.csv", index=False)

    # (3) 確かめ
    grid = []
    for seats in [10, 200]:
        for ratio in [2, 5, 10, 30]:
            for q in [0.1, 0.4, 0.7]:
                people = seats * ratio
                sz, ns, npair = make_entries(people, q)
                reps = 20000 if seats == 10 else 3000
                for rule, name in RULES.items():
                    win = draw(rng, sz, seats, rule, reps)
                    sm = summarize(win, sz, ns, seats)
                    grid.append({"seats": seats, "ratio_by_people": ratio, "pair_share_people": q, "rule": rule,
                                 "rule_name": name, "reps": reps, "seats_over_people_pct": r(seats / people * 100, 3),
                                 **{k: r(v, 3 if k.endswith("_pct") else 4) for k, v in sm.items()}})
        print("grid", seats, round(time.time() - T0, 1), flush=True)
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    gs = {}
    for rule in RULES:
        x = g[g.rule == rule]
        gs[rule] = {"pair_over_solo_min": r(x.pair_over_solo.min()), "pair_over_solo_max": r(x.pair_over_solo.max()),
                    "n_cases": int(len(x)), "n_pair_higher": int((x.pair_over_solo > 1).sum()),
                    "p_solo_over_formula_min": r((x.p_solo_person_pct / x.seats_over_people_pct).min()),
                    "p_solo_over_formula_max": r((x.p_solo_person_pct / x.seats_over_people_pct).max()),
                    "p_pair_over_formula_min": r((x.p_pair_person_pct / x.seats_over_people_pct).min()),
                    "p_pair_over_formula_max": r((x.p_pair_person_pct / x.seats_over_people_pct).max())}
        for seats in [10, 200]:
            y = x[x.seats == seats]
            gs[rule][f"seats{seats}_pair_over_solo_min"] = r(y.pair_over_solo.min())
            gs[rule][f"seats{seats}_pair_over_solo_max"] = r(y.pair_over_solo.max())
    # ①で、組がいちばん不利な場合
    x = g[g.rule == "entry"].sort_values("pair_over_solo").iloc[0]
    gs["entry_worst_case"] = {k: (r(v) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (int, np.integer)) else v))
                              for k, v in x.to_dict().items()}
    x = g[g.rule == "people"].sort_values("pair_over_solo").iloc[-1]
    gs["people_max_case"] = {k: (r(v) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (int, np.integer)) else v))
                             for k, v in x.to_dict().items()}
    out["grid_summary"] = gs
    out["run_sec_main"] = None

    # 図1：1人あたりの当たる見込み
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xs = np.arange(2)
    for i, (key, col, lab) in enumerate([("p_solo_person_pct", BLUE, "1人で申し込んだ人"), ("p_pair_person_pct", ORANGE, "2人1組で申し込んだ人")]):
        vals = [base[k][key] for k in RULES]
        bars = ax.bar(xs + (i - 0.5) * 0.36, vals, 0.34, color=col, label=lab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.3f}%", ha="center", fontsize=9.5)
    ax.axhline(S / PEOPLE * 100, color=GRAY, ls="--", lw=1)
    ax.text(1.62, S / PEOPLE * 100 + 0.3, "席÷人数 10%", color=GRAY, fontsize=9, ha="right")
    ax.set_xticks(xs, [RULES[k] for k in RULES])
    ax.set_ylim(0, 21)
    ax.set_ylabel("1人あたりの当たる見込み（%）")
    ax.set_title(f"①では1人も組もほぼ同じ、②では組の人が1人の人の{base['people']['pair_over_solo']}倍")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1176_per_person.png", SRC + "。席200・申し込む人2,000人・組の人40%、各4,000回")

    # 図2：2人でそろって行ける・どちらかが行ける
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    labs = ["組で申し込み\n（そろって当たる）", "別々に1人ずつ\n（2人とも当たる）", "別々に1人ずつ\n（どちらかが当たる）"]
    for i, (rule, col) in enumerate([("entry", BLUE), ("people", ORANGE)]):
        vals = [base[rule]["p_pair_person_pct"], base[rule]["two_solo_both_pct"], base[rule]["two_solo_any_pct"]]
        bars = ax.bar(np.arange(3) + (i - 0.5) * 0.36, vals, 0.34, color=col, label=RULES[rule])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.3f}%", ha="center", fontsize=9)
    ax.set_xticks(np.arange(3), labs)
    ax.set_ylim(0, 22)
    ax.set_ylabel("割合（%）")
    ax.set_title("同じ2人でも、何を「当たり」と数えるかで値が変わる")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1176_two_people.png", SRC + "。別々は1人の申し込みどうしを2件ずつ組にして数えた")

    # 図3：確かめ（組の人÷1人の人）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0), sharey=True)
    for ax, rule in zip(axes, RULES):
        for seats, ls in [(200, "-"), (10, "--")]:
            for ratio, col in zip([2, 5, 10, 30], [GREEN, BLUE, ORANGE, INK]):
                y = g[(g.rule == rule) & (g.seats == seats) & (g.ratio_by_people == ratio)].sort_values("pair_share_people")
                ax.plot(y.pair_share_people * 100, y.pair_over_solo, ls=ls, marker="o", ms=4, color=col,
                        label=f"倍率{ratio}倍・席{seats}")
        ax.axhline(1, color=GRAY, lw=0.8)
        ax.set_title(RULES[rule])
        ax.set_xlabel("組で申し込む人の割合（%）")
        ax.set_xticks([10, 40, 70])
        ax.set_ylim(0, 2.1)
    axes[0].set_ylabel("組の人の見込み ÷ 1人の人の見込み")
    axes[1].legend(frameon=False, fontsize=7.5, ncol=2, loc="lower right")
    fig.suptitle("決まり②では組の人がいつも上、①では席が少ないと組の人がやや下", fontsize=12, y=1.04)
    save(fig, "a1176_grid.png", SRC + "。24通り×2つの決まり（席200は各3,000回、席10は各20,000回）")

    out["run_sec"] = r(time.time() - T0, 1)
    out.pop("run_sec_main")
    out.pop("run_sec")
    with open(RES / "a1176_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("done", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
