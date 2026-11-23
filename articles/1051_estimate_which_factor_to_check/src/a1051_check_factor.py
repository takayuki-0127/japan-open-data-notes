"""1051 要素の1つを実際に数えて確かめるなら、どの要素から確かめると外れがいちばん縮むのか？（架空のデータ）

架空の B市の、架空のサービス「自転車の出張修理」の1年の依頼件数を、5つの要素の掛け算で見込む。
本当の値は作成者が置く。見込む人の当て推量は、本当の値×exp(σ_i×z_i)（z は標準正規、要素どうしの相関 ρ）。
要素を1つだけ実際に数えて確かめる（台帳を引く、または n 件を数える）と、その要素は数えた値に入れかわる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, NullLocator
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1051
SRC = "架空の B市と架空のサービスの概算（作成者が乱数で作成、seed 1051）"
NAMES = ["①世帯数", "②自転車のある世帯の割合", "③自転車のある世帯の台数", "④1台が1年に修理の要る回数", "⑤修理のうち出張を頼む割合"]
TRUE = np.array([80000, 0.55, 1.6, 0.30, 0.08])
SIGMA = np.array([0.10, 0.25, 0.20, 0.60, 0.80])
N_PEOPLE = 200000
N_COUNT = 100


def measure(rng, k, n, m):
    """要素 k を数えた値（m 人分）。①は台帳でちょうど。②⑤は n 件の割合、③は n 世帯の台数の平均、④は n 台の1年の修理回数の平均。
    数えて0件だったときは 0.5件として扱う"""
    if k == 0:
        return np.full(m, TRUE[0])
    if k == 1:
        return np.maximum(rng.binomial(n, TRUE[1], m), 0.5) / n
    if k == 2:
        return 1 + rng.poisson((TRUE[2] - 1) * n, m) / n
    if k == 3:
        return np.maximum(rng.poisson(TRUE[3] * n, m), 0.5) / n
    return np.maximum(rng.binomial(n, TRUE[4], m), 0.5) / n


def formula_se2(k, n):
    """数えた値の対数の分散（近似の式）"""
    return [0.0, (1 - TRUE[1]) / (n * TRUE[1]), (TRUE[2] - 1) / n / TRUE[2] ** 2, 1 / (n * TRUE[3]), (1 - TRUE[4]) / (n * TRUE[4])][k]


def guesses(rng, m, sigma, rho):
    c = np.full((5, 5), rho); np.fill_diagonal(c, 1.0)
    z = rng.standard_normal((m, 5)) @ np.linalg.cholesky(c).T
    return TRUE * np.exp(sigma * z)


def run(rng, m=N_PEOPLE, sigma=SIGMA, rho=0.0, n=N_COUNT):
    g = guesses(rng, m, sigma, rho)
    truth = TRUE.prod()
    lr = {"確かめない": np.log(g.prod(1) / truth)}
    for k in range(5):
        h = g.copy(); h[:, k] = measure(rng, k, n, m)
        lr[f"{NAMES[k]}を確かめる"] = np.log(h.prod(1) / truth)
    return lr


def summ(lr):
    rows = []
    for name, x in lr.items():
        a = np.abs(x)
        rows.append({"strategy": name, "sd_log": round(float(x.std()), 4),
                     "median_miss_times": round(float(np.exp(np.median(a))), 4),
                     "p90_miss_times": round(float(np.exp(np.quantile(a, .9))), 4),
                     "within2x_pct": round(float((a <= np.log(2)).mean()) * 100, 2),
                     "median_ratio": round(float(np.exp(np.median(x))), 4)})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    lr = run(rng)
    base = summ(lr)
    form_sd = [round(float(np.sqrt((SIGMA ** 2).sum())), 4)]
    for k in range(5):
        v = (SIGMA ** 2).sum() - SIGMA[k] ** 2 + formula_se2(k, N_COUNT)
        form_sd.append(round(float(np.sqrt(v)), 4))
    base["formula_sd_log"] = form_sd
    base["formula_median_miss_times"] = [round(float(np.exp(0.6745 * v)), 4) for v in form_sd]   # 正規分布なら |外れ| の中央値は 0.6745σ
    base.to_csv(RES / "strategies_base.csv", index=False)
    # 1人ずつ：どの要素を確かめていたら、その人の外れがいちばん縮んだか
    keys = [f"{NAMES[k]}を確かめる" for k in range(5)]
    after = np.abs(np.vstack([lr[k] for k in keys]))
    best = after.argmin(0)
    best_share = {NAMES[k]: round(float((best == k).mean()) * 100, 2) for k in range(5)}
    # data：見込む人の最初の2,000人の当て推量
    g = guesses(np.random.default_rng(SEED + 1), 2000, SIGMA, 0.0)
    d = pd.DataFrame(g, columns=["households", "share_with_bike", "bikes_per_household", "repairs_per_bike", "share_onsite"])
    d.insert(0, "person", np.arange(1, 2001)); d["estimate"] = g.prod(1)
    d.round(5).to_csv(DATA / "guesses_2000.csv", index=False)

    # 数える件数 n ごとの、④と⑤を確かめたときの対数の標準偏差
    by_n = []
    for n in [10, 15, 20, 30, 50, 100, 200, 300]:
        l = run(np.random.default_rng(SEED * 10 + n), 100000, n=n)
        s = summ(l).set_index("strategy")
        row = {"n": n}
        for k in [3, 4]:
            key = f"{NAMES[k]}を確かめる"
            row[f"f{k+1}_sd_log"] = s.loc[key, "sd_log"]
            row[f"f{k+1}_median_miss"] = s.loc[key, "median_miss_times"]
            row[f"f{k+1}_formula_sd"] = round(float(np.sqrt((SIGMA ** 2).sum() - SIGMA[k] ** 2 + formula_se2(k, n))), 4)
        row["f5_zero_found_pct"] = round(float((1 - TRUE[4]) ** n) * 100, 2)
        by_n.append(row)
    by_n = pd.DataFrame(by_n)
    by_n.to_csv(RES / "by_count_n.csv", index=False)

    # 確かめ：n × 相関 ρ × ⑤の当て推量の外れ σ5（36通り）
    sens = []
    for n in [10, 20, 30, 50, 100, 300]:
        for rho in [0.0, 0.3]:
            for s5 in [0.5, 0.8, 1.0]:
                sg = SIGMA.copy(); sg[4] = s5
                l = run(np.random.default_rng(SEED * 1000 + len(sens)), 60000, sg, rho, n)
                s = summ(l).set_index("strategy")
                sd = {k: s.loc[f"{NAMES[k]}を確かめる", "sd_log"] for k in range(5)}
                md = {k: s.loc[f"{NAMES[k]}を確かめる", "median_miss_times"] for k in range(5)}
                sens.append({"n": n, "rho": rho, "sigma5": s5, "none_sd_log": s.loc["確かめない", "sd_log"],
                             "none_median_miss": s.loc["確かめない", "median_miss_times"],
                             **{f"f{k+1}_sd_log": sd[k] for k in range(5)},
                             **{f"f{k+1}_median_miss": md[k] for k in range(5)},
                             "best_by_sd": NAMES[min(sd, key=sd.get)], "best_by_median": NAMES[min(md, key=md.get)]})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    cnt_sd = sens.best_by_sd.value_counts().to_dict(); cnt_md = sens.best_by_median.value_counts().to_dict()
    disagree = sens[sens.best_by_sd != sens.best_by_median]
    s_n100 = sens[sens.n >= 100]
    summary = {"n_settings": int(len(sens)),
               "best_by_sd_counts": {k: int(v) for k, v in cnt_sd.items()},
               "best_by_median_counts": {k: int(v) for k, v in cnt_md.items()},
               "n_disagree": int(len(disagree)),
               "f5_best_by_sd_when_n_ge_100": int((s_n100.best_by_sd == NAMES[4]).sum()), "n_settings_n_ge_100": int(len(s_n100)),
               "f1_reduction_median_miss_pct_range": [
                   round(float(((sens.none_median_miss - sens.f1_median_miss) / (sens.none_median_miss - 1) * 100).min()), 2),
                   round(float(((sens.none_median_miss - sens.f1_median_miss) / (sens.none_median_miss - 1) * 100).max()), 2)],
               "best_median_miss_range": [round(float(sens[[f"f{k+1}_median_miss" for k in range(5)]].min(1).min()), 4),
                                          round(float(sens[[f"f{k+1}_median_miss" for k in range(5)]].min(1).max()), 4)],
               "none_median_miss_range": [float(sens.none_median_miss.min()), float(sens.none_median_miss.max())]}
    out = {"settings": {"true": TRUE.tolist(), "true_total": round(float(TRUE.prod()), 2), "sigma": SIGMA.tolist(),
                        "people": N_PEOPLE, "count_n": N_COUNT},
           "strategies_base": base.to_dict("records"), "best_factor_share_per_person_pct": best_share,
           "by_count_n": by_n.to_dict("records"), "sensitivity_summary": summary}
    json.dump(out, open(RES / "a1051_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：確かめる要素ごとの外れ（中央値の棒と90%点）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    b = base.iloc[::-1].reset_index(drop=True)
    cols = [ORANGE if "⑤" in s else (BLUE if "④" in s else (GRAY if "確かめない" in s else LIGHT)) for s in b.strategy]
    ax.barh(b.strategy, b.median_miss_times, color=cols)
    ax.plot(b.p90_miss_times, range(len(b)), "|", color=INK, ms=12, mew=1.5)
    for i, (v, p) in enumerate(zip(b.median_miss_times, b.p90_miss_times)):
        ax.text(v + 0.08, i, f"{v:.2f}倍", va="center", fontsize=8.5, color=INK)
    ax.axvline(1, color=GRAY, lw=.8, ls="--")
    ax.set_xlim(0, float(b.p90_miss_times.max()) * 1.08)
    ax.set_xlabel("外れの大きさ（倍。棒は中央値、縦線は90%点＝10人に1人はこれ以上。1ならぴったり）", fontsize=9.5)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_title(f"いちばん外れやすい⑤を数えると、外れの中央値がいちばん縮む（{N_COUNT}件を数える）")
    save(fig, "a1051_strategies.png", SRC)

    # 図2：数える件数 n と、④・⑤を確かめたあとの外れ
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(by_n.n, by_n.f4_median_miss, "o-", color=BLUE, label="④（1台の修理回数）を確かめる")
    ax.plot(by_n.n, by_n.f5_median_miss, "o-", color=ORANGE, label="⑤（出張を頼む割合）を確かめる")
    ax.axhline(base.iloc[0].median_miss_times, color=GRAY, lw=1, ls="--")
    ax.text(150, base.iloc[0].median_miss_times + 0.02, "確かめない", color=GRAY, fontsize=8.5, va="bottom")
    ax.set_xscale("log"); ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(by_n.n); ax.set_xticklabels([str(v) for v in by_n.n])
    ax.set_ylim(1, None)
    ax.set_xlabel("数える件数 n（対数の目盛り）"); ax.set_ylabel("外れの大きさの中央値（倍）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("数える件数が20〜30件だと、⑤を数えても④より縮まない")
    save(fig, "a1051_by_n.png", SRC)

    # 図3：1人ずつ見て、どの要素を確かめていたらいちばん縮んだか
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    vals = [best_share[nm] for nm in NAMES]
    ax.barh(NAMES[::-1], vals[::-1], color=[ORANGE, BLUE, LIGHT, LIGHT, LIGHT])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.tick_params(axis="y", labelsize=8.5)
    ax.set_xlabel("その人の外れがいちばん縮んだ要素だった割合（%、20万人）")
    ax.set_title("1人ずつ見ると、⑤がいちばんとは限らない")
    save(fig, "a1051_best_share.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
