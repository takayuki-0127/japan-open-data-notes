"""286 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか（④ 振り返り R010）

使い方: python a286.py <japan-open-data-notes のクローン>
  A. README で勾配ブースティング（LightGBM・XGBoost・GBM など）を書いた記事を数え、うち線形のモデルと並べた記事を数える
  B. 両方の成績を README に書いた10本・19組（data/cases.csv は README から手で写した）で、
     勾配ブースティング ÷ 線形 の比（外れ・誤差は小さいほど良い。R²・C は大きいほど良いので向きをそろえる）を並べる
"""
import re, sys, os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import readmes, group_of, dedup, title_of

repo = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
docs = dedup(readmes(repo))

GBM = r"LightGBM|XGBoost|勾配ブースティング|GBDT|HistGradient|CatBoost|GBM"
LIN = r"線形回帰|リッジ|Ridge|ロジスティック回帰|Lasso|ラッソ|ElasticNet|OLS|重回帰|Cox"
rows = []
for folder, t in docs:
    if re.search(GBM, t):
        rows.append({"article": folder, "group": group_of(folder), "title": title_of(t)[:80],
                     "linear_too": bool(re.search(LIN, t))})
A = pd.DataFrame(rows)
A.to_csv(os.path.join(OUT, "data", "gbm_articles.csv"), index=False)

C = pd.read_csv(os.path.join(OUT, "data", "cases.csv"))
# 比：1 より小さいと勾配ブースティングが良い（R²・C は 1−値 の比で向きをそろえる）
def ratio(r):
    if r.lower_is_better == 1:
        return r.gbm / r.linear
    return (1 - r.gbm) / (1 - r.linear)
C["ratio"] = C.apply(ratio, axis=1)
C["winner"] = C.ratio.map(lambda x: "勾配ブースティング" if x < 0.97 else ("線形" if x > 1.03 else "ほぼ同じ"))
C["label"] = C.article + " " + C.task + "／" + C.split
C.to_csv(os.path.join(OUT, "results", "cases_ratio.csv"), index=False)

# ランダムな分け方 → 場所で分けたときの比の変化
pairs = []
for (a, task), g in C.groupby(["article", "task"], sort=False):
    rnd = g[g.split.str.contains("ランダム")]
    blk = g[g.split.str.contains("ブロック|予報区")]
    if len(rnd) and len(blk):
        for _, b in blk.iterrows():
            pairs.append({"article": a, "task": task, "block": b.split, "ratio_random": round(rnd.ratio.iloc[0], 3), "ratio_block": round(b.ratio, 3)})
P = pd.DataFrame(pairs)
P.to_csv(os.path.join(OUT, "results", "random_vs_block.csv"), index=False)

summary = {
    "gbm_articles": int(len(A)), "gbm_with_linear": int(A.linear_too.sum()),
    "cases": int(len(C)), "case_articles": int(C.article.nunique()),
    "winner_counts": C.winner.value_counts().to_dict(),
    "winner_articles_gbm": sorted(C[C.winner == "勾配ブースティング"].article.unique().tolist()),
    "winner_articles_linear_or_tie": sorted(C[C.winner != "勾配ブースティング"].article.unique().tolist()),
    "ratio_min": round(C.ratio.min(), 3), "ratio_max": round(C.ratio.max(), 3),
    "pairs": P.to_dict("records"),
}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

# 図1：19組の比
D = C.iloc[::-1]
fig, ax = plt.subplots(figsize=(8.6, 7.2))
col = D.winner.map({"勾配ブースティング": "#2f6fb0", "線形": "#d9822b", "ほぼ同じ": "#888888"})
ax.barh(range(len(D)), D.ratio - 1, left=1, color=col)
ax.axvline(1, color="#333", lw=1)
ax.set_yticks(range(len(D))); ax.set_yticklabels(D.label, fontsize=8.5)
for i, (r, m) in enumerate(zip(D.ratio, D.metric)):
    ax.text(r + (0.02 if r >= 1 else -0.02), i, f"{r:.2f}", va="center", ha="left" if r >= 1 else "right", fontsize=8)
ax.set_xlabel("勾配ブースティング ÷ 線形（外れの比。1より小さいと勾配ブースティングが良い）", fontsize=9)
ax.set_title("自分の記事の19組：勾配ブースティングと線形の成績の比", fontsize=12)
ax.set_xlim(0.3, 1.35)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a286_ratio.png"), dpi=150); plt.close(fig)

# 図2：ランダム → 場所で分けたとき
fig, ax = plt.subplots(figsize=(7.6, 4.6))
ys = []
for i, r in P.sort_values("ratio_block").iterrows():
    ax.plot([0, 1], [r.ratio_random, r.ratio_block], marker="o", color="#2f6fb0" if r.ratio_block < 0.97 else "#d9822b")
    y = r.ratio_block
    while any(abs(y - z) < 0.035 for z in ys):
        y += 0.035
    ys.append(y)
    ax.text(1.04, y, f"{r.article} {r.task}（{r.block}）", va="center", fontsize=8.5)
ax.axhline(1, color="#333", lw=1, ls="--")
ax.set_xticks([0, 1]); ax.set_xticklabels(["ランダムに分けて確かめる", "場所で分けて確かめる"])
ax.set_xlim(-0.1, 2.0); ax.set_ylabel("勾配ブースティング ÷ 線形")
ax.set_title("場所で分けて確かめると、勾配ブースティングの有利は小さくなった", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a286_block.png"), dpi=150); plt.close(fig)

# 図3：早見表（記録からの整理）
tbl = [
    ["地点や時間が多く、特徴量の組み合わせが効く", "F03・F75・F158 地価、F22 電力", "外れが3.5〜6割減った"],
    ["説明が直線に近い", "F74 気温（標高で −0.60℃/100m）", "ほぼ同じ。線形＋残差の補間が最良"],
    ["月次の1系列を先まで当てる", "F13 失業率", "ElasticNet が少し良い"],
    ["事業体・市区町村の横の比較で、説明が弱い", "F144 水道料金、F123 出生率（県で分けたとき）", "同じか、線形が良い"],
    ["見ていない場所・時期に当てる", "F03・F123（場所）、F149（時間）", "差が縮むか、線形が追いつく"],
]
fig, ax = plt.subplots(figsize=(10.5, 3.6)); ax.axis("off")
tb = ax.table(cellText=tbl, colLabels=["状況", "自分の記事", "結果"], loc="center", cellLoc="left", colWidths=[0.40, 0.30, 0.30])
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.9)
for (r, c), cell in tb.get_celld().items():
    if r == 0: cell.set_facecolor("#e8eef6"); cell.set_text_props(weight="bold")
ax.set_title("状況ごとに、どちらが良かったか（記録を見て後から整理したもの）", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a286_table.png"), dpi=150); plt.close(fig)
