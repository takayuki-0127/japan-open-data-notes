"""354 地域を比べた記事で、順位の表はどれだけ載せていたか（④ 振り返り R109）— 集計と図

使い方: python a354.py
  data/ranking_counts.csv（原稿ごとの数）、data/readme_rank_tables.csv（README の表）、
  data/manual_check.csv（低い側・少ない側の言葉と地域の名前が同じ文にある90文を、目で読んで分けたもの。記事の番号と分類だけ）をまとめる。
  地域を比べた記事＝本文に都道府県の名前が5つ以上あるか「都道府県」などの言葉が2回以上（都道府県）、「市区町村」「市町村」が2回以上（市区町村）
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import common
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, "..", *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
D = pd.read_csv(P("data", "ranking_counts.csv"), dtype={"id": str}); R = pd.read_csv(P("data", "readme_rank_tables.csv")); H = pd.read_csv(P("data", "manual_check.csv"), dtype={"id": str})
Ht = pd.read_csv(P("data", "manual_check_top_sample.csv"))
D["unit"] = "全国・その他"; D.loc[(D.n_pref_names >= 5) | (D.w_pref >= 2), "unit"] = "都道府県"; D.loc[D.w_muni >= 2, "unit"] = "市区町村"
D["top_named"] = (D.top_pref + D.top_muni) > 0; D["bottom_named"] = (D.bottom_pref + D.bottom_muni) > 0; D["rankw"] = D.rank_word > 0; D["figcap"] = D.fig_rank_caption > 0; D["ranktbl"] = D.rank_table_rows >= 3
os.makedirs(P("results"), exist_ok=True); os.makedirs(P("figures"), exist_ok=True)
U = pd.crosstab(D.group, D.unit).reindex(ORDER)[["都道府県", "市区町村", "全国・その他"]]; U.loc["全体"] = U.sum(); U.to_csv(P("results", "units_by_group.csv"))
Rg = D[D.unit != "全国・その他"]
cols = {"rankw": "順位の言葉がある", "title_rank_word": "題名に順位の言葉", "top_named": "名前つきの「高い・多い」の文", "bottom_named": "名前つきの「低い・少ない」の文", "figcap": "図の説明に順位・並べた順", "ranktbl": "順位の表（3行以上）"}
def tab(by):
    t = Rg.groupby(by)[list(cols)].agg(lambda x: (x > 0).mean()); t.columns = list(cols.values()); t.insert(0, "記事", Rg.groupby(by).size()); return t
bu = tab("unit").reindex(["都道府県", "市区町村"]); allr = pd.DataFrame([[len(Rg)] + [(Rg[c] > 0).mean() for c in cols]], index=["地域を比べた記事の全体"], columns=bu.columns)
pd.concat([bu, allr]).round(3).to_csv(P("results", "ranking_by_unit.csv"))
bgp = tab("group").reindex(ORDER); bgp.round(3).to_csv(P("results", "ranking_by_group.csv"))
H["group"] = H.id.map(lambda s: group_of((s if s[0] in "FT" else "%03d" % int(s)) + "_x"))
CAT = ["評価を含む指標で名指し", "どちらとも言える", "中立の指標", "名指しなし・順位づけでない"]
hc = H.category.value_counts().reindex(CAT).fillna(0).astype(int); hg = pd.crosstab(H.group, H.category).reindex(ORDER).fillna(0).astype(int).reindex(columns=CAT, fill_value=0); hg.loc["全体"] = hg.sum(); hg.to_csv(P("results", "manual_check_by_group.csv"))
ha = H.groupby("category").id.nunique().reindex(CAT).fillna(0).astype(int)
ag = H[H.category == CAT[0]].groupby("group").id.nunique().reindex(ORDER).fillna(0).astype(int)
summary = dict(manuscripts=int(len(D)), regional=int(len(Rg)), units={k: int(v) for k, v in U.loc["全体"].items()}, share_regional={c: round(float(allr.iloc[0][c]), 4) for c in cols.values()},
               counts=dict(rank_word=int(Rg.rankw.sum()), title_rank_word=int((Rg.title_rank_word > 0).sum()), top_named=int(Rg.top_named.sum()), bottom_named=int(Rg.bottom_named.sum()), fig_caption=int(Rg.figcap.sum()), rank_table_manuscript=int((D.rank_table_rows >= 3).sum())),
               readme=dict(readmes=int(len(R)), rank_rows_5plus=int((R.rank_rows >= 5).sum()), rank_rows_any=int((R.rank_rows > 0).sum()), rank_header=int((R.rank_header > 0).sum())),
               bottom_sentences=int(len(H)), bottom_sentences_by_category={k: int(v) for k, v in hc.items()}, bottom_articles_by_category={k: int(v) for k, v in ha.items()},
               flagged_articles_by_group={o: int(ag[o]) for o in ORDER}, top_sample=dict(read=int(Ht.read[0]), flagged=int(Ht.iloc[0, 1]), either=int(Ht.iloc[0, 2])),
               title_bottom_named=int((D.title_bottom_named > 0).sum()), title_top_named=int((D.title_top_named > 0).sum()))
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(U.to_string()); print(pd.concat([bu, allr]).round(3).T.to_string()); print(bgp.round(2).to_string()); print(hg.to_string()); print(summary)

plt.rcParams["font.size"] = 10
# 図1 地域の単位
fig, ax = plt.subplots(figsize=(9, 4.3)); x = np.arange(len(ORDER)); b = np.zeros(len(ORDER))
for c, col in [("都道府県", "#2c6fb7"), ("市区町村", "#f0a03c"), ("全国・その他", "#d9d9d9")]:
    v = U.loc[ORDER, c].values; ax.bar(x, v, 0.62, bottom=b, color=col, label=c)
    for i, (bb, w) in enumerate(zip(b, v)):
        if w >= 6: ax.text(i, bb + w / 2, str(int(w)), ha="center", va="center", fontsize=9)
    b += v
ax.set_xticks(x); ax.set_xticklabels(SHORT); ax.set_ylabel("原稿の数"); ax.set_title(f"記事が比べている地域の単位（原稿 {len(D)}本のうち、地域を比べた記事は {len(Rg)}本）"); ax.legend(fontsize=9)
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a354_units.png"), dpi=150); plt.close(fig)
# 図2 順位の書き方
fig, ax = plt.subplots(figsize=(9, 4.4)); k = list(cols.values()); y = np.arange(len(k)); w = 0.38
for j, (u, col) in enumerate([("都道府県", "#2c6fb7"), ("市区町村", "#f0a03c")]):
    v = bu.loc[u, k].values * 100; ax.barh(y + (j - 0.5) * w, v, w, color=col, label=f"{u}を比べた記事（{int(bu.loc[u,'記事'])}本）")
    for i, a in enumerate(v): ax.text(a + 0.8, i + (j - 0.5) * w, f"{a:.0f}%", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels(k, fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 75); ax.set_xlabel("記事の割合（%）"); ax.set_title("地域を比べた記事での、順位の書き方（機械で数えたもの）"); ax.legend(fontsize=9, loc="lower right")
ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(P("figures", "a354_ranking_forms.png"), dpi=150); plt.close(fig)
# 図3 「低い・少ない」＋地域の名前の文を読んだ結果
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
cc = ["#d1495b", "#f0a03c", "#9cc3ea", "#d9d9d9"]; ax = axs[0]
ax.barh(range(4), hc.values, color=cc)
for i, (a, n) in enumerate(zip(hc.values, ha.values)): ax.text(a + 0.6, i, f"{a}文（{n}本）", va="center", fontsize=9)
ax.set_yticks(range(4)); ax.set_yticklabels(["評価を含む指標で\n地域を名指し", "どちらとも言える", "中立の指標", "名指しなし・\n順位づけでない"], fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, max(hc.values) * 1.45)
ax.set_title(f"「低い・少ない」＋地域の名前の文 {len(H)}文を読んだ分類", fontsize=10); ax.spines[["top", "right"]].set_visible(False)
ax = axs[1]; ax.bar(np.arange(len(ORDER)), ag.values, 0.6, color="#d1495b")
for i, a in enumerate(ag.values): ax.text(i, a + 0.1, str(int(a)), ha="center", fontsize=9)
ax.set_xticks(np.arange(len(ORDER))); ax.set_xticklabels(SHORT, fontsize=8, rotation=30, ha="right"); ax.set_ylim(0, max(ag.values) + 1.5); ax.set_ylabel("記事の数")
ax.set_title("「評価を含む指標で名指し」があった記事", fontsize=10); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(P("figures", "a354_bottom_named.png"), dpi=150); plt.close(fig)
