"""353 結論の言い切り方は、どう変わったか（④ 振り返り R108）— 集計と図

使い方: python a353.py
  data/endings.csv（a353_extract.py が原稿の結論の文を、文末の言い方で分けて数えたもの。記事ごとに1行）をまとめる。
  結論の文＝題名の答えの部分＋書き出し（最初の見出しより前）＋「分かること」「まとめ」「結論」の節
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
C = ["unknown", "null", "hedge", "past", "plain", "question"]
JA = {"unknown": "見えなかった・言えない", "null": "変わらなかった・ほぼ同じ", "hedge": "かもしれない・（推測）", "past": "「〜た」の言い切り", "plain": "そのほかの言い切り", "question": "問いの文"}
D = pd.read_csv(P("data", "endings.csv"), dtype={"id": str})
for k in C: D["c_" + k] = D["title_" + k] + D["lead_" + k] + D["sec_" + k]
D["c_n"] = D[["c_" + k for k in C if k != "question"]].sum(axis=1)
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
def grp(f):
    t = f(D.groupby("group")).reindex(ORDER); t.loc["全体"] = f(D.assign(group="全体").groupby("group")).loc["全体"]; return t
# 文の割合（問いの文を除く）
S = grp(lambda g: g[["c_" + k for k in C if k != "question"] + ["c_n"]].sum())
share = S[["c_unknown", "c_null", "c_hedge", "c_past", "c_plain"]].div(S.c_n, axis=0); share.columns = [JA[k] for k in C[:5]]
share.insert(0, "結論の文", S.c_n.astype(int)); share.insert(0, "記事", list(D.groupby("group").size().reindex(ORDER)) + [len(D)]); share.round(4).to_csv(P("results", "sentence_share.csv"))
# 記事の割合（結論の文に1つでもある）
D["a_unknown"] = D.c_unknown > 0; D["a_null"] = D.c_null > 0; D["a_hedge"] = D.c_hedge > 0; D["a_either"] = (D.c_unknown + D.c_null) > 0
D["t_unknown"] = D.title_any_unknown > 0; D["t_null"] = D.title_any_null > 0; D["t_either"] = (D.title_any_unknown + D.title_any_null) > 0
D["end_unknown"] = D.title_unknown > 0  # 題名の最後が「見えなかった・言えない」
A = grp(lambda g: g[["a_unknown", "a_null", "a_either", "a_hedge", "t_unknown", "t_null", "t_either", "end_unknown"]].mean())
A.columns = ["結論に「見えなかった」", "結論に「変わらなかった」", "どちらか", "結論に「かもしれない・推測」", "題名に「見えなかった」", "題名に「変わらなかった」", "題名にどちらか", "題名の最後が「見えなかった」"]
A.round(4).to_csv(P("results", "article_share.csv"))
# 結論が長くなっただけで、どこまで増えるか：全体の割合 p のまま、記事ごとの結論の文の数 n で「1つでもある」確率 1-(1-p)^n を出す
p_e = (D.c_unknown.sum() + D.c_null.sum()) / D.c_n.sum(); p_h = D.c_hedge.sum() / D.c_n.sum()
D["exp_either"] = 1 - (1 - p_e) ** D.c_n; D["exp_hedge"] = 1 - (1 - p_h) ** D.c_n
E = grp(lambda g: g[["c_n", "a_either", "exp_either", "a_hedge", "exp_hedge"]].mean())
E.columns = ["結論の文の数（平均）", "どちらかがある記事（実際）", "同（文の数だけから見込む）", "「かもしれない・推測」がある記事（実際）", "同（文の数だけから見込む）"]; E.round(4).to_csv(P("results", "expected_from_length.csv"))
# 本文全体の文（比べるため）
B = grp(lambda g: g[["body_" + k for k in C]].sum()); Bs = B[["body_unknown", "body_null", "body_hedge"]].div(B[["body_" + k for k in C if k != "question"]].sum(axis=1), axis=0)
Bs.columns = [JA[k] for k in C[:3]]; Bs.round(4).to_csv(P("results", "body_sentence_share.csv"))
# 看板記事を番号順に（前後30本）
F = D[D.id.str.startswith("F")].assign(num=lambda x: x.id.str[1:].astype(int)).sort_values("num").set_index("num")
roll = F[["a_either", "a_hedge", "t_either"]].astype(float).rolling(30, center=True, min_periods=15).mean(); roll.round(4).to_csv(P("results", "f_series_rolling.csv"))
summary = dict(articles=int(len(D)), conclusion_sentences=int(S.loc["全体", "c_n"]), questions=int(D.c_question.sum()),
               sentence_share={o: {k: round(float(share.loc[o, JA[k]]), 4) for k in C[:5]} for o in ORDER + ["全体"]},
               article_share={o: {c: round(float(A.loc[o, c]), 4) for c in A.columns} for o in ORDER + ["全体"]},
               counts=dict(title_unknown=int(D.t_unknown.sum()), title_null=int(D.t_null.sum()), title_either=int(D.t_either.sum()), title_end_unknown=int(D.end_unknown.sum())))
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
summary["expected_from_length"] = {o: [round(float(E.loc[o].iloc[0]), 2)] + [round(float(v), 4) for v in E.loc[o].iloc[1:]] for o in ORDER + ["全体"]}
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(E.round(3).to_string())
print(share.round(3).to_string()); print(A.round(3).T.to_string()); print(Bs.round(3).to_string()); print(summary["counts"])

plt.rcParams["font.size"] = 10
x = np.arange(len(ORDER)); lab = [f"{s}\n({int(share.loc[o,'記事'])}本)" for s, o in zip(SHORT, ORDER)]
# 図1 結論の文のうち、言い切らない文末の割合
fig, ax = plt.subplots(figsize=(9, 4.5)); w = 0.27
for j, (k, col) in enumerate(zip(C[:3], ["#d1495b", "#f0a03c", "#2c6fb7"])):
    v = share.loc[ORDER, JA[k]] * 100; ax.bar(x + (j - 1) * w, v, w, color=col, label=JA[k])
    for i, a in enumerate(v): ax.text(i + (j - 1) * w, a + 0.05, f"{a:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=9); ax.set_ylabel("結論の文に占める割合（%）"); ax.set_title("結論の文の文末：言い切らない言い方の割合（問いの文を除く）")
ax.legend(fontsize=9); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a353_sentence_share.png"), dpi=150); plt.close(fig)
# 図2 記事の割合
fig, ax = plt.subplots(figsize=(9, 4.5))
for c, col, mk in [("どちらか", "#d1495b", "o"), ("結論に「かもしれない・推測」", "#2c6fb7", "s"), ("題名にどちらか", "#888888", "^")]:
    v = A.loc[ORDER, c] * 100; ax.plot(x, v, marker=mk, color=col, lw=2, label={"どちらか": "結論に「見えなかった」か「変わらなかった」の文がある", "結論に「かもしれない・推測」": "結論に「かもしれない・（推測）」の文がある", "題名にどちらか": "題名に「見えなかった」か「変わらなかった」がある"}[c])
    for i, a in enumerate(v): ax.text(i, a + 2.2, f"{a:.0f}", ha="center", fontsize=8, color=col)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=9); ax.set_ylim(0, 100); ax.set_ylabel("記事の割合（%）"); ax.set_title("言い切らない言い方が、結論や題名にある記事の割合")
ax.legend(fontsize=8, loc="upper left"); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a353_article_share.png"), dpi=150); plt.close(fig)
# 図3 看板記事の番号順
fig, ax = plt.subplots(figsize=(9, 4.3))
ax.plot(roll.index, roll.a_either * 100, color="#d1495b", lw=2, label="結論に「見えなかった」か「変わらなかった」")
ax.plot(roll.index, roll.a_hedge * 100, color="#2c6fb7", lw=2, label="結論に「かもしれない・（推測）」")
ax.plot(roll.index, roll.t_either * 100, color="#888888", lw=1.5, ls="--", label="題名に「見えなかった」か「変わらなかった」")
for v in (100, 200, 256): ax.axvline(v, color="#cccccc", lw=0.8)
ax.set_xlabel("看板記事の番号（F）"); ax.set_ylabel("前後30本のうちの割合（%）"); ax.set_ylim(0, 100); ax.set_title("看板記事を番号順に並べたときの推移（前後30本の平均）")
ax.legend(fontsize=8, loc="upper left"); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a353_f_series.png"), dpi=150); plt.close(fig)
