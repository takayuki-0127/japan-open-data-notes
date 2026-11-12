"""321 題名に書いた数字は、結果のファイルと合っているか（④ 振り返り R101）— その2：集計と図

使い方: python a321.py
  data/tokens.csv（a321_extract.py の出力）と data/manual_check.csv（機械で見つからなかった数字を README で1つずつ確かめた結果）を合わせ、
  記事のグループごと・数字の種類ごとに数える
"""
import os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import group_of

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
SHORT = ["000–099", "100–226", "F01–99", "F100–199", "F200–255", "精選", "1000本計画"]
D = pd.read_csv(os.path.join(OUT, "data", "tokens.csv"), dtype={"id": str, "token": str})
M = pd.read_csv(os.path.join(OUT, "data", "manual_check.csv"), dtype=str)
T = pd.read_csv(os.path.join(OUT, "data", "titles.csv"), dtype={"id": str})
D = D.merge(M[["id", "token", "judge", "note"]], on=["id", "token"], how="left")
need = D.cls.str[0].isin(list("DE"))
assert D[need].judge.notna().all(), D[need & D.judge.isna()][["id", "token"]]
D.loc[~need, "judge"] = None
D["group"] = D.folder.map(group_of)

def final(r):
    c = r.cls[0]
    if c == "A": return "README に同じ数字"
    if c == "B": return "結果ファイルに同じ数字"
    if c == "C": return "四捨五入すると一致"
    if c == "F": return "年数（始まりと終わりの年から数えられる）"
    return "読んで確かめた：" + r.judge
D["final"] = D.apply(final, axis=1)
D.to_csv(os.path.join(OUT, "results", "tokens_judged.csv"), index=False)

n = len(D); arts = D.id.nunique()
by_final = D.final.value_counts()
by_final.rename("個数").to_frame().assign(割合=(by_final / n).round(4)).to_csv(os.path.join(OUT, "results", "by_class.csv"))
flag = D[D.judge.isin(["切り捨てになっている", "粗い言い換え", "期間の言い方が粗い"])]
flag[["id", "folder", "token", "unit", "judge", "note"]].to_csv(os.path.join(OUT, "results", "to_review.csv"), index=False)

# グループ別
g = D.groupby("group")
tab = pd.DataFrame({
    "記事": g.id.nunique(),
    "題名の数字": g.size(),
    "README に同じ数字": g.apply(lambda x: (x.cls.str[0] == "A").mean()),
    "結果ファイルだけに同じ数字": g.apply(lambda x: (x.cls.str[0] == "B").mean()),
    "丸めると一致": g.apply(lambda x: (x.cls.str[0] == "C").mean()),
    "年数": g.apply(lambda x: (x.cls.str[0] == "F").mean()),
    "読んで確かめた": g.apply(lambda x: x.cls.str[0].isin(list("DE")).mean()),
}).reindex(ORDER)
allt = T.assign(group=T.id.map(lambda s: group_of((s if s[0] in "FT" else "%03d" % int(s)) + "_x")))
allt = allt[allt.id.map(lambda s: (s if s[0] in "FT" else str(int(s)))).isin(set(D.id.map(lambda s: s if s[0] in "FT" else str(int(s)))) | set())]
per_art = D.groupby("id").size()
T2 = T.copy(); T2["k"] = T2.id; T2["n"] = T2.id.map(per_art).fillna(0)
T2["group"] = T2.id.map(lambda s: group_of((s if s[0] in "FT" else "%03d" % int(s)) + "_x"))
folders = set(D.folder)
have = pd.read_csv(os.path.join(OUT, "data", "articles_checked.csv"), dtype={"id": str}) if os.path.exists(os.path.join(OUT, "data", "articles_checked.csv")) else None
tab["題名の数字（1本あたり中央値）"] = T2[T2.id.isin(have.id) if have is not None else T2.n >= 0].groupby("group").n.median().reindex(ORDER)
tab["題名に数字がない記事"] = T2[T2.id.isin(have.id) if have is not None else T2.n >= 0].groupby("group").n.apply(lambda x: (x == 0).mean()).reindex(ORDER)
tab.round(4).to_csv(os.path.join(OUT, "results", "by_group.csv"))

# 種類別
k = D.groupby("kind")
kt = pd.DataFrame({"個数": k.size(), "README に同じ数字": k.apply(lambda x: (x.cls.str[0] == "A").mean()), "丸めると一致": k.apply(lambda x: (x.cls.str[0] == "C").mean()),
                   "読んで確かめた": k.apply(lambda x: x.cls.str[0].isin(list("DE")).mean())}).reindex(["率", "量", "期間", "個数"])
kt.round(4).to_csv(os.path.join(OUT, "results", "by_kind.csv"))
# 桁数別（有効数字1桁の数字は、偶然 README にあることがある）
D["sigc"] = D.sig.clip(upper=3).map({1: "1桁", 2: "2桁", 3: "3桁以上"})
s = D.groupby("sigc"); st_ = pd.DataFrame({"個数": s.size(), "README に同じ数字": s.apply(lambda x: (x.cls.str[0] == "A").mean())}).round(4)
st_.to_csv(os.path.join(OUT, "results", "by_digits.csv"))
manual = D[need].judge.value_counts()
summary = dict(articles=int(arts), tokens=int(n), per_article_median=float(per_art.median()),
               exact_readme=int((D.cls.str[0] == "A").sum()), exact_results_only=int((D.cls.str[0] == "B").sum()), rounded=int((D.cls.str[0] == "C").sum()),
               year_span=int((D.cls.str[0] == "F").sum()), manual=int(need.sum()), manual_breakdown={a: int(b) for a, b in manual.items()},
               to_review=int(len(flag)), to_review_articles=sorted(flag.id.unique().tolist()),
               share_auto=round(float((~need).mean()), 4),
               articles_all_auto=round(float(D.groupby("id").apply(lambda x: (~x.cls.str[0].isin(list("DE"))).all()).mean()), 4))
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1)); print(tab.round(3).to_string()); print(kt.round(3)); print(st_)

# 図1：グループ別の内訳
fig, ax = plt.subplots(figsize=(9, 4.6))
cols = ["README に同じ数字", "結果ファイルだけに同じ数字", "丸めると一致", "年数", "読んで確かめた"]
colors = ["#2c6fb7", "#7fb0de", "#f0a030", "#b0b0b0", "#d04a3a"]
left = pd.Series(0.0, index=ORDER)
for c, col in zip(cols, colors):
    ax.barh(SHORT, tab[c] * 100, left=left.values, color=col, label=c); left += tab[c] * 100
for i, o in enumerate(ORDER):
    ax.text(101, i, f"{int(tab.loc[o, '題名の数字'])}個", va="center", fontsize=9)
ax.invert_yaxis(); ax.set_xlim(0, 112); ax.set_xlabel("題名の数字に占める割合（%）")
ax.set_title("題名の数字は、README・結果ファイルのどこにあったか（記事のグループ別）", fontsize=11)
ax.legend(ncol=3, fontsize=8, loc="lower center", bbox_to_anchor=(0.45, -0.38), frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a321_by_group.png"), dpi=150); plt.close(fig)

# 図2：1本あたりの題名の数字の個数
fig, ax = plt.subplots(figsize=(8, 4.2))
b = ax.bar(SHORT, tab["題名の数字（1本あたり中央値）"], color="#2c6fb7")
for r_, v in zip(b, tab["題名の数字（1本あたり中央値）"]): ax.text(r_.get_x() + r_.get_width() / 2, v + 0.1, f"{v:g}", ha="center", fontsize=10)
ax.set_ylabel("題名の数字の個数（1本あたり中央値）"); ax.set_title("題名に入れた数字は、看板記事で増えた（年と「1人あたり」などは除く）", fontsize=11)
ax.tick_params(axis="x", labelsize=9); fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a321_per_title.png"), dpi=150); plt.close(fig)

# 図3：読んで確かめた数字の内訳（表）
order = ["丸め・表記の違い", "計算すると出る", "幅のある言い回し", "切り捨てになっている", "粗い言い換え", "期間の言い方が粗い"]
ex = {"丸め・表記の違い": "題名「87%」← README「87.1」／題名「1.85倍」← 指数185",
      "計算すると出る": "題名「27%小さい」← README の損 13.6 と 9.9",
      "幅のある言い回し": "題名「4割弱」← 0.37／題名「5倍台」",
      "切り捨てになっている": "題名「7経営体」← 7.5倍／「25%減」← −25.5%／「98%」← 98.5%",
      "粗い言い換え": "題名「2倍に」← +105〜+175%",
      "期間の言い方が粗い": "題名「90年で」← 1931〜60年と1995〜2024年の平均の比較"}
ok = {"丸め・表記の違い": "合っている", "計算すると出る": "合っている", "幅のある言い回し": "合っている", "切り捨てになっている": "直す候補", "粗い言い換え": "直す候補", "期間の言い方が粗い": "直す候補"}
rows = [[o, str(int(manual.get(o, 0))), ok[o], ex[o]] for o in order]
fig, ax = plt.subplots(figsize=(11, 3.4)); ax.axis("off")
tb = ax.table(cellText=rows, colLabels=["読んで確かめた結果", "個数", "判定", "例"], loc="center", cellLoc="left", colWidths=[0.2, 0.06, 0.1, 0.64])
tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 1.7)
for (r_, c_), cell in tb.get_celld().items():
    if r_ == 0: cell.set_facecolor("#dfe8f3"); cell.set_text_props(weight="bold")
    elif rows[r_ - 1][2] == "直す候補": cell.set_facecolor("#fbe9e6")
ax.set_title(f"機械で見つからなかった{int(need.sum())}個を、README と結果ファイルで1つずつ確かめた", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a321_manual.png"), dpi=150); plt.close(fig)
