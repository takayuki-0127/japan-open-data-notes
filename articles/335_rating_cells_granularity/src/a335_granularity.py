"""335 料率の区分を細かくすると、翌年の外れは小さくなるのか、大きくなるのか（架空の地域別データ、seed 335）"""
import json
import numpy as np, pandas as pd
from common import *

SEED, REPS = 335, 300
NREG, NDIS, NAREA = 8, 40, 200                 # 8地方 → 40地区 → 200地域（5つずつ入れ子）
BASE = 0.06
SD = dict(region=0.15, district=0.10, area=0.07)   # 事故率の本当の差（対数の標準偏差）：地方＞地区＞地域
YEARS = 3                                      # 料率を作るのに使う過去の年数
SIZES = [20_000, 100_000, 500_000, 2_500_000]  # 契約の総数
LEVELS = [("全体で1つ", 1), ("8地方", 8), ("40地区", 40), ("200地域", 200)]


def make_world(rng, total):
    dis_of_area = np.repeat(np.arange(NDIS), NAREA // NDIS); reg_of_dis = np.repeat(np.arange(NREG), NDIS // NREG)
    reg_of_area = reg_of_dis[dis_of_area]
    lam = BASE * np.exp(rng.normal(0, SD["region"], NREG)[reg_of_area] + rng.normal(0, SD["district"], NDIS)[dis_of_area] + rng.normal(0, SD["area"], NAREA))
    w = rng.lognormal(0, 1.0, NAREA); expo = np.maximum(np.round(total * w / w.sum()), 1)       # 地域の契約数は大小さまざま
    return dict(lam=lam, expo=expo, group={1: np.zeros(NAREA, int), 8: reg_of_area, 40: dis_of_area, 200: np.arange(NAREA)})


def group_rate(claims, expo, g, k):
    c = np.bincount(g, claims, k); e = np.bincount(g, expo, k); return (c / e)[g]


def credibility(claims, expo, world):
    """細かい区分の実績を、1つ上の区分の率に寄せる（上から順に。寄せる強さはデータから決める）"""
    rate = np.full(NAREA, claims.sum() / expo.sum())
    for k in (8, 40, 200):
        g = world["group"][k]; c = np.bincount(g, claims, k); e = np.bincount(g, expo, k); parent = np.bincount(g, rate * expo, k) / e
        obs = c / e
        # 区分の間の本当の差（分散）を、実績の散らばりから事故の偶然の分を引いて見積もる
        within = (parent / e)                                   # ポアソンの偶然による分散 ≒ 率÷契約数
        a = max(np.average((obs - parent) ** 2 - within, weights=e), 0.0)
        z = a / (a + within) if a > 0 else np.zeros(k)
        rate = (z * obs + (1 - z) * parent)[g]
    return rate


def one_run(rng, total):
    w = make_world(rng, total); lam, expo = w["lam"], w["expo"]
    hist = rng.poisson(lam * expo * YEARS); nxt = rng.poisson(lam * expo)                       # 過去3年の合計と、次の年
    out = {}
    for name, k in LEVELS:
        pred = group_rate(hist, expo * YEARS, w["group"][k], k)
        out[name] = pred
    out["200地域を上の区分に寄せる"] = credibility(hist, expo * YEARS, w)
    res = {}
    for name, pred in out.items():
        res[name] = dict(vs_true=np.sqrt(np.average((pred / lam - 1) ** 2, weights=expo)),          # 本当の事故率からのずれ
                         vs_next=np.sqrt(np.average((pred - nxt / expo) ** 2, weights=expo)) / (nxt.sum() / expo.sum()),   # 次の年の実績からのずれ
                         small=np.sqrt(np.average((pred / lam - 1) ** 2, weights=expo * (expo <= np.quantile(expo, .25)))),
                         large=np.sqrt(np.average((pred / lam - 1) ** 2, weights=expo * (expo >= np.quantile(expo, .75)))))
    # 年ごとの振れ：200地域の単年の事故率が、前の年からどれだけ動くか（本当の率は動いていない）
    y1 = rng.poisson(lam * expo) / expo; y2 = rng.poisson(lam * expo) / expo
    return res, expo, np.abs(y2 - y1) / lam


def main():
    rng = np.random.default_rng(SEED); names = [n for n, _ in LEVELS] + ["200地域を上の区分に寄せる"]
    rows = []; swing = []
    for total in SIZES:
        acc = {n: {k: [] for k in ("vs_true", "vs_next", "small", "large")} for n in names}
        for _ in range(REPS):
            r, expo, sw = one_run(rng, total)
            for n in names:
                for k in acc[n]: acc[n][k].append(r[n][k])
            if total in (100_000, 500_000): swing.append(pd.DataFrame({"total": total, "expo": expo, "swing": sw}))
        for n in names:
            rows.append(dict(total=total, cells=n, avg_per_area=total / NAREA, **{k: float(100 * np.mean(v)) for k, v in acc[n].items()}))
    T = pd.DataFrame(rows); T.round(3).to_csv(RES / "error_by_granularity.csv", index=False)
    S = pd.concat(swing); bins = [0, 100, 300, 1000, 3000, 10000, 1e9]; lab = ["〜100件", "100〜300", "300〜1,000", "1,000〜3,000", "3,000〜1万", "1万件〜"]
    S["size"] = pd.cut(S.expo, bins, labels=lab)
    sw = S.groupby("size", observed=True).swing.agg(median="median", p90=lambda x: x.quantile(.9), n="size").reset_index()
    sw["median"] *= 100; sw["p90"] *= 100; sw.round(2).to_csv(RES / "year_to_year_swing.csv", index=False)
    best = {str(t): T[(T.total == t) & (T.cells.isin([n for n, _ in LEVELS]))].sort_values("vs_true").cells.iloc[0] for t in SIZES}
    res = dict(settings=dict(seed=SEED, reps=REPS, levels=[n for n, _ in LEVELS], sd=SD, base=BASE, years=YEARS, sizes=SIZES),
               best_plain=best, table=T.round(3).to_dict(orient="records"), swing=sw.round(2).to_dict(orient="records"))
    json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    w = make_world(np.random.default_rng(SEED), 100_000); h = np.random.default_rng(SEED + 1).poisson(w["lam"] * w["expo"] * YEARS)
    pd.DataFrame({"area": np.arange(NAREA) + 1, "district": w["group"][40] + 1, "region": w["group"][8] + 1, "policies": w["expo"].astype(int),
                  "true_rate": w["lam"].round(5), "claims_3y": h}).to_csv(DATA / "example_areas_100k.csv", index=False)

    # 図1：区分の細かさと誤差（本当の事故率からのずれ）
    fig, ax = plt.subplots(figsize=(8.2, 4.4)); cols = [ORANGE, BLUE, GREEN, "#8a5cc2"]
    for t, c in zip(SIZES, cols):
        d = T[(T.total == t) & (T.cells.isin([n for n, _ in LEVELS]))]
        ax.plot(range(4), d.vs_true, "o-", color=c, label=f"契約{t//10000:,}万件（1地域平均{t//NAREA:,}件）")
        dd = T[(T.total == t) & (T.cells == "200地域を上の区分に寄せる")]; ax.plot([4], dd.vs_true, "D", color=c)
    ax.set_xticks(range(5)); ax.set_xticklabels([n for n, _ in LEVELS] + ["200地域を\n上の区分に寄せる"]); ax.set_ylabel("料率の、本当の事故率からのずれ（%）"); ax.set_ylim(0)
    ax.legend(frameon=False, fontsize=8.5); ax.set_title("細かくして良くなるのは、契約の数が足りているときだけ")
    save(fig, "a335_error_by_granularity.png", "架空の地域別データ（過去3年の実績で料率を作る。300回の平均、seed 335）。ずれは契約数で重みをつけたRMSE", y=-0.06)

    # 図2：小さい地域と大きい地域（契約50万件）
    d = T[T.total == 500_000]; fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(5); wd = 0.38
    ax.bar(x - wd / 2, d.small, wd, color=ORANGE, label="契約が少ない下位25%の地域"); ax.bar(x + wd / 2, d.large, wd, color=BLUE, label="契約が多い上位25%の地域")
    ax.set_xticks(x); ax.set_xticklabels([n for n, _ in LEVELS] + ["200地域を\n上の区分に寄せる"]); ax.set_ylabel("本当の事故率からのずれ（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("細かい区分は大きい地域で当たり、小さい地域で外れる（契約50万件）")
    save(fig, "a335_small_vs_large.png", "架空の地域別データ（300回の平均）。地域の契約数は大小さまざまに置いた", y=-0.06)

    # 図3：年ごとの振れ
    fig, ax = plt.subplots(figsize=(7.8, 4.2)); x = np.arange(len(sw))
    ax.bar(x, sw["p90"], color=LIGHT, label="10地域に1つはこれ以上動く"); ax.bar(x, sw["median"], color=BLUE, label="真ん中の地域")
    for i, (m, p) in enumerate(zip(sw["median"], sw["p90"])): ax.text(i, p + 1, f"{p:.0f}%", ha="center", fontsize=8.5); ax.text(i, m + 1, f"{m:.0f}%", ha="center", fontsize=8.5, color="white" if m > 12 else INK)
    ax.set_xticks(x); ax.set_xticklabels(sw["size"]); ax.set_xlabel("地域の契約数"); ax.set_ylabel("単年の事故率が前の年から動いた幅（本当の率に対する%）")
    ax.legend(frameon=False, fontsize=9); ax.set_title("本当の事故率が変わらなくても、小さい地域の実績は年ごとに大きく動く")
    save(fig, "a335_year_to_year_swing.png", "架空の地域別データ。本当の事故率は2年とも同じで、動いた分はすべて偶然", y=-0.06)
    print(T.round(2).to_string()); print(sw.round(1).to_string()); print(best)


if __name__ == "__main__":
    main()
