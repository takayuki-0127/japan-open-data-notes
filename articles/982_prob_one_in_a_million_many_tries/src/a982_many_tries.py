"""982 「100万分の1の偶然」は、どれくらい起きるのか？（試す回数の多さ、架空のデータ）

架空の店が、毎日1回、3けたの番号（000〜999）を抽選する。番号はどれも同じ起きやすさで、日どうし・店どうしは互いに影響しないと置く。
「同じ番号が3日続けて出る」は、1軒の店の、ある日から3日間について100万分の1（1日目は何でもよく、2日目と3日目が1日目に合う確率 1/1000×1/1000）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 982
SRC = "架空の店の毎日の抽選（作成者が乱数で作成、seed 982）"
rng = np.random.default_rng(SEED)
P = 1e-6


def patterns(d):
    """d：店×日の番号。3日の窓ごとに、各型が起きたか"""
    a, b, c = d[:, :-2], d[:, 1:-1], d[:, 2:]
    same = (a == b) & (b == c)
    up = ((b - a) % 1000 == 1) & ((c - b) % 1000 == 1)
    down = ((a - b) % 1000 == 1) & ((b - c) % 1000 == 1)
    zoro = (a % 111 == 0) & (b % 111 == 0) & (c % 111 == 0)
    fixed = (a == 777) & (b == 777) & (c == 777)
    return {"same": same, "up": up, "down": down, "zoro": zoro, "fixed777": fixed}


def runs_count(same):
    """3日続きの窓が連なった塊を1回と数える（4日続けば窓は2つだが塊は1つ）"""
    s = same.astype(np.int8)
    starts = (s[:, 1:] == 1) & (s[:, :-1] == 0)
    return int(s[:, 0].sum() + starts.sum())


def formula(shops, years, p=P):
    w = shops * (365 * years - 2)
    return 1 - (1 - p) ** w, w * p


def simulate(shops, years, reps, seed):
    g = np.random.default_rng(seed)
    rows = []
    for r in range(reps):
        d = g.integers(0, 1000, size=(shops, 365 * years), dtype=np.int16)
        pt = patterns(d)
        row = {k: int(v.sum()) for k, v in pt.items()}
        row["same_runs"] = runs_count(pt["same"])
        row["any4"] = int((pt["same"] | pt["up"] | pt["down"] | pt["zoro"]).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    # 1回分のデータ（20軒×1年）
    d0 = rng.integers(0, 1000, size=(20, 365), dtype=np.int16)
    pd.DataFrame({"shop_id": np.repeat(np.arange(1, 21), 365), "day": np.tile(np.arange(1, 366), 20),
                  "number": [f"{x:03d}" for x in d0.ravel()]}).to_csv(DATA / "draws_example.csv", index=False)

    # 乱数：1,000軒×1年を1,000回、1,000軒×10年を60回、100軒×10年を300回、1軒×10年を10万回は式のみ
    sims = {}
    for shops, years, reps in [(1000, 1, 1000), (1000, 10, 60), (100, 10, 300)]:
        s = simulate(shops, years, reps, SEED * 100 + shops + years)
        f_p, f_mean = formula(shops, years)
        sims[f"{shops}shops_{years}y"] = {
            "shops": shops, "years": years, "reps": reps, "windows": shops * (365 * years - 2),
            "P_same_atleast1_sim": round(float((s.same > 0).mean()) * 100, 2),
            "P_same_atleast1_formula": round(f_p * 100, 2),
            "mean_same_windows_sim": round(float(s.same.mean()), 3),
            "mean_same_formula": round(f_mean, 3),
            "mean_same_runs_sim": round(float(s.same_runs.mean()), 3),
            "P_any4_atleast1_sim": round(float((s.any4 > 0).mean()) * 100, 2),
            "P_any4_atleast1_formula": round((1 - (1 - 4 * P) ** (shops * (365 * years - 2))) * 100, 2),
            "mean_any4_sim": round(float(s.any4.mean()), 3),
            "mean_by_pattern_sim": {k: round(float(s[k].mean()), 3) for k in ["same", "up", "down", "zoro"]},
            "fixed777_total_events": int(s.fixed777.sum()),
            "P_fixed777_formula": round((1 - (1 - 1e-9) ** (shops * (365 * years - 2))) * 100, 4)}
        if shops == 1000 and years == 1:
            dist = s.same.value_counts().sort_index()
            sims[f"{shops}shops_{years}y"]["dist_same"] = {int(k): int(v) for k, v in dist.items()}
            sims[f"{shops}shops_{years}y"]["dist_same_pct"] = {int(k): round(v / reps * 100, 1) for k, v in dist.items()}

    # 式：店の数×年数（同じ番号が3日続く、1軒・1日あたり100万分の1）
    grid = []
    for shops in [1, 10, 100, 1000, 10000]:
        for years in [1, 10, 30]:
            fp, fm = formula(shops, years)
            grid.append({"shops": shops, "years": years, "windows": shops * (365 * years - 2),
                         "P_atleast1": round(fp * 100, 3), "expected_events": round(fm, 4),
                         "P_atleast1_fixed777": round((1 - (1 - 1e-9) ** (shops * (365 * years - 2))) * 100, 4),
                         "P_atleast1_any4": round((1 - (1 - 4 * P) ** (shops * (365 * years - 2))) * 100, 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "by_shops_years.csv", index=False)

    # 待ち時間：どこかで初めて起きるまでの年数（中央値、式）
    wait = []
    for shops in [1, 10, 100, 1000, 10000]:
        per_year = shops * 365 * P
        wait.append({"shops": shops, "median_years_same": round(np.log(2) / per_year, 2),
                     "median_years_any4": round(np.log(2) / (4 * per_year), 2)})
    wait = pd.DataFrame(wait)
    wait.to_csv(RES / "waiting_years.csv", index=False)

    # 確かめ1：番号の出やすさに偏りがあるとき（作成者が置いた偏り：重みを対数正規、σ）
    bias = []
    for sg in [0.0, 0.3, 0.6, 1.0]:
        w = np.exp(np.random.default_rng(SEED + int(sg * 10)).normal(0, sg, 1000)) if sg > 0 else np.ones(1000)
        p = w / w.sum()
        pw = float((p ** 3).sum())  # 3日とも同じ番号になる確率（1つの窓）
        bias.append({"sigma": sg, "max_over_min_number": round(float(p.max() / p.min()), 1),
                     "P_per_window_in_millionths": round(pw * 1e6, 3),
                     "P_1000shops_1y": round((1 - (1 - pw) ** 363000) * 100, 2)})
    # 確かめ2：店どうしが同じ抽選を使い回すとき（1,000軒が、互いに独立な G 個の抽選を分け合う）
    share = []
    for G in [1, 10, 100, 1000]:
        share.append({"independent_draws": G, "P_1y": round(formula(G, 1)[0] * 100, 3),
                      "P_10y": round(formula(G, 10)[0] * 100, 3)})
    pd.DataFrame(bias).to_csv(RES / "robust_bias.csv", index=False)
    pd.DataFrame(share).to_csv(RES / "robust_shared_draws.csv", index=False)

    # 1軒の店から見たとき（式）
    one = {f"{y}y": round(formula(1, y)[0] * 100, 4) for y in [1, 10, 30]}
    check = {k: round(abs(v["P_same_atleast1_sim"] - v["P_same_atleast1_formula"]), 2) for k, v in sims.items()}
    out = {"P_per_window": P, "P_per_window_fixed777": 1e-9, "ratio_any_vs_fixed": 1000,
           "abs_diff_sim_formula_pt": check, "one_shop_P_same_pct": one, "simulations": sims,
           "grid_formula": grid.to_dict("records"),
           "robust_bias": bias, "robust_shared_draws": share, "waiting_years": wait.to_dict("records")}
    json.dump(out, open(RES / "a982_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：店の数と年数で、どこかで起きる確率（式）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for years, col in [(1, BLUE), (10, ORANGE), (30, GREEN)]:
        g = grid[grid.years == years]
        ax.plot(g.shops, g.P_atleast1, marker="o", color=col, label=f"{years}年")
        r = g[g.shops == 1000].iloc[0]
        if years == 1:
            ax.text(r.shops * 1.2, r.P_atleast1 - 3, f"{r.P_atleast1:.1f}%", color=col, fontsize=9)
        elif years == 10:
            ax.text(r.shops / 1.2, r.P_atleast1 - 4, f"{r.P_atleast1:.1f}%", color=col, fontsize=9, ha="right")
    ax.set_xscale("log"); ax.set_xticks([1, 10, 100, 1000, 10000]); ax.set_xticklabels(["1軒", "10軒", "100軒", "1,000軒", "1万軒"])
    ax.set_xlabel("抽選をしている店の数（対数の目盛り）"); ax.set_ylabel("どこかで1回以上起きる確率（%）"); ax.set_ylim(0, 105)
    ax.legend(frameon=False, title="見ている期間", fontsize=9, loc="upper left")
    ax.set_title("「同じ番号が3日続く」（1軒・1日あたり100万分の1）が、どこかで起きる確率")
    save(fig, "a982_shops_years.png", SRC)

    # 図2：1,000軒×1年の1,000回で、何回起きたか
    s1 = sims["1000shops_1y"]
    dist = pd.Series(s1["dist_same"])
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(dist.index, dist.values / 1000 * 100, color=[GRAY] + [BLUE] * (len(dist) - 1), width=.6)
    for x, v in zip(dist.index, dist.values / 1000 * 100):
        ax.text(x, v + 1, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(dist.index)
    ax.set_xlabel("1年に、1,000軒のどこかで「同じ番号が3日続く」が起きた回数"); ax.set_ylabel("年の割合（%、乱数1,000年分）")
    ax.set_title(f"1,000軒なら、{s1['P_same_atleast1_sim']:.1f}%の年にどこかで起きた（式では{s1['P_same_atleast1_formula']:.1f}%）")
    save(fig, "a982_count_1000shops.png", SRC)

    # 図3：数え方で変わる「100万分の1」
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    g = grid[grid.years == 1].set_index("shops")
    labels = ["決めた番号（777）が\n3日続く\n（1軒・1日10億分の1）", "どれかの番号が\n3日続く\n（100万分の1）", "4つの型のどれか\n（同じ・1ずつ増える・\n1ずつ減る・ぞろ目）"]
    vals = [g.loc[1000, "P_atleast1_fixed777"], g.loc[1000, "P_atleast1"], g.loc[1000, "P_atleast1_any4"]]
    ax.bar(range(3), vals, color=[GRAY, BLUE, ORANGE], width=.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.3g}%", ha="center", fontsize=10)
    ax.set_xticks(range(3)); ax.set_xticklabels(labels, fontsize=9.5); ax.set_ylim(0, 100)
    ax.set_ylabel("どこかで起きる確率（%、式）")
    ax.set_title("店1,000軒・1年：何を「同じ偶然」と数えるかで、起きやすさは桁で変わる", fontsize=12)
    save(fig, "a982_what_counts.png", SRC, y=-0.06)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
