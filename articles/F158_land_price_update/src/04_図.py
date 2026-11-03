"""図を作る"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, YEARS, LABEL

t = pd.read_csv(RES / "strategy_by_year.csv")
ex = pd.read_csv(RES / "strategy_extra.csv")
t = pd.concat([t, ex[ex["strategy"].str.startswith("2017")]])
ty = t[t["year"] != "2018-2026"].copy(); ty["year"] = ty["year"].astype(int)
P = lambda s, c="median_ape": ty[ty.strategy == s].sort_values("year")[["year", c]]

# 図1 更新しない／毎年更新の外れの推移
fig, ax = plt.subplots(figsize=(8, 4.6))
spec = [("2017年のまま", ORANGE, "2017年のモデルのまま", "-"),
        ("2017年のまま＋都道府県×用途ごとの変化で補正", ORANGE, "2017年のまま＋都道府県×用途ごとの変化で補正", "--"),
        ("毎年更新", BLUE, "毎年更新（前年の公示で学習し直す）", "-"),
        ("同じ年のモデル（参考）", GRAY, "参考：その年の公示で学習（1年遅れなし）", ":")]
for s, c, lab, ls in spec:
    d = P(s); ax.plot(d.year, d.median_ape * 100, color=c, ls=ls, lw=2.2 if ls == "-" else 1.6, marker="o", ms=4, label=lab)
ax.set_ylabel("誤差の中央値（%）"); ax.set_xlabel("予測する年の公示")
ax.set_title("2017年のモデルのままだと、外れは年に0.8ポイントずつ広がった", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_ylim(15, 25)
ax.text(2026.1, P("2017年のまま").median_ape.iloc[-1] * 100, f"{P('2017年のまま').median_ape.iloc[-1]*100:.1f}%", color=ORANGE, va="center", fontsize=10)
ax.text(2026.1, P("毎年更新").median_ape.iloc[-1] * 100 - .2, f"{P('毎年更新').median_ape.iloc[-1]*100:.1f}%", color=BLUE, va="center", fontsize=10)
ax.set_xlim(2017.7, 2026.9)
fig.text(0.01, -0.07, "見ていない場所（20km四方のブロックで分けた5分割の検証側）の公示価格を、前年までのデータで予測。誤差＝|予測÷実際−1|", fontsize=8, color=GRAY)
save(fig, "fig1_frozen_vs_update.png")

# 図2 更新の間隔
names = [("毎年更新", "毎年"), ("2年ごと", "2年ごと"), ("3年ごと", "3年ごと"), ("5年ごと", "5年ごと"),
         ("直近3年をまとめて学習", "直近3年を\nまとめて毎年"), ("2017年のまま＋全国の変化で補正", "2017年のまま\n＋全国補正"), ("2017年のまま", "更新しない")]
a = t[t.year == "2018-2026"].set_index("strategy")
ref = a.loc["同じ年のモデル（参考）", "median_ape"]
fig, ax = plt.subplots(figsize=(8, 4.4))
v = [a.loc[s, "median_ape"] * 100 for s, _ in names]
cols = [BLUE, BLUE, LIGHT, LIGHT, GREEN, ORANGE, ORANGE]
ax.bar(range(len(v)), v, color=cols)
for i, x in enumerate(v): ax.text(i, x + .1, f"{x:.1f}", ha="center", fontsize=10)
ax.axhline(ref * 100, color=GRAY, ls=":", lw=1.5); ax.text(-.4, 20.3, f"点線：参考（その年の公示で学習、1年遅れなし）{ref*100:.1f}%", color=GRAY, ha="left", fontsize=9)
ax.set_xticks(range(len(v))); ax.set_xticklabels([n for _, n in names], fontsize=9)
ax.set_ylim(17, 20.5); ax.set_ylabel("誤差の中央値（%、2018〜2026年の平均）")
ax.set_title("2年に1回の更新で、毎年更新とほぼ同じだった", loc="left")
save(fig, "fig2_interval.png")

# 図3 偏り（中央値の log 誤差）と地価のばらつき
disp = pd.read_csv(RES / "price_dispersion.csv")
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axs[0]
for s, c, lab, ls in spec:
    d = P(s, "bias"); ax.plot(d.year, (np.exp(d.bias) - 1) * 100, color=c, ls=ls, marker="o", ms=4, label=lab)
ax.axhline(0, color=INK, lw=.8); ax.set_ylabel("予測÷実際−1 の中央値（%）"); ax.set_title("予測は年を追うごとに低めにずれた", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=8)
ax = axs[1]
ax.plot(disp.year, disp.p90_p10, color=PURPLE, marker="o")
ax.set_title("高い地点と安い地点の差は開いた", loc="left", fontsize=12)
ax.set_ylabel("上から10%の地点 ÷ 下から10%の地点（倍）")
for i in (0, len(disp) - 1): ax.text(disp.year[i], disp.p90_p10[i] + .5, f"{disp.p90_p10[i]:.1f}倍", ha="center", fontsize=10, color=PURPLE)
save(fig, "fig3_bias_dispersion.png")
print("fig1-3 ok")

# 図4 重要度（SHAP）の割合の推移
g = pd.read_csv(RES / "importance_group_share.csv")
imp = pd.read_csv(RES / "importance_by_year.csv")
fig, axs = plt.subplots(1, 2, figsize=(13.5, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1], wspace=0.95))
ax = axs[0]
cols = {"駅と乗降客数": BLUE, "用途地域・容積率など": GREEN, "土地と建物の条件": GRAY, "都心からの距離・位置": ORANGE, "市区町村の人口": PURPLE}
for grp, c in cols.items():
    s = g[g.group == grp]; m = s[s.boot == 0].sort_values("year")
    lo, hi = s.groupby("year")["share"].min(), s.groupby("year")["share"].max()
    ax.fill_between(lo.index, lo * 100, hi * 100, color=c, alpha=.2, lw=0)
    ax.plot(m.year, m.share * 100, color=c, marker="o", ms=3.5)
    ax.text(2026.2, m.share.iloc[-1] * 100, f"{grp} {m.share.iloc[-1]*100:.0f}%", color=c, va="center", fontsize=9)
ax.set_xlim(2016.6, 2029.6); ax.set_ylabel("重要度（平均 |SHAP|）の割合（%）")
ax.set_title("重要度の割合は、10年でほとんど動かなかった", loc="left", fontsize=12)
ax = axs[1]
b0 = imp[imp.boot == 0].pivot(index="feature", columns="year", values="mean_abs_shap"); sh = b0 / b0.sum() * 100
diff = (sh[2026] - sh[2017]).sort_values()
sel = pd.concat([diff.head(4), diff.tail(4)])
yy = np.arange(len(sel))
ax.barh(yy, sel.values, color=[ORANGE if v < 0 else BLUE for v in sel.values])
ax.set_yticks(yy); ax.set_yticklabels([f"{LABEL[f]}（{sh.loc[f,2017]:.1f}→{sh.loc[f,2026]:.1f}%）" for f in sel.index], fontsize=9)
ax.axvline(0, color=INK, lw=.8); ax.set_xlabel("割合の変化（ポイント、2017→2026年）")
ax.set_title("動いた特徴量（上下4つ）", loc="left", fontsize=12)
fig.text(0.01, -0.10, "各年の全地点で学習したモデルを、10年すべてにある3,000地点で SHAP 分解。帯は地点をブートストラップした2回を含む3回の最小〜最大", fontsize=8, color=GRAY)
save(fig, "fig4_importance.png")

# 図5 効き方の大きさの変化（SHAP の区間平均を%に）
d = pd.read_csv(RES / "shap_dependence.csv.gz")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
for ax, f, bins, xl in ((axs[0], "muni_pop_change", [-30, -8, -5, -3, -1, 1, 3, 20], ["−8%未満", "−8〜−5", "−5〜−3", "−3〜−1", "−1〜+1", "+1〜+3", "+3%超"]),
                        (axs[1], "log_pass_10km", None, None)):
    s = d[d.feature == f].copy()
    s["bin"] = pd.cut(s.x, bins) if bins else pd.qcut(s.x, 8)
    m = s.groupby(["bin", "year"], observed=True).shap.mean().unstack()
    for yr, c, ls in ((2017, GRAY, "--"), (2021, LIGHT, "-"), (2026, BLUE, "-")):
        ax.plot(range(len(m)), (np.exp(m[yr]) - 1) * 100, color=c, ls=ls, marker="o", lw=2, label=f"{yr}年")
    ax.axhline(0, color=INK, lw=.6)
    ax.set_xticks(range(len(m)))
    ax.set_xticklabels(xl if xl else [f"{i+1}" for i in range(len(m))], fontsize=8.5)
    ax.legend(frameon=False, fontsize=9)
axs[0].set_title("市区町村の人口増減率（2015→20年）の効き方", loc="left", fontsize=12)
axs[0].set_ylabel("価格への寄与（SHAP を%に換算、区間の平均）"); axs[0].set_xlabel("人口増減率")
axs[1].set_title("10km内の駅の乗降客数の効き方", loc="left", fontsize=12); axs[1].set_xlabel("乗降客数の8分位（1＝少ない、8＝多い）")
for ax, f, lo, hi in ((axs[0], "muni_pop_change", 0, 6), (axs[1], "log_pass_10km", 0, 7)):
    pass
save(fig, "fig5_effect_size.png")

# 図6 頑健性：毎年更新との差
rb = pd.read_csv(RES / "robust_by_variant.csv"); rb = rb[rb.year == "2018-2026"]
main = t[t.year == "2018-2026"].copy(); main.insert(0, "variant", "基本（全地点・20km四方ブロック・LightGBM）")
rb = pd.concat([main, rb])
order = ["基本（全地点・20km四方ブロック・LightGBM）", "属性が10年変わらなかった地点だけ", "地点単位のランダム5分割", "住宅地だけ", "小さいモデル（葉15・200本）", "リッジ回帰"]
strs = [("2年ごと", LIGHT), ("5年ごと", BLUE), ("2017年のまま＋全国の変化で補正", "#f2b093"), ("2017年のまま", ORANGE)]
fig, ax = plt.subplots(figsize=(9, 4.6))
w = .2
for j, (s, c) in enumerate(strs):
    vals = []
    for v in order:
        r = rb[rb.variant == v].set_index("strategy")
        vals.append((r.loc[s, "median_ape"] - r.loc["毎年更新", "median_ape"]) * 100)
    ax.barh(np.arange(len(order)) + (j - 1.5) * w, vals, height=w, color=c, label=s.replace("2017年のまま＋全国の変化で補正", "2017年のまま＋全国補正"))
ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=9); ax.invert_yaxis()
ax.axvline(0, color=INK, lw=.8); ax.set_xlabel("毎年更新との差（誤差の中央値、ポイント。2018〜2026年）")
ax.set_title("どの条件でも「2年ごと≒毎年」「更新しないと悪い」の並びは同じ", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="lower right")
save(fig, "fig6_robustness.png")
print("all figs ok")
