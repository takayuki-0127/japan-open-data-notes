"""1024 同じ人の重複した予約は、埋まり具合をどれだけ押し上げるのか？（架空のデータ）

架空の宿（20室）。泊まりたい夜の予約の申し込みが、何日か前から1部屋ずつ入る。
一部の人は、泊まる夜を決めかねて、前後1〜7日の別の夜も「仮に」押さえる（重複した予約）。
決める日（早いほうの夜の3〜14日前）に仮の予約を取り消すが、10%は取り消し忘れて当日来ない。
何日か前の時点の埋まり具合が、重複した予約でどれだけ押し上げられるか、
満室に見えて断った人がどれだけ出るかを、重複がない場合（同じ申し込み）と比べて数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1024
SRC = "架空の宿の予約（作成者が乱数で作成、seed 1024）"
ROOMS = 20
LEAD_MEAN, LEAD_MAX = 20, 90
DOW = np.array([0.85, 0.85, 0.85, 0.85, 0.85, 1.375, 1.375])   # 日〜土の夜。平均1
SNAP = (30, 14, 7, 1)
BASE = dict(dup=0.10, demand=18.0, r_lo=3, r_hi=14, forget=0.10)
WARM = 120


def make_requests(rng, n_nights, demand):
    lam = demand * DOW[np.arange(n_nights) % 7]
    n = rng.poisson(lam)
    night = np.repeat(np.arange(n_nights), n)
    lead = np.minimum(rng.geometric(1 / LEAD_MEAN, size=night.size), LEAD_MAX)
    return night, night - lead


def run(rng_dup, night, bday, n_nights, dup, r_lo, r_hi, forget, use_dup=True):
    m = night.size
    is_dup = rng_dup.random(m) < dup
    k = rng_dup.integers(1, 8, size=m) * rng_dup.choice([-1, 1], size=m)
    alt = night + k
    r = rng_dup.integers(r_lo, r_hi + 1, size=m)
    forg = rng_dup.random(m) < forget
    order = rng_dup.permutation(m)
    if not use_dup:
        is_dup = np.zeros(m, bool)
    order = order[np.argsort(bday[order], kind="stable")]
    allb = np.zeros(n_nights, int)        # 押さえられた部屋（仮も含む）
    gen = np.zeros(n_nights, int)         # 本当に泊まる人の部屋
    held = np.zeros(n_nights, int)        # 仮の予約で押さえた部屋（いまの数）
    forgot = np.zeros(n_nights, int)
    lost = np.zeros(n_nights, int)
    snap_all = {s: np.full(n_nights, -1) for s in SNAP}
    snap_gen = {s: np.full(n_nights, -1) for s in SNAP}
    rel = {}
    d0 = int(bday.min())
    pos = 0
    for d in range(d0, n_nights):
        for s in SNAP:
            t = d + s
            if 0 <= t < n_nights:
                snap_all[s][t] = allb[t]; snap_gen[s][t] = gen[t]
        for t2 in rel.pop(d, []):
            allb[t2] -= 1; held[t2] -= 1
        while pos < m and bday[order[pos]] == d:
            i = order[pos]; pos += 1
            t = night[i]
            if allb[t] >= ROOMS:
                lost[t] += 1
                continue
            allb[t] += 1; gen[t] += 1
            if is_dup[i]:
                t2 = alt[i]
                if t2 <= d or t2 < 0 or t2 >= n_nights or allb[t2] >= ROOMS:
                    continue
                allb[t2] += 1; held[t2] += 1
                if forg[i]:
                    forgot[t2] += 1
                else:
                    dd = max(d, min(t, t2) - r[i])
                    if dd == d:
                        allb[t2] -= 1; held[t2] -= 1
                    else:
                        rel.setdefault(dd, []).append(t2)
    df = pd.DataFrame({"night": np.arange(n_nights), "requests": np.bincount(night, minlength=n_nights),
                       "lost": lost, "stayed": gen, "forgot_holds": forgot})
    for s in SNAP:
        df[f"fill_all_{s}d"] = snap_all[s] / ROOMS
        df[f"fill_true_{s}d"] = snap_gen[s] / ROOMS
    return df.iloc[WARM:n_nights - WARM].reset_index(drop=True)


def pair(seed_off, n_nights, dup, demand, r_lo, r_hi, forget):
    rng = np.random.default_rng([SEED, seed_off])
    night, bday = make_requests(rng, n_nights, demand)
    a = run(np.random.default_rng([SEED, seed_off, 1]), night, bday, n_nights, dup, r_lo, r_hi, forget, True)
    b = run(np.random.default_rng([SEED, seed_off, 1]), night, bday, n_nights, dup, r_lo, r_hi, forget, False)
    return a, b


def summarize(a, b):
    out = {"nights": int(len(a))}
    for s in SNAP:
        out[f"fill_all_{s}d"] = round(float(a[f"fill_all_{s}d"].mean()) * 100, 2)
        out[f"fill_true_{s}d"] = round(float(a[f"fill_true_{s}d"].mean()) * 100, 2)
        out[f"inflation_{s}d_pt"] = round(out[f"fill_all_{s}d"] - out[f"fill_true_{s}d"], 2)
        out[f"inflation_{s}d_rooms"] = round(float((a[f"fill_all_{s}d"] - a[f"fill_true_{s}d"]).mean()) * ROOMS, 2)
        out[f"fill_nodup_{s}d"] = round(float(b[f"fill_all_{s}d"].mean()) * 100, 2)
    f7 = a["fill_all_7d"]
    full7 = f7 >= 0.9
    out["share_nights_look_90_7d"] = round(float(full7.mean()) * 100, 2)
    out["share_true_below_90_among_look_90_7d"] = round(float((a.loc[full7, "fill_true_7d"] < 0.9).mean()) * 100, 2)
    out["share_nights_look_90_7d_nodup"] = round(float((b["fill_all_7d"] >= 0.9).mean()) * 100, 2)
    out["stayed_rate"] = round(float(a.stayed.mean() / ROOMS) * 100, 2)
    out["stayed_rate_nodup"] = round(float(b.stayed.mean() / ROOMS) * 100, 2)
    out["stayed_diff_pt"] = round(out["stayed_rate"] - out["stayed_rate_nodup"], 2)
    out["lost_per_100_nights"] = round(float(a.lost.mean()) * 100, 1)
    out["lost_per_100_nights_nodup"] = round(float(b.lost.mean()) * 100, 1)
    out["extra_lost_per_100_nights"] = round(out["lost_per_100_nights"] - out["lost_per_100_nights_nodup"], 1)
    out["lost_share_of_requests"] = round(float(a.lost.sum() / a.requests.sum()) * 100, 2)
    out["lost_share_of_requests_nodup"] = round(float(b.lost.sum() / b.requests.sum()) * 100, 2)
    out["forgot_rooms_per_100_nights"] = round(float(a.forgot_holds.mean()) * 100, 1)
    out["noshow_rate_of_booked_1d"] = round(float(a.forgot_holds.sum() / (a.fill_all_1d.sum() * ROOMS)) * 100, 2)
    # 恒等式の確かめ：取り消しのない泊まる人は「申し込み−断った人」
    out["check_stayed_eq_requests_minus_lost"] = bool(((a.requests - a.lost) == a.stayed).all() and ((b.requests - b.lost) == b.stayed).all())
    out["check_nodup_all_eq_true"] = bool(all((b[f"fill_all_{s}d"] == b[f"fill_true_{s}d"]).all() for s in SNAP))
    return out


def main():
    t0 = time.time()
    a, b = pair(0, 3240, **BASE)
    res = {"base": summarize(a, b), "setting": dict(BASE, rooms=ROOMS, lead_mean=LEAD_MEAN, lead_max=LEAD_MAX,
                                                     dow=DOW.tolist(), snapshots=list(SNAP), n_nights_analyzed=int(len(a)), warm_nights_dropped_each_end=WARM)}
    out = a.copy()
    out["stayed_nodup"] = b.stayed; out["lost_nodup"] = b.lost
    out.head(1000).to_csv(DATA / "nights.csv", index=False, float_format="%.4f")

    # 申し込みの多さ（夜ごと）別：7日前の押し上げ
    a["dem_bin"] = pd.cut(a.requests, [0, 12, 16, 20, 24, 28, 100], right=False)
    byb = a.groupby("dem_bin", observed=True).agg(nights=("night", "size"), fill_all_7d=("fill_all_7d", "mean"),
                                                  fill_true_7d=("fill_true_7d", "mean"), lost=("lost", "mean")).reset_index()
    byb["lost_nodup"] = b.groupby(a.dem_bin, observed=True).lost.mean().values
    byb["dem_bin"] = ["11以下", "12〜15", "16〜19", "20〜23", "24〜27", "28以上"][:len(byb)]
    for c in ["fill_all_7d", "fill_true_7d"]:
        byb[c] = (byb[c] * 100).round(2)
    byb["inflation_7d_pt"] = (byb.fill_all_7d - byb.fill_true_7d).round(2)
    byb["lost_per_100_nights"] = (byb.lost * 100).round(1); byb["lost_per_100_nights_nodup"] = (byb.lost_nodup * 100).round(1)
    byb = byb.drop(columns=["lost", "lost_nodup"])
    byb.to_csv(RES / "by_demand.csv", index=False)

    rows = []
    j = 1
    for dup in (0.05, 0.10, 0.20):
        for dem in (12.0, 18.0, 24.0):
            for (lo, hi), rn in [((1, 3), "夜の1〜3日前"), ((3, 14), "夜の3〜14日前（基本）"), ((7, 21), "夜の7〜21日前")]:
                aa, bb = pair(j, 840, dup, dem, lo, hi, BASE["forget"]); j += 1
                s = summarize(aa, bb)
                rows.append({"dup": dup, "demand": dem, "release": rn, "r_lo": lo, "r_hi": hi,
                             "inflation_30d_pt": s["inflation_30d_pt"], "inflation_14d_pt": s["inflation_14d_pt"], "inflation_7d_pt": s["inflation_7d_pt"],
                             "inflation_1d_pt": s["inflation_1d_pt"], "fill_true_7d": s["fill_true_7d"],
                             "stayed_diff_pt": s["stayed_diff_pt"], "extra_lost_per_100_nights": s["extra_lost_per_100_nights"],
                             "share_true_below_90_among_look_90_7d": s["share_true_below_90_among_look_90_7d"]})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    COLS = ["inflation_30d_pt", "inflation_14d_pt", "inflation_7d_pt", "inflation_1d_pt", "stayed_diff_pt", "extra_lost_per_100_nights"]
    res["grid"] = {c + "_min": float(grid[c].min()) for c in COLS}
    res["grid"].update({c + "_max": float(grid[c].max()) for c in COLS})
    res["grid"]["n_stayed_lower"] = int((grid.stayed_diff_pt < 0).sum())
    res["grid"]["n"] = int(len(grid))
    res["grid"]["nights_each"] = 840 - 2 * WARM
    with open(RES / "a1024_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    B = res["base"]
    # 図1：何日前の埋まり具合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    xs = list(SNAP)
    ya = [B[f"fill_all_{s}d"] for s in xs]; yt = [B[f"fill_true_{s}d"] for s in xs]; yn = [B[f"fill_nodup_{s}d"] for s in xs]
    ax.plot(xs, ya, "o-", color=ORANGE, label="押さえた部屋（仮の予約も含む）")
    ax.plot(xs, yt, "o-", color=BLUE, label="そのうち本当に泊まる人の部屋")
    ax.plot(xs, yn, "s-", color=GRAY, lw=5, alpha=0.5, zorder=1, label="重複がない場合（同じ申し込み、青とほぼ重なる）")
    for x, v1, v2 in zip(xs, ya, yt):
        ax.text(x, v1 + 2, f"{v1:.1f}", ha="center", fontsize=8, color=ORANGE)
        ax.text(x, v2 - 5, f"{v2:.1f}", ha="center", fontsize=8, color=BLUE)
    ax.invert_xaxis(); ax.set_xticks(xs); ax.set_xticklabels([f"{s}日前" for s in xs])
    ax.set_ylim(0, 100); ax.set_ylabel("20室に対する割合（%、平均）")
    ax.set_title("何日前に見た埋まり具合か（重複した予約10%）")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    save(fig, "a1024_by_days.png", SRC)

    # 図2：申し込みの多さ別の、断った人（100夜あたり）
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(len(byb))
    ax.bar(x - 0.2, byb.lost_per_100_nights_nodup, 0.4, color=GRAY, label="重複がない場合")
    ax.bar(x + 0.2, byb.lost_per_100_nights, 0.4, color=ORANGE, label="重複した予約10%")
    ax.set_xticks(x); ax.set_xticklabels(["11以下", "12〜15", "16〜19", "20〜23", "24〜27", "28以上"][:len(byb)])
    ax.set_xlabel("その夜の申し込みの数（件、20室に対して）")
    ax.set_ylabel("満室で断った人（100夜あたり）")
    ax.set_title("満室で断った人（申し込みの多さ別）")
    ax.legend(fontsize=9, frameon=False)
    save(fig, "a1024_lost.png", SRC)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    mk = {"夜の1〜3日前": "o", "夜の3〜14日前（基本）": "s", "夜の7〜21日前": "^"}
    cl = {0.05: LIGHT, 0.10: BLUE, 0.20: INK}
    for _, r in grid.iterrows():
        ax.scatter(r.inflation_7d_pt, r.extra_lost_per_100_nights, marker=mk[r.release], color=cl[r.dup], s=40)
    for k2, m in mk.items():
        ax.scatter([], [], marker=m, color=GRAY, label=f"仮の予約の取り消し：{k2}")
    for d2, c in cl.items():
        ax.scatter([], [], marker="o", color=c, label=f"重複した予約 {int(d2 * 100)}%")
    ax.set_xlabel("7日前の埋まり具合の押し上げ（ポイント）")
    ax.set_ylabel("重複で増えた断った人（100夜あたり）", labelpad=8)
    ax.set_title("置き方を変えた27通り")
    ax.legend(fontsize=8, frameon=False, loc="upper left", ncol=2)
    save(fig, "a1024_grid.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(byb.to_string()); print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
