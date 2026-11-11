"""288 書き続けてわかった、分析記事の書き方（④ 振り返り R020）

使い方: python a288.py
  data/md_stats.csv は、手元の記事 md（note の下書きの原稿、549本）を数えたもの（src/zz_288_md.py で作成）。
  記事のグループごとに、題名の長さ・題名が問いの形か・本文の長さ・図の数・見出しの数・
  冒頭の「この記事で分かること」・「言えないこと」の見出し・「推測」の数・1文の長さを並べる
"""
import os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import group_of

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]

M = pd.read_csv(os.path.join(OUT, "data", "md_stats.csv"), dtype={"file_num": str, "prefix": str})
M["prefix"] = M.prefix.fillna("")
M = M.drop_duplicates(["prefix", "num"], keep="first")
M["group"] = (M.prefix + M.num.astype(str) + "_x").map(group_of)
M = M[M.group.notna()]
M["sui_per10k"] = M.suisoku / M.chars * 10000
M["title_rest_share"] = M.title_after_q / M.title_len
agg = M.groupby("group").agg(
    articles=("num", "size"),
    title_len=("title_len", "median"),
    title_q=("title_q", "mean"),
    title_digits=("title_digits", "mean"),
    title_after_q=("title_after_q", "median"),
    chars=("chars", "median"),
    images=("images", "median"),
    h2=("h2", "median"),
    wakaru_top=("wakaru_top", "mean"),
    ienai=("ienai", "mean"),
    sui_per10k=("sui_per10k", "mean"),
    sui_any=("suisoku", lambda x: (x > 0).mean()),
    sent_len=("sent_len", "median"),
).reindex(ORDER).round(3)
agg.to_csv(os.path.join(OUT, "results", "by_group.csv"))
tot = {"articles": int(len(M)), "chars_median": float(M.chars.median()), "images_median": float(M.images.median()),
       "corr_title_len_chars": round(M[["title_len", "chars"]].corr().iloc[0, 1], 3)}
json.dump({"total": tot, "by_group": agg.reset_index().to_dict("records")}, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(agg.to_string()); print(tot)

x = range(len(ORDER))
# 図1：題名
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.bar(x, agg.title_len, color="#c9d6e8", label="題名の長さ（中央値）")
ax.bar(x, agg.title_after_q, color="#2f6fb0", label="うち「？」の後ろ（答えの部分）")
for i, (a, b) in enumerate(zip(agg.title_len, agg.title_after_q)):
    ax.text(i, a + 2, f"{a:.0f}字", ha="center", fontsize=9)
ax2 = ax.twinx(); ax2.plot(x, agg.title_q * 100, color="#d9822b", marker="o", label="問いの形の題名の割合（右）"); ax2.set_ylim(0, 105); ax2.set_ylabel("%")
ax.set_xticks(list(x)); ax.set_xticklabels(SHORT, fontsize=9); ax.set_ylabel("字")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper left")
ax.set_title("題名は、問いの後ろに答えを書く形で長くなった", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a288_title.png"), dpi=150); plt.close(fig)

# 図2：本文の長さと図の数
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.bar(x, agg.chars, color="#2f6fb0")
for i, (c, im) in enumerate(zip(agg.chars, agg.images)):
    ax.text(i, c + 80, f"{c:,.0f}字\n図{im:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(list(x)); ax.set_xticklabels(SHORT, fontsize=9); ax.set_ylabel("本文の文字数（中央値、URL・空白を除く）")
ax.set_ylim(0, agg.chars.max() * 1.25)
ax.set_title("本文の長さと図の数（中央値）", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a288_length.png"), dpi=150); plt.close(fig)

# 図3：型が入った割合
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.plot(x, agg.wakaru_top * 100, marker="o", label="冒頭に「この記事で分かること」")
ax.plot(x, agg.ienai * 100, marker="s", label="「言えないこと」などの見出し")
ax.plot(x, agg.sui_any * 100, marker="^", label="「推測」と書いた記事")
ax.set_xticks(list(x)); ax.set_xticklabels(SHORT, fontsize=9); ax.set_ylim(0, 105); ax.set_ylabel("記事の割合（%）")
ax.legend(fontsize=9, loc="lower right")
ax.set_title("「分かること」と「言えないこと」は最初からあり、増えたのは「推測」", fontsize=11.5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a288_parts.png"), dpi=150); plt.close(fig)
