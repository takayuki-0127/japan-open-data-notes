"""05 図（figures/）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, COLORS

ps = pd.read_csv(RES / "pscore.csv"); pairs = pd.read_csv(RES / "pairs.csv")
base_idx = ps.index
# 1. 傾向スコアの分布（マッチング前後）
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
bins = np.linspace(0, 1, 26)
for a, (ttl, t, c) in zip(ax, [("マッチング前", ps[ps.group == "作成"].ps, ps[ps.group == "未作成"].ps),
                               ("マッチング後", ps.loc[pairs.t].ps, ps.loc[pairs.c].ps)]):
    a.hist(t, bins=bins, alpha=.6, color=COLORS["作成"], label=f"計画を作成（{len(t)}）", density=True)
    a.hist(c, bins=bins, alpha=.6, color=COLORS["未作成"], label=f"未作成（{len(c)}" + ("・重複あり）" if ttl == "マッチング後" else "）"), density=True)
    a.set_title(ttl); a.set_xlabel("傾向スコア（計画を作る確率の予測）"); a.legend(fontsize=9)
ax[0].set_ylabel("密度")
fig.suptitle("図1　傾向スコアの分布：似た市町村どうしを組にする", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "a14_pscore.png", dpi=150); plt.close()

# 2. ラブプロット
b = pd.read_csv(RES / "balance.csv")
fig, ax = plt.subplots(figsize=(8, 4.2))
y = np.arange(len(b))[::-1]
ax.scatter(b["マッチング前"], y, color=COLORS["未作成"], label="マッチング前", s=40)
ax.scatter(b["マッチング後"], y, color=COLORS["作成"], label="マッチング後", s=40, marker="D")
for v in (-0.1, 0.1): ax.axvline(v, ls="--", color="#bbb", lw=1)
ax.axvline(0, color="#888", lw=.8)
ax.set_yticks(y); ax.set_yticklabels(b["変数"], fontsize=9)
ax.set_xlabel("標準化した差（作成 − 未作成）。±0.1 の内側ならそろっている")
ax.legend(fontsize=9, loc="lower right")
fig.suptitle("図2　共変量のバランス：マッチングで規模の差はほぼ消えた", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "a14_balance.png", dpi=150); plt.close()

# 3. DID の人口密度の変化（作成・未作成、マッチング後）
d = pd.read_csv(DATA / "analysis.csv")
bs = d[d.group.isin(["作成", "未作成"])].reset_index(drop=True)
ev = pd.read_csv(RES / "event_psm.csv")
per = ["2005→10", "2010→15", "2015→20"]; cols = ["d_dens_2010", "d_dens_2015", "d_dens_2020"]
mt = [bs.loc[pairs.t, c].mean() for c in cols]; mc = [np.average(bs.loc[pairs.c, c], weights=pairs.w) for c in cols]
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4))
x = np.arange(3)
ax[0].plot(x, mt, "o-", color=COLORS["作成"], label="計画を作成（マッチング後）")
ax[0].plot(x, mc, "s--", color=COLORS["未作成"], label="似た未作成の市町村")
ax[0].plot(x, [bs[bs.group == "未作成"][c].mean() for c in cols], ":", color="#bbb", label="未作成の全体")
ax[0].axvspan(1.5, 2.5, color="#fde9d9", alpha=.6); ax[0].text(2, max(mt) + .3, "計画の作成\n（2017〜20年）", ha="center", fontsize=9)
ax[0].set_xticks(x); ax[0].set_xticklabels(per); ax[0].set_ylabel("DID の人口密度の変化（%）")
ax[0].legend(fontsize=8.5, loc="lower left"); ax[0].set_title("5年ごとの変化（平均）", fontsize=11)
ax[1].errorbar(x, ev["マッチング後の差"], yerr=[ev["マッチング後の差"] - ev["95%下"], ev["95%上"] - ev["マッチング後の差"]],
               fmt="o", color=COLORS["作成"], capsize=4)
ax[1].axhline(0, color="#888", lw=.8); ax[1].axvspan(1.5, 2.5, color="#fde9d9", alpha=.6)
ax[1].set_xticks(x); ax[1].set_xticklabels(per); ax[1].set_ylabel("作成 − 似た未作成（%ポイント）")
ax[1].set_title("差と95%区間（ブートストラップ）", fontsize=11)
fig.suptitle("図3　中心部（DID）の人口密度：計画を作った市町村でも、同じように下がっていた", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "a14_trend.png", dpi=150); plt.close()

# 4. 作成時期ごとの効果
c = pd.read_csv(RES / "cohort_att.csv")
fig, ax = plt.subplots(figsize=(9, 4.2))
labs = sorted(c["公表の時点"].unique())
for k, (p, col, off, mk) in enumerate([("2010→15（計画前）", "#9aa0a6", -0.12, "s"), ("2015→20（計画後）", COLORS["作成"], 0.12, "o")]):
    s = c[c["期間"] == p].set_index("公表の時点").loc[labs]
    xx = np.arange(len(labs)) + off
    ax.errorbar(xx, s["効果"], yerr=[s["効果"] - s["95%下"], s["95%上"] - s["効果"]], fmt=mk, color=col, capsize=3, label=p)
s = c[c["期間"].str.contains("計画後")].set_index("公表の時点").loc[labs]
ax.set_xticks(range(len(labs)))
ax.set_xticklabels([f"{l[:7]}まで\n{n}市町村\n国勢調査まで{y}年" for l, n, y in zip(labs, s["市町村数"], s["国勢調査（2020年10月）までの年数"])], fontsize=8.5)
ax.axhline(0, color="#888", lw=.8); ax.set_ylabel("作成 − 未作成（%ポイント）")
ax.legend(fontsize=9); ax.set_title("図4　公表した時期ごとの効果：早く作った市町村ほど効果が大きい、という形は見えない", loc="left", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "a14_cohort.png", dpi=150); plt.close()

# 5. 人口規模別と頑健性
sz = pd.read_csv(RES / "size_att.csv"); rb = pd.read_csv(RES / "robustness.csv")
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [1, 1.9]})
yy = np.arange(len(sz))[::-1]
ax[0].errorbar(sz["効果"], yy, xerr=[sz["効果"] - sz["95%下"], sz["95%上"] - sz["効果"]], fmt="o", color=COLORS["作成"], capsize=3)
ax[0].set_yticks(yy); ax[0].set_yticklabels([f"{a}\n（作成{b}・未作成{c}）" for a, b, c in zip(sz["規模"], sz["作成"], sz["未作成"])], fontsize=8.5)
ax[0].axvline(0, color="#888", lw=.8); ax[0].set_xlabel("効果（%ポイント）"); ax[0].set_title("人口規模別（二重頑健）", fontsize=11)
yy = np.arange(len(rb))[::-1]
colr = [COLORS["作成"] if "偽" not in s else "#9aa0a6" for s in rb["設定"]]
for yi, (_, r), cc in zip(yy, rb.iterrows(), colr):
    ax[1].errorbar(r["効果"], yi, xerr=[[r["効果"] - r["95%下"]], [r["95%上"] - r["効果"]]], fmt="o", color=cc, capsize=3)
ax[1].set_yticks(yy); ax[1].set_yticklabels(rb["設定"], fontsize=8.5)
ax[1].axvline(0, color="#888", lw=.8); ax[1].set_xlabel("効果（%ポイント）"); ax[1].set_title("推定方法・比べる相手を変える", fontsize=11)
fig.suptitle("図5　どの切り方でも、区間は0をまたいだ", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "a14_robustness.png", dpi=150); plt.close()
print("ok")
