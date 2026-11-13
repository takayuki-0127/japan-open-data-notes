"""530 裾の重いデータで2つの群を比べると、t 検定と順位の検定で、差を見つける力はどれだけ違うのか（保険数理・リスク）

架空の2群（たとえば2つの区分の1件あたりの損害額）。
- 分布：正規（平均10・標準偏差3）、対数正規（σ=1）、パレート型（ロマックス、形 α=3 と α=1.5。α=1.5は分散が無限）
- 差：2つ目の群をすべて k 倍する（k=1：差なし、k=1.25・1.5）
- 1群の件数 n = 20・50・200
- 検定：ウェルチの t 検定、マン・ホイットニーの順位検定、対数をとってからのウェルチの t 検定（いずれも両側5%）
差を見つける割合（検出力）と、差がないのに見つかる割合（誤検出率）を出す。乱数の種 530、各場面 4,000回。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の2群の損害額（作成者が乱数で作成、seed 530）"
SIMS = 4000
NS = [20, 50, 200]
KS = [1.0, 1.25, 1.5]
DISTS = ["正規", "対数正規", "パレートα3", "パレートα1.5"]
TESTS = {"welch": "ウェルチの t", "mw": "順位（マン・ホイットニー）", "logt": "対数の t"}


def draw(rng, dist, size):
    if dist == "正規":
        x = rng.normal(10, 3, size)
        return np.clip(x, 0.01, None)            # 損害額なので負にしない（ほぼ起きない）
    if dist == "対数正規":
        return rng.lognormal(0, 1, size)
    a = 3.0 if dist == "パレートα3" else 1.5
    return rng.pareto(a, size) + 1e-9            # 0付近から始まる裾の重い分布


def run(x, y):
    p_w = stats.ttest_ind(x, y, axis=1, equal_var=False).pvalue
    p_m = stats.mannwhitneyu(x, y, axis=1, alternative="two-sided").pvalue
    p_l = stats.ttest_ind(np.log(x), np.log(y), axis=1, equal_var=False).pvalue
    return {"welch": p_w, "mw": p_m, "logt": p_l}


def main():
    rng = np.random.default_rng(530)
    rows = []
    for dist in DISTS:
        for n in NS:
            for k in KS:
                x = draw(rng, dist, (SIMS, n))
                y = draw(rng, dist, (SIMS, n)) * k
                ps = run(x, y)
                for t, p in ps.items():
                    rows.append(dict(dist=dist, n=n, k=k, test=t, reject=round(float((p < 0.05).mean()), 4)))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "summary.csv", index=False)
    piv = {d: {f"n={n}": {f"k={k}": {TESTS[t]: float(df[(df.dist == d) & (df.n == n) & (df.k == k) & (df.test == t)].reject.iloc[0]) for t in TESTS} for k in KS} for n in NS} for d in DISTS}
    json.dump({"sims": SIMS, "棄却率（k=1は誤検出率、それ以外は検出力）": piv}, open(RES / "a530_main.json", "w"), ensure_ascii=False, indent=1)

    cols = {"welch": BLUE, "mw": ORANGE, "logt": GREEN}
    # 図1：n=50・k=1.25 の検出力
    fig, ax = plt.subplots(figsize=(9, 4.3))
    w = 0.26
    for j, t in enumerate(TESTS):
        s = df[(df.n == 50) & (df.k == 1.25) & (df.test == t)].set_index("dist").loc[DISTS]
        xs = np.arange(len(DISTS)) + (j - 1) * w
        ax.bar(xs, s.reject * 100, w, color=cols[t], label=TESTS[t])
        for x_, y_ in zip(xs, s.reject * 100):
            ax.text(x_, y_ + 1, f"{y_:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(range(len(DISTS))); ax.set_xticklabels(DISTS)
    ax.set_ylabel("差を見つける割合（%）"); ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("1群50件・2つ目の群が1.25倍：裾が重いほど t 検定は差を見落とす", fontsize=12)
    save(fig, "a530_power_n50.png", SRC)

    # 図2：件数ごとの検出力（対数正規とパレートα1.5、k=1.25）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for j, d in enumerate(["対数正規", "パレートα1.5"]):
        for t in TESTS:
            s = df[(df.dist == d) & (df.k == 1.25) & (df.test == t)]
            ax[j].plot(s.n, s.reject * 100, marker="o", color=cols[t], label=TESTS[t])
        ax[j].set_xscale("log"); ax[j].minorticks_off(); ax[j].set_xticks(NS); ax[j].set_xticklabels([str(n) for n in NS])
        ax[j].set_xlabel("1群の件数"); ax[j].set_title(f"{d}・1.25倍", fontsize=11)
    ax[0].set_ylabel("差を見つける割合（%）"); ax[0].legend(frameon=False, fontsize=9)
    fig.suptitle("件数が増えても、裾が重いと t 検定の見つける力は伸びにくい", fontsize=12, y=1.03)
    save(fig, "a530_power_by_n.png", SRC)

    # 図3：誤検出率（k=1）
    fig, ax = plt.subplots(figsize=(9, 4.3))
    for j, t in enumerate(TESTS):
        s = df[(df.n == 20) & (df.k == 1.0) & (df.test == t)].set_index("dist").loc[DISTS]
        xs = np.arange(len(DISTS)) + (j - 1) * w
        ax.bar(xs, s.reject * 100, w, color=cols[t], label=TESTS[t])
        for x_, y_ in zip(xs, s.reject * 100):
            ax.text(x_, y_ + 0.15, f"{y_:.1f}", ha="center", fontsize=8.5)
    ax.axhline(5, color=INK, ls=":", lw=1)
    ax.set_xticks(range(len(DISTS))); ax.set_xticklabels(DISTS)
    ax.set_ylabel("差がないのに見つかる割合（%）"); ax.set_ylim(0, 8); ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=3)
    ax.set_title("差がないとき（1群20件）：t 検定は裾が重いと控えめになりすぎる", fontsize=12)
    save(fig, "a530_false_positive.png", SRC)
    print(df.pivot_table(index=["dist", "n", "k"], columns="test", values="reject").to_string())


if __name__ == "__main__":
    main()
