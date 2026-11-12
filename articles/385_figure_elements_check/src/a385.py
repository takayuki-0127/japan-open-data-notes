"""385 図には、軸の名前・単位・出典がそろっているか（④ 振り返り R115）— 集計と図

使い方: python a385.py
  data/figure_code.csv（a385_extract.py が、図を保存する所ごとに拾った 0/1）をまとめる。
  数の軸 ＝ 横向きの棒グラフ（barh）なら横軸、それ以外は縦軸。表や模式図（軸を消した図）と、色のマスの図（imshow など）は、軸の集計から外す。
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = common.GROUPS; SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
D = pd.read_csv(P("data", "figure_code.csv"), keep_default_na=False)
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
D["any_label"] = ((D.xlabel == 1) | (D.ylabel == 1)).astype(int)
D["axes_fig"] = ((D.no_axes == 0) & (D.grid_image == 0)).astype(int)
D["value_label"] = np.where(D.barh == 1, D.xlabel, D.ylabel)
D["unit"] = D.unit_in_label
A = D[D.axes_fig == 1]
K = ["title", "value_label", "unit", "legend", "source"]; JA = ["題名", "数の軸の名前", "軸の名前に単位", "凡例", "出典"]
def tab(df, cols):
    t = df.groupby("group")[cols].mean().reindex(ORDER); t.loc["全体"] = df[cols].mean(); return t
t_all = tab(D, ["title", "legend", "source", "xlabel", "ylabel", "any_label", "no_axes", "grid_image", "barh"]); t_all.insert(0, "figures", list(D.groupby("group").size().reindex(ORDER)) + [len(D)]); t_all.round(4).to_csv(P("results", "elements_all_figures.csv"))
t_ax = tab(A, K + ["xlabel", "ylabel", "any_label"]); t_ax.insert(0, "figures", list(A.groupby("group").size().reindex(ORDER)) + [len(A)]); t_ax.round(4).to_csv(P("results", "elements_axis_figures.csv"))
A = A.assign(all3=((A.value_label == 1) & (A.unit == 1) & (A.source == 1)).astype(int), name_unit=((A.value_label == 1) & (A.unit == 1)).astype(int))
t3 = tab(A, ["name_unit", "all3"]); t3.round(4).to_csv(P("results", "name_unit_source_together.csv"))
unit_given_label = float(A[A.any_label == 1].unit.mean())
art = D.groupby("folder").agg(group=("group", "first"), figures=("k", "size"), source=("source", "mean"), title=("title", "mean"))
art["src_style"] = np.where(art.source == 1, "全部の図に出典", np.where(art.source == 0, "どの図にもなし", "一部の図だけ"))
sa = art.groupby(["group", "src_style"]).size().unstack(fill_value=0).reindex(ORDER); sa.loc["全体"] = sa.sum(); sa.to_csv(P("results", "source_by_article.csv"))
via = D.groupby("via").source.agg(["size", "mean"]); via.round(4).to_csv(P("results", "source_by_save_style.csv"))
pv = D.groupby("group").apply(lambda d: (d.via == "helper").mean(), include_groups=False).reindex(ORDER)
kind = dict(tables_or_diagrams=int(D.no_axes.sum()), grid_images=int(((D.grid_image == 1) & (D.no_axes == 0)).sum()), horizontal_bars=int(((D.barh == 1) & (D.axes_fig == 1)).sum()), axis_figures=int(len(A)))
summary = dict(figures=int(len(D)), articles=int(D.folder.nunique()), per_article_median=float(art.figures.median()), kinds=kind,
               share_all={c: round(float(t_all.loc["全体", c]), 4) for c in ["title", "legend", "source", "xlabel", "ylabel", "any_label"]},
               share_axis={j: round(float(t_ax.loc["全体", k]), 4) for k, j in zip(K, JA)}, unit_given_any_label=round(unit_given_label, 4),
               name_and_unit=round(float(t3.loc["全体", "name_unit"]), 4), name_unit_source=round(float(t3.loc["全体", "all3"]), 4),
               source_by_group={s: round(float(t_all.loc[g, "source"]), 4) for s, g in zip(SHORT, ORDER)}, source_articles={k: int(v) for k, v in sa.loc["全体"].items()},
               source_via_helper=round(float(via.loc["helper", "mean"]), 4), source_via_savefig=round(float(via.loc["savefig", "mean"]), 4), helper_share_by_group={s: round(float(pv[g]), 4) for s, g in zip(SHORT, ORDER)})
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(t_all.round(2).to_string()); print(t_ax.round(2).to_string()); print(t3.round(2).to_string()); print(sa.to_string()); print(via); print(summary)

plt.rcParams["font.size"] = 10
# 図1 要素ごとの割合（軸のある図）
v = [t_ax.loc["全体", k] * 100 for k in K]; fig, ax = plt.subplots(figsize=(9, 4.3)); ax.bar(range(5), v, color=["#1d5a9e", "#1d5a9e", "#6f9fd0", "#b9cfe4", "#eb6834"])
for i, x in enumerate(v): ax.text(i, x + 1.5, f"{x:.0f}%", ha="center", fontsize=10)
ax.set_xticks(range(5)); ax.set_xticklabels(JA); ax.set_ylim(0, 112); ax.set_ylabel("図の割合（%）"); ax.set_title(f"図を作るコードに、その要素を書き込む命令がある割合（軸のある図 {len(A):,}枚）")
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a385_elements.png"), dpi=150); plt.close(fig)
# 図2 グループ × 要素
M = t_ax.loc[ORDER, K].values * 100; fig, ax = plt.subplots(figsize=(9, 4.6)); im = ax.imshow(M, cmap="Blues", vmin=0, vmax=100, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]): ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=9, color="white" if M[i, j] > 60 else "black")
ax.set_xticks(range(5)); ax.set_xticklabels(JA); ax.set_yticks(range(7)); ax.set_yticklabels([f"{s}（{int(t_ax.loc[g,'figures'])}枚）" for s, g in zip(SHORT, ORDER)])
ax.set_title("記事のまとまりごとの、要素がある図の割合（%、軸のある図）"); fig.colorbar(im, ax=ax, shrink=0.8); fig.tight_layout(); fig.savefig(P("figures", "a385_by_group.png"), dpi=150); plt.close(fig)
# 図3 出典：記事ごと
rowsn = ORDER + ["全体"]; cols = ["全部の図に出典", "一部の図だけ", "どの図にもなし"]; colr = ["#1d5a9e", "#b9cfe4", "#e9b872"]; sh = sa.reindex(rowsn)[cols].div(sa.reindex(rowsn)[cols].sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(9, 4.4)); bottom = np.zeros(len(rowsn))
for c, cl in zip(cols, colr):
    w = sh[c].values; ax.barh(np.arange(len(rowsn)), w, left=bottom, color=cl, label=c)
    for i, (b, x) in enumerate(zip(bottom, w)):
        if x >= 7: ax.text(b + x / 2, i, f"{x:.0f}%", ha="center", va="center", fontsize=8, color="white" if c == cols[0] else "black")
    bottom += w
ax.set_yticks(np.arange(len(rowsn))); ax.set_yticklabels([f"{s}（{int(sa.loc[g].sum())}本）" for s, g in zip(SHORT + ["全体"], rowsn)]); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("記事の割合（%）")
ax.set_title("図の中に出典を書き込んでいる記事"); ax.legend(fontsize=9, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.3)); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a385_source_by_article.png"), dpi=150); plt.close(fig)
