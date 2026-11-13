"""537 回答の選択肢が「1,000万円以上」で打ち切られていると、平均はどれだけ小さく出るのか（統計・集計）

架空の年収（万円）を、100万円刻み＋「1,000万円以上」の11区分で聞いたことにする。
- 本当の分布：対数正規。中央値 m（350・450・550万円）と散らばり σ（0.5・0.7・0.9）を変える
- 裾の重い場合：800万円より上をパレート（α 1.8・2.5・3.5）に置きかえた分布も作る
- 回答者 10,000人、各場面 200回くり返す（乱数の種 537）
平均の出し方：
  M1 区分の中央の値で埋め、「1,000万円以上」は 1,000万円（下限）で埋める
  M2 同じく、「1,000万円以上」は 1,500万円（下限の1.5倍）で埋める
  M3 「1,000万円以上」にパレートを当てる。α は 800万円以上の人数と 1,000万円以上の人数の比から出す
中央値は区分の中での直線補間で出し、本当の中央値と比べる。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の年収の回答（作成者が乱数で作成、seed 537）"
N = 10_000
REPS = 200
EDGES = np.arange(0, 1001, 100)          # 0,100,...,1000（その上は開いた区分）
TOP = 1000.0


def draw(rng, m, sigma, alpha=None):
    x = rng.lognormal(np.log(m), sigma, N)
    if alpha is not None:
        hi = x > 800
        x[hi] = 800 * (1 - rng.random(hi.sum())) ** (-1 / alpha)
    return x


def grouped(x):
    c = np.histogram(x[x < TOP], bins=EDGES)[0]
    return c, int((x >= TOP).sum())


def estimates(c, ctop):
    mids = (EDGES[:-1] + EDGES[1:]) / 2
    n = c.sum() + ctop
    body = (c * mids).sum()
    m1 = (body + ctop * TOP) / n
    m2 = (body + ctop * TOP * 1.5) / n
    n800 = c[-2:].sum() + ctop                       # 800万円以上
    if ctop > 0 and n800 > ctop:
        a = np.log(n800 / ctop) / np.log(TOP / 800)
    else:
        a = np.nan
    top_mean = a * TOP / (a - 1) if a > 1.05 else np.nan
    m3 = (body + ctop * top_mean) / n if np.isfinite(top_mean) else np.nan
    # 中央値（直線補間）
    cum = np.cumsum(np.append(c, ctop)) / n
    k = int(np.searchsorted(cum, 0.5))
    lo_c = cum[k - 1] if k > 0 else 0
    med = EDGES[k] + (0.5 - lo_c) / (cum[k] - lo_c) * 100 if k < len(c) else TOP
    return m1, m2, m3, med, a


def main():
    rng = np.random.default_rng(537)
    rows = []
    scen = [("lognormal", m, s, None) for m in [350, 450, 550] for s in [0.5, 0.7, 0.9]]
    scen += [("pareto_tail", 450, 0.7, a) for a in [1.8, 2.5, 3.5]]
    for fam, m, s, a in scen:
        for r in range(REPS):
            x = draw(rng, m, s, a)
            c, ctop = grouped(x)
            m1, m2, m3, med, ahat = estimates(c, ctop)
            rows.append(dict(family=fam, median_param=m, sigma=s, alpha=a if a else np.nan, rep=r,
                             true_mean=x.mean(), true_median=float(np.median(x)), top_share=ctop / N,
                             top_true_mean=float(x[x >= TOP].mean()) if ctop else np.nan,
                             m1=m1, m2=m2, m3=m3, grouped_median=med, alpha_hat=ahat))
    df = pd.DataFrame(rows)
    for k in ["m1", "m2", "m3"]:
        df[k + "_bias_pct"] = (df[k] / df.true_mean - 1) * 100
    df["median_bias_pct"] = (df.grouped_median / df.true_median - 1) * 100
    df.to_csv(RES / "reps.csv", index=False, float_format="%.6f")
    keys = ["family", "median_param", "sigma", "alpha"]
    sm = df.groupby(keys, dropna=False).agg(
        top_share=("top_share", "mean"), true_mean=("true_mean", "mean"), top_true_mean=("top_true_mean", "mean"),
        m1_bias_pct=("m1_bias_pct", "mean"), m2_bias_pct=("m2_bias_pct", "mean"),
        m3_bias_pct=("m3_bias_pct", "mean"), m3_bias_p10=("m3_bias_pct", lambda v: np.nanquantile(v, 0.1)),
        m3_bias_p90=("m3_bias_pct", lambda v: np.nanquantile(v, 0.9)), m3_na=("m3", lambda v: v.isna().mean()),
        median_bias_pct=("median_bias_pct", "mean"), alpha_hat=("alpha_hat", "median")).reset_index()
    sm.to_csv(RES / "summary.csv", index=False, float_format="%.6f")
    fit = np.polyfit(sm[sm.family == "lognormal"].top_share * 100, sm[sm.family == "lognormal"].m1_bias_pct, 1)
    json.dump({"rows": sm.round(6).to_dict("records"), "m1_bias_vs_top_share_slope": float(fit[0]),
               "m1_bias_vs_top_share_intercept": float(fit[1])}, open(RES / "a537_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：基準の場面（中央値450・σ0.7）での3つの出し方
    b = sm[(sm.family == "lognormal") & (sm.median_param == 450) & (sm.sigma == 0.7)].iloc[0]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    labs = ["M1 上は下限（1,000万円）", "M2 上は1.5倍（1,500万円）", "M3 上にパレート", "中央値（補間）"]
    vals = [b.m1_bias_pct, b.m2_bias_pct, b.m3_bias_pct, b.median_bias_pct]
    ax.barh(labs[::-1], vals[::-1], color=[GRAY, GREEN, ORANGE, BLUE][::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + (0.15 if v >= 0 else -0.15), i, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=9)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("本当の値とのずれ（%）")
    ax.set_title(f"中央値450万円・σ0.7（「1,000万円以上」{b.top_share*100:.1f}%）で、平均はどれだけずれるか")
    ax.set_xlim(min(vals) - 3, max(vals) + 3)
    save(fig, "a537_bias_base.png", SRC + "。200回の平均")

    # 図2：上の区分の割合と、M1 の過小の大きさ
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ln = sm[sm.family == "lognormal"]
    for s, col in [(0.5, LIGHT), (0.7, BLUE), (0.9, INK)]:
        t = ln[ln.sigma == s]
        ax.plot(t.top_share * 100, t.m1_bias_pct, "o-", color=col, label=f"M1・σ {s}")
        ax.plot(t.top_share * 100, t.m3_bias_pct, "s:", color=col, alpha=0.8, label=f"M3・σ {s}")
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("「1,000万円以上」の割合（%）")
    ax.set_ylabel("平均のずれ（%）")
    ax.legend(fontsize=8, frameon=False, ncol=2)
    ax.set_title("上の区分が多いほど、M1 は小さく、M3 は大きく外れる（対数正規の場合）")
    save(fig, "a537_bias_vs_top_share.png", SRC + "。点は中央値350・450・550万円")

    # 図3：裾の重さ（パレート α）を変えたとき
    pt = sm[sm.family == "pareto_tail"].sort_values("alpha")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    xx = np.arange(len(pt)); w = 0.25
    ax.bar(xx - w, pt.m1_bias_pct, w, color=GRAY, label="M1 上は下限")
    ax.bar(xx, pt.m2_bias_pct, w, color=GREEN, label="M2 上は1.5倍")
    ax.bar(xx + w, pt.m3_bias_pct, w, color=ORANGE, label="M3 パレート")
    for off, col in [(-w, "m1_bias_pct"), (0, "m2_bias_pct"), (w, "m3_bias_pct")]:
        for xi, v in zip(xx + off, pt[col]):
            ax.text(xi, v + (0.4 if v >= 0 else -0.4), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
    ax.set_xticks(xx); ax.set_xticklabels([f"α {a}\n上の区分の本当の平均\n{t:,.0f}万円" for a, t in zip(pt.alpha, pt.top_true_mean)], fontsize=9)
    ax.axhline(0, color=INK, lw=0.8); ax.set_ylabel("平均のずれ（%）")
    ax.legend(fontsize=8, frameon=False)
    ax.set_ylim(pt.m1_bias_pct.min() - 4, max(4, pt.m2_bias_pct.max() + 3))
    ax.set_title("裾が本当にパレートなら、M3 はほぼ合う。M1・M2 は裾が重いほど外れる")
    save(fig, "a537_bias_by_tail.png", SRC + "。中央値450万円・σ0.7、800万円より上をパレートに置きかえ")

    print(sm.to_string())
    print(fit)


if __name__ == "__main__":
    main()
