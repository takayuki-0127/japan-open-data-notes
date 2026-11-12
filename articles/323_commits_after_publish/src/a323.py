"""323 公開したあとの手直しは、どれくらいあったか（④ 振り返り R103）— その2：集計と図

使い方: python a323.py
  data/commit_folder.csv（コミット × 記事フォルダ）から、フォルダごとに
  - コミットの数（GitHub の画面からのアップロードは src・data などのフォルダごとに1コミットになるので、作業の回数より多い）
  - 手直し＝すでにあるファイルを書き換えたコミット：何本の記事で、最初のコミットの何分後・何日後に、どの種類のファイルを直したか
  を数える。あとからファイルを足しただけのコミット、60分以上あけたコミットも別に数える
"""
import os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
P = lambda *a: os.path.join(OUT, *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
KINDS = ["README", "PLAN", "src", "results", "data", "figures", "other"]
D = pd.read_csv(P("data", "commit_folder.csv")); C = pd.read_csv(P("data", "commits.csv"))
D["t"] = pd.to_datetime(D.datetime, utc=True).dt.tz_convert("Asia/Tokyo")
D = D.sort_values(["folder", "t"]).reset_index(drop=True)
D["group"] = D.folder.map(group_of); D = D[D.group.notna()].copy()
D["mins"] = (D.t - D.groupby("folder").t.transform("min")).dt.total_seconds() / 60
D["fix"] = D.modified > 0
D["fix_readme_only"] = D.fix & (D.mod_README > 0) & (D[["mod_" + k for k in KINDS if k != "README"]].sum(axis=1) == 0)
gap = D.groupby("folder").t.diff().dt.total_seconds() / 60
D["burst"] = (gap.isna() | (gap > 60)).groupby(D.folder).cumsum()
D.drop(columns=["t"]).round(2).to_csv(P("results", "commit_folder_flags.csv"), index=False)

f = D.groupby("folder")
F = pd.DataFrame({"group": f.group.first(), "commits": f.size(), "fix_commits": f.fix.sum(), "files_modified": f.modified.sum(), "files_added": f.added.sum(),
                  "span_hours": f.mins.max() / 60, "bursts": f.burst.max(), "last_fix_hours": f.apply(lambda x: x[x.fix].mins.max() / 60 if x.fix.any() else float("nan"))})
F["has_fix"] = F.fix_commits > 0
F.round(3).to_csv(P("results", "by_folder.csv"))
g = F.groupby("group")
tab = pd.DataFrame({"記事": g.size(), "コミット（中央値）": g.commits.median(), "手直しがあった記事": g.has_fix.sum(), "手直しがあった記事の割合": g.has_fix.mean(),
                    "手直しのコミット（あった記事の中央値）": F[F.has_fix].groupby("group").fix_commits.median(),
                    "最後の手直しまで（時間、中央値）": F[F.has_fix].groupby("group").last_fix_hours.median()}).reindex(ORDER).round(3)
tab.to_csv(P("results", "by_group.csv"))
X = D[D.fix]
bins = [-1, 10, 60, 360, 1440, 4320, 1e9]; labels = ["10分以内", "〜1時間", "〜6時間", "〜1日", "〜3日", "3日超"]
when = pd.cut(X.mins, bins=bins, labels=labels).value_counts().reindex(labels)
when.rename("手直しのコミット").to_csv(P("results", "fix_when.csv"))
kinds = {k: int(X["mod_" + k].sum()) for k in KINDS}
kinds_commits = {k: int((X["mod_" + k] > 0).sum()) for k in KINDS}
late_add = D[(D.added > 0) & (D.modified == 0) & (D.mins > 60)]
summary = dict(period=[str(D.t.min())[:16], str(D.t.max())[:16]], commits_total=int(len(C)), default_message_share=round(float(C.default_message.mean()), 3),
               root_readme_commits=int(((C.root_readme > 0) & (C.folders_touched == 0)).sum()), folder_commits=int(len(D)), folders=int(len(F)),
               commits_per_folder_median=float(F.commits.median()), files_added=int(D.added.sum()), files_modified=int(D.modified.sum()),
               fix_commits=int(len(X)), fix_share_of_commits=round(float(len(X) / len(D)), 4), folders_with_fix=int(F.has_fix.sum()), folders_with_fix_share=round(float(F.has_fix.mean()), 3),
               fix_within_1h=int((X.mins <= 60).sum()), fix_within_6h=int((X.mins <= 360).sum()), fix_after_1day=int((X.mins > 1440).sum()),
               fix_after_1day_detail=X[X.mins > 1440][["folder", "mins"]].assign(days=lambda d: (d.mins / 1440).round(1)).drop(columns="mins").to_dict("records"),
               fix_files_by_kind=kinds, fix_commits_by_kind=kinds_commits, fix_readme_only=int(X.fix_readme_only.sum()), fix_readme_only_share=round(float(X.fix_readme_only.mean()), 3),
               late_add_commits=int(len(late_add)), late_add_folders=int(late_add.folder.nunique()),
               folders_with_second_burst=int((F.bursts > 1).sum()), span_hours_median=round(float(F.span_hours.median()), 2), span_hours_p90=round(float(F.span_hours.quantile(0.9)), 2),
               span_hours_max=round(float(F.span_hours.max()), 1))
# note に公開した記事：公開日より後に、フォルダへのコミットがあったか
NP = pd.read_csv(P("data", "note_published.csv"), dtype=str)
import re as _re
key = lambda fo: (lambda m: m.group(1) if m.group(1)[0] in "FT" else str(int(m.group(1))))(_re.match(r"((?:F|T)?\d+)_", fo))
D["id"] = D.folder.map(key)
Q = D.merge(NP, on="id")
Q["after_note"] = Q.t.dt.strftime("%Y-%m-%d") > Q.published
qa = Q.groupby("id").agg(any_commit_after=("after_note", "max"), fix_after=("after_note", lambda x: 0))
qa["fix_after"] = Q[Q.after_note & Q.fix].groupby("id").size().reindex(qa.index).fillna(0).astype(int)
qa["add_after"] = Q[Q.after_note & ~Q.fix].groupby("id").size().reindex(qa.index).fillna(0).astype(int)
qa.to_csv(P("results", "after_note_publish.csv"))
summary["note_published_with_folder"] = int(len(qa)); summary["note_published_any_commit_after"] = int(qa.any_commit_after.sum()); summary["note_published_fix_after"] = int((qa.fix_after > 0).sum())
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1)); print(tab.to_string()); print(when.to_string())

plt.rcParams["font.size"] = 10
fig, ax1 = plt.subplots(figsize=(8.6, 4.3))
v = tab["手直しがあった記事の割合"] * 100
b = ax1.bar(SHORT, v, color="#2c6fb7")
for r_, x, n_, m_ in zip(b, v, tab["記事"], tab["手直しがあった記事"]): ax1.text(r_.get_x() + r_.get_width() / 2, x + 1.5, f"{x:.0f}%\n（{int(m_)}/{int(n_)}本）", ha="center", fontsize=9)
ax1.set_ylabel("ファイルを書き換えたコミットがある記事（%）"); ax1.set_ylim(0, max(v) + 18); ax1.tick_params(axis="x", labelsize=9)
ax1.set_title("アップロードのあとにファイルを書き換えた記事の割合", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a323_fix_share.png"), dpi=150); plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
axes[0].bar(labels, when.values, color="#2c6fb7")
for i, x in enumerate(when.values): axes[0].text(i, x + 1.5, str(int(x)), ha="center")
axes[0].set_title("手直しは、そのフォルダの最初のコミットの何分後か", fontsize=10.5); axes[0].set_ylabel("手直しのコミットの数"); axes[0].tick_params(axis="x", labelsize=9)
kk = ["figures", "results", "README", "src", "data", "other", "PLAN"]; nm = ["図", "results", "README", "src", "data", "その他", "PLAN"]
axes[1].barh(nm[::-1], [kinds[k] for k in kk][::-1], color="#f0a030")
for i, k in enumerate(kk[::-1]): axes[1].text(kinds[k] + 1, i, str(kinds[k]), va="center")
axes[1].set_title("書き換えたファイルの種類（のべ）", fontsize=10.5); axes[1].set_xlabel("ファイルの数")
fig.tight_layout(); fig.savefig(P("figures", "a323_when_what.png"), dpi=150); plt.close(fig)

rows = [[s, str(int(tab.loc[o, "記事"])), f"{tab.loc[o, 'コミット（中央値）']:g}", f"{int(tab.loc[o, '手直しがあった記事'])}本（{tab.loc[o, '手直しがあった記事の割合'] * 100:.0f}%）",
         ("—" if pd.isna(tab.loc[o, "最後の手直しまで（時間、中央値）"]) else f"{tab.loc[o, '最後の手直しまで（時間、中央値）']:.1f}時間")] for s, o in zip(SHORT, ORDER)]
fig, ax = plt.subplots(figsize=(9.5, 3.6)); ax.axis("off")
tb = ax.table(cellText=rows, colLabels=["グループ", "記事", "コミット\n（中央値）", "書き換えが\nあった記事", "最初のコミットから\n最後の書き換えまで（中央値）"], loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 1.75)
for (r_, c_), cell in tb.get_celld().items():
    if r_ == 0: cell.set_facecolor("#dfe8f3"); cell.set_text_props(weight="bold"); cell.set_height(cell.get_height() * 1.5)
ax.set_title("記事フォルダごとのコミットと、ファイルの書き換え", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a323_table.png"), dpi=150); plt.close(fig)
