"""324 自分の文章は、読みやすくなったのか（④ 振り返り R104）— 集計と図

使い方: python a324.py
  data/md_sentence_stats.csv（src/zz_324_md.py で手元の原稿 md を1本ずつ数えたもの。本文は入っていない）を、
  記事のグループごと・番号の順に並べる。見るのは 1文の長さ（中央値）、60字を超える文の割合、100字以上の文の割合、
  読点の数、かっこ書きのある文の割合、漢字の割合、1段落の文の数
"""
import os, json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
P = lambda *a: os.path.join(OUT, *a)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
M = pd.read_csv(P("data", "md_sentence_stats.csv"), dtype={"id": str})
M["group"] = M.id.map(lambda s: group_of((s if s[0] in "FT" else "%03d" % int(s)) + "_x"))
M = M[M.group.notna()].copy()
M["num"] = M.id.str.extract(r"(\d+)")[0].astype(int)
g = M.groupby("group")
tab = g.agg(記事=("id", "size"), 文の数=("n_sent", "median"), 一文の字数=("med_len", "median"), かっこを除いた字数=("med_len_nopar", "median"),
            六十字超=("share_gt60", "median"), 百字以上=("share_ge100", "median"), 読点=("commas_per_sent", "median"), かっこのある文=("share_paren", "median"),
            推測のある文=("share_suisoku", "mean"), 漢字=("kanji", "median"), 一段落の文=("mean_sent_per_para", "median"), いちばん長い文=("max_len", "median")).reindex(ORDER).round(3)
tab.to_csv(P("results", "by_group.csv"))
# 記事ごとの値の散らばり（グループの中の四分位）
q = g.med_len.quantile([0.25, 0.5, 0.75]).unstack().reindex(ORDER); q.to_csv(P("results", "med_len_quartiles.csv"))
# 看板記事の番号順（F01〜F295）：20本の移動中央値
Fs = M[M.id.str.startswith("F")].sort_values("num")
roll = Fs.set_index("num")[["med_len", "share_gt60", "share_paren"]].rolling(20, center=True, min_periods=10).median()
roll.round(3).to_csv(P("results", "f_series_rolling.csv"))
# 1文の長さと、かっこ・推測・文の数の関係（記事ごと）
cor = M[["med_len", "share_paren", "share_suisoku", "n_sent", "commas_per_sent", "kanji", "digit"]].corr(method="spearman").med_len.round(3).to_dict()
# 文の数が同じくらいの記事どうしで比べる（長い記事ほど文が長いだけではないか）
M["size"] = pd.cut(M.n_sent, [0, 40, 80, 160, 10000], labels=["〜40文", "41〜80文", "81〜160文", "161文〜"])
bysize = M.pivot_table(index="group", columns="size", values="med_len", aggfunc="median", observed=False).reindex(ORDER)
cnt = M.pivot_table(index="group", columns="size", values="med_len", aggfunc="size", observed=False).reindex(ORDER)
bysize.where(cnt >= 5).round(1).to_csv(P("results", "med_len_by_article_size.csv"))
first, low, sel = tab.loc["100–226"], tab.loc["F200–F255"], tab.loc["F256–F295（精選）"]
summary = dict(articles=int(len(M)), groups={o: int(tab.loc[o, "記事"]) for o in ORDER},
               med_len={o: float(tab.loc[o, "一文の字数"]) for o in ORDER}, share_gt60={o: float(tab.loc[o, "六十字超"]) for o in ORDER},
               med_len_nopar={o: float(tab.loc[o, "かっこを除いた字数"]) for o in ORDER}, share_paren={o: float(tab.loc[o, "かっこのある文"]) for o in ORDER},
               spearman_with_med_len=cor, f_rolling_min=[int(roll.med_len.idxmin()), float(roll.med_len.min())], f_rolling_max=[int(roll.med_len.idxmax()), float(roll.med_len.max())])
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(tab.to_string()); print(q.to_string()); print(bysize.where(cnt >= 5).round(1).to_string()); print(cor); print(summary["f_rolling_min"], summary["f_rolling_max"])

plt.rcParams["font.size"] = 10
fig, ax = plt.subplots(figsize=(8.8, 4.4))
x = np.arange(len(ORDER))
ax.bar(x - 0.2, tab["一文の字数"], 0.4, color="#2c6fb7", label="1文の字数（中央値）")
ax.bar(x + 0.2, tab["かっこを除いた字数"], 0.4, color="#9cc3ea", label="かっこ書きを除いた字数（中央値）")
for i, o in enumerate(ORDER):
    ax.text(i - 0.2, tab.loc[o, "一文の字数"] + 0.6, f"{tab.loc[o, '一文の字数']:g}", ha="center", fontsize=9)
    ax.text(i + 0.2, tab.loc[o, "かっこを除いた字数"] + 0.6, f"{tab.loc[o, 'かっこを除いた字数']:g}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(SHORT, fontsize=9); ax.set_ylabel("字"); ax.set_ylim(0, 58); ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
ax.set_title("1文の長さ（記事ごとの中央値を、グループの中央値でまとめた）", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a324_sentence_length.png"), dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.8, 4.4))
ax.scatter(Fs.num, Fs.med_len, s=9, color="#b9c7d8", label="記事1本")
ax.plot(roll.index, roll.med_len, color="#2c6fb7", lw=2, label="前後20本の中央値")
for a_, b_, t_ in [(1, 99, "F01–99"), (100, 199, "F100–199"), (200, 255, "F200–255"), (256, 295, "精選")]:
    ax.axvline(a_ - 0.5, color="#aaa", lw=0.6, ls=":"); ax.text((a_ + b_) / 2, 73, t_, ha="center", fontsize=9, color="#555")
ax.set_ylim(20, 77); ax.set_xlabel("看板記事の番号（おおむね作った順）"); ax.set_ylabel("1文の字数（記事ごとの中央値）"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title("看板記事を番号順に並べると、1文は短くなったあと、精選でまた長くなった", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a324_f_series.png"), dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.8, 4.4))
ax.bar(x - 0.27, tab["六十字超"] * 100, 0.27, color="#d04a3a", label="60字を超える文")
ax.bar(x, tab["かっこのある文"] * 100, 0.27, color="#f0a030", label="かっこ書きのある文")
ax.bar(x + 0.27, tab["推測のある文"] * 100, 0.27, color="#7a7a7a", label="「推測」と書いた文")
for i, o in enumerate(ORDER):
    for dx, c in [(-0.27, "六十字超"), (0, "かっこのある文"), (0.27, "推測のある文")]:
        ax.text(i + dx, tab.loc[o, c] * 100 + 0.7, f"{tab.loc[o, c] * 100:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(SHORT, fontsize=9); ax.set_ylabel("文に占める割合（%）"); ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left"); ax.set_ylim(0, 62)
ax.set_title("長い文・かっこ書き・「推測」のある文の割合", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a324_long_paren.png"), dpi=150); plt.close(fig)
