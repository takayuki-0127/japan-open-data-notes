"""268 差の差・回帰不連続・合成コントロールを、どう選んできたか（④ 振り返り R009）

使い方: python a268.py <japan-open-data-notes のクローン>
  A. 手法ごとに、README で2回以上その名前を書いた記事を数え、うち「プラセボ」「事前（の差・傾き）」の確かめを書いた記事を数える
  B. 10本の実例（data/cases.csv は README から手で写した）を、状況→手法→確かめた後の表にする
"""
import re, sys, os, json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from common import readmes, group_of, dedup, title_of

repo = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
docs = dedup(readmes(repo))

METHODS = {
    "差の差": r"差の差|DiD|difference-in-differences",
    "イベントスタディ": r"イベントスタディ|event study",
    "合成コントロール": r"合成コントロール|合成対照|synthetic control|Synthetic DID|SCM",
    "回帰不連続": r"回帰不連続|RDD|RDiT",
    "操作変数": r"操作変数|2SLS|バーティク",
    "中断時系列・ベイズ構造時系列": r"中断時系列|分割時系列|CausalImpact|ベイズ構造時系列",
}
CHECK_PLACEBO = r"プラセボ|placebo|並べ替え"
CHECK_PRE = r"計画前|実施前|開業前|前の期間|事前の(差|傾き|当てはまり|トレンド)|事前トレンド|平行トレンド|並行トレンド|処置前|RMSPE|第1段階|1段目|帯域|バンド幅"
rows = []
for folder, t in docs:
    for m, pat in METHODS.items():
        if len(re.findall(pat, t, re.I)) >= 2:
            rows.append({"article": folder, "group": group_of(folder), "method": m, "title": title_of(t)[:80],
                         "placebo": bool(re.search(CHECK_PLACEBO, t, re.I)),
                         "pre": bool(re.search(CHECK_PRE, t, re.I)),
                         "main": bool(re.search(pat, title_of(t), re.I)) or len(re.findall(pat, t, re.I)) >= 5,
                         "zero": bool(re.search(r"0と区別できない|0をまたぐ|ゼロと区別|区間は0|効果なしと区別できない", t))})
M = pd.DataFrame(rows)
M.to_csv(os.path.join(OUT, "data", "method_articles.csv"), index=False)
gm = M.groupby("method").agg(articles=("article", "size"), main=("main", "sum"), placebo=("placebo", "sum"), pre=("pre", "sum"), zero=("zero", "sum"))
gm["either"] = M.assign(e=M.placebo | M.pre).groupby("method").e.sum()
gm["main_either"] = M[M.main].assign(e=lambda d: d.placebo | d.pre).groupby("method").e.sum()
gm = gm.reindex(list(METHODS)).fillna(0).astype(int)
gm.to_csv(os.path.join(OUT, "results", "method_counts.csv"))
C = pd.read_csv(os.path.join(OUT, "data", "cases.csv"), dtype=str)

summary = {"readmes_dedup": len(docs), "articles_any_method": int(M.article.nunique()),
           "articles_2plus_methods": int((M.groupby("article").size() >= 2).sum()),
           "by_method": gm.to_dict(orient="index"),
           "main_articles": int(M[M.main].article.nunique()),
           "main_with_check": int((M[M.main].groupby("article").placebo.any() | M[M.main].groupby("article").pre.any()).sum()),
           "share_with_check": round(100 * (M.groupby("article").placebo.any() | M.groupby("article").pre.any()).mean(), 1),
           "share_zero_phrase": round(100 * M.groupby("article").zero.any().mean(), 1)}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

# 図1 状況から手法を選ぶ流れ
fig, ax = plt.subplots(figsize=(10.5, 5.4)); ax.axis("off"); ax.set_xlim(0, 10.5); ax.set_ylim(0, 6)
Q = [("比べる相手（処置を受けなかった所）はいるか", 5.4),
     ("処置を受けたのは1つの地域だけか", 4.3),
     ("始まった年は所によってずれるか", 3.2),
     ("年齢・日付などの境目で決まるか", 2.1),
     ("外から決まる変動（産業構成など）を使えるか", 1.0)]
A = [("いない → 対照を複数並べる・中断時系列（F263・F240）", "#e8a23a"),
     ("1つ → 合成コントロール・Synthetic DID（029・F29）", "#4f81bd"),
     ("ずれる → 段階的な差の差（F145）。同じ年なら差の差＋イベントスタディ（F01）", "#4f81bd"),
     ("境目がある → 回帰不連続（F31）・時間の回帰不連続（F88）", "#5b9b5b"),
     ("使える → 操作変数（F46）。第1段階が弱ければ使わない（F234）", "#8064a2")]
for (q, y), (a, c) in zip(Q, A):
    ax.add_patch(FancyBboxPatch((0.1, y - 0.35), 4.1, 0.7, boxstyle="round,pad=0.02", fc="#f2f2f2", ec="#888"))
    ax.text(2.15, y, q, ha="center", va="center", fontsize=9.5)
    ax.annotate("", xy=(4.6, y), xytext=(4.25, y), arrowprops=dict(arrowstyle="->", color="#555"))
    ax.add_patch(FancyBboxPatch((4.65, y - 0.35), 5.75, 0.7, boxstyle="round,pad=0.02", fc=c, ec=c, alpha=0.9))
    ax.text(4.8, y, a, ha="left", va="center", fontsize=9, color="white")
ax.set_title("図1 記事で手法を選んだときの状況（上から順に当てはめた。README の記録から整理）", fontsize=11.5, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a268_flow.png"), dpi=150); plt.close()

# 図2 実例の表
fig, ax = plt.subplots(figsize=(11.5, 4.3)); ax.axis("off")
cell = [[r.記事, r.選んだ手法, r.主な推定, r.確かめ方, r.確かめた後] for r in C.itertuples()]
tb = ax.table(cellText=cell, colLabels=["記事", "選んだ手法", "主な推定", "確かめ方", "確かめた後"], loc="center", cellLoc="left",
              colWidths=[0.06, 0.22, 0.22, 0.22, 0.28])
tb.auto_set_font_size(False); tb.set_fontsize(8.6); tb.scale(1, 1.5)
for (i, j), c in tb.get_celld().items():
    if i == 0:
        c.set_facecolor("#e6e6e6")
ax.set_title("図2 10本の実例：主な推定と、確かめた後（README の数字から）", fontsize=12, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a268_cases.png"), dpi=150); plt.close()

# 図3 手法ごとの記事数と確かめの有無
fig, ax = plt.subplots(figsize=(8.5, 4.2))
x = range(len(gm))
ax.bar(x, gm.articles, color="#e3e3e3", label="手法の名前を2回以上書いた記事（紹介しただけの記事も入る）")
ax.bar(x, gm["main"], color="#c9d6ea", width=0.7, label="うち主な手法として使った記事（題名にある・5回以上）")
ax.bar(x, gm.main_either, color="#4f81bd", width=0.4, label="そのうちプラセボか事前の確かめを書いた記事")
for i, (a, m, e) in enumerate(zip(gm.articles, gm["main"], gm.main_either)):
    ax.text(i, a + 0.4, f"{e}/{m}（{a}）", ha="center", fontsize=9)
ax.set_xticks(list(x)); ax.set_xticklabels([m.replace("・", "・\n") for m in gm.index], fontsize=8.5)
ax.set_ylabel("記事の数"); ax.set_ylim(0, gm.articles.max() * 1.15); ax.legend(fontsize=8.5)
ax.set_title(f"図3 手法ごとの記事の数と、確かめを書いた記事（重複を除いた {len(docs)} 本から）", fontsize=11, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a268_counts.png"), dpi=150); plt.close()
