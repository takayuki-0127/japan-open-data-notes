"""520 0を含むデータを log(x+1) で変換して回帰すると、係数はどれだけずれるのか（統計の考え方）

架空のデータ。2つのグループ（x=0 と x=1、各半分、合計2万人）の、1年の支出額 y（円）。
y は「使うかどうか」と「使うならいくら」の2段階で作る：
  使う確率 = ロジスティック(a0 + a1・x)、x=0 で40%
  使うときの額 = 5,000円 × exp(β・x + ε)、ε は平均0・標準偏差1.2の正規分布
本当の効果（x=1 の平均 ÷ x=0 の平均 − 1）を、次の方法で推定して比べる：
  (1) log(y+1) を x で回帰（円のまま） (2) 千円にしてから log(y+1) (3) log(y+c) の c を変える
  (4) ポアソン回帰（平均の比を直接推定） (5) 2段階モデル（使うかどうか＋使った人の log(y)）
各200回くり返す。x が 0/1 なので、回帰の係数はグループごとの平均から計算できる（statsmodels で1回分を確かめる）。
"""
import json
import numpy as np, pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 520
SRC = "架空の支出額（作成者が乱数で作成、seed 520）"
N, REPS, SIG, BASE, P0 = 20_000, 200, 1.2, 5000.0, 0.40
SCEN = {"A": dict(beta=0.2, a1=0.0, label="使う額だけ増える"),
        "B": dict(beta=0.0, a1=0.5, label="使う人だけ増える"),
        "C": dict(beta=0.2, a1=0.5, label="両方増える")}
CS = [0.01, 0.1, 1, 10, 100, 1000, 10_000, 100_000]


def gen(beta, a1, rng):
    x = np.repeat([0, 1], N // 2)
    a0 = np.log(P0 / (1 - P0)); p = 1 / (1 + np.exp(-(a0 + a1 * x)))
    use = rng.random(N) < p
    y = np.where(use, BASE * np.exp(beta * x + rng.normal(0, SIG, N)), 0.0)
    return x, y


def truth(beta, a1):
    a0 = np.log(P0 / (1 - P0)); p1 = 1 / (1 + np.exp(-(a0 + a1)))
    return p1 / P0 * np.exp(beta) - 1


def est(x, y):
    o = {}
    for c in CS:
        b = np.log(y[x == 1] + c).mean() - np.log(y[x == 0] + c).mean()
        o[f"log_y_plus_{c:g}yen"] = np.exp(b) - 1
    o["log1p_yen"] = o["log_y_plus_1yen"]
    o["log1p_thousand"] = o["log_y_plus_1000yen"]           # log(y/1000 + 1) = log(y+1000) − log1000
    o["poisson"] = y[x == 1].mean() / y[x == 0].mean() - 1
    pos = y > 0; q1 = pos[x == 1].mean(); q0 = pos[x == 0].mean()
    b2 = np.log(y[pos & (x == 1)]).mean() - np.log(y[pos & (x == 0)]).mean()
    o["two_part"] = q1 / q0 * np.exp(b2) - 1
    # 合計の予測：log(y+1)（円）で当てはめた値を exp(·)−1 で戻して合計する
    f0 = np.log(y[x == 0] + 1).mean(); f1 = np.log(y[x == 1] + 1).mean()
    o["sum_ratio_log1p_naive"] = ((np.exp(f0) - 1) * (x == 0).sum() + (np.exp(f1) - 1) * (x == 1).sum()) / y.sum()
    o["sum_ratio_poisson"] = 1.0                            # ポアソン回帰は定数項があれば合計を必ず合わせる
    lv = np.log(y[pos]); s2 = lv.var()                      # 2段階：対数正規の戻し（exp(σ²/2)）を入れる
    o["sum_ratio_two_part"] = sum(pos[x == g].mean() * np.exp(lv[x[pos] == g].mean() + s2 / 2) * (x == g).sum() for g in [0, 1]) / y.sum()
    return o


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for k, s in SCEN.items():
        tv = truth(s["beta"], s["a1"])
        for r in range(REPS):
            x, y = gen(s["beta"], s["a1"], rng)
            rows.append(dict(scen=k, rep=r, truth=tv, zero_share=float((y == 0).mean()), **est(x, y)))
    df = pd.DataFrame(rows)
    agg = df.drop(columns="rep").groupby("scen").mean()
    agg.round(5).to_csv(RES / "mean_by_scenario.csv")
    # statsmodels で1回分を確かめる
    r2 = np.random.default_rng(SEED + 1); x, y = gen(0.2, 0.5, r2); X = sm.add_constant(x.astype(float))
    ols = sm.OLS(np.log1p(y), X).fit().params[1]; poi = sm.GLM(y, X, family=sm.families.Poisson()).fit().params[1]
    e = est(x, y)
    check = dict(ols_log1p_sm=round(float(np.exp(ols) - 1), 6), ols_log1p_closed=round(float(e["log1p_yen"]), 6),
                 poisson_sm=round(float(np.exp(poi) - 1), 6), poisson_closed=round(float(e["poisson"]), 6))
    cols = ["truth", "zero_share", "log1p_yen", "log1p_thousand", "poisson", "two_part", "sum_ratio_log1p_naive", "sum_ratio_poisson", "sum_ratio_two_part"]
    sd = df.groupby("scen")[["log1p_yen", "poisson", "two_part"]].std()
    out = dict(seed=SEED, n=N, reps=REPS, sigma=SIG, base_yen=BASE, p0=P0,
               scenarios={k: dict(**{c: round(float(agg.loc[k, c]), 4) for c in cols},
                                  sd_over_reps={c: round(float(sd.loc[k, c]), 4) for c in sd.columns},
                                  by_c={f"{c:g}": round(float(agg.loc[k, f"log_y_plus_{c:g}yen"]), 4) for c in CS})
                          for k in SCEN}, statsmodels_check=check)
    json.dump(out, open(RES / "a520_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=0))

    # 図1：方法ごとの推定（％）
    meths = [("log1p_yen", "log(y+1)・円", ORANGE), ("log1p_thousand", "log(y+1)・千円", LIGHT), ("poisson", "ポアソン回帰", BLUE), ("two_part", "2段階モデル", GREEN)]
    fig, ax = plt.subplots(figsize=(7.6, 4.4)); xs = np.arange(3); w = 0.19
    for j, (c, lab, col) in enumerate(meths):
        v = [agg.loc[k, c] * 100 for k in SCEN]
        ax.bar(xs + (j - 1.5) * w, v, w, color=col, label=lab)
        for xx, vv in zip(xs + (j - 1.5) * w, v): ax.text(xx, vv + (1 if vv >= 0 else -1), f"{vv:.0f}", ha="center", va="bottom" if vv >= 0 else "top", fontsize=8)
    for i, k in enumerate(SCEN):
        ax.hlines(agg.loc[k, "truth"] * 100, i - 0.42, i + 0.42, color=INK, lw=2, ls="--")
    ax.set_xticks(xs, [f"{SCEN[k]['label']}\n本当 +{agg.loc[k,'truth']*100:.0f}%" for k in SCEN])
    ax.set_ylabel("推定した効果（x=1 の平均が何%多いか）"); ax.set_ylim(-5, max(260, float(agg[['log1p_yen']].max().iloc[0] * 100) + 25))
    ax.set_title("log(y+1) の係数は、使う人が増えると本当の効果と大きくずれる（破線＝本当の値）")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left")
    save(fig, "a520_by_method.png", SRC + "。0の割合は54〜60%、各200回の平均")

    # 図2：c を変えたとき（シナリオ C）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for k, col in [("A", BLUE), ("C", ORANGE)]:
        v = [agg.loc[k, f"log_y_plus_{c:g}yen"] * 100 for c in CS]
        ax.plot(CS, v, "o-", color=col, lw=2.2, label=f"{SCEN[k]['label']}（本当 +{agg.loc[k,'truth']*100:.0f}%）")
        ax.axhline(agg.loc[k, "truth"] * 100, color=col, ls="--", lw=1)
    ax.set_xscale("log"); ax.set_xlabel("足す数 c（円、対数）  ※ 千円にして +1 は c=1,000円と同じ")
    ax.set_ylabel("log(y+c) から出した効果（%）")
    ax.set_title("足す数 c（＝単位の選び方）しだいで、推定した効果が何倍も変わる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a520_by_c.png", SRC + "。破線はそれぞれの本当の値")

    # 図3：合計の予測
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    labs = ["log(y+1) を exp(·)−1 で戻す", "2段階モデル（戻しの補正あり）", "ポアソン回帰"]
    v = [agg.loc["C", "sum_ratio_log1p_naive"] * 100, agg.loc["C", "sum_ratio_two_part"] * 100, agg.loc["C", "sum_ratio_poisson"] * 100]
    b_ = ax.barh(labs[::-1], v[::-1], color=[BLUE, GREEN, ORANGE])
    for bb, vv in zip(b_, v[::-1]): ax.text(vv + 1, bb.get_y() + bb.get_height() / 2, f"{vv:.1f}%", va="center", fontsize=10)
    ax.axvline(100, color=INK, ls="--", lw=1); ax.set_xlim(0, 120); ax.set_xlabel("予測の合計 ÷ 実際の合計（%）")
    ax.set_title("log(y+1) の予測をそのまま戻すと、合計は実際の約1%にしかならない")
    save(fig, "a520_sum.png", SRC + "。「両方増える」の場合、各200回の平均")


if __name__ == "__main__":
    main()
