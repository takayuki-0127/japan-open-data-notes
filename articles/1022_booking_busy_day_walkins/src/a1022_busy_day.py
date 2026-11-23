"""1022 予約の多い日は、当日も多いのか？（架空のデータ）

架空の飲食店（48席・夜1回の営業）の2,100日（300週）。
予約の人数と、当日の予約なしの客（飛び込み）の来たい人数は、どちらも曜日と季節で動く。
予約は前もって入るので当日の天気に動かず、飛び込みは当日の天気で動く（作成者の置き方）。
曜日をそろえると、予約と飛び込みをつなぐのは季節だけ。
席が埋まると飛び込みは断るので、記録に残る「座れた飛び込み」は来たい人数より少ない。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1022
SRC = "架空の飲食店の予約と来店（作成者が乱数で作成、seed 1022）"
N_DAYS = 2100
WD = ["月", "火", "水", "木", "金", "土", "日"]
BASE_B = np.array([14, 14, 14, 14, 28, 34, 22], float)     # 予約の人数の平均（曜日ごと）
BASE_W = np.array([9, 9, 9, 9, 16, 18, 13], float)         # 飛び込みの来たい人数の平均
SHOW = 0.92                                               # 予約した人が来る割合


def contrast(base, k):
    """曜日の差を k 倍にする（平均は同じ）"""
    m = base.mean()
    return np.clip(m + (base - m) * k, 1, None)


def simulate(rng, seats=48, season_amp=0.15, wd_k=1.0, n=N_DAYS):
    day = np.arange(n)
    wd = day % 7
    season = season_amp * np.sin(2 * np.pi * day / 364)
    lam_b = contrast(BASE_B, wd_k)[wd] * np.exp(season + rng.normal(0, 0.15, n))
    lam_w = contrast(BASE_W, wd_k)[wd] * np.exp(season + rng.normal(0, 0.25, n))
    b = np.minimum(rng.poisson(lam_b), seats)                 # 席の数を超える予約は受けない
    arrived = rng.binomial(b, SHOW)
    w_demand = rng.poisson(lam_w)
    w_seated = np.minimum(w_demand, seats - arrived)
    return pd.DataFrame({"day": day + 1, "weekday": [WD[i] for i in wd], "wd": wd, "booked": b,
                         "booked_arrived": arrived, "walkin_demand": w_demand, "walkin_seated": w_seated,
                         "turned_away": w_demand - w_seated})


def within(df, col):
    """曜日ごとの平均を引いた値"""
    return df[col] - df.groupby("wd")[col].transform("mean")


def corrs(df):
    r = lambda a, b: float(np.corrcoef(a, b)[0, 1])
    return {"raw_seated": r(df.booked, df.walkin_seated),
            "raw_demand": r(df.booked, df.walkin_demand),
            "within_seated": r(within(df, "booked"), within(df, "walkin_seated")),
            "within_demand": r(within(df, "booked"), within(df, "walkin_demand"))}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    df = simulate(rng)
    df.drop(columns="wd").to_csv(DATA / "days.csv", index=False)
    out = {}
    c = corrs(df)
    out["base_corr"] = {k: round(v, 3) for k, v in c.items()}

    # 予約の多い4分の1の日と少ない4分の1の日：座れた飛び込みの平均
    q = df.booked.rank(pct=True)
    qw = df.groupby("wd").booked.rank(pct=True)               # 同じ曜日の中での順位
    def topbot(rank):
        top, bot = df[rank > 0.75], df[rank <= 0.25]
        return {"top_seated": round(float(top.walkin_seated.mean()), 2), "bottom_seated": round(float(bot.walkin_seated.mean()), 2),
                "top_demand": round(float(top.walkin_demand.mean()), 2), "bottom_demand": round(float(bot.walkin_demand.mean()), 2),
                "top_turned_away": round(float(top.turned_away.mean()), 2), "bottom_turned_away": round(float(bot.turned_away.mean()), 2)}
    out["quartiles_all_days"] = topbot(q)
    out["quartiles_same_weekday"] = topbot(qw)

    # 曜日ごと
    rows = []
    for i, w in enumerate(WD):
        g = df[df.wd == i]
        rows.append({"weekday": w, "days": int(len(g)), "booked_mean": round(g.booked.mean(), 2),
                     "walkin_demand_mean": round(g.walkin_demand.mean(), 2), "walkin_seated_mean": round(g.walkin_seated.mean(), 2),
                     "days_with_turned_away_pct": round((g.turned_away > 0).mean() * 100, 1),
                     "corr_seated": round(float(np.corrcoef(g.booked, g.walkin_seated)[0, 1]), 3),
                     "corr_demand": round(float(np.corrcoef(g.booked, g.walkin_demand)[0, 1]), 3)})
    wdt = pd.DataFrame(rows)
    wdt.to_csv(RES / "by_weekday.csv", index=False)
    out["by_weekday"] = wdt.to_dict("records")

    # 回帰の傾き：予約が1人多い日は、座れた飛び込みが何人多いか
    def slope(x, y): return float(np.polyfit(x, y, 1)[0])
    out["slope_raw_seated"] = round(slope(df.booked, df.walkin_seated), 3)
    out["slope_within_seated"] = round(slope(within(df, "booked"), within(df, "walkin_seated")), 3)
    out["slope_within_demand"] = round(slope(within(df, "booked"), within(df, "walkin_demand")), 3)

    # 季節の振れがないときの「本当のつながり」0 の確かめ（同じ置き方で季節だけ0）
    c0 = corrs(simulate(np.random.default_rng(SEED + 1), season_amp=0.0))
    out["season0_corr"] = {k: round(v, 3) for k, v in c0.items()}

    # 確かめ：席の数×季節の振れ×曜日の差（27通り）
    grid = []
    for seats in [36, 48, 72]:
        for amp in [0.0, 0.15, 0.3]:
            for k in [0.0, 1.0, 1.5]:
                g = simulate(np.random.default_rng(SEED * 100 + len(grid)), seats, amp, k)
                cc = corrs(g)
                grid.append({"seats": seats, "season_amp": amp, "weekday_k": k,
                             **{kk: round(v, 3) for kk, v in cc.items()},
                             "days_with_turned_away_pct": round(float((g.turned_away > 0).mean() * 100), 1)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    gk = grid[grid.weekday_k > 0]
    out["grid"] = {
        "n_cases": int(len(grid)),
        "raw_seated_range": [float(grid.raw_seated.min()), float(grid.raw_seated.max())],
        "raw_seated_range_with_weekday": [float(gk.raw_seated.min()), float(gk.raw_seated.max())],
        "within_seated_range": [float(grid.within_seated.min()), float(grid.within_seated.max())],
        "within_demand_range": [float(grid.within_demand.min()), float(grid.within_demand.max())],
        "raw_gt_within_seated_cases": int((grid.raw_seated > grid.within_seated).sum()),
        "with_weekday_cases": int(len(gk)),
        "raw_gt_within_seated_with_weekday": int((gk.raw_seated > gk.within_seated).sum()),
        "raw_seated_by_seats": {str(s_): [float(g.raw_seated.min()), float(g.raw_seated.max())] for s_, g in grid.groupby("seats")},
        "within_seated_lt_within_demand_cases": int((grid.within_seated < grid.within_demand).sum()),
        "within_seated_negative_cases": int((grid.within_seated < 0).sum()),
        "within_demand_by_amp": {str(a): [float(g.within_demand.min()), float(g.within_demand.max())]
                                 for a, g in grid.groupby("season_amp")},
        "within_seated_by_seats": {str(s): [float(g.within_seated.min()), float(g.within_seated.max())]
                                   for s, g in grid.groupby("seats")},
    }
    run_sec = round(time.time() - t0, 1)
    json.dump(out, open(RES / "a1022_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：予約の人数と座れた飛び込み（曜日で色分け）
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    jit = np.random.default_rng(1).uniform(-.3, .3, (2, len(df)))
    groups = [([0, 1, 2, 3], "月〜木", GRAY), ([6], "日", LIGHT), ([4], "金", BLUE), ([5], "土", ORANGE)]
    for ids, nm, col in groups:
        m = df.wd.isin(ids)
        ax.scatter(df.booked[m] + jit[0][m], df.walkin_seated[m] + jit[1][m], s=5, color=col, alpha=.45, lw=0, label=nm)
    ax.set_xlabel("予約の人数"); ax.set_ylabel("座れた飛び込みの人数")
    ax.legend(frameon=False, fontsize=9, markerscale=3, title="曜日", title_fontsize=9, loc="upper left")
    ax.set_title(f"全部の日の相関は{c['raw_seated']:.2f}。同じ曜日どうしでは{c['within_seated']:.2f}".replace("-", "−"))
    save(fig, "a1022_scatter.png", SRC)

    # 図2：4つの相関
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    labs = ["全部の日・座れた飛び込み", "全部の日・来たい人数（断った人も）", "同じ曜日・座れた飛び込み", "同じ曜日・来たい人数（断った人も）"]
    vals = [c["raw_seated"], c["raw_demand"], c["within_seated"], c["within_demand"]]
    cols = [GRAY, GRAY, BLUE, LIGHT]
    ax.barh(labs[::-1], vals[::-1], color=cols[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + (0.02 if v >= 0 else -0.02), i, f"{v:.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
    ax.axvline(0, color=INK, lw=.8); ax.set_xlim(-0.6, 1)
    ax.set_xlabel("予約の人数との相関（2,100日）")
    ax.set_title("曜日をそろえると、座れた飛び込みとの相関は負になる")
    save(fig, "a1022_corrs.png", SRC, y=-0.07)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(grid))
    ax.scatter(x, grid.raw_seated, color=GRAY, s=22, label="全部の日・座れた飛び込み")
    ax.scatter(x, grid.within_seated, color=BLUE, s=22, label="同じ曜日・座れた飛び込み")
    ax.scatter(x, grid.within_demand, color=ORANGE, s=22, marker="^", label="同じ曜日・来たい人数（断った人も）")
    ax.axhline(0, color=INK, lw=.8)
    for i in [9, 18]:
        ax.axvline(i - .5, color=GRAY, lw=.6, ls=":")
    for i, s in enumerate([36, 48, 72]):
        ax.text(i * 9 + 4, 1.02, f"{s}席", ha="center", fontsize=9)
    ax.set_xticks(x, [f"{a:g}/{k:g}" for a, k in zip(grid.season_amp, grid.weekday_k)], rotation=90, fontsize=7)
    ax.set_xlabel("季節の振れ／曜日の差の倍率"); ax.set_ylabel("予約の人数との相関"); ax.set_ylim(-0.7, 1.08)
    ax.legend(frameon=False, fontsize=8, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.27))
    ax.set_title("27通り：席の数・季節の振れ・曜日の差を変えて", pad=16)
    save(fig, "a1022_grid.png", SRC, y=-0.2)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", run_sec)


if __name__ == "__main__":
    main()
