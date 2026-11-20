"""853 割り込みの仕事が1割あると、終わる日はどれだけ延びるのか？（架空のデータ）

架空のプロジェクト：集中して行う作業が40日分（1日8時間＝480分）。毎日、割り込みの仕事が入る。
1日の割り込みの回数はポアソン分布、1回の長さは指数分布。回数×長さの平均が1日48分（1割）になるように置く。
割り込みのあと作業に戻るまでの「切り替えの手間」を1回 s 分と置く。
その日のうちに終わらなかった割り込みは、翌日に回す（割り込みの仕事は必ず先に片付ける）。
"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 853
SRC = "架空のプロジェクト（作成者が乱数で作成、seed 853）"
DAY = 480.0
WORK_DAYS = 40
N_SIM = 20_000
MAX_DAYS = 160


def simulate(rng, per_day, share=0.10, switch=0.0, burst_cv=0.0, n=N_SIM, keep_log=False):
    mean_len = share * DAY / per_day
    lam = np.full((n, MAX_DAYS), per_day)
    if burst_cv > 0:  # 日ごとの忙しさの波（平均1）
        k = 1 / burst_cv ** 2
        lam = lam * rng.gamma(k, 1 / k, (n, MAX_DAYS))
    cnt = rng.poisson(lam)
    dur = rng.gamma(np.maximum(cnt, 1e-12), mean_len) * (cnt > 0)
    need = dur + cnt * switch               # その日に割り込みで取られる時間（分）
    focus = np.empty_like(need)
    back = np.zeros(n)                       # その日に終わらなかった割り込みは翌日に回す
    for t in range(MAX_DAYS):
        tot = back + need[:, t]
        used = np.minimum(tot, DAY)
        back = tot - used
        focus[:, t] = DAY - used
    cum = np.cumsum(focus, 1)
    target = WORK_DAYS * DAY
    idx = (cum < target).sum(1)              # 0始まりで、終わる日の番号
    prev = np.where(idx > 0, cum[np.arange(n), np.maximum(idx - 1, 0)], 0.0)
    frac = (target - prev) / np.maximum(focus[np.arange(n), idx], 1e-9)
    days = idx + frac
    if keep_log:
        return days, cnt[0], dur[0], focus[0]
    return days


def summarize(days):
    return {"mean": round(float(days.mean()), 2), "p50": round(float(np.median(days)), 2),
            "p90": round(float(np.quantile(days, 0.9)), 2),
            "delay_pct": round(float(days.mean() / WORK_DAYS - 1) * 100, 1),
            "ontime_44": round(float((days <= 44).mean()), 4), "ontime_44_4": round(float((days <= WORK_DAYS / 0.9).mean()), 4)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 回数と切り替えの手間を変える（割り込みの時間は1日48分＝1割で一定）
    rows = []
    for per_day in [0.5, 1, 2, 4, 8]:
        for sw in [0, 5, 15]:
            d = simulate(np.random.default_rng(SEED * 100 + int(per_day * 10) + sw * 1000), per_day, switch=sw)
            rows.append({"per_day": per_day, "mean_len_min": round(48 / per_day, 1), "switch_min": sw, **summarize(d)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "delay_by_count_switch.csv", index=False)

    # 理屈の値：1日の作業時間 = 480 - 48 - 回数×s
    theory = {f"{p}_{s}": round(WORK_DAYS * DAY / (DAY - 48 - p * s), 2) for p in [0.5, 1, 2, 4, 8] for s in [0, 5, 15]}

    # 2) 割り込みの割合を変える（1日4回、s=0 と 15分）
    share_rows = []
    for share in [0.05, 0.10, 0.20, 0.30]:
        for sw in [0, 15]:
            d = simulate(np.random.default_rng(SEED * 7 + int(share * 100) + sw), 4, share=share, switch=sw)
            share_rows.append({"share": share, "switch_min": sw, **summarize(d),
                               "naive_days": round(WORK_DAYS * (1 + share), 2)})
    share_df = pd.DataFrame(share_rows)
    share_df.to_csv(RES / "delay_by_share.csv", index=False)

    # 3) 確かめ：日ごとの忙しさの波（1日4回・s=15、波の大きさ CV 0・0.5・1・2）
    burst = []
    for cv in [0.0, 0.5, 1.0, 2.0]:
        d = simulate(np.random.default_rng(SEED * 11 + int(cv * 10)), 4, switch=15, burst_cv=cv)
        burst.append({"burst_cv": cv, **summarize(d)})
    burst_df = pd.DataFrame(burst)
    burst_df.to_csv(RES / "burst_check.csv", index=False)

    # 1回分の記録（1日4回・s=15）
    days, cnt, dur, focus = simulate(np.random.default_rng(SEED), 4, switch=15, n=1, keep_log=True)
    last = int(np.ceil(days[0]))
    log = pd.DataFrame({"day": np.arange(1, last + 1), "n_interrupt": cnt[:last], "interrupt_min": np.round(dur[:last], 1),
                        "switch_min": cnt[:last] * 15, "focus_min": np.round(focus[:last], 1)})
    log["cum_focus_days"] = np.round(np.cumsum(focus[:last]) / DAY, 3)
    log.to_csv(DATA / "one_project_4perday_switch15.csv", index=False)

    g = grid.set_index(["per_day", "switch_min"])
    out = {"setting": {"work_days": WORK_DAYS, "minutes_per_day": DAY, "interrupt_min_per_day": 48, "n_sim": N_SIM},
           "grid": rows, "theory_mean_days": theory, "by_share": share_rows, "burst_check": burst,
           "one_project": {"finish_days": round(float(days[0]), 2), "total_interrupts": int(cnt[:last].sum()),
                           "mean_interrupt_min_per_day": round(float(dur[:last].mean()), 1)},
           "headline": {"s0_mean": float(g.loc[(4, 0), "mean"]), "s15_4_mean": float(g.loc[(4, 15), "mean"]),
                        "s15_8_mean": float(g.loc[(8, 15), "mean"]), "s15_1_mean": float(g.loc[(1, 15), "mean"])}}
    json.dump(out, open(RES / "a853_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：回数と切り替えの手間ごとの延び
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(5); w = 0.26
    for i, (sw, col) in enumerate([(0, GRAY), (5, LIGHT), (15, BLUE)]):
        v = grid[grid.switch_min == sw].delay_pct.values
        ax.bar(x + (i - 1) * w, v, w, color=col, label=f"切り替えの手間 {sw}分")
        for xi, vi in zip(x + (i - 1) * w, v):
            ax.text(xi, vi + .6, f"{vi:.0f}", ha="center", fontsize=8)
    ax.axhline(10, color=ORANGE, lw=1, ls="--", label="「1割延びる」と見た線")
    ax.set_xticks(x, ["0.5回\n(96分)", "1回\n(48分)", "2回\n(24分)", "4回\n(12分)", "8回\n(6分)"])
    ax.set_xlabel("1日の割り込みの回数（かっこ内は1回の平均の長さ。合計はどれも1日48分）")
    ax.set_ylabel("40日分の作業が延びた割合（%、平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("割り込みの時間が同じ1割でも、細かく何度も入るほど延びる")
    save(fig, "a853_delay_bars.png", SRC, y=-0.07)

    # 図2：終わる日の分布（s=0・1日1回 と s=15・1日4回・8回）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bins = np.linspace(40, 70, 121)
    for (p, sw, col, lab) in [(1, 0, GRAY, "1日1回・切り替え0分"), (4, 15, BLUE, "1日4回・切り替え15分"),
                              (8, 15, ORANGE, "1日8回・切り替え15分")]:
        d = simulate(np.random.default_rng(SEED * 100 + int(p * 10) + sw * 1000), p, switch=sw)
        ax.hist(d, bins=bins, color=col, alpha=.6, density=True, label=lab)
    ax.axvline(44, color=INK, lw=1, ls="--"); ax.text(44.3, ax.get_ylim()[1] * .92, "44日（40日＋1割）", fontsize=9)
    ax.set_xlabel("40日分の作業が終わる日（日）"); ax.set_yticks([]); ax.legend(frameon=False, fontsize=9, loc="upper right")
    on1 = float(g.loc[(1, 0), "ontime_44"]) * 100
    ax.set_title(f"「40日＋1割＝44日」に間に合ったのは、1日1回・切り替え0分でも{on1:.0f}%")
    save(fig, "a853_finish_hist.png", SRC)

    # 図3：割り込みの割合と延び
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for sw, col in [(0, GRAY), (15, BLUE)]:
        s = share_df[share_df.switch_min == sw]
        ax.plot(s.share * 100, s.delay_pct, "o-", color=col, label=f"1日4回・切り替え{sw}分")
        for xs, ys in zip(s.share * 100, s.delay_pct):
            ax.text(xs, ys + 2, f"{ys:.0f}%", ha="center", fontsize=8.5, color=col)
    ax.plot([5, 10, 20, 30], [5, 10, 20, 30], ls="--", color=ORANGE, label="割り込みの割合と同じだけ延びる（素朴な見方）")
    ax.set_xlabel("割り込みの仕事が1日に占める割合（%）"); ax.set_ylabel("延びた割合（%、平均）")
    ax.set_xticks([5, 10, 20, 30]); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("割り込みが増えるほど、素朴な見方との差は開く")
    save(fig, "a853_share.png", SRC)
    print(json.dumps(out["headline"], ensure_ascii=False))
    print(grid.to_string()); print(share_df.to_string()); print(burst_df.to_string()); print(out["one_project"])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
