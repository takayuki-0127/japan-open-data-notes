"""F178 の図（5枚）"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import statsmodels.api as sm
from common import DATA, RES, FIG

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
FIG.mkdir(exist_ok=True)
C1, C2, C3, C4, GR = "#2a6f97", "#d1495b", "#edae49", "#66a182", "#9a9a9a"

M = pd.read_csv(DATA / "pref_master.csv")
S = pd.read_csv(RES / "model_summary.csv").set_index("model")
INF = pd.read_csv(RES / "influence_by_pref.csv")
L2 = pd.read_csv(RES / "leave_two_out.csv")
P = pd.read_csv(RES / "f80_pairs.csv")
BY = pd.read_csv(RES / "flip_by_pbin.csv")
J = json.load(open(RES / "f80_sweep_summary.json"))

# 1 物価と所得：東京を含む・除く、頑健回帰
fig, ax = plt.subplots(figsize=(8, 5.4))
x, y = M.ln_inc, M.ln_price * 100
tk = M.pref == "東京"
ax.scatter(np.exp(x[~tk]), y[~tk], s=28, color=C1, alpha=.8, label="46道府県")
ax.scatter(np.exp(x[tk]), y[tk], s=60, color=C2, label="東京")
xs = np.linspace(x.min(), x.max(), 50)
def line(model, lab, col, ls):
    b = model.params
    ax.plot(np.exp(xs), (b.iloc[0] + b.iloc[1] * xs) * 100, color=col, ls=ls, lw=2, label=lab)
X = sm.add_constant(x)
line(sm.OLS(M.ln_price, X).fit(), f"最小二乗（47県） 傾き {S.loc['A_物価と所得','coef']:.3f}", C1, "-")
line(sm.OLS(M.ln_price[~tk], X[~tk]).fit(), f"最小二乗（東京を除く） 傾き {S.loc['A_物価と所得','top_dfb_coef_without']:.3f}", C2, "--")
line(sm.QuantReg(M.ln_price, X).fit(q=.5), f"中央値の回帰（47県） 傾き {S.loc['A_物価と所得','lad_coef']:.3f}", C3, ":")
ax.set_xlabel("所得（課税対象所得÷納税義務者数、2024年、千円）")
ax.set_ylabel("物価の地域差（全国＝0、%・対数）")
ax.set_title("物価と所得の傾きは、東京1点で0.067→0.042に", loc="left")
ax.legend(fontsize=9, frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "f178_1_price_income_tokyo.png", dpi=150); plt.close(fig)

# 2 DFBETA（注目する係数への影響）を県ごとに：A と B4
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=False)
for ax, m, ttl in zip(axes, ["A_物価と所得", "B4_女性の寿命と医師（DAG＋気温・失業）"], ["物価と所得（F114）", "女性の寿命と医師・調整あり（F65）"]):
    t = INF[INF.model == m].sort_values("dfbeta").reset_index(drop=True)
    thr = 2 / np.sqrt(47)
    cols = [C2 if abs(v) > 1 else (C3 if abs(v) > thr else GR) for v in t.dfbeta]
    ax.bar(range(47), t.dfbeta, color=cols)
    for v in [thr, -thr]: ax.axhline(v, color=C3, ls="--", lw=1)
    for v in [1, -1]: ax.axhline(v, color=C2, ls=":", lw=1)
    big = t[t.dfbeta.abs() > 1]
    for i, r in big.iterrows(): ax.text(i, r.dfbeta + (0.05 if r.dfbeta > 0 else -0.15), r.pref, ha="center", fontsize=9, color=C2)
    ax.set_xticks([]); ax.set_xlabel("47都道府県（DFBETA の小さい順）"); ax.set_title(ttl, loc="left", fontsize=11)
axes[0].set_ylabel("DFBETA（その県を除くと、係数が標準誤差の何倍動くか）")
fig.suptitle("目安 2/√n（破線）を超える県は4〜5、1（点線）を超えるのは各1県", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f178_2_dfbeta_by_pref.png", dpi=150); plt.close(fig)

# 3 1県・2県を除いたときの係数（元の係数＝1）と、p<0.05 が保たれたか
fig, ax = plt.subplots(figsize=(9, 4.8))
models = ["A_物価と所得", "B3_女性の寿命と医師（調整なし）", "B4_女性の寿命と医師（DAG＋気温・失業）"]
labels = ["物価と所得", "女性の寿命と医師\n（調整なし）", "女性の寿命と医師\n（調整あり）"]
rng = np.random.default_rng(178)
for k, m in enumerate(models):
    d = L2[L2.model == m]; b0 = S.loc[m, "coef"]
    r = d.coef / b0; ok = d.p < 0.05
    jit = rng.uniform(-.28, .28, len(d))
    ax.scatter(r[ok], k + jit[ok], s=4, color=C1, alpha=.35)
    ax.scatter(r[~ok], k + jit[~ok.values], s=6, color=C2, alpha=.8)
    ax.text(1.62, k, f"p≥0.05 {(~ok).mean():.1%}", va="center", fontsize=10, color=C2)
ax.axvline(1, color="k", lw=.8); ax.axvline(0, color=GR, lw=.8)
ax.set_yticks(range(3)); ax.set_yticklabels(labels); ax.set_xlim(-0.1, 1.95)
ax.set_xlabel("2県を除いたときの係数（元の係数＝1）。赤は p≥0.05 になった組み合わせ")
ax.set_title("2県を除く1,081通り：結論が変わる組み合わせは0.2〜13%", loc="left")
fig.tight_layout(); fig.savefig(FIG / "f178_3_leave_two_out.png", dpi=150); plt.close(fig)

# 4 F80 の指標どうし：最も効く1県を除くと判定が変わる割合（p の大きさ別）と、乱数データとの比較
fig, ax = plt.subplots(figsize=(9, 4.8))
xi = np.arange(len(BY))
ax.plot(xi, BY.flip_real * 100, "o-", color=C2, lw=2, label=f"都道府県の指標（{J['n_pairs']:,}組）")
ax.plot(xi, BY["flip_sim_正規"] * 100, "s--", color=C1, label="乱数：正規分布")
ax.plot(xi, BY["flip_sim_t分布（自由度3）"] * 100, "^:", color=C4, label="乱数：裾の重い分布（t、自由度3）")
ax.set_xticks(xi); ax.set_xticklabels(BY.pbin, fontsize=9)
ax.axvspan(3.5, 5.5, color=C3, alpha=.12)
ax.set_xlabel("元の回帰の p 値"); ax.set_ylabel("1県を除くと p<0.05 の判定が入れ替わる割合（%）")
ax.set_title("p が 0.001〜0.01 の組では、正規分布の約10倍入れ替わる", loc="left")
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f178_4_flip_by_p.png", dpi=150); plt.close(fig)

# 5 確かめ方ごとに、p<0.05 だった組のうち p≥0.05 になる割合 ＋ 何県で変わるか
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw=dict(width_ratios=[1.3, 1]))
items = [("いちばん効く1県を除く（DFBETA）", J["flip_drop_top_dfb"]), ("Cook の距離が最大の1県を除く", J["flip_drop_top_cook"]),
         ("向きを逆にして1県を除く", J["flip_reverse"]), ("どちらかの向きで1県を除く", J["flip_either_direction"]),
         ("標準誤差を HC3 にする", J["hc3_disagree"]), ("順位相関にする", J["spearman_disagree"]),
         ("Huber の頑健回帰", J["huber_disagree"]), ("両方を対数にする", J["log_disagree"])]
ax = axes[0]
ax.barh(range(len(items))[::-1], [v * 100 for _, v in items], color=[C2] * 4 + [C1] * 4)
ax.set_yticks(range(len(items))[::-1]); ax.set_yticklabels([a for a, _ in items], fontsize=9)
for i, (_, v) in enumerate(items): ax.text(v * 100 + .3, len(items) - 1 - i, f"{v:.0%}", va="center", fontsize=9)
ax.set_xlabel(f"p<0.05 だった{J['n_sig']:,}組のうち、p≥0.05 になる割合（%）")
ax.set_title("確かめ方で、答えの変わり方は3〜16%", loc="left", fontsize=11)
g = J["greedy_steps_dist"]; ks = ["1.0", "2.0", "3.0", "4.0", "5.0", "NaN"]; lab = ["1県", "2県", "3県", "4県", "5県", "6県以上"]
v = np.array([g.get(k, 0) for k in ks]) / J["n_sig"] * 100
ax = axes[1]; ax.bar(lab, v, color=[C2, C3, C3, C3, C3, C1])
for i, t in enumerate(v): ax.text(i, t + .5, f"{t:.0f}%", ha="center", fontsize=9)
ax.set_ylabel("割合（%）"); ax.set_title("何県除けば p≥0.05 になるか", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f178_5_methods_and_steps.png", dpi=150); plt.close(fig)
print("ok")
