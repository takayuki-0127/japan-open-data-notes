"""325 同じ処理を、何回書き直していたか（④ 振り返り R105）— その2：重なりを数える

使い方: python a325.py
  data/functions.csv.gz（関数ごとのハッシュと MinHash）と data/files.csv から
  - まったく同じ関数（書式・コメント・docstring を除いて同じ）が、いくつの記事フォルダに写されていたか
  - ほぼ同じ関数（トークン4つ並びの集合の重なり＝Jaccard が 0.8 以上と見積もられ、まったく同じではないもの）の組
  - common.py（記事ごとに置いた共通ファイル）が何通りあったか
  を数える。30トークン未満の小さな関数は除く。別の記事フォルダとの重なりだけを数える（同じフォルダの中の重なりは数えない）
"""
import os, json, collections
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
P = lambda *a: os.path.join(OUT, *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
MINTOK, TH, K, BAND = 30, 0.8, 64, 4
G = pd.read_csv(P("data", "functions.csv.gz")); Fi = pd.read_csv(P("data", "files.csv"))
G["group"] = G.folder.map(group_of); G = G[G.group.notna()].reset_index(drop=True)
Fi["group"] = Fi.folder.map(group_of); Fi = Fi[Fi.group.notna()]
big = G[G.tokens >= MINTOK].reset_index(drop=True)
MH = np.array([[int(x, 16) for x in s.split()] for s in big.minhash], dtype=np.uint64)

# まったく同じ関数
ex = big.groupby("exact").agg(folders=("folder", "nunique"), n=("folder", "size"), name=("func", lambda x: x.value_counts().index[0]), names=("func", "nunique"),
                              lines=("lines", "median"), tokens=("tokens", "median"))
exd = ex[ex.folders >= 2].sort_values("folders", ascending=False)
big["exact_folders"] = big.exact.map(ex.folders)
big["is_exact_copy"] = big.exact_folders >= 2
exd.head(40).to_csv(P("results", "exact_top.csv"))

# ほぼ同じ関数：LSH（4個ずつ16帯）で候補を出し、64個の MinHash の一致の割合で Jaccard を見積もる
parent = list(range(len(big)))
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
pairs = set()
for b in range(K // BAND):
    buckets = collections.defaultdict(list)
    for i, row in enumerate(MH[:, b * BAND:(b + 1) * BAND]): buckets[row.tobytes()].append(i)
    for idx in buckets.values():
        if 2 <= len(idx) <= 400:
            for a in range(len(idx)):
                for c in range(a + 1, len(idx)): pairs.add((idx[a], idx[c]))
fold = big.folder.values; exa = big.exact.values
near_pairs = 0; near_idx = set()
for a, c in pairs:
    if fold[a] == fold[c]: continue
    j = float((MH[a] == MH[c]).mean())
    if j >= TH:
        ra, rc = find(a), find(c)
        if ra != rc: parent[ra] = rc
        if exa[a] != exa[c]: near_pairs += 1; near_idx.add(a); near_idx.add(c)
big["cluster"] = [find(i) for i in range(len(big))]
cl = big.groupby("cluster").agg(folders=("folder", "nunique"), n=("folder", "size"), versions=("exact", "nunique"), name=("func", lambda x: x.value_counts().index[0]),
                                files=("file", lambda x: x.value_counts().index[0]), lines=("lines", "median"))
fam = cl[cl.folders >= 2].sort_values("folders", ascending=False)       # 2つ以上の記事にまたがる「同じ処理」のまとまり
fam_multi = fam[fam.versions >= 2]                                       # うち、書き方の違う版が2つ以上ある（＝書き直していた）
fam.head(40).to_csv(P("results", "families_top.csv"))
big["fam_folders"] = big.cluster.map(cl.folders); big["fam_versions"] = big.cluster.map(cl.versions)
big["shared"] = big.fam_folders >= 2
big["rewritten"] = big.shared & (big.fam_versions >= 2)
big.drop(columns=["minhash"]).to_csv(P("results", "functions_flags.csv"), index=False)

# グループ別：関数のうち、ほかの記事にも同じ・ほぼ同じものがある割合
g = big.groupby("group")
tab = pd.DataFrame({"記事": Fi.groupby("group").folder.nunique(), "py ファイル": Fi.groupby("group").size(), "行": Fi.groupby("group").lines.sum(),
                    "関数（30トークン以上）": g.size(), "まったく同じものが別の記事にある": g.is_exact_copy.mean(), "同じかほぼ同じものが別の記事にある": g.shared.mean()}).reindex(ORDER).round(3)
tab.to_csv(P("results", "by_group.csv"))
# common.py
cm = Fi[Fi.file == "common.py"]; cmv = cm.groupby("file_hash").folder.nunique().sort_values(ascending=False)
dup_lines = int(big[big.is_exact_copy].lines.sum() - big[big.is_exact_copy].groupby("exact").lines.first().sum())
shared_lines = int(big[big.shared].lines.sum() - big[big.shared].groupby("cluster").lines.first().sum())
ident_files = Fi.groupby("file_hash").folder.nunique(); 
summary = dict(folders=int(Fi.folder.nunique()), py_files=int(len(Fi)), lines=int(Fi.lines.sum()), functions=int(len(G)), functions_big=int(len(big)),
               exact_groups=int(len(exd)), exact_functions=int(big.is_exact_copy.sum()), exact_share=round(float(big.is_exact_copy.mean()), 3),
               exact_max_folders=int(exd.folders.max()), exact_top=[[r.name_ if False else r["name"], int(r.folders)] for _, r in exd.head(8).iterrows()],
               near_pairs=int(near_pairs), families=int(len(fam)), families_rewritten=int(len(fam_multi)), families_rewritten_versions_median=float(fam_multi.versions.median()),
               shared_functions=int(big.shared.sum()), shared_share=round(float(big.shared.mean()), 3), rewritten_functions=int(big.rewritten.sum()), rewritten_share=round(float(big.rewritten.mean()), 3),
               fam_top=[[r["name"], int(r.folders), int(r.versions)] for _, r in fam.head(10).iterrows()],
               lines_in_functions=int(big.lines.sum()), dup_lines_exact=dup_lines, dup_lines_shared=shared_lines, dup_lines_shared_share=round(shared_lines / int(big.lines.sum()), 3),
               common_py_files=int(len(cm)), common_py_versions=int(cm.file_hash.nunique()), common_py_top_version_folders=int(cmv.iloc[0]), common_py_used_once=int((cmv == 1).sum()),
               identical_files_groups=int((ident_files >= 2).sum()), threshold=TH, min_tokens=MINTOK)
# 決まった処理の行：何本の記事に、何通りの書き方で出てくるか
I = pd.read_csv(P("data", "idioms.csv")); I["group"] = I.folder.map(group_of); I = I[I.group.notna()]
I["in_common"] = I.file == "common.py"
ig = I.groupby("idiom")
idi = pd.DataFrame({"行": ig.size(), "記事": ig.folder.nunique(), "ファイル": ig.apply(lambda x: x[["folder", "file"]].drop_duplicates().shape[0]),
                    "書き方（通り）": ig.line.nunique(), "いちばん多い書き方の記事": ig.apply(lambda x: x.groupby("line").folder.nunique().max()),
                    "common.py の中": ig.in_common.mean()}).sort_values("記事", ascending=False).round(3)
idi.to_csv(P("results", "idioms.csv"))
fontv = I[I.idiom == "日本語フォントの設定"].groupby("line").folder.nunique().sort_values(ascending=False).head(8)
fontv.rename("記事").to_csv(P("results", "font_variants_top.csv"))
summary["idioms"] = {k: dict(folders=int(r["記事"]), variants=int(r["書き方（通り）"]), top_variant_folders=int(r["いちばん多い書き方の記事"])) for k, r in idi.iterrows()}
print(idi.to_string()); print(fontv.to_string())
# 確かめ：しきい値と最小の大きさを変える
rob = {}
for th in (0.7, 0.9):
    par = list(range(len(big)))
    def f2(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for a, c in pairs:
        if fold[a] != fold[c] and float((MH[a] == MH[c]).mean()) >= th:
            ra, rc = f2(a), f2(c)
            if ra != rc: par[ra] = rc
    cc = pd.Series([f2(i) for i in range(len(big))]); nf = big.folder.groupby(cc).nunique(); rob[f"しきい値{th}"] = round(float(cc.map(nf).ge(2).mean()), 3)
b60 = big[big.tokens >= 60]; rob["60トークン以上の関数だけ"] = round(float(b60.shared.mean()), 3)
summary["robust_shared_share"] = rob
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1)); print(tab.to_string()); print(fam.head(15).to_string())

plt.rcParams["font.size"] = 10
fig, ax = plt.subplots(figsize=(8.8, 4.4)); x = np.arange(len(ORDER))
ax.bar(x - 0.2, tab["まったく同じものが別の記事にある"] * 100, 0.4, color="#2c6fb7", label="まったく同じ関数が別の記事にある")
ax.bar(x + 0.2, tab["同じかほぼ同じものが別の記事にある"] * 100, 0.4, color="#f0a030", label="同じか、ほぼ同じ関数が別の記事にある")
for i, o in enumerate(ORDER):
    ax.text(i - 0.2, tab.loc[o, "まったく同じものが別の記事にある"] * 100 + 1, f"{tab.loc[o, 'まったく同じものが別の記事にある'] * 100:.0f}", ha="center", fontsize=9)
    ax.text(i + 0.2, tab.loc[o, "同じかほぼ同じものが別の記事にある"] * 100 + 1, f"{tab.loc[o, '同じかほぼ同じものが別の記事にある'] * 100:.0f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(SHORT, fontsize=9); ax.set_ylabel("関数に占める割合（%）"); ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("ほかの記事にも同じ関数がある割合（30トークン以上の関数）", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a325_by_group.png"), dpi=150); plt.close(fig)

top = fam.head(12)[::-1]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ypos = np.arange(len(top))
ax.barh(ypos, top.folders.values, color="#2c6fb7"); ax.set_yticks(ypos); ax.set_yticklabels([f"{r['name']}（{r.files}）" for _, r in top.iterrows()])
for i, (_, r) in enumerate(top.iterrows()): ax.text(r.folders + 1, i, f"{int(r.folders)}本・{int(r.versions)}通り", va="center", fontsize=9)
ax.set_xlabel("その処理が出てくる記事の数"); ax.set_xlim(0, top.folders.max() * 1.25)
ax.set_title("いちばん多くの記事に出てくる処理（関数の名前・ファイル）と、書き方の数", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a325_top_families.png"), dpi=150); plt.close(fig)

vc = fam.versions.clip(upper=6).value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 4.2))
lab = [("1通り（写しただけ）" if v == 1 else f"{v}通り" if v < 6 else "6通り以上") for v in vc.index]
ax.bar(lab, vc.values, color=["#9cc3ea"] + ["#d04a3a"] * (len(vc) - 1))
for i, v in enumerate(vc.values): ax.text(i, v + 2, str(int(v)), ha="center")
ax.set_ylabel("処理のまとまりの数"); ax.set_title(f"2本以上の記事に出てくる処理 {len(fam)}組：書き方は何通りあったか", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a325_versions.png"), dpi=150); plt.close(fig)
