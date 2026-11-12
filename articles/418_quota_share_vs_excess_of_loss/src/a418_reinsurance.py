"""418 同じ再保険料を払うなら、割合で分ける形と大きな損害だけ渡す形で、手元の損害の振れはどれだけ違うか（架空の損害）
年の事故件数：ポアソン（200件）。損害額：平均1。裾の軽い分布（ガンマ、CV1.5）と重い分布（パレート、CV3.3）。
渡す損害の期待値をそろえて比べる（再保険料＝渡す損害の期待値×同じ係数、と置く）。"""
import json
import numpy as np, pandas as pd
from scipy import optimize, stats
from common import *

SEED, LAM, YEARS = 418, 200, 200_000
QS = [0.10, 0.20, 0.30, 0.50]                      # 渡す損害の期待値の割合

A_P = 2.2                                          # パレート（ロマックス）の形。平均1、CV=sqrt(a/(a-2))=3.3
SH = 1 / 1.5 ** 2                                  # ガンマの形。CV1.5
S2 = np.log(1 + 3.3166 ** 2)                       # 対数正規。パレートと同じ CV
def draw(name, rng, n):
    if name == "裾が軽い（ガンマ）": return rng.gamma(SH, 1 / SH, n)
    if name == "裾が重い（対数正規）": return rng.lognormal(-S2 / 2, np.sqrt(S2), n)
    return rng.pareto(A_P, n) * (A_P - 1)
def lev(name, m):
    """E[min(X, m)]（上限つきの期待値）"""
    if name == "裾が軽い（ガンマ）":
        return stats.gamma.cdf(m, SH + 1, scale=1 / SH) + m * stats.gamma.sf(m, SH, scale=1 / SH)
    if name == "裾が重い（対数正規）":
        s = np.sqrt(S2); mu = -S2 / 2
        return stats.norm.cdf((np.log(m) - mu - S2) / s) + m * stats.norm.sf((np.log(m) - mu) / s)
    th = A_P - 1
    return 1 - (th / (m + th)) ** (A_P - 1)
DISTS = ["裾が軽い（ガンマ）", "裾が重い（対数正規）", "裾が重い（パレート）"]

def summ(x):
    m = x.mean()
    return dict(平均=m, 振れ=x.std(ddof=1), 振れ_平均比=x.std(ddof=1) / m, 上位0_5=np.quantile(x, 0.995), 上位0_5_平均比=np.quantile(x, 0.995) / m,
                上位0_5と平均の差=np.quantile(x, 0.995) - m)
rows, rets = [], []
for di, name in enumerate(DISTS):
    rng = np.random.default_rng([SEED, di])
    N = rng.poisson(LAM, YEARS); X = draw(name, rng, N.sum()); idx = np.repeat(np.arange(YEARS), N)
    agg = lambda v: np.bincount(idx, weights=v, minlength=YEARS)
    gross = agg(X); rows.append(dict(分布=name, 形="再保険なし", 渡す割合=0.0, 境目=np.nan, 層の幅=np.nan, 渡した割合_実際=0.0, **summ(gross)))
    for q in QS:
        M = optimize.brentq(lambda m: lev(name, m) - (1 - q), 1e-6, 1e9)          # E[(X-M)+] = q
        rets.append(dict(分布=name, 渡す割合=q, 境目=M, 境目を超える事故の割合=(X > M).mean()))
        prop = (1 - q) * gross
        xl = agg(np.minimum(X, M))
        # 上限つきの層：M2 から幅 10×M2 までを渡す（期待値を q にそろえる）
        f2 = lambda m: lev(name, 11 * m) - lev(name, m) - q
        gr = np.linspace(M, 1e-4, 4000); fv = np.array([f2(m) for m in gr]); k = np.where(fv > 0)[0]   # M から下へ探す
        M2 = optimize.brentq(f2, gr[k[0]], gr[k[0] - 1]) if len(k) else np.nan
        for form, ret, b, wd in [("割合で分ける", prop, np.nan, np.nan), ("大きな損害を渡す（上限なし）", xl, M, np.inf)] + \
                                ([("大きな損害を渡す（上限つき）", agg(np.minimum(X, M2) + np.maximum(X - 11 * M2, 0)), M2, 10 * M2)] if M2 == M2 else []):
            rows.append(dict(分布=name, 形=form, 渡す割合=q, 境目=b, 層の幅=wd, 渡した割合_実際=1 - ret.mean() / gross.mean(), **summ(ret)))
    # 年の合計で渡す形（ストップロス）：合計が d を超えた分を渡す。期待値を q=10% にそろえる
    for q in [0.10]:
        d = optimize.brentq(lambda d: np.maximum(gross - d, 0).mean() - q * LAM, 0, gross.max())
        rows.append(dict(分布=name, 形="年の合計の超過を渡す", 渡す割合=q, 境目=d, 層の幅=np.inf, 渡した割合_実際=1 - np.minimum(gross, d).mean() / gross.mean(), **summ(np.minimum(gross, d))))
    if di == 2: pd.DataFrame(dict(年=np.arange(1, 301), 件数=N[:300], 再保険なし=gross[:300])).round(3).to_csv(DATA / "example_gross_300years_pareto.csv", index=False)
    print(name, "done", flush=True)
T = pd.DataFrame(rows)
base = T[T.形 == "再保険なし"].set_index("分布")
T["振れの減り_パーセント"] = 100 * (1 - T.振れ / T.分布.map(base.振れ))
T["振れ_平均比の減り_パーセント"] = 100 * (1 - T.振れ_平均比 / T.分布.map(base.振れ_平均比))
T["上位0_5と平均の差の減り_パーセント"] = 100 * (1 - T.上位0_5と平均の差 / T.分布.map(base.上位0_5と平均の差))
T.to_csv(RES / "retained_volatility.csv", index=False)
RT = pd.DataFrame(rets); RT.to_csv(RES / "retention_points.csv", index=False)

def g(n, f, q, c):
    d = T[(T.分布 == n) & (T.形 == f) & (np.isclose(T.渡す割合, q))]
    return float(d[c].iloc[0]) if len(d) else float("nan")
main = dict(条件=dict(年の事故件数=LAM, 年数=YEARS, 乱数の種=SEED),
            再保険なし={n: dict(振れ_平均比=float(base.loc[n, "振れ_平均比"]), 上位0_5_平均比=float(base.loc[n, "上位0_5_平均比"])) for n in DISTS},
            渡す割合20={n: {f: dict(振れの減り=g(n, f, .2, "振れの減り_パーセント"), 振れ_平均比=g(n, f, .2, "振れ_平均比"), 上位0_5_平均比=g(n, f, .2, "上位0_5_平均比"),
                                 差の減り=g(n, f, .2, "上位0_5と平均の差の減り_パーセント")) for f in T[(T.分布 == n) & np.isclose(T.渡す割合, .2)].形} for n in DISTS},
            境目=RT.round(3).to_dict("records"),
            年の合計={n: dict(振れの減り=g(n, "年の合計の超過を渡す", .1, "振れの減り_パーセント"), 差の減り=g(n, "年の合計の超過を渡す", .1, "上位0_5と平均の差の減り_パーセント"),
                         事故ごと_振れの減り=g(n, "大きな損害を渡す（上限なし）", .1, "振れの減り_パーセント"), 事故ごと_差の減り=g(n, "大きな損害を渡す（上限なし）", .1, "上位0_5と平均の差の減り_パーセント")) for n in DISTS})
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

FORMS = ["割合で分ける", "大きな損害を渡す（上限つき）", "大きな損害を渡す（上限なし）"]; FC = {FORMS[0]: GRAY, FORMS[1]: BLUE, FORMS[2]: ORANGE}
fig, ax = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
for a, n in zip(ax, DISTS):
    for f in FORMS:
        d = T[(T.分布 == n) & (T.形 == f)]
        a.plot(d.渡す割合 * 100, d.振れの減り_パーセント, "o-", color=FC[f], label=f)
    a.plot([0, 50], [0, 50], color=INK, lw=0.5, ls=":"); a.set_title(n); a.set_xlabel("渡す損害の期待値（もとの損害に対する%）")
ax[0].set_ylabel("手元に残る損害の振れの減り（%）"); ax[0].legend(fontsize=8, frameon=False)
save(fig, "a418_volatility_reduction.png", "架空の損害（年200件）。振れ＝年の損害の合計の標準偏差。点線＝渡した割合と同じだけ減る線。作成者が計算")

fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
x = np.arange(3); w = 0.2
labs = ["再保険なし"] + FORMS; cs = [LIGHT, GRAY, BLUE, ORANGE]
for j, f in enumerate(labs):
    v = [float(base.loc[n, "上位0_5_平均比"]) if f == "再保険なし" else g(n, f, .2, "上位0_5_平均比") for n in DISTS]
    ax[0].bar(x + (j - 1.5) * w, np.array(v) * 100, w, color=cs[j], label=f)
    for xi, vv in zip(x + (j - 1.5) * w, v): ax[0].text(xi, vv * 100 + 2, f"{vv*100:.0f}", ha="center", fontsize=8)
ax[0].set_xticks(x); ax[0].set_xticklabels(DISTS, fontsize=9); ax[0].set_ylabel("200年に1度の年の損害（手元の平均＝100）"); ax[0].set_ylim(100, None)
ax[0].set_title("渡す割合20%：200年に1度の年の、手元の損害"); ax[0].legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2); ax[0].tick_params(axis="x", labelsize=8)
for n, col in zip(DISTS, [GREEN, BLUE, ORANGE]):
    d = RT[RT.分布 == n]; ax[1].plot(d.渡す割合 * 100, d.境目を超える事故の割合 * 100, "o-", color=col, label=n)
    for r in d.itertuples(): ax[1].text(r.渡す割合 * 100 + 1, r.境目を超える事故の割合 * 100, f"境目 {r.境目:.1f}", fontsize=7.5, color=col)
ax[1].set_yscale("log"); ax[1].set_xlabel("渡す損害の期待値（%）"); ax[1].set_ylabel("境目を超える事故の割合（%、対数）"); ax[1].set_title("大きな損害を渡す形の境目（損害額の平均＝1）"); ax[1].legend(fontsize=8, frameon=False)
save(fig, "a418_tail_and_retention.png", "架空の損害（年200件・20万年分）。作成者が計算", y=-0.12)

fig, ax = plt.subplots(figsize=(8.5, 4.3))
x = np.arange(3); w = 0.26
for j, (f, col) in enumerate([("割合で分ける", GRAY), ("大きな損害を渡す（上限なし）", ORANGE), ("年の合計の超過を渡す", GREEN)]):
    v = [g(n, f, .1, "上位0_5と平均の差の減り_パーセント") for n in DISTS]
    ax.bar(x + (j - 1) * w, v, w, color=col, label=f)
    for xi, vv in zip(x + (j - 1) * w, v): ax.text(xi, vv + 1, f"{vv:.0f}%", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(DISTS); ax.set_ylabel("「200年に1度 − 平均」の減り（%）"); ax.set_title("渡す割合10%：悪い年への備えは、どれだけ小さくなるか"); ax.legend(fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3); ax.set_ylim(0, 105)
save(fig, "a418_bad_year_buffer.png", "「200年に1度 − 平均」＝悪い年に、平均より余分に出ていく損害。作成者が計算", y=-0.12)
print(json.dumps(main, ensure_ascii=False, indent=1))
