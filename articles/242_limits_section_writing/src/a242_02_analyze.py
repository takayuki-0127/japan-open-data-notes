"""data/ の表から集計と図を作る（clone は不要）"""
import os, re, json, textwrap
import pandas as pd
import matplotlib.pyplot as plt
from common import GROUPS

here = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(here, "..")
ix = pd.read_csv(f"{B}/data/readme_index.csv")
lim = pd.read_csv(f"{B}/data/limits_items.csv")
rev = pd.read_csv(f"{B}/data/review_items.csv")
ex = pd.read_csv(f"{B}/data/rewrite_examples.csv", dtype=str)

# 1. 言えないことの項目の書き方（看板記事 F01〜F295）
FG = GROUPS[2:6]
L = lim[lim.group.isin(FG)].copy()
L["chars"] = L["item"].str.len()
L["has_suisoku"] = L["item"].str.contains("推測")
L["has_number"] = L["item"].str.contains(r"\d")
L["has_next"] = L["item"].str.contains(r"確かめ|調べ|別の|ほかの(?:データ|方法)|必要|見るには|には.{0,6}が要る|次に")
g = L.groupby("group").agg(items=("item", "size"), chars=("chars", "median"), suisoku=("has_suisoku", "mean"),
                           number=("has_number", "mean"), next=("has_next", "mean")).reindex(FG)
art = ix[ix.group.isin(FG)].groupby("group").agg(n=("folder", "size"), has=("has_limits", "mean"), per=("n_limits", "mean")).reindex(FG)
g = art.join(g)
for c in ["suisoku", "number", "next", "has"]:
    g[c] = (g[c] * 100).round(1)
g["per"] = g.per.round(2)
g.to_csv(f"{B}/results/limits_by_group.csv")

# 2. レビューで直したこと（精選 F256〜F295 と T001）の分類（1項目に複数つく）
CATS = {
    "数字・計算の誤り": r"誤り|実際は|正しくは|計算(?:違い|ミス)|合わない|書き間違|取り違|丸め|四捨五入",
    "言い過ぎ・一般化を弱めた": r"言い過ぎ|強すぎ|言い切|支えられ|一般化|限定|限った|弱め|過大|断定|すり替",
    "（推測）を足した": r"推測",
    "計画（PLAN）との対応": r"計画|PLAN|H\d|仮説|反証",
    "事後の分析だと明記": r"事後|後から|結果を見た後|結果を見てから|後付け",
    "因果の言い方を直した": r"因果|引っ張|効いた|原因と",
    "定義・前提・範囲を書いた": r"定義|前提|範囲|母集団|明記",
    "図・表示を直した": r"図\d?|凡例|縦軸|横軸|題",
}
for c, p in CATS.items():
    rev[c] = rev["item"].str.contains(p.replace("(", "(?:").replace("(?:?:", "(?:"))
rc = pd.DataFrame({"items_pct": (rev[list(CATS)].mean() * 100).round(1),
                   "articles": rev.groupby("folder")[list(CATS)].any().sum(),
                   "articles_pct": (rev.groupby("folder")[list(CATS)].any().mean() * 100).round(1)}).sort_values("items_pct")
rc.to_csv(f"{B}/results/review_categories.csv")

summary = {"readmes": int(len(ix)), "commit": "996936a",
           "flagship_limits_items": int(len(L)), "review_articles": int(rev.folder.nunique()), "review_items": int(len(rev)),
           "review_items_per_article_median": float(rev.groupby("folder").size().median()),
           "limits_by_group": g.to_dict("index"), "review_categories": rc.to_dict("index")}
json.dump(summary, open(f"{B}/results/summary.json", "w"), ensure_ascii=False, indent=1)

# 図1：言えないことの書き方の変化
fig, ax = plt.subplots(1, 2, figsize=(9.5, 4))
x = range(len(FG)); lab = [s.replace("（", "\n（") for s in FG]
ax[0].bar(x, g.per, color="#4C72B0")
for i, v in enumerate(g.per): ax[0].text(i, v + 0.15, f"{v:.1f}", ha="center", fontsize=9)
ax[0].set_xticks(list(x)); ax[0].set_xticklabels(lab, fontsize=8.5); ax[0].set_ylim(0, max(g.per) * 1.25)
ax[0].set_title("1本あたりの「言えないこと」の項目数", fontsize=10.5)
w = 0.27
for k, (c, col, name) in enumerate([("suisoku", "#DD8452", "「推測」がある"), ("number", "#55A868", "数字がある"), ("next", "#8172B2", "確かめ方・次に要るものがある")]):
    ax[1].bar([i + (k - 1) * w for i in x], g[c], width=w, color=col, label=name)
ax[1].set_xticks(list(x)); ax[1].set_xticklabels(lab, fontsize=8.5); ax[1].set_ylim(0, 100)
ax[1].set_title("項目のうち、次のものを含む割合（%）", fontsize=10.5); ax[1].legend(fontsize=8, frameon=False, loc="upper left")
for a in ax: a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{B}/figures/a242_limits_by_group.png", dpi=150); plt.close(fig)

# 図2：見直しで直したことの種類
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.barh(rc.index, rc.items_pct, color="#4C72B0")
for i, (v, a) in enumerate(zip(rc.items_pct, rc.articles)):
    ax.text(v + 0.8, i, f"{v:.0f}%（{a}本で1回以上）", va="center", fontsize=9)
ax.set_xlim(0, rc.items_pct.max() * 1.5)
ax.set_xlabel(f"直したこと {len(rev)} 項目に占める割合（%、1項目に複数つく）")
ax.set_title(f"公開前の見直しで直したことの種類（{rev.folder.nunique()}本）", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{B}/figures/a242_review_fixes.png", dpi=150); plt.close(fig)

# 図3：書き直しの例（表）
fig, ax = plt.subplots(figsize=(9.5, 4.6)); ax.axis("off")
rows = [[r.kind, r.article, "\n".join(textwrap.wrap(r.before, 18)), "\n".join(textwrap.wrap(r.after, 30))] for r in ex.itertuples()]
t = ax.table(cellText=rows, colLabels=["直した点", "記事", "直す前", "直した後"], colWidths=[0.14, 0.07, 0.3, 0.49], loc="center", cellLoc="left")
t.auto_set_font_size(False); t.set_fontsize(8.5)
for (i, j), c in t.get_celld().items():
    c.set_height(0.13 if i else 0.07)
    if i == 0: c.set_facecolor("#E8EEF7")
ax.set_title("言い方を直した例（README の「レビューで直したこと」から）", fontsize=11)
fig.tight_layout(); fig.savefig(f"{B}/figures/a242_rewrite_examples.png", dpi=150); plt.close(fig)
print(g.to_string()); print(rc.to_string()); print(summary["review_items_per_article_median"])
