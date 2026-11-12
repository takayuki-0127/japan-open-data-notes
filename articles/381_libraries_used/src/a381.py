"""381 どのライブラリを、何本の記事で使ったか（④ 振り返り R111）— 集計と図

使い方: python a381.py
  data/imports.csv・requirements.csv・articles.csv（a381_extract.py が作る）をまとめる。
  「外部」＝ Python に付属せず、記事のフォルダにも同じ名前の .py がないモジュール。
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = common.GROUPS; SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
I = pd.read_csv(P("data", "imports.csv")); Q = pd.read_csv(P("data", "requirements.csv"), keep_default_na=False); A = pd.read_csv(P("data", "articles.csv"))
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
N = len(A); ng = A.groupby("group").size().reindex(ORDER)
# import の名前 → 配布パッケージの名前（requirements.txt と突き合わせるため）
PKG = {"sklearn": "scikit-learn", "PIL": "pillow", "yaml": "pyyaml", "bs4": "beautifulsoup4", "dateutil": "python-dateutil", "mpl_toolkits": "matplotlib", "fitz": "pymupdf", "docx": "python-docx", "pptx": "python-pptx", "cv2": "opencv-python", "japanize_matplotlib": "japanize-matplotlib", "pypdf": "pypdf", "Levenshtein": "levenshtein", "umap": "umap-learn", "sksurv": "scikit-survival", "igraph": "python-igraph", "MeCab": "mecab-python3", "skimage": "scikit-image"}
E3 = I[I.kind == "外部"].copy(); E3["pkg"] = E3.module.map(lambda m: PKG.get(m, m).lower().replace("_", "-"))
top = E3.groupby("pkg").folder.nunique().sort_values(ascending=False); top.name = "articles"
t = top.to_frame(); t["share"] = (t.articles / N).round(4)
for g, s in zip(ORDER, SHORT): t[s] = (E3[E3.group == g].groupby("pkg").folder.nunique() / ng[g]).reindex(t.index).fillna(0).round(3)
t.to_csv(P("results", "external_libraries.csv"))
std = I[I.kind == "標準"].groupby("module").folder.nunique().sort_values(ascending=False); (std / N).round(4).rename("share").to_frame().assign(articles=std).head(40).to_csv(P("results", "stdlib_modules.csv"))
loc = I[I.kind == "自作"].groupby("module").folder.nunique().sort_values(ascending=False); loc.rename("articles").head(20).to_csv(P("results", "local_modules.csv"))
# 1本あたりの数
per = E3.groupby("folder").pkg.nunique().reindex(A.folder).fillna(0).astype(int); A["n_ext"] = per.values
A["n_std"] = I[I.kind == "標準"].groupby("folder").module.nunique().reindex(A.folder).fillna(0).astype(int).values
pg = A.groupby("group").agg(articles=("folder", "size"), ext_median=("n_ext", "median"), ext_mean=("n_ext", "mean"), ext_max=("n_ext", "max"), std_median=("n_std", "median"), py_median=("n_py", "median"), req_median=("n_req", "median")).reindex(ORDER)
pg.loc["全体"] = [N, A.n_ext.median(), A.n_ext.mean(), A.n_ext.max(), A.n_std.median(), A.n_py.median(), A.n_req.median()]; pg.round(2).to_csv(P("results", "per_article.csv"))
dist = A.n_ext.value_counts().sort_index(); dist.rename("articles").to_csv(P("results", "n_external_distribution.csv"))
# 版の書き方
Q["how"] = Q.op.map(lambda o: "== で固定" if o == "==" else (">= で下限" if o == ">=" else ("なし" if o == "なし" else "その他")))
vg = Q.groupby(["group", "how"]).size().unstack(fill_value=0).reindex(ORDER); vg.loc["全体"] = vg.sum(); vsh = vg.div(vg.sum(axis=1), axis=0)
vg.to_csv(P("results", "version_spec_counts.csv")); vsh.round(4).to_csv(P("results", "version_spec_share.csv"))
fa = Q.groupby("folder").how.agg(lambda s: "全部 == で固定" if (s == "== で固定").all() else ("全部に版の指定あり" if (s != "なし").all() else ("一部だけ" if (s != "なし").any() else "版の指定なし")))
fa = fa.reindex(A.folder); A["req_style"] = fa.values
fs = A.groupby(["group", "req_style"]).size().unstack(fill_value=0).reindex(ORDER); fs.loc["全体"] = fs.sum(); fs.to_csv(P("results", "requirements_style_by_article.csv"))
# import と requirements の突き合わせ
qs = Q.groupby("folder").name.agg(set); es = E3.groupby("folder").pkg.agg(set)
rows = []
for f in A.folder:
    q = qs.get(f, set()); e = es.get(f, set())
    rows.append(dict(folder=f, imported_not_listed=len(e - q), listed_not_imported=len(q - e), missing=" ".join(sorted(e - q)), extra=" ".join(sorted(q - e))))
M = pd.DataFrame(rows); M.to_csv(P("results", "import_vs_requirements.csv"), index=False)
miss = pd.Series([x for r in rows for x in r["missing"].split()]).value_counts(); extra = pd.Series([x for r in rows for x in r["extra"].split()]).value_counts()
miss.rename("articles").to_csv(P("results", "imported_not_listed_by_library.csv")); extra.rename("articles").to_csv(P("results", "listed_not_imported_by_library.csv"))
summary = dict(articles=N, py_files=int(A.n_py.sum()), external_libraries=int(len(top)), used_once=int((top == 1).sum()), used_in_10plus=int((top >= 10).sum()),
               top10={k: int(v) for k, v in top.head(10).items()}, ext_median=float(A.n_ext.median()), ext_max=int(A.n_ext.max()), ext_3_or_less=int((A.n_ext <= 3).sum()),
               req_lines=int(len(Q)), spec_share={k: round(float(v), 4) for k, v in vsh.loc["全体"].items()}, style_all={k: int(v) for k, v in fs.loc["全体"].items()},
               articles_imported_not_listed=int((M.imported_not_listed > 0).sum()), articles_listed_not_imported=int((M.listed_not_imported > 0).sum()),
               top_missing={k: int(v) for k, v in miss.head(8).items()}, top_extra={k: int(v) for k, v in extra.head(8).items()},
               stdlib_top={k: int(v) for k, v in std.head(10).items()}, local_top={k: int(v) for k, v in loc.head(5).items()})
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(t.head(25).to_string()); print(pg.round(2).to_string()); print(dist.to_string()); print(vg.to_string()); print(vsh.round(3).to_string()); print(fs.to_string()); print(summary)

plt.rcParams["font.size"] = 10
# 図1 上位20
k = 20; s = top.head(k)[::-1]
fig, ax = plt.subplots(figsize=(9, 6)); ax.barh(range(k), s.values / N * 100, color="#1d5a9e")
for i, v in enumerate(s.values): ax.text(v / N * 100 + 1, i, f"{v}本（{v/N*100:.0f}%）", va="center", fontsize=9)
ax.set_yticks(range(k)); ax.set_yticklabels(s.index); ax.set_xlim(0, 118); ax.set_xlabel(f"そのライブラリを import した記事の割合（%、{N}本のうち）")
ax.set_title("記事のコードで使った外部ライブラリ（上位20）"); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a381_top20.png"), dpi=150); plt.close(fig)
# 図2 グループごとの割合（主なライブラリ）
show = ["statsmodels", "scipy", "scikit-learn", "duckdb", "openpyxl", "requests", "lightgbm", "xlrd"]
Mx = t.loc[show, SHORT].values * 100
fig, ax = plt.subplots(figsize=(9, 4.6)); im = ax.imshow(Mx, cmap="Blues", vmin=0, vmax=100, aspect="auto")
for i in range(Mx.shape[0]):
    for j in range(Mx.shape[1]): ax.text(j, i, f"{Mx[i,j]:.0f}", ha="center", va="center", fontsize=9, color="white" if Mx[i, j] > 60 else "black")
ax.set_xticks(range(7)); ax.set_xticklabels([f"{s}\n（{int(ng[g])}本）" for s, g in zip(SHORT, ORDER)], fontsize=9); ax.set_yticks(range(len(show))); ax.set_yticklabels(show)
ax.set_title("記事のまとまりごとの、ライブラリを使った記事の割合（%）"); fig.colorbar(im, ax=ax, shrink=0.8); fig.tight_layout(); fig.savefig(P("figures", "a381_by_group.png"), dpi=150); plt.close(fig)
# 図3 版の書き方
cols = ["== で固定", ">= で下限", "その他", "なし"]; cols = [c for c in cols if c in vsh.columns]; colr = {"== で固定": "#1d5a9e", ">= で下限": "#6f9fd0", "その他": "#b9cfe4", "なし": "#e9b872"}
rowsn = ORDER + ["全体"]; fig, ax = plt.subplots(figsize=(9, 4.4)); bottom = np.zeros(len(rowsn))
for c in cols:
    v = vsh.loc[rowsn, c].values * 100; ax.barh(np.arange(len(rowsn)), v, left=bottom, color=colr[c], label=c)
    for i, (b, w) in enumerate(zip(bottom, v)):
        if w >= 7: ax.text(b + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=8, color="white" if c == "== で固定" else "black")
    bottom += v
ax.set_yticks(np.arange(len(rowsn))); ax.set_yticklabels([f"{s}（{int(vg.loc[g].sum())}行）" for s, g in zip(SHORT + ["全体"], rowsn)]); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("requirements.txt の行の割合（%）")
ax.set_title("requirements.txt に書いた版の指定"); ax.legend(fontsize=9, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.3)); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a381_version_spec.png"), dpi=150); plt.close(fig)
