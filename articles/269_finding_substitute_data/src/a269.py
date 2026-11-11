"""269 「データが取れない」とき、どう代わりを探したか（④ 振り返り R011）

使い方: python a269.py <japan-open-data-notes のクローン>
  A. README の文のうち「代わり・代用・代替・取れない・公開されていない・載っていない」などを含む文を拾う
  B. 拾った文を、どう代わりを作ったか（6種類）の言葉で分ける（1文に複数つく）
  C. 実例（data/cases.csv は README から手で写した）
"""
import re, sys, os, json, random
import pandas as pd
import matplotlib.pyplot as plt
from common import readmes, group_of, GROUPS, dedup

repo = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
docs = dedup(readmes(repo))

HIT = r"代わりに|代わりの|の代わり|代用|代替|取れな|取得できな|入手できな|公開されていな|公表されていな|載っていな|まだ出ていな|ないため|ないので"
NEED = r"データ|統計|表|値|数|系列|公表|公開|載って|ファイル|区分|項目"
KIND = {
    "別の統計・別の表に切り替えた": r"別の|ほかの統計|別表|に切り替え|で代用|を代わりに|代わりに.{0,30}(使|用い|とっ|取っ)|から取",
    "単位を粗くした（日→月、市→県など）": r"月次|月の|年次|年の値|都道府県|全国|県単位|粗い|まとめ|合計で",
    "近い指標で見立てた": r"代理|目安|近い|見立て|みなし|に近似|近似|として扱",
    "延ばした・推計した（推測）": r"延ばし|推計し|補間|按分|直線でつな|伸びで",
    "期間・範囲を変えた": r"期間|年から|年まで|年度から|年度まで|以降|以前|に限っ|に絞",
    "手で写した・PDF から起こした": r"転記|手で|PDF|書き起こ|写し",
}
rows = []
for folder, t in docs:
    for s in re.split(r"(?<=[。\n])", t):
        s = s.strip()
        if len(s) < 12 or not re.search(HIT, s) or not re.search(NEED, s) or re.search(r"代替バイアス|代替効果|交差弾力|みなせない", s):
            continue
        r = {"article": folder, "group": group_of(folder), "sentence": s[:240]}
        for k, v in KIND.items():
            r[k] = bool(re.search(v, s))
        rows.append(r)
S = pd.DataFrame(rows)
S.to_csv(os.path.join(OUT, "data", "substitute_sentences.csv"), index=False)
per_art = S.groupby("article")[list(KIND)].any()
kind_articles = per_art.sum().sort_values()
kind_articles.to_csv(os.path.join(OUT, "results", "kind_articles.csv"), header=["articles"])
none = int((~per_art.any(axis=1)).sum())

ga = pd.DataFrame({"n": pd.Series([group_of(f) for f, _ in docs]).value_counts(),
                   "hit": S.groupby("group").article.nunique()}).reindex(GROUPS).fillna(0).astype(int)
ga["pct"] = (100 * ga.hit / ga.n).round(1)
ga.to_csv(os.path.join(OUT, "results", "by_group.csv"))

# 目で確かめる（乱数 seed 11 で 20 文）
random.seed(11)
smp = S.sample(n=min(20, len(S)), random_state=11)[["article", "sentence"]]
smp.to_csv(os.path.join(OUT, "data", "precision_sample.csv"), index=False)

summary = {"readmes_dedup": len(docs), "sentences": int(len(S)), "articles": int(S.article.nunique()),
           "articles_pct": round(100 * S.article.nunique() / len(docs), 1),
           "kind_articles": {k: int(v) for k, v in kind_articles.items()}, "articles_no_kind": none,
           "by_group": ga.to_dict(orient="index")}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

C = pd.read_csv(os.path.join(OUT, "data", "cases.csv"), dtype=str)

# 図1 実例の表
fig, ax = plt.subplots(figsize=(11.5, 4.1)); ax.axis("off")
cell = [[r.記事, r.ほしかったもの, r.代わりにしたもの, r.確かめたこと, r.言えなくなったこと] for r in C.itertuples()]
tb = ax.table(cellText=cell, colLabels=["記事", "ほしかったもの", "代わりにしたもの", "確かめたこと", "言えなくなったこと"],
              loc="center", cellLoc="left", colWidths=[0.06, 0.2, 0.25, 0.24, 0.25])
tb.auto_set_font_size(False); tb.set_fontsize(8.4); tb.scale(1, 1.55)
for (i, j), c in tb.get_celld().items():
    if i == 0:
        c.set_facecolor("#e6e6e6")
ax.set_title("図1 代わりを探した9本：何の代わりに、何を使ったか（README から）", fontsize=12, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a269_cases.png"), dpi=150); plt.close()

# 図2 代わりの作り方
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.barh(range(len(kind_articles)), kind_articles.values, color="#4f81bd")
for i, v in enumerate(kind_articles.values):
    ax.text(v + 0.5, i, str(int(v)), va="center", fontsize=9)
ax.set_yticks(range(len(kind_articles))); ax.set_yticklabels(kind_articles.index, fontsize=9)
ax.set_xlabel(f"記事の数（代わりの記録がある {S.article.nunique()} 本のうち。1本に複数つく）")
ax.set_title("図2 代わりをどう作ったか（README の文を言葉で分けた）", fontsize=12, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a269_kinds.png"), dpi=150); plt.close()

# 図3 グループ別
SHORT = {"F256–F295（精選）": "精選\nF256–F295", "227–・T（1000本計画）": "1000本計画\n227–・T"}
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.bar(range(len(ga)), ga.pct, color="#5b9b5b")
for i, (p, h, n) in enumerate(zip(ga.pct, ga.hit, ga.n)):
    ax.text(i, p + 1, f"{p:.0f}%\n（{h}/{n}）", ha="center", fontsize=8.5)
ax.set_xticks(range(len(ga))); ax.set_xticklabels([SHORT.get(g, g) for g in ga.index], fontsize=8.5)
ax.set_ylabel("代わりの記録がある記事の割合（%）"); ax.set_ylim(0, max(ga.pct) * 1.3)
ax.set_title("図3 代わりの記録がある記事の割合（グループ別）", fontsize=12, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a269_groups.png"), dpi=150); plt.close()
