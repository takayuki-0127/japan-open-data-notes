"""858 締め切り直前に作業が集まると、品質の点検は何件漏れるのか？（架空のデータ）

架空のプロジェクト。作り手が20日間で60件の成果物（資料の章・画面など）を作り、1件ずつ点検に回す。
点検する人は1日に C 件（基本4件、20日で80件分）を、来た順に見る。点検では、入っていた不具合の9割が見つかる。
成果物が仕上がる時刻の分布を変え、「最後の4日（全体の2割）に仕上がる割合」が20%（ならす）〜80%（直前に集まる）で、
締め切りの時点で点検されずに出る件数・見逃される不具合の件数を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 858
SRC = "架空のプロジェクトの成果物と点検（作成者が乱数で作成、seed 858）"
N_ITEM, DAYS, CAP, P_DEF, P_DETECT = 60, 20, 4.0, 0.2, 0.9
SHARES = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
REPS = 4000


def beta_a(share):
    """仕上がり時刻 t/DAYS ~ Beta(a,1)。最後の2割に入る割合が share になる a"""
    return float(np.log(1 - share) / np.log(0.8))


def finish_times(rng, share, n=N_ITEM):
    return np.sort(rng.beta(beta_a(share), 1.0, n) * DAYS)


def run_queue(t, cap):
    """来た順に1件 1/cap 日で点検。締め切り（DAYS）までに点検が終わった件を checked=True"""
    done = np.empty_like(t)
    free = 0.0
    for i, x in enumerate(t):
        free = max(free, x) + 1.0 / cap
        done[i] = free
    return done <= DAYS + 1e-12


def run_rush(t, cap):
    """持ち越さず、その日に仕上がった分はその日に全部見る。多い日は1件の時間が短くなり、見つかる割合が下がる"""
    day = np.minimum(t.astype(int), DAYS - 1)
    n_d = np.bincount(day, minlength=DAYS)
    return P_DETECT * np.minimum(1.0, cap / n_d[day])


def one(rng, share, cap=CAP, p_def=P_DEF, mode="queue"):
    t = finish_times(rng, share)
    bad = rng.random(N_ITEM) < p_def
    if mode == "queue":
        chk = run_queue(t, cap)
        found = bad & chk & (rng.random(N_ITEM) < P_DETECT)
        unchecked = int((~chk).sum())
    else:
        p = run_rush(t, cap)
        found = bad & (rng.random(N_ITEM) < p)
        unchecked = 0
    return {"unchecked": unchecked, "defects": int(bad.sum()), "leaked": int((bad & ~found).sum()),
            "last4_share": float((t >= DAYS * 0.8).mean())}


def summarize(rows):
    d = pd.DataFrame(rows)
    return {"unchecked_mean": round(float(d.unchecked.mean()), 2),
            "unchecked_p90": float(d.unchecked.quantile(.9)),
            "defects_mean": round(float(d.defects.mean()), 2),
            "leaked_mean": round(float(d.leaked.mean()), 2),
            "leaked_p90": float(d.leaked.quantile(.9)),
            "leak_rate": round(float(d.leaked.sum() / d.defects.sum()), 3),
            "p_leak_ge3": round(float((d.leaked >= 3).mean()), 3),
            "last4_share_obs": round(float(d.last4_share.mean()), 3)}


def main():
    rng = np.random.default_rng(SEED)
    # 1回分の仕上がり時刻（ならす20%・直前60%）
    one_rows = []
    for sh in [0.2, 0.6]:
        t = finish_times(rng, sh)
        chk = run_queue(t, CAP)
        for i, (x, c) in enumerate(zip(t, chk)):
            one_rows.append({"share_last4": sh, "item": i + 1, "finish_day": round(float(x), 3), "checked": int(c)})
    pd.DataFrame(one_rows).to_csv(DATA / "one_project_items.csv", index=False)

    # 2) 基本：仕上がりの集まり方 × 点検のしかた（REPS回）
    base = []
    for mode in ["queue", "rush"]:
        for sh in SHARES:
            r = np.random.default_rng(SEED * 100 + int(sh * 100) + (0 if mode == "queue" else 7))
            s = summarize([one(r, sh, mode=mode) for _ in range(REPS)])
            base.append({"mode": mode, "share_last4": sh, **s})
    base = pd.DataFrame(base)
    base.to_csv(RES / "by_share_mode.csv", index=False)

    # 3) 確かめ：点検の力 C × 集まり方（来た順・未点検で出る）
    rob = []
    for cap in [3.0, 3.5, 4.0, 5.0, 6.0, 8.0]:
        for sh in [0.2, 0.4, 0.6, 0.8]:
            r = np.random.default_rng(SEED * 1000 + int(cap * 10) * 10 + int(sh * 10))
            s = summarize([one(r, sh, cap=cap) for _ in range(REPS)])
            rob.append({"cap_per_day": cap, "cap_total": cap * DAYS, "share_last4": sh, **s})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness_cap.csv", index=False)

    # 4) 確かめ：不具合の入る割合
    rob2 = []
    for pd_ in [0.1, 0.2, 0.3]:
        for sh in [0.2, 0.6]:
            r = np.random.default_rng(SEED * 3 + int(pd_ * 100) + int(sh * 1000))
            s = summarize([one(r, sh, p_def=pd_) for _ in range(REPS)])
            rob2.append({"p_defect": pd_, "share_last4": sh, **s})
    rob2 = pd.DataFrame(rob2)
    rob2.to_csv(RES / "robustness_defect_rate.csv", index=False)

    o1 = pd.DataFrame(one_rows)
    one_unchecked = {str(sh): int((o1[o1.share_last4 == sh].checked == 0).sum()) for sh in [0.2, 0.6]}
    out = {"one_project_unchecked": one_unchecked, "setting": {"items": N_ITEM, "days": DAYS, "cap_per_day": CAP, "p_defect": P_DEF,
                       "p_detect": P_DETECT, "reps": REPS,
                       "beta_a": {str(s): round(beta_a(s), 3) for s in SHARES}},
           "base": base.to_dict("records"), "robust_cap": rob.to_dict("records"),
           "robust_defect_rate": rob2.to_dict("records")}
    json.dump(out, open(RES / "a858_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の仕上がり（1日ごとの件数）と点検の力
    o = pd.DataFrame(one_rows)
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6), sharey=True)
    for ax, sh, ttl in zip(axes, [0.2, 0.6], ["ならして仕上げる（最後の4日に20%）", "直前に集まる（最後の4日に60%）"]):
        g = o[o.share_last4 == sh]
        d = np.minimum(g.finish_day.astype(int), DAYS - 1)
        ok = np.bincount(d[g.checked == 1], minlength=DAYS)
        ng = np.bincount(d[g.checked == 0], minlength=DAYS)
        x = np.arange(1, DAYS + 1)
        ax.bar(x, ok, color=BLUE, label="締め切りまでに点検できた")
        ax.bar(x, ng, bottom=ok, color=ORANGE, label="点検されずに出た")
        ax.axhline(CAP, color=INK, lw=1, ls="--")
        ax.text(8.6 if sh == 0.2 else 0.6, CAP + 0.3, "点検の力（1日4件）", fontsize=8.5)
        ax.set_title(f"{ttl}\n未点検 {int(ng.sum())}件", fontsize=11)
        ax.set_xlabel("仕上がった日")
    axes[0].set_ylabel("仕上がった件数（60件中）")
    axes[1].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("1回分の例：仕上がりが直前に集まると、点検が追いつかない", fontsize=12, y=1.04)
    save(fig, "a858_one_project.png", SRC)

    # 図2：集まり方と見逃される不具合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for mode, col, lab in [("queue", ORANGE, "来た順に見て、見きれない分は未点検で出す"),
                           ("rush", BLUE, "その日の分は全部見る（多い日は急いで見る）")]:
        g = base[base["mode"] == mode]
        ax.plot(g.share_last4 * 100, g.leaked_mean, "o-", color=col, label=lab)
    ax.axhline(base.iloc[0].defects_mean, color=GRAY, lw=1, ls=":")
    ax.text(20, base.iloc[0].defects_mean + 0.25, f"入っていた不具合（平均{base.iloc[0].defects_mean:.1f}件）", fontsize=8.5, color=GRAY)
    ax.set_xlabel("最後の4日（全体の2割）に仕上がった割合（%）"); ax.set_ylabel("見逃された不具合（件、4,000回の平均）")
    ax.set_ylim(0, 13.5); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("仕上がりが直前に集まるほど、見逃しは増える（点検の力は全体で80件分）")
    save(fig, "a858_leak_by_share.png", SRC)

    # 図3：点検の力を変えると
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cols = {0.2: LIGHT, 0.4: BLUE, 0.6: ORANGE, 0.8: INK}
    for sh in [0.2, 0.4, 0.6, 0.8]:
        g = rob[rob.share_last4 == sh]
        ax.plot(g.cap_total, g.unchecked_mean, "o-", color=cols[sh], label=f"最後の4日に{int(sh*100)}%")
    ax.axvline(N_ITEM, color=GRAY, lw=1, ls=":"); ax.text(62, 33, "成果物60件", fontsize=8.5, color=GRAY)
    ax.set_xlabel("20日間の点検の力（件分）"); ax.set_ylabel("点検されずに出た件数（平均）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("点検の力を足しても、直前に集まる分は残る")
    save(fig, "a858_capacity.png", SRC)
    print(base.to_string()); print(rob.to_string()); print(rob2.to_string())


if __name__ == "__main__":
    main()
