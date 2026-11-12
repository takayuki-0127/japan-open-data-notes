"""446 指標をいくつも同時に見ると、効果が0でも何%で「差あり」が出るのか
検定統計量 z を相関つきの多変量正規で直接引く（1指標あたり両側5%）。seed 446"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *

rng = np.random.default_rng(446)
REP = 20000
ALPHA = 0.05
MS = [1, 2, 3, 5, 10, 20]
RHOS = [0.0, 0.3, 0.6, 0.9]
EFFECT = stats.norm.ppf(0.975) + stats.norm.ppf(0.8)   # 1指標だけなら検出力80%になる z の平均


def draw_z(m, rho, mean, rep):
    """相関 rho（どの組も同じ）の z。共通の成分＋固有の成分"""
    c = rng.standard_normal((rep, 1)); e = rng.standard_normal((rep, m))
    return np.sqrt(rho) * c + np.sqrt(1 - rho) * e + mean


def pvals(z):
    return 2 * stats.norm.sf(np.abs(z))


def reject(p, method):
    rep, m = p.shape
    if method == "none": return p < ALPHA
    if method == "bonf": return p < ALPHA / m
    order = np.argsort(p, axis=1); ps = np.take_along_axis(p, order, axis=1)
    if method == "holm":
        thr = ALPHA / (m - np.arange(m)); ok = ps < thr
        keep = np.cumprod(ok, axis=1).astype(bool)          # 最初に外れた所から後ろは全部だめ
    elif method == "bh":
        thr = ALPHA * (np.arange(m) + 1) / m; ok = ps <= thr
        last = np.where(ok.any(axis=1), m - 1 - np.argmax(ok[:, ::-1], axis=1), -1)
        keep = np.arange(m)[None, :] <= last[:, None]       # 最後に通った所から前は全部通す
    out = np.zeros_like(keep); np.put_along_axis(out, order, keep, axis=1)
    return out


METHODS = [("none", "補正なし"), ("bonf", "ボンフェローニ"), ("holm", "ホルム"), ("bh", "FDR（BH法）")]

# ---- 1. 効果が全部0のとき：少なくとも1つ「差あり」と出る割合
rows = []
for rho in RHOS:
    for m in MS:
        p = pvals(draw_z(m, rho, 0.0, REP))
        for k, name in METHODS:
            r = reject(p, k)
            rows.append(dict(rho=rho, m=m, method=name, any_reject=r.any(axis=1).mean(), mean_rejects=r.sum(axis=1).mean()))
null = pd.DataFrame(rows); null["formula_indep"] = 1 - (1 - ALPHA) ** null.m
null.round(4).to_csv(RES / "null_any_reject.csv", index=False)

# ---- 2. 本当に差がある指標が混ざるとき（m 本のうち2本に効果。m=1 は1本）
rows = []
for rho in [0.0, 0.3, 0.6]:
    for m in MS:
        k_true = min(2, m); mean = np.zeros(m); mean[:k_true] = EFFECT
        p = pvals(draw_z(m, rho, mean, REP))
        for k, name in METHODS:
            r = reject(p, k); tp = r[:, :k_true]; fp = r[:, k_true:]
            nrej = r.sum(axis=1)
            rows.append(dict(rho=rho, m=m, n_true=k_true, method=name,
                             power_each=tp.mean(), power_all=tp.all(axis=1).mean(),
                             any_false=fp.any(axis=1).mean() if m > k_true else 0.0,
                             fdr=np.where(nrej > 0, fp.sum(axis=1) / np.maximum(nrej, 1), 0).mean()))
mix = pd.DataFrame(rows); mix.round(4).to_csv(RES / "mixed_power.csv", index=False)

# ---- 3. 検出力を80%に戻すのに要る人数（ボンフェローニ、独立な式）
rows = []
for m in MS:
    need = ((stats.norm.ppf(1 - ALPHA / (2 * m)) + stats.norm.ppf(0.8)) / EFFECT) ** 2
    rows.append(dict(m=m, sample_ratio_bonf=need))
ss = pd.DataFrame(rows); ss.round(3).to_csv(RES / "sample_size_ratio.csv", index=False)

# ---- 4. 確かめ：実際に2群のデータを作って t 検定をした場合（m=10、相関0.3、各群2,000人、4,000回）
m, rho, n, rep2 = 10, 0.3, 2000, 4000
L = np.linalg.cholesky(np.full((m, m), rho) + (1 - rho) * np.eye(m)); hit = 0
ex = None
for i in range(rep2):
    a = rng.standard_normal((n, m)) @ L.T; b = rng.standard_normal((n, m)) @ L.T
    t, pv = stats.ttest_ind(a, b, axis=0)
    hit += (pv < ALPHA).any()
    if i == 0: ex = pd.DataFrame({"metric": [f"指標{j+1}" for j in range(m)], "mean_a": a.mean(0), "mean_b": b.mean(0), "t": t, "p": pv})
ex.round(4).to_csv(DATA / "example_one_test.csv", index=False)
check_data = hit / rep2
check_z = float(null[(null.rho == rho) & (null.m == m) & (null.method == "補正なし")].any_reject.iloc[0])

g = lambda df, **kw: df.loc[np.logical_and.reduce([df[k] == v for k, v in kw.items()])]
main = dict(rep=REP, alpha=ALPHA, effect_z=round(float(EFFECT), 3),
            any_reject_none={f"rho{r}": {int(x.m): round(float(x.any_reject), 4) for x in g(null, rho=r, method="補正なし").itertuples()} for r in RHOS},
            any_reject_m10_rho0={n_: round(float(g(null, rho=0.0, m=10, method=n_).any_reject.iloc[0]), 4) for _, n_ in METHODS},
            any_reject_m10_rho06={n_: round(float(g(null, rho=0.6, m=10, method=n_).any_reject.iloc[0]), 4) for _, n_ in METHODS},
            power_each_rho03={n_: {int(x.m): round(float(x.power_each), 4) for x in g(mix, rho=0.3, method=n_).itertuples()} for _, n_ in METHODS},
            any_false_rho03={n_: {int(x.m): round(float(x.any_false), 4) for x in g(mix, rho=0.3, method=n_).itertuples()} for _, n_ in METHODS},
            fdr_rho03={n_: {int(x.m): round(float(x.fdr), 4) for x in g(mix, rho=0.3, method=n_).itertuples()} for _, n_ in METHODS},
            sample_ratio_bonf={int(x.m): round(float(x.sample_ratio_bonf), 3) for x in ss.itertuples()},
            check_real_data_m10_rho03=round(float(check_data), 4), check_z_m10_rho03=round(check_z, 4))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

SRC = "架空のテスト（作成者が乱数で作成、seed 446）。1指標あたり両側5%で判定"
# 図1
fig, ax = plt.subplots(figsize=(7.6, 4.6))
cols = {0.0: INK, 0.3: BLUE, 0.6: ORANGE, 0.9: GREEN}
for rho in RHOS:
    d = g(null, rho=rho, method="補正なし")
    ax.plot(d.m, d.any_reject * 100, "o-", color=cols[rho], label=f"指標どうしの相関 {rho}")
ax.plot(MS, [(1 - 0.95 ** m) * 100 for m in MS], ":", color=GRAY, label="式：1−0.95のm乗（独立なとき）")
ax.axhline(5, color=GRAY, lw=0.8); ax.set_xticks(MS)
ax.set_xlabel("同時に見る指標の数"); ax.set_ylabel("少なくとも1つ「差あり」と出た割合（%）")
ax.set_title("効果が0でも、指標を増やすと「差あり」が出やすくなる（補正なし）"); ax.legend(frameon=False, fontsize=9)
save(fig, "a446_any_reject_by_metrics.png", SRC)
# 図2
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=True)
for ax, rho in zip(axes, [0.0, 0.6]):
    d = null[(null.rho == rho) & (null.m == 10)]
    b = ax.bar(d.method, d.any_reject * 100, color=[GRAY, BLUE, LIGHT, ORANGE])
    for r_, v in zip(b, d.any_reject * 100): ax.text(r_.get_x() + r_.get_width() / 2, v + 0.6, f"{v:.1f}%", ha="center", fontsize=10)
    ax.axhline(5, color=INK, lw=0.8, ls="--"); ax.set_title(f"指標10本・相関 {rho}"); ax.tick_params(axis="x", labelsize=9)
axes[0].set_ylabel("少なくとも1つ「差あり」と出た割合（%）")
fig.suptitle("補正をかけると、効果0で「差あり」が出る割合は5%以下に戻る", y=1.02)
save(fig, "a446_corrections_null.png", SRC + "。点線は5%")
# 図3
fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
mc = {"補正なし": GRAY, "ボンフェローニ": BLUE, "ホルム": LIGHT, "FDR（BH法）": ORANGE}
for _, name in METHODS:
    d = g(mix, rho=0.3, method=name)
    axes[0].plot(d.m, d.power_each * 100, "o-", color=mc[name], label=name)
    axes[1].plot(d.m[d.m > 2], d.any_false[d.m > 2] * 100, "o-", color=mc[name], label=name)
for ax in axes: ax.set_xticks(MS); ax.set_xlabel("同時に見る指標の数（うち2本に本当の差）")
axes[0].set_ylabel("本当に差がある指標を見つけた割合（%）"); axes[0].set_title("見つける力"); axes[0].legend(frameon=False, fontsize=9)
axes[1].set_ylabel("差のない指標を1つ以上「差あり」とした割合（%）"); axes[1].set_title("まちがった「差あり」"); axes[1].axhline(5, color=INK, lw=0.8, ls="--")
fig.suptitle("補正は、まちがいを減らす代わりに、見つける力を下げる（相関0.3）", y=1.02)
save(fig, "a446_power_vs_false.png", SRC + "。差のある指標は、1本だけなら80%で見つかる大きさ")
print(json.dumps(main, ensure_ascii=False)[:1500])
