"""351 出典には、統計の名前・表の番号・取得日がそろっているか（④ 振り返り R106）— 集計と図

使い方: python a351.py
  data/source_elements.csv（a351_extract.py が README から拾った 0/1）を、要素ごと・記事のグループごとにまとめる。
  「公的な統計などを出典にした記事」＝出典の節に、公表元の名前と、かぎかっこで書いた統計・資料の名前の両方がある記事
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common  # フォントの設定
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
D = pd.read_csv(P("data", "source_elements.csv"))
D["public"] = (D.publisher & D.stat_name).astype(int)
Pb = D[D.public == 1].copy()
Pb["three_sec"] = (Pb.stat_name & Pb.table_id & Pb.fetch_date).astype(int)
Pb["three_any"] = (Pb.stat_name & Pb.table_id_anywhere & Pb.fetch_date_anywhere).astype(int)
Pb["n_any"] = Pb.stat_name + Pb.table_id_anywhere + Pb.fetch_date_anywhere
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
cols = ["stat_name", "publisher", "url", "terms", "period", "table_id", "fetch_date", "table_id_anywhere", "fetch_date_anywhere", "three_sec", "three_any", "url_estat_list", "url_top_only"]
allr = D.groupby("group").agg(README=("folder", "size"), 出典の節あり=("has_section", "mean"), 公的な出典=("public", "mean")).reindex(ORDER)
allr.loc["全体"] = [len(D), D.has_section.mean(), D.public.mean()]
allr.round(3).to_csv(P("results", "all_readmes.csv"))
bg = Pb.groupby("group")[cols].mean().reindex(ORDER); bg.insert(0, "n", Pb.groupby("group").size().reindex(ORDER))
bg.loc["全体"] = [len(Pb)] + [Pb[c].mean() for c in cols]
bg.round(3).to_csv(P("results", "by_group.csv"))
dist = Pb.groupby("group").n_any.value_counts().unstack(fill_value=0).reindex(ORDER); dist.loc["全体"] = dist.sum(); dist.to_csv(P("results", "n_elements.csv"))
tot = bg.loc["全体"]
summary = dict(readmes=int(len(D)), public=int(len(Pb)), share_section={c: round(float(tot[c]), 4) for c in ["stat_name", "publisher", "url", "terms", "period", "table_id", "fetch_date"]},
               share_anywhere=dict(table_id=round(float(tot.table_id_anywhere), 4), fetch_date=round(float(tot.fetch_date_anywhere), 4)),
               three_in_section=int(Pb.three_sec.sum()), three_anywhere=int(Pb.three_any.sum()), n_any={int(k): int(v) for k, v in dist.loc["全体"].items()},
               url_estat_list=round(float(tot.url_estat_list), 4), no_section=int((D.has_section == 0).sum()))
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(allr.round(3).to_string()); print(bg.round(2).T.to_string()); print(dist.to_string()); print(summary)

plt.rcParams["font.size"] = 10
# 図1 要素ごと（出典の節／README のどこか）
lab = ["統計・資料の名前", "公表元", "URL", "使い方の決まり\n（加工して作成など）", "年・期間", "表の番号・ID", "取得した日"]
k = ["stat_name", "publisher", "url", "terms", "period", "table_id", "fetch_date"]
sec = [tot[c] * 100 for c in k]; anyw = [np.nan] * 5 + [tot.table_id_anywhere * 100, tot.fetch_date_anywhere * 100]
fig, ax = plt.subplots(figsize=(9, 4.5)); x = np.arange(len(k))
ax.bar(x - 0.2, sec, 0.4, color="#2c6fb7", label="出典の節に書いてある")
ax.bar(x + 0.2, [0 if np.isnan(v) else v for v in anyw], 0.4, color="#f0a03c", label="README のどこかに書いてある")
for i, v in enumerate(sec): ax.text(i - 0.2, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9)
for i, v in enumerate(anyw):
    if not np.isnan(v): ax.text(i + 0.2, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=9); ax.set_ylim(0, 112); ax.set_ylabel("記事の割合（%）")
ax.set_title(f"出典に書いてある要素（公的な統計などを出典にした README {len(Pb)}本）"); ax.legend(loc="upper right", fontsize=9)
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a351_elements.png"), dpi=150); plt.close(fig)
# 図2 グループごと
fig, ax = plt.subplots(figsize=(9, 4.5)); x = np.arange(len(ORDER))
for c, l, col, mk in [("url", "URL（出典の節）", "#888888", "o"), ("terms", "使い方の決まり（出典の節）", "#bbbbbb", "s"), ("table_id_anywhere", "表の番号・ID（README のどこか）", "#2c6fb7", "o"), ("fetch_date_anywhere", "取得した日（README のどこか）", "#d1495b", "o")]:
    y = bg.loc[ORDER, c] * 100; ax.plot(x, y, marker=mk, color=col, label=l, lw=2)
    for i, v in enumerate(y):
        if c in ("table_id_anywhere", "fetch_date_anywhere"): ax.text(i, v + 3, f"{v:.0f}", ha="center", fontsize=8, color=col)
ax.set_xticks(x); ax.set_xticklabels([f"{s}\n({int(bg.loc[o,'n'])}本)" for s, o in zip(SHORT, ORDER)], fontsize=9); ax.set_ylim(0, 110); ax.set_ylabel("記事の割合（%）")
ax.set_title("記事のグループごとの、出典の要素"); ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(0.0, 0.5)); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a351_by_group.png"), dpi=150); plt.close(fig)
# 図3 名前・表・取得日のうちいくつあるか
fig, ax = plt.subplots(figsize=(9, 4.2)); rows = ORDER + ["全体"]; bottom = np.zeros(len(rows))
sh = dist.reindex(rows).div(dist.reindex(rows).sum(axis=1), axis=0) * 100
for kk, col, l in [(1, "#c9d6e3", "名前だけ"), (2, "#7fb0de", "名前＋もう1つ"), (3, "#1d5a9e", "名前・表・取得日の3つ")]:
    v = sh[kk].values if kk in sh else np.zeros(len(rows)); ax.barh(np.arange(len(rows)), v, left=bottom, color=col, label=l)
    for i, (b, w) in enumerate(zip(bottom, v)):
        if w >= 6: ax.text(b + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=8, color="white" if kk == 3 else "black")
    bottom += v
ax.set_yticks(np.arange(len(rows))); ax.set_yticklabels(SHORT + ["全体"]); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("記事の割合（%）")
ax.set_title("統計の名前・表の番号・取得日のうち、README のどこかに書いてある数"); ax.legend(fontsize=8, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.32))
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a351_three_elements.png"), dpi=150); plt.close(fig)
