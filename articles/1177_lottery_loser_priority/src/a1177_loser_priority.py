"""1177 落選が続いた人を優先する決まりにすると、当たるまでの回数はどれだけそろうのか？（架空のデータ）

作成者が置いた架空の料理教室の毎回の抽選（1回20席）を、何回も続けて行う。
決まりは3種類。
  ①毎回まったくのくじ：申し込んだ人から等しく20人を引く
  ②k回続けて落選した人を先に：続けて k 回以上落選している人を先に引き（その人数が席より多ければ、その中から引く）、残りの席をほかの人から引く
  ③落選の回数だけ口を足す：口の数＝1＋続けて落選した回数。口の数に比例して先に引かれやすい（1人1席まで）
「当たるまでの回数」＝前に当たった次の申し込みから、次に当たるまでに申し込んだ回数（当たった回を含む）。
(1) 基本：200人が毎回申し込む（倍率10倍）。40組×300回の抽選、はじめの60回は数えない
(2) たまに申し込む人がまざるとき（毎回申し込む100人と、3割の回だけ申し込む334人）。②で、休んだ回に落選の数を0に戻すか、続きから数えるか
(3) 確かめ：倍率（2・5・10・20倍）×決まり（①、②の k=1・2・3・5・8・12と「倍率−1」、③）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1177
SRC = "架空の料理教室の抽選（作成者が置いた申し込みと乱数、seed 1177）"
T0 = time.time()
SEATS = 20
YEAR = 24


def r(x, d=4):
    return round(float(x), d)


def simulate(rng, n, rule, k=None, runs=40, rounds=300, burn=60, apply_p=None, reset_on_skip=False):
    """rule: 'uniform' / 'priority' / 'weight'。apply_p: 人ごとの申し込む確率（None なら全員毎回）"""
    losses = np.zeros((runs, n), np.int64)
    gaps = []
    gap_owner = []
    wins = np.zeros((runs, n), np.int64)
    applied = np.zeros((runs, n), np.int64)
    yearly = []
    year_w = np.zeros((runs, n), np.int64)
    year_a = np.zeros((runs, n), np.int64)
    run_idx = np.arange(runs)[:, None]
    for t in range(rounds):
        if apply_p is None:
            app = np.ones((runs, n), bool)
        else:
            app = rng.random((runs, n)) < apply_p[None, :]
        u = rng.random((runs, n))
        if rule == "uniform":
            key = u
        elif rule == "priority":
            key = u + (losses < k) * 2.0
        else:
            key = -np.log(u) / (1.0 + losses)
        key = np.where(app, key, np.inf)
        sel = np.argpartition(key, SEATS - 1, axis=1)[:, :SEATS]
        win = np.zeros((runs, n), bool)
        win[run_idx, sel] = True
        win &= app
        if t >= burn:
            g = losses[win] + 1
            gaps.append(g)
            gap_owner.append(np.broadcast_to(np.arange(n), (runs, n))[win])
            wins += win
            applied += app
            year_w += win
            year_a += app
            if (t - burn + 1) % YEAR == 0:
                yearly.append(year_w.copy())
                year_w[:] = 0
                year_a[:] = 0
        lost = app & ~win
        losses = np.where(win, 0, np.where(lost, losses + 1, losses))
        if reset_on_skip:
            losses = np.where(app, losses, 0)
    gaps = np.concatenate(gaps)
    owner = np.concatenate(gap_owner)
    yearly = np.stack(yearly)  # years×runs×n
    return gaps, owner, wins, applied, yearly


def gap_stats(g, yearly, mask=None):
    y = yearly if mask is None else yearly[:, :, mask]
    return {"gap_mean": r(g.mean(), 3), "gap_sd": r(g.std(), 3), "gap_median": r(np.median(g), 1),
            "gap_p90": r(np.percentile(g, 90), 1), "gap_p99": r(np.percentile(g, 99), 1), "gap_max": int(g.max()),
            "gap_over24_pct": r((g > 24).mean() * 100, 3),
            "year_zero_win_pct": r((y == 0).mean() * 100, 3), "year_wins_mean": r(y.mean(), 3),
            "year_wins_sd": r(y.std(), 3), "n_gaps": int(len(g))}


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"seats": SEATS, "year_rounds": YEAR}}
    N = 200
    out["setting"].update({"people": N, "ratio": N / SEATS, "runs": 40, "rounds": 300, "burn": 60})
    rules = [("uniform", None, "①毎回まったくのくじ"), ("priority", 3, "②3回続けて落選した人を先に"),
             ("priority", 5, "②5回続けて落選した人を先に"), ("priority", 9, "②9回続けて落選した人を先に"),
             ("weight", None, "③落選の回数だけ口を足す")]
    base = []
    dists = {}
    for rule, k, name in rules:
        g, owner, wins, applied, yearly = simulate(rng, N, rule, k)
        st = gap_stats(g, yearly)
        key = rule if k is None else f"{rule}{k}"
        base.append({"rule": key, "name": name, **st})
        dists[key] = g
        print(key, round(time.time() - T0, 1), flush=True)
    bdf = pd.DataFrame(base)
    bdf.to_csv(RES / "base_rules.csv", index=False)
    out["base"] = base
    out["formula_uniform"] = {"gap_mean": r(N / SEATS, 3), "gap_sd": r(np.sqrt(1 - SEATS / N) / (SEATS / N), 3),
                              "gap_over24_pct": r((1 - SEATS / N) ** 24 * 100, 3),
                              "year_zero_win_pct": r((1 - SEATS / N) ** YEAR * 100, 3)}
    # 回数の分布（1〜40回と41回以上）
    hist = []
    for key, g in dists.items():
        for v in range(1, 41):
            hist.append({"rule": key, "tries": str(v), "share_pct": r((g == v).mean() * 100, 3)})
        hist.append({"rule": key, "tries": "41以上", "share_pct": r((g > 40).mean() * 100, 3)})
    pd.DataFrame(hist).to_csv(RES / "tries_distribution.csv", index=False)
    # data：①と②（5回）の、はじめの組の当たるまでの回数（最初の2,000件）
    pd.DataFrame({"gap_no": np.arange(1, 2001), "tries_uniform": dists["uniform"][:2000],
                  "tries_priority5": dists["priority5"][:2000],
                  "tries_weight": dists["weight"][:2000]}).to_csv(DATA / "tries_examples.csv", index=False)

    # (2) たまに申し込む人がまざる
    NF, NI, PI = 100, 334, 0.3
    ap = np.concatenate([np.ones(NF), np.full(NI, PI)])
    mixed = []
    for rule, k, reset, name in [("uniform", None, False, "①毎回まったくのくじ"),
                                 ("priority", 5, False, "②5回（休んでも続きから数える）"),
                                 ("priority", 5, True, "②5回（休むと0に戻す）"),
                                 ("weight", None, False, "③口を足す（休んでも続きから数える）"),
                                 ("weight", None, True, "③口を足す（休むと0に戻す）")]:
        g, owner, wins, applied, yearly = simulate(rng, NF + NI, rule, k, apply_p=ap, reset_on_skip=reset)
        for grp, m in [("毎回申し込む人", np.arange(NF + NI) < NF), ("3割の回だけ申し込む人", np.arange(NF + NI) >= NF)]:
            gm = g[m[owner]]
            y = yearly[:, :, m]
            mixed.append({"rule": name, "group": grp,
                          "win_per_application_pct": r(wins[:, m].sum() / applied[:, m].sum() * 100, 3),
                          "applications_per_year": r(applied[:, m].sum() / (yearly.shape[0] * 40 * m.sum()), 3),
                          "gap_mean_applications": r(gm.mean(), 3), "gap_sd_applications": r(gm.std(), 3),
                          "year_zero_win_pct": r((y == 0).mean() * 100, 3)})
        print("mixed", name, round(time.time() - T0, 1), flush=True)
    mdf = pd.DataFrame(mixed)
    mdf.to_csv(RES / "mixed_applicants.csv", index=False)
    out["mixed"] = {"frequent_people": NF, "occasional_people": NI, "occasional_apply_p": PI,
                    "mean_applicants": r(NF + NI * PI, 1), "rows": mixed}

    # (3) 確かめ
    grid = []
    for ratio in [2, 5, 10, 20]:
        n = SEATS * ratio
        for rule, k in [("uniform", None)] + [("priority", kk) for kk in sorted({1, 2, 3, 5, 8, 12, ratio - 1})] + [("weight", None)]:
            g, owner, wins, applied, yearly = simulate(rng, n, rule, k, runs=20, rounds=260, burn=60)
            st = gap_stats(g, yearly)
            grid.append({"ratio": ratio, "rule": rule if k is None else f"priority{k}", "k": k if k else "",
                         **st})
        print("grid", ratio, round(time.time() - T0, 1), flush=True)
    gdf = pd.DataFrame(grid)
    uni = gdf[gdf.rule == "uniform"].set_index("ratio")
    gdf["sd_vs_uniform"] = [r(row.gap_sd / uni.loc[row.ratio, "gap_sd"], 4) for row in gdf.itertuples()]
    gdf["mean_vs_ratio"] = [r(row.gap_mean / row.ratio, 4) for row in gdf.itertuples()]
    gdf.to_csv(RES / "grid.csv", index=False)
    best = gdf[gdf.rule != "uniform"].sort_values("gap_sd").groupby("ratio").first().reset_index()
    out["grid_summary"] = {
        "mean_vs_ratio_min": r(gdf.mean_vs_ratio.min()), "mean_vs_ratio_max": r(gdf.mean_vs_ratio.max()),
        "sd_vs_uniform_min": r(gdf[gdf.rule != "uniform"].sd_vs_uniform.min()),
        "sd_vs_uniform_max": r(gdf[gdf.rule != "uniform"].sd_vs_uniform.max()),
        "smallest_sd_rule_by_ratio": best[["ratio", "rule", "gap_sd", "sd_vs_uniform"]].to_dict(orient="records"),
        "weight_sd_vs_uniform": gdf[gdf.rule == "weight"][["ratio", "sd_vs_uniform", "gap_p99", "year_zero_win_pct"]].to_dict(orient="records"),
        "k_ratio_minus1": gdf[gdf.k.astype(str) == gdf.ratio.sub(1).astype(str)][["ratio", "rule", "gap_sd", "gap_max", "year_zero_win_pct"]].to_dict(orient="records"),
        "uniform": gdf[gdf.rule == "uniform"][["ratio", "gap_mean", "gap_sd", "gap_p99", "year_zero_win_pct"]].to_dict(orient="records")}

    # 図1：当たるまでの回数の分布
    fig, ax = plt.subplots(figsize=(8, 4.3))
    xs = np.arange(1, 41)
    for key, col, lab in [("uniform", GRAY, "①毎回まったくのくじ"), ("priority5", BLUE, "②5回続けて落選した人を先に"),
                          ("weight", ORANGE, "③落選の回数だけ口を足す")]:
        g = dists[key]
        ax.plot(xs, [(g == v).mean() * 100 for v in xs], color=col, marker="o", ms=3, lw=1.6, label=lab)
    ax.set_xlabel("当たるまでに申し込んだ回数（当たった回を含む）")
    ax.set_ylabel("割合（%）")
    ax.set_ylim(0, None)
    ax.set_xlim(0, 41)
    ax.set_title(f"平均はどれも{bdf.gap_mean.min():.3f}〜{bdf.gap_mean.max():.3f}回、そろい方が違う")
    ax.legend(frameon=False)
    save(fig, "a1177_tries_dist.png", SRC + "。200人が毎回申し込み、1回20席（倍率10倍）")

    # 図2：決まりごとの標準偏差と1年で一度も当たらない割合
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    labs = ["①くじ", "②3回", "②5回", "②9回", "③口を足す"]
    cols = [GRAY, BLUE, BLUE, BLUE, ORANGE]
    for ax, col, ttl, fmt in [(axes[0], "gap_sd", "当たるまでの回数の標準偏差（回）", "{:.3f}"),
                              (axes[1], "year_zero_win_pct", "24回（1年）で一度も当たらない人（%）", "{:.3f}")]:
        vals = bdf[col].values
        bars = ax.bar(np.arange(5), vals, color=cols, width=0.6)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.01, fmt.format(v), ha="center", fontsize=9)
        ax.set_xticks(np.arange(5), labs)
        ax.set_title(ttl, fontsize=11.5)
        ax.set_ylim(0, max(vals) * 1.15)
    fig.suptitle("落選を優先すると、ばらつきと一度も当たらない人が減る", fontsize=12.5, y=1.03)
    save(fig, "a1177_by_rule.png", SRC + "。40組×240回（はじめの60回を除く）")

    # 図3：たまに申し込む人（1回の申し込みあたりの当たり）
    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    names = [x["rule"] for x in mixed[::2]]
    for i, (grp, col) in enumerate([("毎回申し込む人", BLUE), ("3割の回だけ申し込む人", ORANGE)]):
        vals = [x["win_per_application_pct"] for x in mixed if x["group"] == grp]
        bars = ax.bar(np.arange(len(names)) + (i - 0.5) * 0.38, vals, 0.36, color=col, label=grp)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.2, f"{v:.3f}", ha="center", fontsize=8.5)
    ax.set_xticks(np.arange(len(names)), [n.replace("（", "\n（") for n in names], fontsize=8.5)
    ax.set_ylabel("1回の申し込みあたり当たった割合（%）")
    ax.set_ylim(0, 21)
    ax.set_title("休むと0に戻す数え方では、たまに申し込む人が下がる")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1177_occasional.png", SRC + "。毎回申し込む100人と、3割の回だけ申し込む334人")

    with open(RES / "a1177_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("done", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
