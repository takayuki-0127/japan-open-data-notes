"""352 専門用語には、最初に一言の説明が付いているか（④ 振り返り R107）— 集計と図

使い方: python a352.py
  data/term_first_use.csv（a352_extract.py の機械の判定。記事×用語で1行）と、
  data/manual_check.csv（50行を目で読んだ判定）をまとめる
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
LAB = {"paren": "直後のかっこ", "swap": "ふつうの言葉が先\n（用語はかっこの中）", "toha": "「とは」「と呼ぶ」など", "section": "「用語を先に」の節", "next": "次の文で説明", "none": "説明なし"}
D = pd.read_csv(P("data", "term_first_use.csv"), dtype={"id": str}); D["ex"] = (D.label != "none").astype(int)
H = pd.read_csv(P("data", "manual_check.csv"), dtype={"id": str})
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
T = D.groupby("term").agg(記事=("id", "size"), 説明つき=("ex", "sum"), 本文での回数=("n", "sum")).sort_values("記事", ascending=False)
T["説明つきの割合"] = (T["説明つき"] / T["記事"]).round(3); T["説明なしの記事"] = T["記事"] - T["説明つき"]; T.to_csv(P("results", "by_term.csv"))
G = D.groupby("group").agg(記事=("id", "nunique"), 記事と用語の組=("id", "size"), 説明つき=("ex", "mean")).reindex(ORDER)
A = D.groupby(["group", "id"]).ex.agg(["mean", "size"]).reset_index()
G["用語が出た記事のうち全部に説明"] = A.assign(all=(A["mean"] == 1)).groupby("group")["all"].mean().reindex(ORDER)
G["1つも説明なし"] = A.assign(z=(A["mean"] == 0)).groupby("group")["z"].mean().reindex(ORDER)
G.loc["全体"] = [D.id.nunique(), len(D), D.ex.mean(), (A["mean"] == 1).mean(), (A["mean"] == 0).mean()]; G.round(3).to_csv(P("results", "by_group.csv"))
L = D.label.value_counts().reindex(list(LAB)).fillna(0).astype(int); L.to_csv(P("results", "by_label.csv"), header=["記事と用語の組"])
hm = H.assign(m=np.where(H.machine == "none", "機械：説明なし", "機械：説明つき")).pivot_table(index="m", columns="hand", values="id", aggfunc="size", fill_value=0); hm.to_csv(P("results", "manual_check_table.csv"))
pe = hm.loc["機械：説明つき"]; pn = hm.loc["機械：説明なし"]
prec = pe.get("説明あり", 0) / pe.sum(); miss_lo = pn.get("説明あり", 0) / pn.sum(); miss_hi = (pn.get("説明あり", 0) + pn.get("どちらとも言える", 0)) / pn.sum()
share = D.ex.mean(); adj_lo = share * prec + (1 - share) * miss_lo; adj_hi = share * prec + (1 - share) * miss_hi
top = T[T["記事"] >= 10]
summary = dict(articles_with_terms=int(D.id.nunique()), pairs=int(len(D)), terms_found=int(D.term.nunique()), share_explained_machine=round(float(share), 4), labels={k: int(v) for k, v in L.items()},
               hand=dict(flagged=int(pe.sum()), flagged_ok=int(pe.get("説明あり", 0)), unflagged=int(pn.sum()), unflagged_explained=int(pn.get("説明あり", 0)), unflagged_either=int(pn.get("どちらとも言える", 0))),
               share_adjusted=[round(float(adj_lo), 3), round(float(adj_hi), 3)],
               most_unexplained={k: int(v) for k, v in T["説明なしの記事"].sort_values(ascending=False).head(8).items()},
               best_terms={k: float(v) for k, v in top["説明つきの割合"].sort_values(ascending=False).head(5).items()}, worst_terms={k: float(v) for k, v in top["説明つきの割合"].sort_values().head(5).items()},
               by_group={o: round(float(G.loc[o, "説明つき"]), 3) for o in ORDER})
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(T.to_string()); print(G.round(3).to_string()); print(L.to_string()); print(hm.to_string()); print(summary)

plt.rcParams["font.size"] = 10
# 図1 用語ごと（10本以上の記事に出た用語）
t = top.sort_values("記事"); fig, ax = plt.subplots(figsize=(9, 6.2)); y = np.arange(len(t))
ax.barh(y, t["説明つき"], color="#2c6fb7", label="最初に出た所に説明あり"); ax.barh(y, t["説明なしの記事"], left=t["説明つき"], color="#d9d9d9", label="説明なし")
for i, (n, s) in enumerate(zip(t["記事"], t["説明つきの割合"])): ax.text(n + 2, i, f"{s*100:.0f}%", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels(t.index, fontsize=9); ax.set_xlabel("その用語が本文に出てくる記事の数"); ax.set_title("用語ごとの、最初に出た所の説明（右の数字は説明つきの割合、機械の判定）")
ax.legend(loc="lower right", fontsize=9); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a352_by_term.png"), dpi=150); plt.close(fig)
# 図2 グループごと
fig, ax = plt.subplots(figsize=(9, 4.3)); x = np.arange(len(ORDER)); v = G.loc[ORDER, "説明つき"] * 100
ax.bar(x, v, 0.6, color="#2c6fb7")
for i, (a, n) in enumerate(zip(v, G.loc[ORDER, "記事と用語の組"])): ax.text(i, a + 0.8, f"{a:.0f}%\n({int(n)}組)", ha="center", fontsize=9)
ax.axhline(share * 100, color="#888888", ls="--", lw=1); ax.text(len(ORDER) - 0.45, share * 100 + 0.6, f"全体 {share*100:.0f}%", fontsize=9, color="#555555", ha="right")
ax.set_xticks(x); ax.set_xticklabels(SHORT); ax.set_ylim(0, max(v) * 1.35); ax.set_ylabel("説明つきの割合（%）"); ax.set_title("記事のグループごとの、最初に出た所に説明がある割合（機械の判定）")
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a352_by_group.png"), dpi=150); plt.close(fig)
# 図3 説明のしかた
fig, ax = plt.subplots(figsize=(9, 4.0)); k = [c for c in LAB if c != "none"]; v = [L[c] for c in k]
ax.barh(range(len(k)), v, color="#2c6fb7")
for i, a in enumerate(v): ax.text(a + 1.5, i, f"{a}", va="center", fontsize=9)
ax.set_yticks(range(len(k))); ax.set_yticklabels([LAB[c] for c in k]); ax.invert_yaxis(); ax.set_xlabel("記事と用語の組の数")
ax.set_title(f"説明のしかた（説明つき {int(D.ex.sum())}組の内訳。説明なしは {int(L['none'])}組）"); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a352_how.png"), dpi=150); plt.close(fig)
