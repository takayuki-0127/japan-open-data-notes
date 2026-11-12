"""355 README の8つの節は、どれだけそろっているか（④ 振り返り R110）— 集計と図

使い方: python a355.py
  data/sections.csv（a355_extract.py が README の見出しから拾った 0/1）を、節ごと・記事のグループごとにまとめる。
  8つの節＝問い・データ・手法・結果・頑健性・再現手順・言えないこと・出典
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
K = ["question", "data", "method", "result", "robust", "repro", "limits", "source"]
JA = ["問い", "データ", "手法", "結果", "頑健性", "再現手順", "言えないこと", "出典"]
D = pd.read_csv(P("data", "sections.csv"))
D["q_any"] = (D.question | D.tbl_question); D["m_any"] = (D.method | D.tbl_method)
K2 = ["q_any", "data", "m_any", "result", "robust", "repro", "limits", "source"]
D["n8"] = D[K].sum(axis=1); D["n8_tbl"] = D[K2].sum(axis=1); D["s8"] = D[["strict_" + k for k in K]].sum(axis=1)
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
def table(cols):
    t = D.groupby("group")[cols].mean().reindex(ORDER); t.loc["全体"] = D[cols].mean(); return t
head = table(K); head.columns = JA; head.insert(0, "README", list(D.groupby("group").size().reindex(ORDER)) + [len(D)])
head["8つ全部"] = list((D.n8 == 8).groupby(D.group).mean().reindex(ORDER)) + [(D.n8 == 8).mean()]
head.round(3).to_csv(P("results", "sections_by_group.csv"))
wt = table(K2); wt.columns = JA; wt["8つ全部"] = list((D.n8_tbl == 8).groupby(D.group).mean().reindex(ORDER)) + [(D.n8_tbl == 8).mean()]
wt.round(3).to_csv(P("results", "sections_by_group_with_tables.csv"))
st = table(["strict_" + k for k in K]); st.columns = JA; st.round(3).to_csv(P("results", "sections_strict_names.csv"))
dist = D.groupby("group").n8_tbl.value_counts().unstack(fill_value=0).reindex(ORDER); dist.loc["全体"] = dist.sum(); dist.to_csv(P("results", "n_sections.csv"))
F = D[D.group.isin(ORDER[2:6])]
miss = {ja: int((F[k] == 0).sum()) for k, ja in zip(K2, JA)}
other = D.groupby("group")[["chars", "n_heads"]].median().reindex(ORDER); other["計画の節"] = D.groupby("group").extra_plan.mean().reindex(ORDER); other["レビューの節"] = D.groupby("group").extra_review.mean().reindex(ORDER)
other.round(3).to_csv(P("results", "length_and_extra.csv"))
summary = dict(readmes=int(len(D)), all8_heading=int((D.n8 == 8).sum()), all8_with_tables=int((D.n8_tbl == 8).sum()), flagship=int(len(F)), flagship_all8=int((F.n8_tbl == 8).sum()),
               flagship_missing=miss, share_heading={ja: round(float(head.loc["全体", ja]), 4) for ja in JA}, share_with_tables={ja: round(float(wt.loc["全体", ja]), 4) for ja in JA},
               median_chars={o: float(other.loc[o, "chars"]) for o in ORDER})
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(head.round(2).to_string()); print(wt.round(2).to_string()); print(st.round(2).to_string()); print(dist.to_string()); print(other.to_string()); print(summary)

plt.rcParams["font.size"] = 10
# 図1 節×グループ（見出しか表にある割合）
M = wt.loc[ORDER, JA].values * 100
fig, ax = plt.subplots(figsize=(9, 4.6)); im = ax.imshow(M, cmap="Blues", vmin=0, vmax=100, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]): ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=9, color="white" if M[i, j] > 60 else "black")
ax.set_xticks(range(8)); ax.set_xticklabels(JA); ax.set_yticks(range(7)); ax.set_yticklabels([f"{s}（{int(head.loc[o,'README'])}本）" for s, o in zip(SHORT, ORDER)])
ax.set_title("README に節がある割合（%）。問いと手法は、表の列で書いたものも数えた"); fig.colorbar(im, ax=ax, shrink=0.8); fig.tight_layout(); fig.savefig(P("figures", "a355_sections_heatmap.png"), dpi=150); plt.close(fig)
# 図2 そろっている節の数
fig, ax = plt.subplots(figsize=(9, 4.3)); rows = ORDER + ["全体"]; sh = dist.reindex(rows).div(dist.reindex(rows).sum(axis=1), axis=0) * 100; bottom = np.zeros(len(rows))
cols = {4: "#f3d9b1", 5: "#e9b872", 6: "#b9cfe4", 7: "#6f9fd0", 8: "#1d5a9e"}
for kk in sorted(sh.columns):
    v = sh[kk].values; ax.barh(np.arange(len(rows)), v, left=bottom, color=cols.get(kk, "#dddddd"), label=f"{kk}つ")
    for i, (b, w) in enumerate(zip(bottom, v)):
        if w >= 7: ax.text(b + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=8, color="white" if kk == 8 else "black")
    bottom += v
ax.set_yticks(np.arange(len(rows))); ax.set_yticklabels(SHORT + ["全体"]); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("README の割合（%）")
ax.set_title("8つの節のうち、そろっている数"); ax.legend(fontsize=8, ncol=6, loc="lower center", bbox_to_anchor=(0.5, -0.3)); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a355_n_sections.png"), dpi=150); plt.close(fig)
# 図3 決めた名前そのものか、別の名前か
fig, ax = plt.subplots(figsize=(9, 4.3)); x = np.arange(8)
a = st.loc["全体", JA].values * 100; b = wt.loc["全体", JA].values * 100
ax.bar(x, b, 0.6, color="#b9cfe4", label="同じ役目の別の名前・表も含める"); ax.bar(x, a, 0.6, color="#1d5a9e", label="決めた名前そのものの見出し")
for i in range(8): ax.text(i, b[i] + 1.5, f"{a[i]:.0f}／{b[i]:.0f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(JA); ax.set_ylim(0, 115); ax.set_ylabel("README の割合（%）"); ax.set_title(f"節の名前のそろい方（README {len(D)}本）"); ax.legend(fontsize=9, loc="lower left")
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a355_names.png"), dpi=150); plt.close(fig)
