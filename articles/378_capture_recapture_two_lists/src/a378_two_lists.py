"""A378 重なりのある2つの名簿から、全体の人数はどこまで当てられるのか
架空の全体10万人から2つの名簿を作り、重なりから全体を推定する方法（リンカーン・ピーターセン、チャップマンの補正）が、
前提どおりのとき・崩れたときにどれだけ外れるかを数える。乱数の種は378。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, N, REPS = 378, 100_000, 2000
SRC = "架空のデータ（作成者が乱数で作成、seed 378）"


def chapman(n1, n2, m):
    est = (n1 + 1) * (n2 + 1) / (m + 1) - 1
    var = (n1 + 1) * (n2 + 1) * (n1 - m) * (n2 - m) / ((m + 1) ** 2 * (m + 2))
    return est, np.sqrt(var)


def summarize(est, se, true=N):
    err = (est / true - 1) * 100
    cover = ((est - 1.96 * se <= true) & (true <= est + 1.96 * se)).mean() * 100
    return dict(bias_pct=float(err.mean()), rmse_pct=float(np.sqrt((err ** 2).mean())), p10=float(np.percentile(err, 10)), p90=float(np.percentile(err, 90)), cover95=float(cover))


def logit(p): return np.log(p / (1 - p))
def expit(x): return 1 / (1 + np.exp(-x))


_ICPT = {}
def intercept(sd):
    """平均の載る割合が10%になる切片（載りやすさ z は標準正規）。sd ごとに1回だけ求める"""
    if sd not in _ICPT:
        z = np.random.default_rng(12345).normal(0, 1, 400_000); lo, hi = -10.0, 5.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if expit(mid + sd * z).mean() > 0.10: hi = mid
            else: lo = mid
        _ICPT[sd] = mid
    return _ICPT[sd]


def draw_lists(rng, p1, p2):
    """p1・p2：1人ずつの「名簿1・名簿2に載る確率」。載るかどうかは人ごとに独立に決める"""
    a = rng.random(len(p1)) < p1; b = rng.random(len(p2)) < p2
    return a, b


def main():
    rng = np.random.default_rng(SEED)
    res = {}

    # ---- 1. 前提どおり：だれも同じ確率で載り、2つの名簿は独立 ----
    rows = []
    for p in (0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40):
        n1 = rng.binomial(N, p, REPS); n2 = rng.binomial(N, p, REPS); m = rng.hypergeometric(n1, N - n1, n2)
        est, se = chapman(n1, n2, m); lp = np.where(m > 0, n1 * n2 / np.maximum(m, 1), np.nan)
        r = summarize(est, se); r.update(coverage=p, mean_overlap=float(m.mean()), lp_undefined_pct=float((m == 0).mean() * 100),
                                         lp_bias_pct=float((np.nanmean(lp) / N - 1) * 100)); rows.append(r)
    ideal = pd.DataFrame(rows); ideal.to_csv(RES / "ideal_by_list_size.csv", index=False)

    # ---- 2. 載りやすさが人で違う（2つの名簿で同じ人が載りやすい） ----
    rows = []
    REP2 = 200
    for sd in (0.0, 0.5, 1.0, 1.5, 2.0):
        for corr in (1.0, 0.5, 0.0, -0.5):
            est_l, se_l = [], []
            for _ in range(REP2):
                z1 = rng.normal(0, 1, N); z2 = corr * z1 + np.sqrt(1 - corr ** 2) * rng.normal(0, 1, N)
                # 平均の載る割合がどの場合も10%になるように切片を合わせてある
                c0 = intercept(sd)
                a, b = draw_lists(rng, expit(c0 + sd * z1), expit(c0 + sd * z2))
                e, s = chapman(a.sum(), b.sum(), (a & b).sum()); est_l.append(e); se_l.append(s)
            r = summarize(np.array(est_l), np.array(se_l)); r.update(sd=sd, corr=corr); rows.append(r)
            if sd == 0.0: break
    het = pd.DataFrame(rows); het.to_csv(RES / "heterogeneity.csv", index=False)

    # 載りやすさのばらつきを、載る確率の「上位1割と下位1割の比」で言い直す
    spread = {}
    for sd in (0.5, 1.0, 1.5, 2.0):
        z = rng.normal(0, 1, 200_000)
        p = expit(intercept(sd) + sd * z); spread[str(sd)] = {"p10": float(np.percentile(p, 10) * 100), "p50": float(np.percentile(p, 50) * 100), "p90": float(np.percentile(p, 90) * 100), "cv": float(p.std() / p.mean())}

    # ---- 3. 層に分けて推定する：載りやすさを決める要因の一部（年齢層など）が分かっている ----
    rows = []
    for known in (0.0, 0.25, 0.5, 0.75, 1.0):       # 載りやすさのばらつきのうち、分かっている要因で決まる割合
        est_all, est_strat = [], []
        for _ in range(REP2):
            sd = 1.5
            g = rng.integers(0, 5, N)                               # 分かっている区分（5つ）
            gz = (g - 2) / np.sqrt(2.0)                             # 平均0・分散1
            z = np.sqrt(known) * gz + np.sqrt(1 - known) * rng.normal(0, 1, N)
            p = expit(intercept(sd) + sd * z)
            a, b = draw_lists(rng, p, p)
            est_all.append(chapman(a.sum(), b.sum(), (a & b).sum())[0])
            est_strat.append(sum(chapman(a[g == k].sum(), b[g == k].sum(), (a & b)[g == k].sum())[0] for k in range(5)))
        rows.append(dict(known=known, bias_all=float((np.mean(est_all) / N - 1) * 100), bias_strat=float((np.mean(est_strat) / N - 1) * 100)))
    strat = pd.DataFrame(rows); strat.to_csv(RES / "stratified.csv", index=False)

    # ---- 4. 名寄せの誤り：同じ人を別人と見る（見逃し）、別人を同じ人と見る（取り違え） ----
    rows = []
    for miss in (0.0, 0.02, 0.05, 0.10, 0.20):
        for false_per_1000 in (0.0, 1.0, 5.0):
            n1 = rng.binomial(N, 0.10, REPS); n2 = rng.binomial(N, 0.10, REPS); m = rng.hypergeometric(n1, N - n1, n2)
            m_obs = rng.binomial(m, 1 - miss) + rng.poisson(false_per_1000 / 1000 * np.minimum(n1, n2))
            est, se = chapman(n1, n2, m_obs)
            r = summarize(est, se); r.update(miss=miss, false_per_1000=false_per_1000); rows.append(r)
    link = pd.DataFrame(rows); link.to_csv(RES / "linkage_errors.csv", index=False)

    # ---- 5. 全体が閉じていない：名簿2を作るまでに、人が入れ替わる ----
    rows = []
    for turnover in (0.0, 0.05, 0.10, 0.20):
        n1 = rng.binomial(N, 0.10, REPS)
        stay = rng.binomial(n1, 1 - turnover)                  # 名簿1の人のうち、まだ全体に残っている人
        n2 = rng.binomial(N, 0.10, REPS)                       # 名簿2は、入れ替わった後の全体（同じ10万人規模）から
        m = rng.hypergeometric(stay, N - stay, n2)
        est, se = chapman(n1, n2, m); r = summarize(est, se); r.update(turnover=turnover); rows.append(r)
    openpop = pd.DataFrame(rows); openpop.to_csv(RES / "open_population.csv", index=False)

    # 例の1回分（図1用と data）
    z = rng.normal(0, 1, N)
    a, b = draw_lists(rng, np.full(N, 0.10), np.full(N, 0.10))
    ex = dict(n1=int(a.sum()), n2=int(b.sum()), both=int((a & b).sum()), neither=int((~a & ~b).sum()))
    ex["estimate"] = float(chapman(ex["n1"], ex["n2"], ex["both"])[0]); ex["union"] = ex["n1"] + ex["n2"] - ex["both"]
    pd.DataFrame([ex]).to_csv(DATA / "example_one_draw.csv", index=False)

    res = {"N": N, "example": ex, "ideal": ideal.round(2).to_dict("records"), "heterogeneity": het.round(2).to_dict("records"),
           "spread": spread, "stratified": strat.round(2).to_dict("records"), "linkage": link.round(2).to_dict("records"), "open": openpop.round(2).to_dict("records")}
    json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    pd.set_option("display.width", 220)
    print(ex); print(ideal.round(2).to_string()); print(het.round(2).to_string()); print(spread); print(strat.round(2).to_string()); print(link.round(2).to_string()); print(openpop.round(2).to_string())

    # ---------- 図 ----------
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(ideal.coverage * 100, ideal.rmse_pct, color=BLUE, lw=2, marker="o")
    for _, r in ideal.iterrows(): ax.text(r.coverage * 100, r.rmse_pct * 1.12, f"{r.rmse_pct:.1f}%\n（重なり{r.mean_overlap:,.0f}人）", ha="center", fontsize=8)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(ideal.coverage * 100); ax.set_xticklabels([f"{c * 100:g}%" for c in ideal.coverage])
    ax.set_xlabel("1つの名簿に載る人の割合"); ax.set_ylabel("推定の誤差（RMSE、%）")
    ax.set_title("前提どおりなら、誤差は「重なった人数」で決まる（全体10万人）"); ax.margins(y=0.25)
    save(fig, "a378_ideal.png", SRC)

    fig, ax = plt.subplots(figsize=(9, 4.4))
    cols = {1.0: ORANGE, 0.5: BLUE, 0.0: GRAY, -0.5: GREEN}
    labs = {1.0: "2つの名簿で、同じ人が載りやすい", 0.5: "半分くらい重なる", 0.0: "載りやすさは名簿ごとに無関係", -0.5: "片方に載りやすい人は、もう片方に載りにくい"}
    base = het[het.sd == 0].iloc[0]
    for c in (1.0, 0.5, 0.0, -0.5):
        g = het[(het["corr"] == c) & (het.sd > 0)]
        ax.plot([0] + list(g.sd), [base.bias_pct] + list(g.bias_pct), color=cols[c], lw=2, marker="o", label=labs[c])
        ax.text(g.sd.iloc[-1] + 0.03, g.bias_pct.iloc[-1], f"{g.bias_pct.iloc[-1]:+.0f}%", color=cols[c], fontsize=9, va="center")
    ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("載りやすさの人による違いの大きさ（0＝全員同じ）"); ax.set_ylabel("推定の偏り（%、本当は10万人）")
    ax.set_xlim(-0.05, 2.3); ax.legend(fontsize=8, frameon=False, loc="lower left")
    ax.set_title("載りやすい人が両方の名簿で同じだと、全体を小さく見積もる")
    save(fig, "a378_heterogeneity.png", SRC)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    ax = axes[0]
    for f, c in ((0.0, BLUE), (1.0, GRAY), (5.0, ORANGE)):
        g = link[link.false_per_1000 == f]
        ax.plot(g.miss * 100, g.bias_pct, color=c, lw=2, marker="o", label=f"取り違え：名簿1,000人あたり{f:g}件")
    ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("同じ人を別人と見た割合（%）"); ax.set_ylabel("推定の偏り（%）"); ax.legend(fontsize=8, frameon=False)
    ax.set_title("名寄せの見逃しは、全体を大きく見積もる", fontsize=11)
    ax = axes[1]
    ax.plot(strat.known * 100, strat.bias_all, color=ORANGE, lw=2, marker="o", label="全体をまとめて推定")
    ax.plot(strat.known * 100, strat.bias_strat, color=BLUE, lw=2, marker="o", label="分かっている5区分ごとに推定して足す")
    ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("載りやすさの違いのうち、分かっている区分で決まる割合（%）"); ax.legend(fontsize=8, frameon=False)
    ax.set_title("区分ごとに推定すると、分かっている分だけ戻る", fontsize=11)
    save(fig, "a378_linkage_and_strata.png", SRC)


if __name__ == "__main__":
    main()
