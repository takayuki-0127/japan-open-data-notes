"""267 相関を因果だと思いかけたとき、どう止めたか（④ 振り返り R006）

使い方: python a267.py <japan-open-data-notes のクローン>
  A. 「言えないこと」の節に「因果」と書いた記事の割合（グループ別）
  B. 「そろえる」「除く」などの確かめ方を README に書いた記事の数（グループ別）
  C. 題名で「そろえる・除くと」答えが変わったと書いた記事の実例（data/cases.csv は README から手で写した）
"""
import re, sys, os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import readmes, section, group_of, GROUPS, dedup, title_of

repo = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
docs = dedup(readmes(repo))

# ---- A. 言えないこと × 因果 ----
rowsA = []
for folder, t in docs:
    blk = "\n".join(section(t, r"言えないこと|注意|限界"))
    if not blk.strip():
        continue
    rowsA.append({"article": folder, "group": group_of(folder),
                  "causal": bool(re.search(r"因果", blk)),
                  "third": bool(re.search(r"交絡|ほかの要因|別の要因|第3の|見かけ|同時に動|両方に効", blk))})
A = pd.DataFrame(rowsA)
A.to_csv(os.path.join(OUT, "data", "limits_causal.csv"), index=False)
ga = A.groupby("group").agg(n=("article", "size"), causal=("causal", "sum"), third=("third", "sum")).reindex(GROUPS).dropna()
ga["causal_pct"] = (100 * ga.causal / ga.n).round(1)
ga["third_pct"] = (100 * ga.third / ga.n).round(1)
ga.to_csv(os.path.join(OUT, "results", "limits_causal_by_group.csv"))

# ---- B. 止め方の言葉 ----
WAYS = {
    "条件を段階的にそろえる（重回帰）": r"条件をそろえ|段階的に",
    "固定効果（県の違い・年の流れを除く）": r"固定効果",
    "年齢・物価などで調整する": r"年齢調整|年齢をそろえ|年齢構成をそろえ|実質化|物価で割|物価を除",
    "1つの地域・年を外して確かめる": r"を除くと|を除いて|を除いた|外すと|外して",
    "効果がないはずの所で試す（プラセボ）": r"プラセボ|placebo",
    "比べる相手を置く（差の差・合成コントロール）": r"差の差|合成コントロール|合成対照|Synthetic",
}
rowsB = []
for folder, t in docs:
    r = {"article": folder, "group": group_of(folder)}
    for k, v in WAYS.items():
        r[k] = bool(re.search(v, t, re.I))
    rowsB.append(r)
B = pd.DataFrame(rowsB)
B.to_csv(os.path.join(OUT, "data", "ways.csv"), index=False)
wb = pd.Series({k: int(B[k].sum()) for k in WAYS}).sort_values()
wb.to_csv(os.path.join(OUT, "results", "ways_counts.csv"), header=["articles"])

# ---- C. 題名の実例 ----
titles = [(f, title_of(t)) for f, t in docs if re.search(r"そろえ|除くと|除いた分|消えた|残った", title_of(t))]
pd.DataFrame(titles, columns=["article", "title"]).to_csv(os.path.join(OUT, "data", "titles_adjusted.csv"), index=False)
C = pd.read_csv(os.path.join(OUT, "data", "cases.csv"), dtype=str)
oc = C["結果"].value_counts()

# ---- D. 因果の注意の書き方（言葉で分ける。1行に複数つく） ----
KIND = {
    "予測・重要度は因果ではない": r"予測|重要度|SHAP|寄与",
    "ほかの理由で同時に動いた可能性": r"同時|両方|別の理由|交絡|ほかの要因|第3|逆向き|逆の因果|向き",
    "集計・記述にとどまる": r"記述|集計|会計|分解",
    "地域の関係を個人に当てはめない": r"個人|1人1人|生態",
    "手法の前提に頼る": r"前提|仮定|平行|識別|操作変数|1段目",
}
rowsD = []
for folder, t in docs:
    blk = "\n".join(section(t, r"言えないこと|注意|限界"))
    for ln in blk.split("\n"):
        if "因果" in ln:
            r = {"article": folder, "line": ln.strip()[:200]}
            for k, v in KIND.items():
                r[k] = bool(re.search(v, ln))
            rowsD.append(r)
D = pd.DataFrame(rowsD)
D.to_csv(os.path.join(OUT, "data", "causal_lines.csv"), index=False)
kd = {k: int(D.groupby("article")[k].any().sum()) for k in KIND}
kd["どれにも当たらない"] = int((~D.groupby("article")[list(KIND)].any().any(axis=1)).sum())

summary = {
    "readmes_total": len(readmes(repo)), "readmes_dedup": len(docs),
    "with_limits_section": int(len(A)), "limits_mention_causal": int(A.causal.sum()),
    "limits_mention_causal_pct": round(100 * A.causal.mean(), 1),
    "limits_mention_third_factor": int(A.third.sum()),
    "ways": {k: int(B[k].sum()) for k in WAYS},
    "any_way": int(B[list(WAYS)].any(axis=1).sum()),
    "titles_adjusted": len(titles),
    "case_outcomes": {k: int(v) for k, v in oc.items()},
    "causal_lines": int(len(D)), "causal_kinds_articles": kd,
}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1)); print(ga)

# ---- 図 ----
COL = {"消えた": "#c0504d", "向きが逆": "#8e2c2a", "縮んだが残った": "#e8a23a", "残った": "#4f81bd", "大きくなった": "#5b9b5b"}
fig, ax = plt.subplots(figsize=(10.5, 4.6))
ax.axis("off")
cell = [[r.記事, r.そろえたもの, r.そろえる前, r.そろえた後, r.結果] for r in C.itertuples()]
tb = ax.table(cellText=cell, colLabels=["記事", "そろえたもの", "そろえる前", "そろえた後", "結果"],
              loc="center", cellLoc="left", colWidths=[0.07, 0.25, 0.24, 0.30, 0.14])
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.55)
for (i, j), c in tb.get_celld().items():
    if i == 0:
        c.set_facecolor("#e6e6e6")
    elif j == 4:
        c.set_facecolor(COL.get(cell[i - 1][4], "white")); c.get_text().set_color("white")
ax.set_title("図1 そろえる前と後の10本（README の数字から）", fontsize=12, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a267_cases.png"), dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(8.5, 4.4))
SHORT = {"F256–F295（精選）": "精選\nF256–F295", "227–・T（1000本計画）": "1000本計画\n227–・T"}
lab = [f"{SHORT.get(g, g)}\n（{int(n)}本）" for g, n in zip(ga.index, ga.n)]
ax.bar(range(len(ga)), ga.causal_pct, color="#4f81bd", label="「因果」と書いた")
ax.bar(range(len(ga)), ga.third_pct, color="#e8a23a", width=0.4, label="ほかの要因・見かけの関係と書いた")
for i, v in enumerate(ga.causal_pct):
    ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
ax.set_xticks(range(len(ga))); ax.set_xticklabels(lab, fontsize=8)
ax.set_ylabel("記事に占める割合（%）"); ax.set_ylim(0, 35)
ax.legend(fontsize=9, loc="upper left")
ax.set_title("図2 「言えないこと・注意」に因果の注意を書いた記事の割合", fontsize=12, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a267_limits_causal.png"), dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(range(len(wb)), wb.values, color="#5b9b5b")
for i, v in enumerate(wb.values):
    ax.text(v + 2, i, str(v), va="center", fontsize=9)
ax.set_yticks(range(len(wb))); ax.set_yticklabels(wb.index, fontsize=9)
ax.set_xlabel(f"README に書いた記事の数（重複を除いた {len(docs)} 本のうち）")
ax.set_title("図3 相関で止まらないために使った確かめ方", fontsize=12, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a267_ways.png"), dpi=150); plt.close()
