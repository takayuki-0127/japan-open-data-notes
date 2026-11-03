"""04 図：figures/ に PNG を5枚書き出す。"""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "axes.spines.top": False, "axes.spines.right": False})
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results"); F = os.path.join(ROOT, "figures"); os.makedirs(F, exist_ok=True)
SRC = "出典：総務省「令和4年就業構造基本調査」（e-Stat データベース 表03700・03800）を加工して作成"
C1, C2, C3, CG = "#1f5fa8", "#d9822b", "#2e9e6a", "#8a8a8a"
BC = {"北海道・東北": "#4c78a8", "関東": "#e45756", "中部": "#54a24b", "近畿": "#f58518", "中国・四国": "#72b7b2", "九州・沖縄": "#b279a2"}
S = json.load(open(os.path.join(R, "summary.json"), encoding="utf-8"))
IND = pd.read_csv(os.path.join(R, "industry_national.csv"), index_col=0)
T = pd.read_csv(os.path.join(R, "decomp_industry_tw.csv"))
RB = pd.read_csv(os.path.join(R, "robustness.csv"))
def foot(fig): fig.text(0.01, 0.005, SRC, fontsize=7, color=CG)
def short(s): return s[1:].replace("（他に分類されないもの）", "（他）").replace("（他に分類されるものを除く）", "").replace("，", "・")

# 図1 産業別のテレワーク実施率（全国）
d = IND[~IND.index.str.contains("分類不能")].sort_values("tw_rate")
fig, ax = plt.subplots(figsize=(8.5, 6.2))
y = np.arange(len(d))
ax.barh(y, d.tw_rate * 100, color=C1, alpha=0.35, label="過去1年にテレワークをした")
ax.barh(y, d.f80_rate * 100, color=C1, label="うち、働く日の8割以上がテレワーク")
for i, (a, b) in enumerate(zip(d.tw_rate, d.f80_rate)):
    ax.text(a * 100 + 0.8, i, f"{a*100:.0f}%", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels([short(s) for s in d.index], fontsize=8.5)
ax.set_xlabel("有業者に占める割合（%）"); ax.axvline(S["national_rate"] * 100, color=CG, ls=":", lw=1)
ax.text(S["national_rate"] * 100 + 0.5, 0.2, f"全体 {S['national_rate']*100:.1f}%", color=CG, fontsize=8)
ax.set_title("産業で大きく違うテレワーク：情報通信は8割、宿泊・飲食や医療・福祉は3〜4%", fontsize=11, loc="left")
ax.legend(loc="lower right", fontsize=8, frameon=False)
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig1_industry_rates.png"), dpi=150); plt.close(fig)

# 図2 産業構成だけで見込んだ率 vs 実際の率
fig, ax = plt.subplots(figsize=(7.8, 6.2))
for b, c in BC.items():
    g = T[T.block == b]; ax.scatter(g.expected * 100, g.actual * 100, s=np.sqrt(g.employed) / 25, color=c, alpha=0.8, label=b, edgecolor="white", lw=0.5)
lim = [0, 42]; ax.plot(lim, lim, color=CG, lw=1, ls="--"); ax.set_xlim(12, 28); ax.set_ylim(4, 42)
ax.text(26.6, 25, "見込みどおり", color=CG, fontsize=8, rotation=0)
for p in ["東京都", "神奈川県", "千葉県", "埼玉県", "大阪府", "愛知県"]:
    r = T.set_index("region").loc[p]; ax.annotate(p, (r.expected * 100, r.actual * 100), xytext=(5, -3), textcoords="offset points", fontsize=8)
ax.set_xlabel("産業の構成だけから見込んだ実施率（%）\n（各産業の全国の実施率 × その県の産業構成）")
ax.set_ylabel("実際の実施率（%）")
ax.set_title(f"産業構成の見込みの幅（{T.expected.min()*100:.0f}〜{T.expected.max()*100:.0f}%）より、\n実際の幅（{T.actual.min()*100:.0f}〜{T.actual.max()*100:.0f}%）のほうがずっと広い", fontsize=11, loc="left")
ax.legend(fontsize=8, frameon=False, loc="upper left", title="円の大きさ＝有業者数", title_fontsize=7.5)
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig2_expected_vs_actual.png"), dpi=150); plt.close(fig)

# 図3 都道府県の差の分解（県コード順）
fig, ax = plt.subplots(figsize=(11, 5.4))
x = np.arange(len(T))
ax.bar(x, T.comp * 100, color=C2, label="産業の構成の違い")
pos = np.where((T.comp >= 0) == (T.within >= 0), T.comp * 100, 0)
ax.bar(x, T.within * 100, bottom=pos, color=C1, alpha=0.8, label="同じ産業の中での実施率の違い")
ax.scatter(x, T.gap * 100, color="black", s=12, zorder=3, label="全国（18.9%）との差")
ax.axhline(0, color="black", lw=0.6)
ax.set_xticks(x); ax.set_xticklabels([{"北海道":"北海道","東京都":"東京","京都府":"京都","大阪府":"大阪"}.get(p, p[:-1]) for p in T.region], rotation=90, fontsize=7.5)
ax.set_ylabel("全国との差（ポイント）")
ax.set_title(f"47都道府県のうち{47-S['n_pref_comp_larger_abs']}で、差の大部分は「同じ産業の中の違い」だった（県コード順）", fontsize=11, loc="left")
ax.legend(fontsize=8, frameon=False, loc="upper left")
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig3_decomposition.png"), dpi=150); plt.close(fig)

# 図4 同じ産業での 東京圏 と それ以外
d = IND[(~IND.index.str.contains("分類不能")) & (IND.employed > 100000)].sort_values("tw_rate_others")
fig, ax = plt.subplots(figsize=(8.5, 6.2)); y = np.arange(len(d))
ax.hlines(y, d.tw_rate_others * 100, d.tw_rate_tokyo_area * 100, color=CG, lw=1.5)
ax.scatter(d.tw_rate_others * 100, y, color=C3, s=30, label="東京圏以外の43道府県", zorder=3)
ax.scatter(d.tw_rate_tokyo_area * 100, y, color="#e45756", s=30, label="東京圏（埼玉・千葉・東京・神奈川）", zorder=3)
for i, r in enumerate(d.ratio_tokyo_others): ax.text(d.tw_rate_tokyo_area.iloc[i] * 100 + 1.2, i, f"{r:.1f}倍", va="center", fontsize=7.5, color="#e45756")
ax.set_yticks(y); ax.set_yticklabels([short(s) for s in d.index], fontsize=8.5); ax.set_xlabel("テレワーク実施率（%）")
ax.set_title("同じ産業でも、東京圏の実施率はそれ以外の1.2〜2.4倍", fontsize=11, loc="left")
ax.legend(fontsize=8, frameon=False, loc="lower right")
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig4_tokyo_vs_others.png"), dpi=150); plt.close(fig)

# 図5 東京圏への集中と、頑健性
fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.0), gridspec_kw={"width_ratios": [1, 1.6]})
ax = axs[0]
v = [S["tokyo_area_share_employed"], S["tokyo_area_share_tw"], S["tokyo_area_share_f80"]]
ax.bar(range(3), np.array(v) * 100, color=[CG, C1, "#e45756"])
for i, a in enumerate(v): ax.text(i, a * 100 + 1.5, f"{a*100:.0f}%", ha="center", fontsize=10)
ax.set_xticks(range(3)); ax.set_xticklabels(["有業者", "テレワークを\nした人", "8割以上が\nテレワークの人"], fontsize=9)
ax.set_ylim(0, 85); ax.set_ylabel("東京圏（1都3県）が占める割合（%）"); ax.set_title("東京圏への集中", fontsize=11, loc="left")
ax = axs[1]
lab = {"主：有業者・産業・実施した": "主の分析（有業者・産業・実施した）", "雇用者（役員を除く）・産業": "雇用者だけ",
       "有業者・職業（産業の代わり）": "産業の代わりに職業で分ける", "有業者・産業・頻度80%以上": "結果を「8割以上がテレワーク」に",
       "有業者・産業・頻度60%以上": "結果を「6割以上がテレワーク」に", "有業者・産業・自宅で実施": "結果を「自宅で実施」に",
       "東京都を除く46道府県": "東京都を除く", "東京圏（1都3県）を除く43道府県": "東京圏を除く",
       "全国の率で重みづけた構成効果（非対称）": "分解の式を非対称にする"}
rb = RB.iloc[::-1]; yy = np.arange(len(rb))
ax.barh(yy, rb.var_share_comp * 100, color=[C2 if i != len(rb) - 1 else "#b5651d" for i in range(len(rb))])
for i, a in enumerate(rb.var_share_comp): ax.text(a * 100 + 0.8, i, f"{a*100:.0f}%", va="center", fontsize=8.5)
ax.set_yticks(yy); ax.set_yticklabels([lab[s] for s in rb.spec], fontsize=8.5); ax.set_xlim(0, 55)
ax.set_xlabel("県の差（分散）のうち、構成の違いで説明できた割合（%）")
ax.set_title("条件を変えても、構成で説明できるのは2〜4割", fontsize=11, loc="left")
foot(fig); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(os.path.join(F, "fig5_concentration_robustness.png"), dpi=150); plt.close(fig)
print("ok")
