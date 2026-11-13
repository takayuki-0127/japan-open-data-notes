"""547 自動車保険のような等級制度で、等級の分布が落ち着くまでに何年かかり、平均の割引率はどこに落ち着くのか（手法の解説・保険数理）

架空の等級制度（実在の等級表ではない）：
  等級 1〜20。新しく入る人は等級6。1年間に事故がなければ1つ上がる（20が上限）、事故1件につき3つ下がる（1が下限）。
  割引率は架空の表：等級6を0%として1等級ごとに5ポイント（等級1は25%割増、等級20は70%割引）。
事故の件数は1年ごとにポアソン（平均 λ、1人ごとに一定）。λ の人ごとのばらつきはガンマ分布（変動係数 0・0.5・1.0）。
等級の動きをマルコフ連鎖として、入った年からの分布の動き（年ごと）と、定常分布（長く続けたときの分布）を出す。
確かめとして、10万人を40年まで乱数で動かす（乱数の種 547）。数字は置いた制度と事故率で決まる。料率の助言ではない。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "出典：架空の等級制度と事故率（作成者が置いたもの、seed 547）"
G = 20
START = 6
DOWN = 3
DISC = np.array([5 * (g - START) for g in range(1, G + 1)], float)   # 割引率（%）、負は割増
YEARS = 200


def trans(lam):
    P = np.zeros((G, G))
    pk = stats.poisson.pmf(np.arange(0, 10), lam); pk[-1] += 1 - pk.sum()
    for g in range(G):
        P[g, min(g + 1, G - 1)] += pk[0]
        for k in range(1, len(pk)):
            P[g, max(g - DOWN * k, 0)] += pk[k]
    return P


def path(lams, w, years=YEARS):
    """λ の混ぜ合わせ（重み w）での、入った年からの等級分布（年×等級）。各 λ の分布も返す"""
    out = np.zeros((years + 1, G)); per = []
    for lam, ww in zip(lams, w):
        P = trans(lam); d = np.zeros(G); d[START - 1] = 1; rows = [d]
        for _ in range(years):
            d = d @ P; rows.append(d)
        rows = np.array(rows); per.append(rows); out += ww * rows
    return out, per


def stationary(lams, w):
    st = np.zeros(G)
    for lam, ww in zip(lams, w):
        P = trans(lam); ev, vec = np.linalg.eig(P.T)
        v = np.real(vec[:, np.argmin(np.abs(ev - 1))]); v = v / v.sum(); st += ww * v
    return st


def gamma_grid(mean, cv, k=200):
    if cv == 0:
        return np.array([mean]), np.array([1.0])
    a = 1 / cv ** 2; q = (np.arange(k) + 0.5) / k
    return stats.gamma.ppf(q, a, scale=mean / a), np.full(k, 1 / k)


def settle(d, st):
    tv = 0.5 * np.abs(d - st).sum(1)
    return tv, int(np.argmax(tv < 0.05)), int(np.argmax(tv < 0.01))


def main():
    rows = []
    for lam in [0.03, 0.05, 0.07, 0.10, 0.15, 0.20]:
        for cv in [0.0, 0.5, 1.0]:
            L, w = gamma_grid(lam, cv)
            d, _ = path(L, w); st = stationary(L, w)
            tv, y05, y01 = settle(d, st)
            rows.append(dict(mean_lambda=lam, cv=cv, years_tv_below_005=y05, years_tv_below_001=y01,
                             stationary_mean_disc=float(st @ DISC), stationary_mean_grade=float(st @ np.arange(1, G + 1)),
                             stationary_share_top=float(st[-1]), stationary_share_surcharge=float(st[:START - 1].sum()),
                             mean_disc_year1=float(d[1] @ DISC), mean_disc_year10=float(d[10] @ DISC), mean_disc_year20=float(d[20] @ DISC)))
    sm = pd.DataFrame(rows); sm.to_csv(RES / "summary.csv", index=False, float_format="%.4f"); print(sm.to_string())

    # 平均0.07・変動係数1.0 の集団で、事故率の低い人と高い人
    L, w = gamma_grid(0.07, 1.0)
    st_each = np.array([stationary([l], [1]) for l in L])
    lo, hi = L < np.quantile(L, 0.25), L > np.quantile(L, 0.75)
    grp = dict(low_q_lambda=float(L[lo].mean()), high_q_lambda=float(L[hi].mean()),
               low_q_disc=float((st_each[lo] @ DISC).mean()), high_q_disc=float((st_each[hi] @ DISC).mean()),
               low_q_grade=float((st_each[lo] @ np.arange(1, G + 1)).mean()), high_q_grade=float((st_each[hi] @ np.arange(1, G + 1)).mean()))
    # 割引で払う額の比（割引後の保険料 ∝ 1−割引率）と、事故率の比
    grp["premium_ratio_high_low"] = float((1 - (st_each[hi] @ DISC).mean() / 100) / (1 - (st_each[lo] @ DISC).mean() / 100))
    grp["lambda_ratio_high_low"] = grp["high_q_lambda"] / grp["low_q_lambda"]
    print(grp)

    # 乱数で確かめる：10万人、λ はガンマ（平均0.07、変動係数1.0）
    rng = np.random.default_rng(547); N = 100_000
    lam = rng.gamma(1.0, 0.07, N); g = np.full(N, START - 1)
    sim = [DISC[g].mean()]
    for _ in range(40):
        k = rng.poisson(lam); g = np.where(k == 0, np.minimum(g + 1, G - 1), np.maximum(g - DOWN * k, 0)); sim.append(DISC[g].mean())
    dmix, per = path(L, w, 40)
    check = dict(sim_mean_disc_year10=sim[10], calc_mean_disc_year10=float(dmix[10] @ DISC),
                 sim_mean_disc_year40=sim[40], calc_mean_disc_year40=float(dmix[40] @ DISC))
    print(check)
    json.dump({"summary": sm.round(4).to_dict("records"), "groups_cv1": grp, "simulation_check": check,
               "disc_table": DISC.tolist()}, open(RES / "a547_main.json", "w"), ensure_ascii=False, indent=1)
    pd.DataFrame({"year": range(41), "sim_mean_disc": sim, "calc_mean_disc": dmix @ DISC}).to_csv(RES / "sim_check.csv", index=False, float_format="%.4f")

    # 図1：平均の割引率の動き（λ 0.03・0.07・0.15、ばらつきなし）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for lam, c in [(0.03, BLUE), (0.07, GREEN), (0.15, ORANGE)]:
        d, _ = path([lam], [1]); st = stationary([lam], [1])
        ax.plot(range(81), (d @ DISC)[:81], color=c, lw=2, label=f"事故率 {lam}件/年")
        ax.axhline(st @ DISC, color=c, ls="--", lw=0.9)
        _, y05, _ = settle(d, st)
        ax.plot(y05, d[y05] @ DISC, "o", color=c)
        ax.annotate(f"{y05}年", (y05, d[y05] @ DISC), xytext=(4, -14), textcoords="offset points", fontsize=9, color=c)
    ax.set_xlabel("入ってからの年数"); ax.set_ylabel("平均の割引率（%）")
    ax.set_title("平均の割引率は何年で落ち着くか（点は分布の差が5%を切った年、点線は定常）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a547_mean_disc_path.png", SRC)

    # 図2：定常分布（λ 0.03 と 0.15）
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); x = np.arange(1, G + 1)
    for lam, c, off in [(0.03, BLUE, -0.2), (0.15, ORANGE, 0.2)]:
        st = stationary([lam], [1]); ax.bar(x + off, st * 100, 0.4, color=c, label=f"事故率 {lam}件/年（平均の割引率 {st @ DISC:.1f}%）")
    ax.set_xticks(x); ax.set_xlabel("等級（6で入り、事故なしで1つ上がり、事故1件で3つ下がる）"); ax.set_ylabel("長く続けたときの割合（%）")
    ax.set_title("長く続けたときの等級の分布（定常分布）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a547_stationary.png", SRC)

    # 図3：事故率の平均と定常の平均割引率、ばらつき別
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for cv, c in [(0.0, GRAY), (0.5, BLUE), (1.0, ORANGE)]:
        s = sm[sm.cv == cv]; ax.plot(s.mean_lambda, s.stationary_mean_disc, "-o", color=c, label=f"事故率のばらつき 変動係数 {cv}")
    ax.set_xlabel("集団の平均の事故率（件/年）"); ax.set_ylabel("定常での平均の割引率（%）")
    ax.set_title("平均の事故率が同じでも、人ごとのばらつきで落ち着く先は変わる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a547_disc_vs_lambda.png", SRC)


if __name__ == "__main__":
    main()
