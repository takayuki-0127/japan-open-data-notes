"""1020 早く予約した人ほどキャンセルしやすいのか？（架空のデータ）

架空の宿の予約。予約は泊まる日の1〜90日前に入り、泊まる日の前日までの毎日、
「残り日数」で決まる確率で取り消される（泊まる日が近いほど取り消しやすい）。
早く予約した人（31〜90日前）だけ、その確率に倍率 m を掛ける（m=1 なら人による違いはない）。
同じ予約を、①予約1件あたりの取り消し率、②予約していた日数1日あたりの取り消し、
③残り日数をそろえた比べ方（泊まる日の1〜7日前の期間だけで1日あたり）の3つで比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1020
SRC = "架空の宿の予約（作成者が乱数で作成、seed 1020）"
MAXL = 90
DAYS = np.arange(1, MAXL + 1)
BINS = [(1, 7), (8, 30), (31, 60), (61, 90)]
BIN_NAMES = ["1〜7日前", "8〜30日前", "31〜60日前", "61〜90日前"]
EARLY_FROM = 31          # 31〜90日前を「早い予約」とする
WIN = 7                  # ③の期間：泊まる日の1〜7日前


def haz(shape):
    """残り d 日の日に取り消す確率（d=1..90）"""
    if shape == "flat":
        return np.full(MAXL, 0.0015)
    if shape == "steep":
        return 0.0004 + 0.02 * np.exp(-(DAYS - 1) / 3)
    return 0.0008 + 0.012 * np.exp(-(DAYS - 1) / 5)          # base


SHAPE_NAMES = {"flat": "残り日数によらず一定（1日0.15%）", "base": "基本（近いほど上がる）",
               "steep": "直前にもっと集まる"}


def lead_probs(mean):
    w = np.exp(-DAYS / mean)
    return w / w.sum()


def simulate(rng, n, m, shape="base", lead_mean=25):
    """取り消した日（残り日数、取り消さなければ0）を返す。あわせて日ごとの数を集める"""
    L = rng.choice(DAYS, size=n, p=lead_probs(lead_mean))
    mult = np.where(L >= EARLY_FROM, m, 1.0)
    h = haz(shape)
    cday = np.zeros(n, dtype=int)
    held = np.zeros(n, dtype=int)                 # 予約していた日数（取り消しの起こりえた日）
    win_hold = np.zeros(n, dtype=int)             # そのうち残り1〜7日の日数
    early, late = L >= EARLY_FROM, L <= WIN
    strat = []                                    # 残り日数ごとの、予約していた件数と取り消した件数
    for d in range(MAXL, 0, -1):
        risk = (L >= d) & (cday == 0)
        held += risk
        if d <= WIN:
            win_hold += risk
        u = rng.random(n)
        hit = risk & (u < mult * h[d - 1])
        cday[hit] = d
        if d <= WIN:
            strat.append((d, int((risk & early).sum()), int((hit & early).sum()),
                          int((risk & late).sum()), int((hit & late).sum())))
    df = pd.DataFrame({"lead_days": L, "cancel_day": cday, "held_days": held, "win_days": win_hold})
    df.attrs["strat"] = strat
    return df


def measures(df):
    """3つの物差し。早い予約（31〜90日前）÷遅い予約（1〜7日前）の比も返す"""
    c = df.cancel_day > 0
    rows = []
    for (a, b), nm in zip(BINS, BIN_NAMES):
        g = df[(df.lead_days >= a) & (df.lead_days <= b)]
        gc = g.cancel_day > 0
        win_c = ((g.cancel_day >= 1) & (g.cancel_day <= WIN)).sum()
        rows.append({"bin": nm, "bookings": int(len(g)), "cancel_rate": gc.mean(),
                     "per_day": gc.sum() / g.held_days.sum(),
                     "window_per_day": win_c / g.win_days.sum()})
    t = pd.DataFrame(rows)
    early = df[df.lead_days >= EARLY_FROM]
    late = df[df.lead_days <= WIN]
    def r1(g): return (g.cancel_day > 0).mean()
    def r2(g): return (g.cancel_day > 0).sum() / g.held_days.sum()
    def r3(g): return ((g.cancel_day >= 1) & (g.cancel_day <= WIN)).sum() / g.win_days.sum()
    # ③ 残り日数ごとに1日あたりを比べてまとめる（マンテル・ヘンツェルの比）
    num = sum(ce * nl / (ne + nl) for d, ne, ce, nl, cl in df.attrs["strat"])
    den = sum(cl * ne / (ne + nl) for d, ne, ce, nl, cl in df.attrs["strat"])
    ratio = {"per_booking": r1(early) / r1(late), "per_day": r2(early) / r2(late), "same_window": num / den,
             "window_pooled": r3(early) / r3(late),
             "early_rate": r1(early), "late_rate": r1(late), "overall_rate": float(c.mean())}
    return t, ratio


def exact_rate(L, m, shape="base"):
    h = haz(shape)[:L] * m
    return 1 - np.prod(1 - h)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {}

    # 1) 人による違いがない（m=1）・基本：予約の早さごとの取り消し率と式
    base = simulate(rng, 200_000, 1.0)
    base.head(20_000).assign(booking_id=np.arange(1, 20_001))[
        ["booking_id", "lead_days", "cancel_day", "held_days", "win_days"]].to_csv(DATA / "bookings_m1.csv", index=False)
    by_lead = base.groupby("lead_days").agg(bookings=("cancel_day", "size"),
                                            sim_rate=("cancel_day", lambda s: (s > 0).mean())).reset_index()
    by_lead["exact_rate"] = [exact_rate(L, 1.0) for L in by_lead.lead_days]
    by_lead.round(5).to_csv(RES / "rate_by_lead_m1.csv", index=False)
    out["m1_exact"] = {f"lead_{L}": round(exact_rate(L, 1.0) * 100, 2) for L in [1, 3, 7, 14, 30, 60, 90]}
    bd = []
    for (a, b), nm in zip(BINS, BIN_NAMES):
        g = by_lead[(by_lead.lead_days >= a) & (by_lead.lead_days <= b)]
        ex = (g.exact_rate * g.bookings).sum() / g.bookings.sum()
        sm = (g.sim_rate * g.bookings).sum() / g.bookings.sum()
        bd.append({"bin": nm, "bookings": int(g.bookings.sum()), "sim_pct": round(sm * 100, 2), "exact_pct": round(ex * 100, 2)})
    out["m1_bins_sim_vs_exact"] = bd
    out["m1_bins_max_abs_diff_pt"] = round(max(abs(x["sim_pct"] - x["exact_pct"]) for x in bd), 2)

    # 2) 3つの場面（早い予約の人が本当は 0.7倍・1倍・1.5倍 取り消しやすい）
    tabs, ratios = [], {}
    for m in [0.7, 1.0, 1.5]:
        df = base if m == 1.0 else simulate(rng, 200_000, m)
        t, r = measures(df)
        t.insert(0, "true_m", m)
        tabs.append(t)
        ratios[str(m)] = {k: round(float(v), 3) if "rate" not in k else round(float(v) * 100, 2) for k, v in r.items()}
    tab = pd.concat(tabs, ignore_index=True)
    tab2 = tab.copy()
    tab2["cancel_rate"] = (tab2.cancel_rate * 100).round(2)
    tab2["per_day"] = (tab2.per_day * 100).round(4)
    tab2["window_per_day"] = (tab2.window_per_day * 100).round(3)
    tab2.to_csv(RES / "measures_by_bin.csv", index=False)
    out["scenarios"] = ratios
    out["note"] = {"cancel_rate": "%", "per_day": "1日あたり%", "window_per_day": "残り1〜7日の1日あたり%",
                   "ratio": "早い予約（31〜90日前）÷遅い予約（1〜7日前）"}

    # 3) 確かめ：本当の倍率×取り消しの起きる時期×予約の早さの分布（45通り）
    grid = []
    for shape in ["flat", "base", "steep"]:
        for lm in [10, 25, 45]:
            for m in [0.5, 0.7, 1.0, 1.5, 2.0]:
                g = simulate(np.random.default_rng(SEED * 100 + len(grid)), 60_000, m, shape, lm)
                _, r = measures(g)
                grid.append({"shape": shape, "lead_mean": lm, "true_m": m,
                             "n_early": int((g.lead_days >= EARLY_FROM).sum()),
                             "ratio_per_booking": round(r["per_booking"], 3), "ratio_per_day": round(r["per_day"], 3),
                             "ratio_same_window": round(r["same_window"], 3), "ratio_window_pooled": round(r["window_pooled"], 3),
                             "overall_rate_pct": round(r["overall_rate"] * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    lt1 = grid[grid.true_m < 1]
    gb = grid[grid["shape"] != "flat"]
    out["grid"] = {
        "n_cases": int(len(grid)),
        "per_booking_range": [float(grid.ratio_per_booking.min()), float(grid.ratio_per_booking.max())],
        "per_booking_range_m1": [float(grid[grid.true_m == 1].ratio_per_booking.min()),
                                 float(grid[grid.true_m == 1].ratio_per_booking.max())],
        "m_lt1_cases": int(len(lt1)),
        "m_lt1_per_booking_gt1": int((lt1.ratio_per_booking > 1).sum()),
        "m_lt1_per_day_gt1": int((lt1.ratio_per_day > 1).sum()),
        "m_lt1_same_window_gt1": int((lt1.ratio_same_window > 1).sum()),
        "per_day_over_m_nonflat_range": [round(float((gb.ratio_per_day / gb.true_m).min()), 3),
                                         round(float((gb.ratio_per_day / gb.true_m).max()), 3)],
        "per_day_over_m_flat_range": [round(float((grid[grid["shape"] == "flat"].ratio_per_day / grid[grid["shape"] == "flat"].true_m).min()), 3),
                                      round(float((grid[grid["shape"] == "flat"].ratio_per_day / grid[grid["shape"] == "flat"].true_m).max()), 3)],
        "same_window_over_m_range": [round(float((grid.ratio_same_window / grid.true_m).min()), 3),
                                     round(float((grid.ratio_same_window / grid.true_m).max()), 3)],
        "per_booking_over_m_range": [round(float((grid.ratio_per_booking / grid.true_m).min()), 3),
                                     round(float((grid.ratio_per_booking / grid.true_m).max()), 3)],
        "n_early_min": int(grid.n_early.min()),
        "m_gt1_nonflat_cases": int(((grid.true_m > 1) & (grid["shape"] != "flat")).sum()),
        "m_gt1_nonflat_per_day_lt1": int(((grid.true_m > 1) & (grid["shape"] != "flat") & (grid.ratio_per_day < 1)).sum()),
        "window_pooled_over_m_nonflat_range": [round(float((gb.ratio_window_pooled / gb.true_m).min()), 3),
                                               round(float((gb.ratio_window_pooled / gb.true_m).max()), 3)],
    }
    out["run_sec"] = round(time.time() - t0, 1)
    run_sec = out.pop("run_sec")
    json.dump(out, open(RES / "a1020_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：予約の早さごとの取り消し率（人による違いなし）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bl = by_lead[by_lead.bookings >= 500]
    ax.scatter(bl.lead_days, bl.sim_rate * 100, s=10, color=BLUE, alpha=.7, lw=0, label="乱数（予約500件以上の日）")
    ax.plot(by_lead.lead_days, by_lead.exact_rate * 100, color=ORANGE, lw=1.6, label="式の値")
    ax.set_xlabel("予約を入れた日（泊まる日の何日前か）"); ax.set_ylabel("予約1件あたりの取り消し率（%）")
    ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("取り消しやすさが同じでも、早い予約ほど取り消し率は高く見える")
    save(fig, "a1020_by_lead.png", SRC)

    # 図2：3つの物差しの比（早い÷遅い）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ms = ["0.7", "1.0", "1.5"]
    keys = [("per_booking", "①予約1件あたり", GRAY), ("per_day", "②予約していた1日あたり", LIGHT),
            ("same_window", "③残り日数ごとに比べる（1〜7日前）", BLUE)]
    x = np.arange(3)
    for i, (k, nm, col) in enumerate(keys):
        v = [ratios[m][k] for m in ms]
        ax.bar(x + (i - 1) * 0.26, v, 0.24, color=col, label=nm)
        for xi, vi in zip(x, v):
            ax.text(xi + (i - 1) * 0.26, vi + 0.05, f"{vi:.2f}", ha="center", fontsize=8)
    for xi, m in zip(x, ms):
        ax.plot([xi - 0.4, xi + 0.4], [float(m)] * 2, color=INK, lw=1, ls="--")
    ax.set_xticks(x, [f"本当は{m}倍" for m in ["0.7", "1", "1.5"]])
    ax.set_ylabel("早い予約÷遅い予約（倍）"); ax.set_ylim(0, max(ratios["1.5"]["per_booking"], 3) + 1.2)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("点線が置いた本当の倍率。③だけが本当の倍率に近い")
    save(fig, "a1020_measures.png", SRC)

    # 図3：45通り
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.6), sharey=True)
    for ax, (k, nm, col) in zip(axes, keys):
        for shp, mk in zip(["flat", "base", "steep"], ["s", "o", "^"]):
            g = grid[grid["shape"] == shp]
            ax.scatter(g.true_m, g[f"ratio_{k}"], s=22, marker=mk, color=col if col != LIGHT else BLUE,
                       alpha=.75, label=SHAPE_NAMES[shp], edgecolor=INK if shp == "flat" else "none", lw=.4)
        ax.plot([0.4, 2.1], [0.4, 2.1], color=INK, lw=.8, ls="--")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xticks([0.5, 1, 2], ["0.5", "1", "2"]); ax.set_yticks([0.1, 0.2, 0.5, 1, 2, 5, 10, 20], ["0.1", "0.2", "0.5", "1", "2", "5", "10", "20"])
        ax.minorticks_off()
        ax.set_title(nm, fontsize=10); ax.set_xlabel("置いた本当の倍率")
    axes[0].set_ylabel("数えた比（早い÷遅い、対数）")
    h_, l_ = axes[1].get_legend_handles_labels()
    fig.legend(h_, l_, frameon=False, fontsize=8.5, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle("45通り（取り消しの時期3×予約の早さの分布3×本当の倍率5）。点線は本当の倍率どおり", fontsize=11, y=1.03)
    save(fig, "a1020_grid.png", SRC, y=-0.13)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", run_sec)


if __name__ == "__main__":
    main()
