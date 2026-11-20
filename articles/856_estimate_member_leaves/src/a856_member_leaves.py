"""856 担当者が1人抜けると、締め切りはどれだけ延びるのか？（架空のデータ）

架空のプロジェクト。担当者 n 人が、それぞれ自分の受け持ち（作業12件ずつ）を持つ。作業の長さは対数正規分布（平均4日）。
手の空いた人は、自分の受け持ちに残りがあればそれを、なければ残りのいちばん多い他人の受け持ちを手伝う（慣れない作業は m 倍かかる）。
途中（抜けない場合に終わる日の f の時点）で1人が抜ける。抜けた人の受け持ちは、残りの人が慣れない作業として m 倍の時間で引き取る。
抜けた人が途中まで進めた作業は、進んだ分を残し、引き継ぎに h 日を足す。
「単純な割り算」の延び＝抜けた時点の残りの作業量 R を (n−1) 人で割った日数 − n 人で割った日数 と比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 856
SRC = "架空のプロジェクトの作業（作成者が乱数で作成、seed 856）"
PER, MEAN_DAYS, SIGMA = 12, 4.0, 0.6
REPS = 1000


def make_tasks(rng, n):
    mu = np.log(MEAN_DAYS) - SIGMA ** 2 / 2
    return [list(rng.lognormal(mu, SIGMA, PER)) for _ in range(n)]


def simulate(tasks, n, leave_at=None, m=1.3, h=3.0, policy="own_first", log=None):
    """作業を進めて、全部が終わる日を返す。leave_at：抜ける日（None なら抜けない）。抜けるのは担当0。"""
    queue = [list(t) for t in tasks]  # 受け持ちごとの、まだ始めていない作業（標準の日数）
    busy = [0.0] * n                   # 手が空く日
    cur = [None] * n                   # (受け持ち, 標準の日数, 始めた日, かかる日数)
    active = [True] * n
    left_handover = False              # 引き継ぎの h 日を、抜けた人の受け持ちの最初の作業に足したか
    t, gone = 0.0, leave_at is None
    remaining_at_leave = None
    while True:
        # 手の空いた人に作業を割り当てる
        for p in range(n):
            if not active[p] or busy[p] > t + 1e-12:
                continue
            if cur[p] is not None and log is not None:
                log.append(cur[p] + (p,))
            cur[p] = None
            own_left = [a for a in range(n) if queue[a]]
            if not own_left:
                continue
            if policy == "handover_first" and not active[0] and queue[0]:
                a = 0
            elif active[p] and queue[p] and (p != 0 or active[0]):
                a = p
            else:
                a = max(own_left, key=lambda k: sum(queue[k]))
            x = queue[a].pop(0)
            mult = 1.0 if (a == p and active[a]) else m
            dur = x * mult
            if a == 0 and not active[0] and not left_handover:
                dur += h; left_handover = True
            cur[p] = (a, x, t, dur)
            busy[p] = t + dur
        running = [busy[p] for p in range(n) if active[p] and cur[p] is not None]
        if not running and not any(queue):
            return t, remaining_at_leave
        nxt = min(running) if running else t
        if not gone and leave_at <= nxt:
            t = leave_at
            gone = True
            active[0] = False
            if cur[0] is not None:  # 途中の作業は進んだ分を残して受け持ちに戻す
                a, x, s, dur = cur[0]
                done_frac = (t - s) / dur
                if log is not None:
                    log.append((a, x * done_frac, s, t - s, 0))
                queue[a].insert(0, x * (1 - done_frac))
                cur[0] = None
            # 抜けた時点の残りの作業量（標準の日数。走っている作業は残りの分）
            rem = sum(sum(q) for q in queue)
            for p in range(1, n):
                if cur[p] is not None:
                    a, x, s, dur = cur[p]
                    rem += x * (busy[p] - t) / dur
            remaining_at_leave = rem
            continue
        t = nxt


def one(rng, n=5, f=0.5, m=1.3, h=3.0, policy="own_first"):
    tasks = make_tasks(rng, n)
    base, _ = simulate(tasks, n, None, m, h)
    fin, rem = simulate(tasks, n, f * base, m, h, policy)
    naive = rem / (n - 1) - rem / n
    return {"base": base, "finish": fin, "ext": fin - base, "naive_ext": naive, "remaining": rem}


def summ(rows):
    d = pd.DataFrame(rows)
    return {"base_days_mean": round(float(d.base.mean()), 1), "ext_mean": round(float(d.ext.mean()), 1),
            "ext_p10": round(float(d.ext.quantile(.1)), 1), "ext_p90": round(float(d.ext.quantile(.9)), 1),
            "naive_ext_mean": round(float(d.naive_ext.mean()), 1),
            "ratio_mean_ext_to_naive": round(float(d.ext.mean() / d.naive_ext.mean()), 2),
            "ext_pct_of_plan": round(float((d.ext / d.base).mean() * 100), 1)}


def main():
    rng = np.random.default_rng(SEED)

    # 1) 抜ける時点ごと（5人・m=1.3・h=3日、各1000回）
    main_rows = []
    for f in [0.2, 0.5, 0.8]:
        s = summ([one(rng, 5, f) for _ in range(REPS)])
        main_rows.append({"leave_at": f, **s})
    main_df = pd.DataFrame(main_rows)
    main_df.to_csv(RES / "by_leave_time.csv", index=False)

    # 2) 確かめ：慣れない作業の倍率 m × 引き継ぎの日数 h（5人・半分の時点、各500回）
    rob = []
    for m in [1.0, 1.3, 1.6]:
        for h in [0.0, 3.0, 6.0]:
            s = summ([one(rng, 5, 0.5, m, h) for _ in range(500)])
            rob.append({"m": m, "h": h, **s})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness_m_h.csv", index=False)

    # 3) 確かめ：人数（m=1.3・h=3日、各500回）
    team = []
    for n in [3, 5, 8]:
        for f in [0.2, 0.5, 0.8]:
            s = summ([one(rng, n, f) for _ in range(500)])
            team.append({"team": n, "leave_at": f, **s})
    team = pd.DataFrame(team)
    team.to_csv(RES / "robustness_team.csv", index=False)

    # 4) 確かめ：引き取り方（自分の受け持ちを先に／抜けた人の受け持ちを先に）、5人・半分の時点・m=1.3・h=3、各1000回
    pol = []
    for name, pl in [("自分の受け持ちを先に", "own_first"), ("抜けた人の受け持ちを先に", "handover_first")]:
        r = np.random.default_rng(SEED * 3)  # 同じ作業で比べる
        s = summ([one(r, 5, 0.5, policy=pl) for _ in range(REPS)])
        pol.append({"policy": name, **s})
    pol = pd.DataFrame(pol)
    pol.to_csv(RES / "policy.csv", index=False)

    # 1回分の記録（5人・半分の時点で担当1が抜ける）
    r1 = np.random.default_rng(SEED * 10)
    tasks = make_tasks(r1, 5)
    lb, la = [], []
    base, _ = simulate(tasks, 5, None, log=lb)
    fin, rem = simulate(tasks, 5, 0.5 * base, log=la)
    rows = []
    for tag, lg in [("抜けない", lb), ("半分で1人抜ける", la)]:
        for a, x, s, dur, p in lg:
            rows.append({"case": tag, "person": p + 1, "area": a + 1, "std_days": x, "start": s, "days": dur})
    pd.DataFrame(rows).to_csv(DATA / "one_run_log.csv", index=False, float_format="%.3f")
    one_run = {"base": round(base, 1), "finish": round(fin, 1), "ext": round(fin - base, 1),
               "naive_ext": round(rem / 4 - rem / 5, 1), "remaining_at_leave": round(rem, 1)}

    out = {"by_leave_time": main_rows, "robustness_m_h": rob.to_dict("records"),
           "robustness_team": team.to_dict("records"), "policy": pol.to_dict("records"), "one_run": one_run}
    json.dump(out, open(RES / "a856_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：抜ける時点ごとの延び（単純な割り算と比べる）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(3)
    ax.bar(x - 0.18, main_df.naive_ext_mean, 0.36, color=GRAY, label="単純な割り算（残り÷4人 − 残り÷5人）")
    ax.bar(x + 0.18, main_df.ext_mean, 0.36, color=BLUE, label="作業を動かして数えた延び（1,000回の平均）")
    ax.errorbar(x + 0.18, main_df.ext_mean, yerr=[main_df.ext_mean - main_df.ext_p10, main_df.ext_p90 - main_df.ext_mean],
                fmt="none", ecolor=INK, lw=1, capsize=3)
    for i, (a, b) in enumerate(zip(main_df.naive_ext_mean, main_df.ext_mean)):
        ax.text(i - 0.18, 0.4, f"{a:.1f}日", ha="center", fontsize=9, color="white")
        ax.text(i + 0.18, 0.4, f"{b:.1f}日", ha="center", fontsize=9, color="white")
    ax.set_xticks(x); ax.set_xticklabels(["2割の時点で抜ける", "半分の時点で抜ける", "8割の時点で抜ける"])
    ax.set_ylabel("終わる日の延び（日）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("1人抜けたときの延びは、単純な割り算より大きい（5人・12件ずつ）")
    save(fig, "a856_by_time.png", SRC + "。慣れない作業1.3倍・引き継ぎ3日。ひげは10〜90%")

    # 図2：m × h
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for h, c in zip([0.0, 3.0, 6.0], [LIGHT, BLUE, INK]):
        g = rob[rob.h == h]
        ax.plot(g.m, g.ratio_mean_ext_to_naive, "o-", color=c, label=f"引き継ぎ {h:.0f}日")
    ax.axhline(1, color=GRAY, lw=.8, ls=":"); ax.text(1.6, 0.93, "単純な割り算と同じ", color=GRAY, fontsize=9, ha="right", va="top")
    ax.set_xticks([1.0, 1.3, 1.6]); ax.set_xticklabels(["1.0倍（慣れの差なし）", "1.3倍", "1.6倍"])
    ax.set_xlabel("慣れない作業にかかる時間の倍率"); ax.set_ylabel("延び ÷ 単純な割り算の延び")
    ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, None)
    ax.set_title("延びが単純な割り算の何倍になるかは、慣れと引き継ぎの置き方で決まる")
    save(fig, "a856_m_h.png", SRC + "。5人・半分の時点で1人抜ける、各500回の平均")

    # 図3：1回分の担当ごとの作業（抜けない／抜ける）
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True)
    for ax, (tag, lg, endt) in zip(axes, [("抜けない", lb, base), ("半分の時点で担当1が抜ける", la, fin)]):
        for a, xx, s, dur, p in lg:
            col = BLUE if a == p else ORANGE
            if a == 0 and tag != "抜けない" and s >= 0.5 * base - 1e-9:
                col = ORANGE
            ax.barh(p + 1, dur, left=s, color=col, edgecolor="white", lw=.5)
        ax.axvline(endt, color=INK, lw=1, ls="--"); ax.text(endt + 0.3, 0.6, f"{endt:.0f}日", fontsize=9)
        ax.set_yticks(range(1, 6)); ax.set_yticklabels([f"担当{k}" for k in range(1, 6)]); ax.invert_yaxis()
        ax.set_title(tag, fontsize=11, loc="left")
    axes[1].axvline(0.5 * base, color=ORANGE, lw=1, ls=":")
    axes[1].set_xlabel("日数（青：自分の受け持ち、橙：他人の受け持ちを手伝う・引き取る）")
    fig.suptitle("抜けた人の受け持ちは、残りの人が慣れない作業として引き取る（1回分）", fontsize=12)
    fig.tight_layout()
    save(fig, "a856_gantt.png", SRC + "。5人・12件ずつ・慣れない作業1.3倍・引き継ぎ3日")
    print("done")


if __name__ == "__main__":
    main()
