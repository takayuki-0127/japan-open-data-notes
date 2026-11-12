"""384 置いたデータは、どれくらいの大きさだったか（④ 振り返り R114）— 集計と図

使い方: python a384.py
  data/files.csv.gz（記事フォルダのファイルの一覧：場所・拡張子・大きさ・中身のハッシュ）と data/csv_rows.csv（data の CSV の行数）をまとめる。
  「data」＝ 記事フォルダの data/ の下。MB は 100万バイト。
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = common.GROUPS; SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
F = pd.read_csv(P("data", "files.csv.gz"), dtype={"sha": str}); R = pd.read_csv(P("data", "csv_rows.csv"))
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
MB = 1e6; folders = sorted(F.folder.unique()); NA = len(folders); gof = F.drop_duplicates("folder").set_index("folder").group
pl = F.assign(place2=F.place.where(F.place.isin(["data", "figures", "results", "src", "(直下)"]), "その他")).groupby("place2")["size"].agg(files="count", bytes="sum").sort_values("bytes", ascending=False)
pl["MB"] = (pl.bytes / MB).round(1); pl["share"] = (pl.bytes / pl.bytes.sum()).round(4); pl.to_csv(P("results", "by_place.csv"))
D = F[F.place == "data"].copy()
a = D.groupby("folder")["size"].agg(files="count", bytes="sum").reindex(folders).fillna(0); a["group"] = gof.reindex(folders).values; a["MB"] = a.bytes / MB
a.to_csv(P("results", "data_by_article.csv"))
q = lambda s, p: float(np.percentile(s, p))
bg = a.groupby("group").agg(articles=("MB", "size"), no_data=("files", lambda s: int((s == 0).sum())), files_median=("files", "median"), MB_median=("MB", "median"), MB_p90=("MB", lambda s: q(s, 90)), MB_max=("MB", "max"), MB_sum=("MB", "sum")).reindex(ORDER)
bg.loc["全体"] = [NA, int((a.files == 0).sum()), a.files.median(), a.MB.median(), q(a.MB, 90), a.MB.max(), a.MB.sum()]; bg.round(3).to_csv(P("results", "data_by_group.csv"))
bins = [-1, 0, 0.1, 1, 5, 10, 20, 1e9]; lab = ["data なし", "0.1MB 未満", "0.1〜1MB", "1〜5MB", "5〜10MB", "10〜20MB", "20MB 以上"]
a["bin"] = pd.cut(a.MB, bins=bins, labels=lab); bd = a.bin.value_counts().reindex(lab); bd.rename("articles").to_csv(P("results", "data_size_bins.csv"))
ex = D.groupby("ext")["size"].agg(files="count", bytes="sum"); ex["MB"] = (ex.bytes / MB).round(2); ex["share_files"] = (ex.files / ex.files.sum()).round(4); ex["share_bytes"] = (ex.bytes / ex.bytes.sum()).round(4)
ex = ex.sort_values("files", ascending=False); ex.to_csv(P("results", "data_formats.csv"))
big = D.sort_values("size", ascending=False).head(30)[["folder", "path", "size"]]; big["MB"] = (big["size"] / MB).round(2); big.to_csv(P("results", "largest_files.csv"), index=False)
sizes = D["size"]; lim = dict(over_10MB=int((sizes > 10e6).sum()), from_8MB=int((sizes >= 8e6).sum()), from_5MB=int((sizes >= 5e6).sum()), from_1MB=int((sizes >= 1e6).sum()), under_100KB=int((sizes < 1e5).sum()))
# 同じ中身のファイル（ハッシュが同じ）が、複数の記事の data にある
du = D[D.sha.notna() & (D.sha != "")].groupby("sha").agg(n=("folder", "nunique"), size=("size", "first"), files=("folder", "size")); dup = du[du.n >= 2]
dup_bytes = float(((dup.files - 1) * dup["size"]).sum()); dup.sort_values("size", ascending=False).head(30).assign(MB=lambda d: (d["size"] / MB).round(2)).to_csv(P("results", "same_content_files.csv"))
art_with_copy = int(D[D.sha.isin(dup.index)].folder.nunique())
R["rows"] = R.lines - 1
rg = R.groupby("group").rows.agg(files="count", median="median", p90=lambda s: q(s, 90), max="max").reindex(ORDER); rg.loc["全体"] = [len(R), R.rows.median(), q(R.rows, 90), R.rows.max()]; rg.round(1).to_csv(P("results", "csv_rows_by_group.csv"))
rb = pd.cut(R.rows, bins=[-1, 100, 1000, 10000, 100000, 1e9], labels=["100行以下", "101〜1,000行", "1,001〜1万行", "1万〜10万行", "10万行超"]).value_counts(sort=False); rb.rename("files").to_csv(P("results", "csv_rows_bins.csv"))
summary = dict(articles=NA, files_all=int(len(F)), MB_all=round(float(F["size"].sum() / MB), 1), data_files=int(len(D)), data_MB=round(float(sizes.sum() / MB), 1), data_share=round(float(sizes.sum() / F["size"].sum()), 4),
               articles_with_data=int((a.files > 0).sum()), files_median=float(a.files.median()), MB_median=round(float(a.MB.median()), 3), MB_mean=round(float(a.MB.mean()), 3), MB_p90=round(q(a.MB, 90), 2), MB_max=round(float(a.MB.max()), 1),
               top10pct_share=round(float(a.MB.sort_values(ascending=False).head(NA // 10).sum() / a.MB.sum()), 4), limits=lim, largest=[(r.folder, r.path, r.MB) for r in big.head(5).itertuples()],
               csv_share_files=float(ex.loc["csv", "share_files"]), csv_share_bytes=float(ex.loc["csv", "share_bytes"]), excel_files=int(ex.loc[["xlsx", "xls"], "files"].sum()), excel_share_bytes=round(float(ex.loc[["xlsx", "xls"], "share_bytes"].sum()), 4),
               same_content_groups=int(len(dup)), same_content_extra_MB=round(dup_bytes / MB, 1), same_content_share_of_data=round(dup_bytes / float(sizes.sum()), 4), articles_with_copied_file=art_with_copy,
               csv_counted=int(len(R)), csv_in_data=int((D.ext == "csv").sum()), rows_median=float(R.rows.median()), rows_p90=q(R.rows, 90), rows_max=int(R.rows.max()), rows_bins={k: int(v) for k, v in rb.items()})
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(pl.to_string()); print(bg.round(2).to_string()); print(bd.to_string()); print(ex.head(12).to_string()); print(rg.round(1).to_string()); print(dup.sort_values("size", ascending=False).head(8).to_string()); print(summary)

plt.rcParams["font.size"] = 10
# 図1 記事ごとの data の大きさ
fig, ax = plt.subplots(figsize=(9, 4.4)); v = bd.values; cols = ["#a3a29c"] + ["#b9cfe4", "#8fb5dc", "#6f9fd0", "#3f7fc0", "#1d5a9e", "#12406f"]
ax.bar(range(len(lab)), v, color=cols)
for i, x in enumerate(v): ax.text(i, x + 3, f"{int(x)}本\n（{x/NA*100:.0f}%）", ha="center", fontsize=9)
ax.set_xticks(range(len(lab))); ax.set_xticklabels(lab); ax.set_ylabel("記事の数（本）"); ax.set_ylim(0, v.max() * 1.22)
ax.set_title(f"記事1本の data フォルダの大きさ（{NA}本、中央値 {a.MB.median():.2f}MB）"); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a384_size_bins.png"), dpi=150); plt.close(fig)
# 図2 形式（数と大きさ）
top = ex.head(8).index.tolist(); oth_f = 1 - ex.loc[top, "share_files"].sum(); oth_b = 1 - ex.loc[top, "share_bytes"].sum()
names = top + ["その他"]; sf = list(ex.loc[top, "share_files"] * 100) + [oth_f * 100]; sb = list(ex.loc[top, "share_bytes"] * 100) + [oth_b * 100]
x = np.arange(len(names)); fig, ax = plt.subplots(figsize=(9, 4.4)); ax.bar(x - 0.2, sf, 0.4, color="#1d5a9e", label="ファイルの数"); ax.bar(x + 0.2, sb, 0.4, color="#e9b872", label="大きさ（バイト）")
for i in range(len(names)): ax.text(i - 0.2, sf[i] + 1, f"{sf[i]:.0f}", ha="center", fontsize=8.5); ax.text(i + 0.2, sb[i] + 1, f"{sb[i]:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(names); ax.set_ylabel("data フォルダ全体に占める割合（%）"); ax.set_title(f"data フォルダのファイルの形式（{len(D):,}個、{sizes.sum()/MB:,.0f}MB）"); ax.legend(fontsize=9)
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a384_formats.png"), dpi=150); plt.close(fig)
# 図3 ファイル1個の大きさ（上限 10MB との距離）
edges = [0, 1e3, 1e4, 1e5, 1e6, 5e6, 8e6, 10e6]; labs = ["1KB 未満", "1〜10KB", "10〜100KB", "0.1〜1MB", "1〜5MB", "5〜8MB", "8〜10MB"]
cnt = pd.cut(sizes, bins=edges, labels=labs, right=False).value_counts(sort=False)
fig, ax = plt.subplots(figsize=(9, 4.4)); ax.bar(range(len(labs)), cnt.values, color=["#b9cfe4"] * 4 + ["#6f9fd0", "#1d5a9e", "#eb6834"])
for i, x_ in enumerate(cnt.values): ax.text(i, x_ + 12, f"{int(x_):,}個", ha="center", fontsize=9)
ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs); ax.set_ylabel("ファイルの数（個）"); ax.set_ylim(0, cnt.max() * 1.15)
ax.set_title(f"data フォルダのファイル1個の大きさ（10MB を超えるファイルは {lim['over_10MB']}個）"); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a384_file_sizes.png"), dpi=150); plt.close(fig)
