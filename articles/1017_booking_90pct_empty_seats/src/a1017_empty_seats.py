"""1017 予約の埋まり具合が9割でも、当日の席はどれだけ空くのか？（架空のデータ）

架空の飲食店（2人卓8卓・4人卓8卓＝48席、夜の1回だけの営業）。
予約は組ごとに入り、合う卓が空いていれば受ける。前日の夜の時点の「埋まり具合」を、
人数（予約の人数÷48席）と卓（予約の入った卓÷16卓）の2通りで数え、
そのあとの取り消し・無断の不来店・人数の減りで、当日どれだけ席が空くかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1017
SRC = "架空の飲食店の予約（作成者が乱数で作成、seed 1017）"
N2, N4 = 8, 8                      # 2人卓・4人卓の数
SEATS = 2 * N2 + 4 * N4            # 48席
TABLES = N2 + N4                   # 16卓
SIZES = np.array([1, 2, 3, 4])
BASE = dict(cancel=0.08, noshow=0.05, shrink=0.10, p_size=(0.08, 0.52, 0.15, 0.25), walkin=0.0)
P_SIZE = {"少ない": (0.05, 0.35, 0.20, 0.40), "基本": (0.08, 0.52, 0.15, 0.25), "多い": (0.10, 0.65, 0.10, 0.15)}
LO, HI = 0.85, 0.95                # 「9割前後」の幅


def simulate(rng, n_days, cancel, noshow, shrink, p_size, walkin):
    p_size = np.asarray(p_size)
    rows = []
    for d in range(n_days):
        lam = rng.uniform(8, 24)                      # その日の予約の申し込みの多さ
        n_req = rng.poisson(lam)
        free2, free4 = N2, N4
        parties = []                                  # (人数, 卓の大きさ)
        for size in rng.choice(SIZES, size=n_req, p=p_size):
            if size <= 2 and free2 > 0:
                free2 -= 1; parties.append((size, 2))
            elif free4 > 0:
                free4 -= 1; parties.append((size, 4))
            # 合う卓がなければ断る（数えない）
        k = len(parties)
        size = np.array([p[0] for p in parties], dtype=int)
        tsz = np.array([p[1] for p in parties], dtype=int)
        u = rng.random(k)
        is_cancel = u < cancel
        is_noshow = (~is_cancel) & (u < cancel + (1 - cancel) * noshow)
        came = ~(is_cancel | is_noshow)
        less = came & (size >= 2) & (rng.random(k) < shrink)
        seated_res = size - less.astype(int)
        booked_people = int(size.sum())
        # 当日の飛び込みの客（基本は0組）。空いた卓に入る
        n_walk = rng.poisson(walkin) if walkin > 0 else 0
        f2 = free2 + int((~came & (tsz == 2)).sum())
        f4 = free4 + int((~came & (tsz == 4)).sum())
        walk_people = 0
        for s in rng.choice(SIZES, size=n_walk, p=p_size):
            if s <= 2 and f2 > 0:
                f2 -= 1; walk_people += s
            elif f4 > 0:
                f4 -= 1; walk_people += s
        seated = int(seated_res[came].sum()) + walk_people
        rows.append({
            "day": d + 1, "parties": k, "booked_people": booked_people,
            "booked_tables": k,
            "fill_people": booked_people / SEATS, "fill_tables": k / TABLES,
            "seat_no_booking": 2 * free2 + 4 * free4,
            "seat_table_leftover": int((tsz - size).sum()),
            "seat_cancel": int(size[is_cancel].sum()),
            "seat_noshow": int(size[is_noshow].sum()),
            "seat_shrink": int(less.sum()),
            "walkin_people": walk_people,
            "seated": seated, "seated_rate": seated / SEATS,
            "expected_ratio": float(((1 - cancel) * (1 - noshow) * (size - shrink * (size >= 2))).sum() / max(booked_people, 1)),
        })
    return pd.DataFrame(rows)


def band(df, col):
    return df[(df[col] >= LO) & (df[col] <= HI)]


def summarize(df):
    out = {}
    for col, name in [("fill_people", "people"), ("fill_tables", "tables")]:
        g = band(df, col)
        parts = {c: float(g[c].mean() / SEATS) for c in
                 ["seat_no_booking", "seat_table_leftover", "seat_cancel", "seat_noshow", "seat_shrink"]}
        out[name] = {
            "days": int(len(g)),
            "fill_people_mean": round(float(g.fill_people.mean()) * 100, 2),
            "fill_tables_mean": round(float(g.fill_tables.mean()) * 100, 2),
            "seated_rate_mean": round(float(g.seated_rate.mean()) * 100, 2),
            "seated_rate_p10": round(float(g.seated_rate.quantile(0.1)) * 100, 2),
            "seated_rate_p90": round(float(g.seated_rate.quantile(0.9)) * 100, 2),
            "share_below_75": round(float((g.seated_rate < 0.75).mean()) * 100, 2),
            "share_at_or_above_90": round(float((g.seated_rate >= 0.90).mean()) * 100, 2),
            "empty_seats_mean": round(float(SEATS - g.seated.mean()), 2),
            "parts_pct": {k: round(v * 100, 2) for k, v in parts.items()},
            "seated_per_booked_person": round(float(g.seated.sum() / g.booked_people.sum()) * 100, 2),
            "formula_seated_per_booked_person": round(float((g.expected_ratio * g.booked_people).sum() / g.booked_people.sum()) * 100, 2),
        }
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    df = simulate(rng, 20000, **BASE)
    df.head(2000).to_csv(DATA / "days.csv", index=False, float_format="%.4f")
    main_res = {"base": summarize(df), "n_days": int(len(df)), "seats": SEATS, "tables": TABLES,
                "setting": {k: (list(v) if isinstance(v, tuple) else v) for k, v in BASE.items()}}
    main_res["seated_rate_gap_people_minus_tables_pt"] = round(main_res["base"]["people"]["seated_rate_mean"]
                                                               - main_res["base"]["tables"]["seated_rate_mean"], 2)

    # 人数の埋まりごとの当日の着席率（帯ごと）
    bins = np.arange(0.40, 1.0001, 0.05)
    df["bin"] = pd.cut(df.fill_people, bins, include_lowest=True)
    by_bin = df.groupby("bin", observed=True).agg(days=("day", "size"), seated_rate=("seated_rate", "mean"),
                                                  fill_tables=("fill_tables", "mean")).reset_index()
    by_bin["bin"] = by_bin["bin"].astype(str)
    by_bin[["seated_rate", "fill_tables"]] = (by_bin[["seated_rate", "fill_tables"]] * 100).round(2)
    by_bin.to_csv(RES / "by_fill_bin.csv", index=False)

    # 確かめ：取り消し×無断×組の人数（27通り×各3000日）
    grid = []
    for i, c in enumerate([0.04, 0.08, 0.15]):
        for j, ns in enumerate([0.02, 0.05, 0.10]):
            for k, (pname, ps) in enumerate(P_SIZE.items()):
                g = simulate(np.random.default_rng(SEED * 100 + i * 9 + j * 3 + k), 3000, c, ns, 0.10, ps, 0.0)
                s = summarize(g)["people"]
                grid.append({"cancel": c, "noshow": ns, "party_mix": pname, "days_in_band": s["days"],
                             "seated_rate_mean": s["seated_rate_mean"], "seated_rate_p10": s["seated_rate_p10"],
                             "seated_rate_p90": s["seated_rate_p90"], "share_below_75": s["share_below_75"],
                             "table_leftover_pct": s["parts_pct"]["seat_table_leftover"],
                             "fill_tables_mean": s["fill_tables_mean"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)

    # 確かめ：当日の飛び込みの客（0・2・4組、各5000日）
    walk = []
    for i, w in enumerate([0.0, 2.0, 4.0]):
        g = simulate(np.random.default_rng(SEED * 1000 + i), 5000, **{**BASE, "walkin": w})
        s = summarize(g)["people"]
        walk.append({"walkin_groups_mean": w, "days_in_band": s["days"], "seated_rate_mean": s["seated_rate_mean"],
                     "seated_rate_p10": s["seated_rate_p10"], "seated_rate_p90": s["seated_rate_p90"],
                     "share_at_or_above_90": s["share_at_or_above_90"]})
    walk = pd.DataFrame(walk)
    walk.to_csv(RES / "sensitivity_walkin.csv", index=False)

    main_res["grid_range"] = {
        "seated_rate_mean_min": float(grid.seated_rate_mean.min()), "seated_rate_mean_max": float(grid.seated_rate_mean.max()),
        "share_below_75_min": float(grid.share_below_75.min()), "share_below_75_max": float(grid.share_below_75.max()),
        "table_leftover_min": float(grid.table_leftover_pct.min()), "table_leftover_max": float(grid.table_leftover_pct.max()),
        "fill_tables_mean_min": float(grid.fill_tables_mean.min()), "fill_tables_mean_max": float(grid.fill_tables_mean.max()),
    }
    with open(RES / "a1017_main.json", "w", encoding="utf-8") as f:
        json.dump(main_res, f, ensure_ascii=False, indent=1)

    # 図1：9割前後の日の48席の内訳
    labels = {"seat_no_booking": "予約のない卓", "seat_table_leftover": "卓の余り（2人で4人卓など）",
              "seat_cancel": "前日の夜からの取り消し", "seat_noshow": "無断で来ない", "seat_shrink": "人数の減り"}
    cols = [GRAY, LIGHT, ORANGE, "#c0392b", GREEN]
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    for r, (key, title) in enumerate([("people", "人数で9割前後の日"), ("tables", "卓で9割前後の日")]):
        s = main_res["base"][key]
        left = s["seated_rate_mean"]
        ax.barh(r, left, color=BLUE)
        ax.text(left / 2, r, f"座った {left:.1f}%", ha="center", va="center", color="white", fontsize=10)
        for (k, lab), c in zip(labels.items(), cols):
            v = s["parts_pct"][k]
            ax.barh(r, v, left=left, color=c)
            if v >= 2.5:
                ax.text(left + v / 2, r, f"{v:.1f}", ha="center", va="center", fontsize=9, color=INK)
            left += v
    ax.set_yticks([0, 1]); ax.set_yticklabels(["人数で9割前後の日", "卓で9割前後の日"])
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("48席のうちの割合（%）")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols]
    ax.legend(handles, list(labels.values()), ncol=3, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.28), frameon=False)
    ax.set_title("前日の夜に9割埋まっていた日の、当日の48席の内訳（平均）")
    save(fig, "a1017_breakdown.png", SRC, y=-0.30)

    # 図2：人数で9割前後の日の、当日の着席率の散らばり
    g = band(df, "fill_people")
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.hist(g.seated_rate * 100, bins=(np.arange(20, 50) - 0.5) / 48 * 100, color=BLUE, edgecolor="white")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.25)
    m = main_res["base"]["people"]
    ax.axvline(m["fill_people_mean"], color=ORANGE, lw=2)
    ax.text(m["fill_people_mean"] + 0.5, ax.get_ylim()[1] * 0.9, f"前日の夜の埋まり\n（平均{m['fill_people_mean']:.1f}%）", color=ORANGE, fontsize=9)
    ax.axvline(m["seated_rate_mean"], color=INK, lw=1.5, ls="--")
    ax.text(m["seated_rate_mean"] - 0.5, ax.get_ylim()[1] * 0.9, f"当日座った\n（平均{m['seated_rate_mean']:.1f}%）", ha="right", fontsize=9)
    ax.set_xlabel("当日座った人数÷48席（%）"); ax.set_ylabel("日数")
    ax.set_title(f"人数で85〜95%埋まっていた{m['days']:,}日の、当日の着席率")
    save(fig, "a1017_hist.png", SRC)

    # 図3：置き方を変えた27通り
    gg = grid.sort_values("seated_rate_mean").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    x = np.arange(len(gg))
    ax.errorbar(x, gg.seated_rate_mean, yerr=[gg.seated_rate_mean - gg.seated_rate_p10, gg.seated_rate_p90 - gg.seated_rate_mean],
                fmt="o", color=BLUE, ecolor=LIGHT, capsize=2)
    base_i = gg.index[(gg.cancel == 0.08) & (gg.noshow == 0.05) & (gg.party_mix == "基本")][0]
    ax.plot(base_i, gg.seated_rate_mean[base_i], "o", color=ORANGE, ms=9, zorder=3)
    ax.annotate("基本の置き方", (base_i, gg.seated_rate_mean[base_i]), xytext=(base_i - 6, 94), color=ORANGE,
                arrowprops=dict(arrowstyle="-", color=ORANGE), fontsize=9)
    ax.axhline(90, color=GRAY, lw=1, ls=":")
    ax.set_xticks([]); ax.set_xlabel("取り消し（4・8・15%）×無断（2・5・10%）×組の人数（3通り）の27通り（低い順）")
    ax.set_ylabel("当日座った人数÷48席（%）"); ax.set_ylim(45, 100)
    ax.set_title("人数で9割前後の日の当日の着席率（点は平均、線は10〜90%の日）")
    save(fig, "a1017_grid.png", SRC)
    print(json.dumps(main_res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
