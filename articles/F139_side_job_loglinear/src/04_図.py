"""図を作る（figures/）。入力: data/side_job_long.csv, results/*.csv"""
from pathlib import Path
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]; R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    font_manager.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C17, C22 = "#9aa5b1", "#1f5aa6"
SRC = "出典：総務省統計局「就業構造基本調査」（2017年・2022年）第52表をもとに作成（所得不詳を除く有業者）"

crude = pd.read_csv(R / "crude_rates.csv")
def lab(v): return v.split("_", 1)[1] if "_" in v and v.split("_")[0].isdigit() else v
ORDER = {"sex": ["男", "女"], "age": ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65〜74歳", "75歳以上"],
         "emp": ["正規", "非正規", "役員", "自営業主など"],
         "inc6": ["1_100万円未満", "2_100〜199万円", "3_200〜299万円", "4_300〜499万円", "5_500〜699万円", "6_700万円以上"]}
TITLE = {"sex": "男女", "age": "年齢", "emp": "本業の雇用形態", "inc6": "本業の年間所得"}

# 図1 属性ごとの副業の割合
fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
for ax, var in zip(axes.flat, ["sex", "age", "emp", "inc6"]):
    lv = ORDER[var]; x = np.arange(len(lv)); w = 0.38
    for i, (y, c) in enumerate([(2017, C17), (2022, C22)]):
        d = crude[(crude.year == y) & (crude["var"] == var)].set_index("level").reindex(lv)
        ax.bar(x + (i - 0.5) * w, 100 * d.rate, w, color=c, label=f"{y}年")
    ax.set_xticks(x); ax.set_xticklabels([lab(v) for v in lv], rotation=30 if len(lv) > 4 else 0, ha="right" if len(lv) > 4 else "center", fontsize=9)
    ax.set_title(TITLE[var], loc="left", fontsize=12); ax.set_ylabel("副業がある人の割合（%）")
axes[0, 0].legend(frameon=False)
fig.suptitle("副業がある人の割合は、雇用形態と所得で大きく違った", x=0.02, ha="left", fontsize=14, fontweight="bold")
fig.text(0.02, 0.005, SRC, fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.02, 1, 0.96)); fig.savefig(F / "fig1_rate_by_attribute.png", dpi=150); plt.close(fig)

# 図2 粗いオッズ比と調整オッズ比（2022）
ors = pd.read_csv(R / "odds_ratios.csv"); o = ors[ors.year == 2022]
rows = []
for var in ["sex", "age", "emp", "inc6"]:
    for lv in ORDER[var]:
        a = o[(o["var"] == var) & (o.level == lv)]
        if len(a) == 0: rows.append((f"{TITLE[var]}：{lab(lv)}（基準）", 1, 1, 1, 1)); continue
        cr = a[a.kind == "粗い"].iloc[0]; ad = a[a.kind == "調整"].iloc[0]
        rows.append((f"{TITLE[var]}：{lab(lv)}", cr.OR, ad.OR, ad.lo, ad.hi))
fig, ax = plt.subplots(figsize=(9, 8.5)); yy = np.arange(len(rows))[::-1]
for yv, (name, cr, ad, lo, hi) in zip(yy, rows):
    ax.plot([lo, hi], [yv, yv], color=C22, lw=2)
    ax.scatter(cr, yv, marker="o", facecolor="white", edgecolor=C17, s=45, zorder=3)
    ax.scatter(ad, yv, marker="o", color=C22, s=40, zorder=4)
ax.axvline(1, color="#333", lw=0.8); ax.set_xscale("log"); ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 3, 4]); ax.set_xticklabels(["0.5", "0.75", "1", "1.5", "2", "3", "4"])
ax.set_yticks(yy); ax.set_yticklabels([r[0] for r in rows], fontsize=9)
ax.scatter([], [], facecolor="white", edgecolor=C17, label="そのまま比べたとき（粗いオッズ比）"); ax.scatter([], [], color=C22, label="他の3属性をそろえたとき（調整オッズ比・95%区間）")
ax.legend(frameon=False, loc="lower right", fontsize=9); ax.set_xlabel("副業がある人のオッズ比（基準＝1）")
ax.set_title("2022年：女性と高齢層の「多さ」は、雇用形態と所得をそろえると消えた", loc="left", fontsize=12.5, fontweight="bold")
fig.text(0.01, 0.005, SRC + "。基準は男・35〜44歳・正規・300〜499万円", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(F / "fig2_crude_vs_adjusted_or.png", dpi=150); plt.close(fig)

# 図3 モデルごとの逸脱度の説明割合
m = pd.read_csv(R / "model_comparison.csv")
keys = ["M1 sexだけ", "M1 ageだけ", "M1 inc6だけ", "M1 empだけ", "M2 4属性の主効果", "M3 主効果＋age×emp", "M3 主効果＋age×inc6", "M3 主効果＋emp×inc6", "M4 主効果＋2属性の組み合わせすべて"]
names = ["男女だけ", "年齢だけ", "所得だけ", "雇用形態だけ", "4属性（足し算）", "＋年齢×雇用形態", "＋年齢×所得", "＋雇用形態×所得", "＋2属性の組み合わせすべて"]
fig, ax = plt.subplots(figsize=(9.5, 5.5)); x = np.arange(len(keys)); w = 0.38
for i, (y, c) in enumerate([(2017, C17), (2022, C22)]):
    d = m[m.year == y].set_index("model").reindex(keys)
    b = ax.bar(x + (i - 0.5) * w, 100 * d.dev_explained, w, color=c, label=f"{y}年")
    if y == 2022:
        for xi, v in zip(x, d.dev_explained): ax.text(xi + 0.19, 100 * v + 1, f"{100*v:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9.5); ax.set_ylabel("逸脱度のうち説明できた割合（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False); ax.set_title("雇用形態だけで7割を説明し、年齢との組み合わせを足すと8割半ばになった", loc="left", fontsize=12.5, fontweight="bold")
fig.text(0.01, 0.005, SRC + "。男女×年齢×雇用形態×所得6区分のセルで当てはめ", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(F / "fig3_deviance_explained.png", dpi=150); plt.close(fig)

# 図4 年齢×雇用形態（2022）
df = pd.read_csv(ROOT / "data" / "side_job_long.csv"); b = df[df.hours == "総数"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
cols = {"正規": "#1f5aa6", "非正規": "#d1762b", "役員": "#4c9a5b", "自営業主など": "#8a5aa6"}
for ax, y in zip(axes, (2017, 2022)):
    d = b[b.year == y]; t = d.pivot_table(index="age", columns=["emp", "side"], values="n", aggfunc="sum").reindex(ORDER["age"])
    for e in ORDER["emp"]:
        r = t[(e, "副業あり")] / (t[(e, "副業あり")] + t[(e, "副業なし")])
        ax.plot(range(7), 100 * r.values, marker="o", color=cols[e], label=e)
    ax.set_xticks(range(7)); ax.set_xticklabels(ORDER["age"], rotation=30, ha="right", fontsize=9); ax.set_title(f"{y}年", loc="left")
axes[0].set_ylabel("副業がある人の割合（%）"); axes[1].legend(frameon=False, fontsize=9)
fig.suptitle("正規の人は年齢とともに副業が増えるが、非正規・自営業主などは若いうちから高く、年齢による差が小さい", x=0.02, ha="left", fontsize=13, fontweight="bold")
fig.text(0.02, 0.005, SRC, fontsize=8, color="#555"); fig.tight_layout(rect=(0, 0.03, 1, 0.94)); fig.savefig(F / "fig4_age_by_employment.png", dpi=150); plt.close(fig)

# 図5 2017→2022 の変化
ch = pd.read_csv(R / "change_by_group.csv"); s = json.load(open(R / "summary.json"))
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1.3, 1, 1.3]})
for ax, var in zip([axes[0], axes[2]], ["age", "inc6"]):
    d = ch[(ch["var"] == var) & ch.level.notna()].set_index("level").reindex(ORDER[var])
    ax.bar(range(len(d)), d.diff_pt, color=C22); ax.set_xticks(range(len(d))); ax.set_xticklabels([lab(v) for v in ORDER[var]], rotation=30, ha="right", fontsize=9)
    ax.set_title(TITLE[var] + "ごとの変化", loc="left", fontsize=11); ax.set_ylabel("変化（%ポイント）"); ax.axhline(0, color="#333", lw=0.6)
c = s["change"]; vals = [c["total_pt"], c["within_pt"], c["composition_pt"]]
axes[1].bar([0, 1, 2], vals, color=[C22, "#5b8fd1", "#c9a227"]); axes[1].axhline(0, color="#333", lw=0.6)
axes[1].set_xticks([0, 1, 2]); axes[1].set_xticklabels(["全体の変化", "同じ属性の中で\n増えた分", "属性の構成が\n変わった分"], fontsize=9)
for i, v in enumerate(vals): axes[1].text(i, v + (0.03 if v >= 0 else -0.08), f"{v:+.2f}", ha="center", fontsize=9)
axes[1].set_title("全体の変化の分解", loc="left", fontsize=11); axes[1].set_ylim(-0.3, 1.1); axes[1].set_ylabel("変化（%ポイント）")
fig.suptitle(f"2017→2022年：副業の割合は{100*s['rate_2017']:.1f}%→{100*s['rate_2022']:.1f}%。増えたのは高齢層と低所得層で、構成の変化ではなかった", x=0.02, ha="left", fontsize=12.5, fontweight="bold")
fig.text(0.02, 0.005, SRC + "。分解は男女×年齢×雇用形態×所得6区分のセルで計算", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 0.93)); fig.savefig(F / "fig5_change_2017_2022.png", dpi=150); plt.close(fig)
print("ok")
