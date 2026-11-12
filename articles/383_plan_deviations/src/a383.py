"""383 先に決めた確かめ方のうち、実際にはできなかったものは何だったか（④ 振り返り R113）— 集計と図

使い方: python a383.py
  data/plans.csv・deviation_items.csv（a383_extract.py）と data/manual_labels.csv（手で付けた分類）をまとめる。
  対象は、README に「計画からのずれ」の節がある記事（精選 F256〜F295 の40本）。
  manual_labels.csv ＝ 「ずれ」の項目を全部読み、計画したデータ・比べ方・確かめ方が計画どおりにできなかった項目に、
    何が（target）・どうなったか（outcome：やめた／代えた／一部だけ）・理由（reason：データ／意味／計算／理由なし）を付けたもの。
  言葉での分類（words_）は、項目の先頭120字に出てくる言葉で機械的に付けた目安で、1項目に複数付くことがある。
"""
import os, json, re
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
PL = pd.read_csv(P("data", "plans.csv")); DV = pd.read_csv(P("data", "deviation_items.csv")); ML = pd.read_csv(P("data", "manual_labels.csv"))
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
PL = PL[PL.has_deviation_section == 1].copy(); n = len(PL)
W = {"計画になかったものを足した": r"加えた|足した|追加|計画にな(い|かった)|結果を見て(から|た後)|問い直し|再問い|計画外|加えて出した",
     "計画と違う形に変えた": r"代わりに|変えた|変更|ではなく|置き換え|実際は|実装は|切り替え|とした計画|計画では|だったが|代えた",
     "計画が決めていなかった": r"書いていなかった|決めていなかった|決めておらず|定めていな|明記していな|決めていない|定めがなく",
     "誤りを直した": r"誤り|誤記|取り違え|間違|レビューで(判明|指摘)|指摘(され|で|を受け)|すり替え|最初の(版|コード|設定)",
     "仮説の判定を書いた": r"H\d[^。]{0,40}(当たり|外れ|支持)|仮説[^。]{0,30}(当たり|外れ|支持)",
     "先に見ていたものを書いた": r"(PLAN|計画)[^。]{0,6}を書く前|計画の前に|目に入|目にし|目で見て"}
for name, pat in W.items(): DV["words_" + name] = DV["head"].map(lambda s: int(bool(re.search(pat, s))))
wc = DV[[c for c in DV.columns if c.startswith("words_")]]; ws = wc.sum().rename(lambda c: c[6:]); ws["どの言葉もない"] = int((wc.sum(axis=1) == 0).sum())
wt = pd.DataFrame({"items": ws, "share": (ws / len(DV)).round(4), "articles": [DV[wc[c] == 1].id.nunique() for c in wc.columns] + [DV[wc.sum(axis=1) == 0].id.nunique()]}); wt.to_csv(P("results", "items_by_words.csv"))
per = PL[["id", "n_hypotheses", "n_planned_checks", "n_deviation_items", "n_readme_robust_items"]].merge(ML.groupby("id").size().rename("not_as_planned").reset_index(), how="left").fillna({"not_as_planned": 0})
per["not_as_planned"] = per.not_as_planned.astype(int); per.to_csv(P("results", "by_article.csv"), index=False)
t_reason = ML.reason.value_counts(); t_out = ML.outcome.value_counts(); t_target = ML.target.value_counts()
x1 = pd.crosstab(ML.target, ML.reason); x1["計"] = x1.sum(axis=1); x1 = x1.sort_values("計", ascending=False); x1.to_csv(P("results", "target_by_reason.csv"))
x2 = pd.crosstab(ML.outcome, ML.reason); x2["計"] = x2.sum(axis=1); x2.to_csv(P("results", "outcome_by_reason.csv"))
RB = ML[ML.target == "頑健性"]; planned = int(PL.n_planned_checks.sum())
summary = dict(articles=n, deviation_items=int(len(DV)), items_median=float(PL.n_deviation_items.median()), items_min=int(PL.n_deviation_items.min()), items_max=int(PL.n_deviation_items.max()),
               planned_checks=planned, planned_checks_median=float(PL.n_planned_checks.median()), readme_robust_items_median=float(PL.n_readme_robust_items.median()),
               not_as_planned=int(len(ML)), not_as_planned_share_of_items=round(len(ML) / len(DV), 4), articles_with_not_as_planned=int(ML.id.nunique()),
               reason={k: int(v) for k, v in t_reason.items()}, outcome={k: int(v) for k, v in t_out.items()}, target={k: int(v) for k, v in t_target.items()},
               robustness_not_as_planned=int(len(RB)), robustness_share_of_planned=round(len(RB) / planned, 4), robustness_outcome={k: int(v) for k, v in RB.outcome.value_counts().items()},
               robustness_reason={k: int(v) for k, v in RB.reason.value_counts().items()}, robustness_articles=int(RB.id.nunique()),
               words={k: int(v) for k, v in ws.items()}, prior_look_articles=int(DV[DV["words_先に見ていたものを書いた"] == 1].id.nunique()))
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(wt.to_string()); print(x1.to_string()); print(x2.to_string()); print(per.describe().round(2).to_string()); print(summary)

plt.rcParams["font.size"] = 10
RC = {"データ": "#1d5a9e", "意味": "#e9b872", "計算": "#6f9fd0", "理由なし": "#a3a29c"}; RJ = {"データ": "データがなかった・そろわなかった", "意味": "計画どおりでは意味がなかった", "計算": "計算できなかった", "理由なし": "理由を書いていない"}
# 図1 理由 × 何が
order = list(x1.index); fig, ax = plt.subplots(figsize=(9, 4.4)); left = np.zeros(len(order))
for r in ["データ", "意味", "計算", "理由なし"]:
    if r not in x1.columns: continue
    v = x1.loc[order, r].values; ax.barh(range(len(order)), v, left=left, color=RC[r], label=RJ[r])
    for i, (b, w) in enumerate(zip(left, v)):
        if w >= 1: ax.text(b + w / 2, i, str(int(w)), ha="center", va="center", fontsize=9, color="white" if r == "データ" else "black")
    left += v
for i, t in enumerate(x1.loc[order, "計"].values): ax.text(t + 0.2, i, f"計{int(t)}", va="center", fontsize=9)
ax.set_yticks(range(len(order))); ax.set_yticklabels(order); ax.invert_yaxis(); ax.set_xlabel("項目の数（個）"); ax.set_xlim(0, x1["計"].max() * 1.18)
ax.set_title(f"計画どおりにできなかった{len(ML)}項目：何が、なぜ（精選{n}本）"); ax.legend(fontsize=9, loc="lower right"); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a383_target_reason.png"), dpi=150); plt.close(fig)
# 図2 計画した確かめ方のゆくえ
done = planned - len(RB); parts = [("計画どおりに行った", done, "#1d5a9e")] + [(k, int(v), c) for (k, c) in [("代えた", "#e9b872"), ("一部だけ", "#6f9fd0"), ("やめた", "#eb6834")] for v in [RB.outcome.value_counts().get(k, 0)]]
fig, ax = plt.subplots(figsize=(9, 2.6)); b = 0
for name, v, c in parts:
    ax.barh(0, v, left=b, color=c, height=0.6)
    if v >= 8: ax.text(b + v / 2, 0, f"{v}", ha="center", va="center", fontsize=10, color="white" if c == "#1d5a9e" else "black")
    b += v
ax.set_xlim(0, planned); ax.set_ylim(-0.6, 0.6); ax.set_yticks([]); ax.set_xlabel(f"計画に書いた頑健性の確かめ方（{planned}個、{n}本）")
hs = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in parts]; ax.legend(hs, [f"{nm}（{v}個、{v/planned*100:.0f}%）" for nm, v, _ in parts], fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.55), frameon=False)
ax.set_title("計画した確かめ方のうち、「ずれ」の節に書かれたもの"); ax.spines[["top", "right", "left"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a383_planned_checks.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
# 図3 「ずれ」の項目に出てくる言葉
w2 = wt.sort_values("items"); fig, ax = plt.subplots(figsize=(9, 4.2)); ax.barh(range(len(w2)), w2["items"].values, color="#6f9fd0")
for i, (v, a_) in enumerate(zip(w2["items"].values, w2.articles.values)): ax.text(v + 1, i, f"{int(v)}項目（{v/len(DV)*100:.0f}%、{int(a_)}本）", va="center", fontsize=9)
ax.set_yticks(range(len(w2))); ax.set_yticklabels(w2.index); ax.set_xlim(0, w2["items"].max() * 1.45); ax.set_xlabel("項目の数（1項目に複数の言葉が付くことがある）")
ax.set_title(f"「計画からのずれ」の{len(DV)}項目に出てくる言葉（機械的な目安）"); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a383_words.png"), dpi=150); plt.close(fig)
