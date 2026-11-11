"""data/ の表から集計と図を作る（clone は不要）"""
import os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import GROUPS

here = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(here, "..")
ix = pd.read_csv(f"{B}/data/readme_index.csv")
d = pd.read_csv(f"{B}/data/trouble_lines.csv")
pc = pd.read_csv(f"{B}/data/precision_check.csv")
cases = pd.read_csv(f"{B}/data/cases.csv", dtype=str)
N = len(ix)

# 1. カテゴリごとの記事数
cat = d.groupby("category").folder.nunique().rename("articles").reset_index()
cat = cat.merge(pc, on="category")
cat["share_pct"] = (cat.articles / N * 100).round(1)
cat["precision_pct"] = (cat.n_relevant / cat.n_checked * 100).round(0)
cat["articles_adj"] = (cat.articles * cat.n_relevant / cat.n_checked).round(0)
cat = cat.sort_values("articles")
cat.to_csv(f"{B}/results/by_category.csv", index=False)

# 2. グループごと：1つ以上のカテゴリが出た記事の割合と、平均のカテゴリ数
per = d.groupby("folder").category.nunique()
ix["n_cat"] = ix.folder.map(per).fillna(0)
ix["any"] = ix.n_cat > 0
gr = ix.groupby("group").agg(n=("folder", "size"), any_pct=("any", "mean"), mean_cat=("n_cat", "mean"), mean_chars=("n_chars", "mean"))
gr = gr.reindex([g for g in GROUPS if g in gr.index])
gr["any_pct"] = (gr.any_pct * 100).round(1); gr["mean_cat"] = gr.mean_cat.round(2); gr["mean_chars"] = gr.mean_chars.round(0)
gr.to_csv(f"{B}/results/by_group.csv")
# 同じ文字数あたりで見る（長い README ほど拾いやすい）
ix["cat_per_10k"] = ix.n_cat / ix.n_chars * 10000
gr2 = ix.groupby("group").cat_per_10k.mean().reindex(gr.index).round(2)
gr2.to_csv(f"{B}/results/by_group_per10k.csv")

summary = {
    "readmes": int(N), "commit": "996936a", "matched_lines": int(len(d)),
    "any_trouble_articles": int(ix["any"].sum()), "any_trouble_pct": round(ix["any"].mean() * 100, 1),
    "by_category": cat.set_index("category")[["articles", "share_pct", "precision_pct", "articles_adj"]].to_dict("index"),
    "by_group": gr.to_dict("index"), "cat_per_10k_chars": gr2.to_dict(),
}
json.dump(summary, open(f"{B}/results/summary.json", "w"), ensure_ascii=False, indent=1)

# 図1：カテゴリごとの記事数
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.barh(cat.category, cat.articles, color="#4C72B0")
for i, r in enumerate(cat.itertuples()):
    ax.text(r.articles + 1, i, f"{r.articles}本（目で確かめた当たり {int(r.precision_pct)}%）", va="center", fontsize=9)
ax.set_xlim(0, cat.articles.max() * 1.6)
ax.set_xlabel("その種類の困りごとが README に書かれていた記事の数（501本中）")
ax.set_title("公的データで困ったことの種類（README の言葉から拾った数）", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{B}/figures/a241_categories.png", dpi=150); plt.close(fig)

# 図2：グループごと
fig, ax = plt.subplots(figsize=(8, 4.2))
x = range(len(gr))
ax.bar(x, gr.any_pct, color="#55A868")
for i, (p, n) in enumerate(zip(gr.any_pct, gr.n)):
    ax.text(i, p + 1.5, f"{p:.0f}%\n（{n}本）", ha="center", fontsize=8.5)
ax.set_xticks(list(x)); ax.set_xticklabels([g.replace("（", "\n（") for g in gr.index], fontsize=8.5)
ax.set_ylim(0, 100); ax.set_ylabel("困りごとが1つ以上書かれていた記事の割合（%）")
ax.set_title("記事のまとまりごとに見ると（README が長いほど拾いやすい点に注意）", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{B}/figures/a241_groups.png", dpi=150); plt.close(fig)

# 図3：実際の例（表）
fig, ax = plt.subplots(figsize=(9.5, 4.8)); ax.axis("off")
import textwrap
rows = [[r.category, r.article, "\n".join(textwrap.wrap(r.case, 52))] for r in cases.itertuples()]
t = ax.table(cellText=rows, colLabels=["種類", "記事", "困ったことと、どうしたか"], colWidths=[0.24, 0.07, 0.69], loc="center", cellLoc="left")
t.auto_set_font_size(False); t.set_fontsize(8)
for (i, j), c in t.get_celld().items():
    c.set_height(0.088 if i else 0.06)
    if i == 0: c.set_facecolor("#E8EEF7")
ax.set_title("実際にあった例（記事の README から）", fontsize=11)
fig.tight_layout(); fig.savefig(f"{B}/figures/a241_cases.png", dpi=150); plt.close(fig)
print(json.dumps({k: summary[k] for k in ["any_trouble_articles", "any_trouble_pct"]}, ensure_ascii=False))
print(cat[["category", "articles", "share_pct", "precision_pct", "articles_adj"]].to_string(index=False)); print(gr); print(gr2)
