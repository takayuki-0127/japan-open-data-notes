"""382 記事どうしは、どうつながっているか（④ 振り返り R112）— 集計と図

使い方: python a382.py
  data/nodes.csv・edges.csv（a382_extract.py が README から拾った言及）をまとめる。
  1組＝「記事 A の README に、記事 B の番号が1回以上出てくる」。向きは A → B。
"""
import os, json, re
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Arc
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = common.GROUPS; SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
N = pd.read_csv(P("data", "nodes.csv"), dtype={"id": str}); E = pd.read_csv(P("data", "edges.csv"), dtype={"src": str, "dst": str})
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
def key(i):
    m = re.match(r"(F|T)?(\d+)", i); return ({None: 0, "F": 1, "T": 2}[m.group(1)], int(m.group(2)))
gi = {g: k for k, g in enumerate(ORDER)}
N["gk"] = N.group.map(gi); N["k1"] = N.id.map(lambda i: key(i)[0]); N["k2"] = N.id.map(lambda i: key(i)[1])
N = N.sort_values(["gk", "k1", "k2"]).reset_index(drop=True); N["pos"] = np.arange(len(N))
R = N[N["read"] == 1]; nr = len(R)
out = E.groupby("src").dst.nunique(); inn = E.groupby("dst").src.nunique()
N["out"] = N.id.map(out).fillna(0).astype(int); N["inn"] = N.id.map(inn).fillna(0).astype(int)
N[["id", "folder", "group", "read", "out", "inn"]].to_csv(P("results", "degree_by_article.csv"), index=False)
R = N[N["read"] == 1]
bg = R.groupby("group").agg(readmes=("id", "size"), out_any=("out", lambda s: (s > 0).mean()), out_mean=("out", "mean"), out_median_if_any=("out", lambda s: s[s > 0].median()),
                            in_any=("inn", lambda s: (s > 0).mean()), in_mean=("inn", "mean"), isolated=("id", lambda s: 0)).reindex(ORDER)
R = R.assign(iso=((R.out == 0) & (R.inn == 0)).astype(int)); bg["isolated"] = R.groupby("group").iso.mean().reindex(ORDER)
bg.loc["全体"] = [nr, (R.out > 0).mean(), R.out.mean(), R.out[R.out > 0].median(), (R.inn > 0).mean(), R.inn.mean(), ((R.out == 0) & (R.inn == 0)).mean()]
bg.round(3).to_csv(P("results", "by_group.csv"))
top = N.sort_values("inn", ascending=False).head(20)[["id", "title", "group", "inn", "out"]]; top.to_csv(P("results", "most_cited.csv"), index=False)
topo = N.sort_values("out", ascending=False).head(20)[["id", "title", "group", "out", "inn"]]; topo.to_csv(P("results", "most_citing.csv"), index=False)
g = dict(zip(N.id, N.group)); E["gs"] = E.src.map(g); E["gd"] = E.dst.map(g)
mat = pd.crosstab(E.gs, E.gd).reindex(index=ORDER, columns=ORDER).fillna(0).astype(int); mat.to_csv(P("results", "group_matrix.csv"))
pos = dict(zip(N.id, N.pos)); E["ps"] = E.src.map(pos); E["pd"] = E.dst.map(pos)
k = {i: key(i) for i in N.id}
same = E[E.src.map(lambda i: k[i][0]) == E.dst.map(lambda i: k[i][0])]
back = (same.src.map(lambda i: k[i][1]) > same.dst.map(lambda i: k[i][1])).mean()
pairs = {(a, b) for a, b in zip(E.src, E.dst)}; mutual = sum((b, a) in pairs for a, b in pairs) // 2
# つながりのまとまり（向きを無視）
par = {i: i for i in N.id}
def find(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
for a, b in pairs: par[find(a)] = find(b)
comp = pd.Series([find(i) for i in N.id]).value_counts()
kinds = E[["link", "F", "T", "num"]].sum()
dist_in = N.inn.value_counts().sort_index(); dist_in.rename("articles").to_csv(P("results", "in_degree_distribution.csv"))
summary = dict(articles=int(len(N)), readmes_read=int(nr), pairs=int(len(E)), mentions=int(E.n.sum()), by_form={a: int(b) for a, b in kinds.items()},
               citing=int((R.out > 0).sum()), citing_share=round(float((R.out > 0).mean()), 4), out_median_if_any=float(R.out[R.out > 0].median()), out_max=int(N.out.max()),
               cited=int((N.inn > 0).sum()), cited_share=round(float((N.inn > 0).mean()), 4), never_cited=int((N.inn == 0).sum()), isolated_read=int(R.iso.sum()), isolated_read_share=round(float(R.iso.mean()), 4),
               top5_share_of_pairs=round(float(N.inn.sort_values(ascending=False).head(5).sum() / len(E)), 4), top20_share_of_pairs=round(float(N.inn.sort_values(ascending=False).head(20).sum() / len(E)), 4),
               to_flagship=round(float(E.gd.isin(ORDER[2:6]).mean()), 4), from_1000=round(float((E.gs == ORDER[6]).mean()), 4), backward_share_same_series=round(float(back), 4), mutual_pairs=int(mutual),
               largest_component=int(comp.iloc[0]), components_2plus=int((comp >= 2).sum()),
               most_cited=[(r.id, int(r.inn)) for r in top.head(10).itertuples()], most_citing=[(r.id, int(r.out)) for r in topo.head(10).itertuples()])
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(bg.round(3).to_string()); print(mat.to_string()); print(top.to_string()); print(topo.head(10).to_string()); print(summary)

plt.rcParams["font.size"] = 10
COL = ["#a3a29c", "#c9b27c", "#a9c9ef", "#6f9fd0", "#1d5a9e", "#eb6834", "#3aa07a"]
# 図1 弧の図
fig, ax = plt.subplots(figsize=(11, 5.2)); n = len(N)
for r in E.itertuples():
    a, b = r.ps, r.pd; w = abs(a - b); c = COL[gi[r.gs]]
    ax.add_patch(Arc(((a + b) / 2, 0), w, w * 0.62, theta1=0, theta2=180, color=c, lw=0.5, alpha=0.45))
b0 = 0
for kk, (gname, s) in enumerate(zip(ORDER, SHORT)):
    m = int((N.group == gname).sum()); ax.barh(-12, m, left=b0, height=14, color=COL[kk]); ax.text(b0 + m / 2, -30, f"{s}\n{m}本", ha="center", va="top", fontsize=8.5); b0 += m
ax.set_xlim(-5, n + 5); ax.set_ylim(-75, n * 0.33); ax.axis("off")
ax.set_title(f"README の中の、ほかの記事への言及（{len(E)}組）。弧の色は言及した側のまとまり", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a382_arcs.png"), dpi=150); plt.close(fig)
# 図2 多く引かれた記事
t = top.head(15)[::-1]; fig, ax = plt.subplots(figsize=(9, 5.6))
ax.barh(range(len(t)), t.inn.values, color=[COL[gi[x]] for x in t.group])
lab = [re.sub(r"^(F|T)?\d+[\s　]*", "", str(x)) for x in t.title]; lab = [f"{i}  {(l[:26] + '…') if len(l) > 27 else l}" for i, l in zip(t.id, lab)]
for i, v in enumerate(t.inn.values): ax.text(v + 0.2, i, f"{v}本", va="center", fontsize=9)
ax.set_yticks(range(len(t))); ax.set_yticklabels(lab, fontsize=8.5); ax.set_xlabel("その記事の番号を README に書いた、ほかの記事の数（本）"); ax.set_xlim(0, t.inn.max() * 1.15); ax.set_xticks(range(0, int(t.inn.max()) + 1, 2))
ax.set_title("ほかの記事から多く引かれた記事（上位15）"); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a382_most_cited.png"), dpi=150); plt.close(fig)
# 図3 まとまり × まとまり
M = mat.values; fig, ax = plt.subplots(figsize=(8.4, 5.2)); im = ax.imshow(M, cmap="Blues", aspect="auto", vmin=0, vmax=M.max())
for i in range(7):
    for j in range(7): ax.text(j, i, str(M[i, j]), ha="center", va="center", fontsize=9, color="white" if M[i, j] > M.max() * 0.6 else "black")
ax.set_xticks(range(7)); ax.set_xticklabels(SHORT, fontsize=8.5); ax.set_yticks(range(7)); ax.set_yticklabels(SHORT, fontsize=9)
ax.set_xlabel("引かれた記事のまとまり"); ax.set_ylabel("引いた記事のまとまり"); ax.set_title("どのまとまりが、どのまとまりを引いたか（組の数）"); fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout(); fig.savefig(P("figures", "a382_group_matrix.png"), dpi=150); plt.close(fig)
