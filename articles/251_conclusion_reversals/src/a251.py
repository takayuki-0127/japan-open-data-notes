"""251 結論が逆になったとき、何を見落としていたか（④ 振り返り R005）

使い方: python a251.py <japan-open-data-notes のクローン>
  - 精選の記事（F256〜F295）と T の「計画と結果」の表から、仮説の判定（支持・外れ・一部）を数える
  - 「レビューで直したこと」の項目のうち、結論・題名・判定を動かした項目を拾い、見落としの種類で数える
"""
import re, sys, os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import readmes, section, items

repo = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")

docs = readmes(repo)

# ---- A. 仮説の判定 ----
def judge(cell):
    c = cell.replace("*", "").strip()
    if re.match(r"^外れの基準に当たらない", c):
        return "支持"
    if re.match(r"^(外れ|外れの基準に当たる)", c):
        return "外れ"
    if re.search(r"^(一部|判定できない|保留|判定保留)", c):
        return "一部・保留"
    if re.search(r"^(支持|当たり|主では支持|主表では支持|基準の上では支持|基本の期間では支持)", c):
        return "支持"
    return None

rows = []
for folder, t in docs:
    if not re.match(r"(F2(5[6-9]|[6-9]\d)|T\d+)_", folder):
        continue
    for blk in [t]:
        for ln in blk.split("\n"):
            if re.match(r"\|\s*\**H\d", ln):
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                j = judge(cells[-1])
                rows.append({"article": folder, "hyp": cells[0].replace("*", "")[:30],
                             "judge": j if j else "その他（数値だけ等）", "cell": cells[-1][:80]})
H = pd.DataFrame(rows)
H.to_csv(os.path.join(OUT, "data", "hypotheses.csv"), index=False)

# ---- B. レビューで結論を動かした項目 ----
TOUCH = r"題名|題と|題に|タイトル|結論|判定|逆|符号|取り下げ|削除し|弱め|消え|誤り"
NOT = r"結論は変わらない|判定は同じ|結論は同じ"
CAUSE = {
    "結果を限る条件を書いていなかった": r"条件|明記|付け|前提|仮定|場合|だけ支持|に限|改訂後",
    "1つの月・年・単位に頼っていた": r"1か月|1年|1つ|山の月|だけを除|1事故|部門|1県|外れ値|極端|除く|除い|除外",
    "比べる基準・偶然の幅": r"基準|ベース|偶然|もともと|区別できない|比べる相手|ふだん|分母",
    "幅・不確かさを出していなかった": r"幅|区間|不確か|ブートストラップ|再標本|標準誤差",
    "定義・測り方・分け方の違い": r"定義|数え方|測り方|方法で変わる|決め方|分け方|単位|混ざ",
    "期間・起点の選び方": r"期間|時期|起点|コロナ|直近|端の年|基準年",
    "計算・コードの誤り": r"誤り|食い違い|計算し直|コード|バグ|`",
    "言葉の強さ・因果": r"言い過ぎ|言い切|断定|強すぎ|因果|引っ張|弱め",
}
rev = []
for folder, t in docs:
    for blk in section(t, r"レビューで直したこと"):
        for it in items(blk):
            touch = bool(re.search(TOUCH, it)) and not re.search(NOT, it)
            rec = {"article": folder, "touch": touch, "text": it[:300]}
            for k, pat in CAUSE.items():
                rec[k] = bool(re.search(pat, it))
            rev.append(rec)
R = pd.DataFrame(rev)
R.to_csv(os.path.join(OUT, "data", "review_items.csv"), index=False)

T = R[R.touch]
cause = pd.DataFrame({
    "種類": list(CAUSE),
    "項目": [int(T[k].sum()) for k in CAUSE],
    "記事": [int(T[T[k]].article.nunique()) for k in CAUSE],
})
cause["項目の割合"] = (cause["項目"] / len(T)).round(3)
cause.to_csv(os.path.join(OUT, "results", "cause_counts.csv"), index=False)

jc = H.groupby("judge").size().reindex(["支持", "外れ", "一部・保留", "その他（数値だけ等）"]).fillna(0).astype(int)
per_art = H.groupby("article").judge.apply(lambda s: (s == "外れ").any())
summary = {
    "hyp_rows": int(len(H)),
    "hyp_articles": int(H.article.nunique()),
    "judge_counts": {k: int(v) for k, v in jc.items()},
    "articles_with_any_miss": int(per_art.sum()),
    "review_articles": int(R.article.nunique()),
    "review_items": int(len(R)),
    "touch_items": int(len(T)),
    "touch_articles": int(T.article.nunique()),
    "touch_no_cause": int((~T[list(CAUSE)].any(axis=1)).sum()),
}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False))
print(cause.to_string(index=False))

# ---- 図 ----
C = {"支持": "#4C78A8", "外れ": "#E45756", "一部・保留": "#F2B701", "その他（数値だけ等）": "#BAB0AC"}
fig, ax = plt.subplots(figsize=(8, 3.2))
left = 0
for k, v in jc.items():
    ax.barh([0], [v], left=left, color=C[k], label=f"{k}（{v}）")
    if v >= 6:
        ax.text(left + v / 2, 0, str(v), ha="center", va="center", color="white", fontsize=11)
    left += v
ax.set_yticks([]); ax.set_xlabel("仮説の数")
ax.set_title(f"計画を先に書いた記事（{H.article.nunique()}本）の仮説{len(H)}個の判定", fontsize=12)
ax.legend(ncol=4, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.35), frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a251_hypotheses.png"), dpi=150); plt.close()

cs = cause.sort_values("項目")
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(cs["種類"], cs["項目"], color="#4C78A8")
for y, (v, a) in enumerate(zip(cs["項目"], cs["記事"])):
    ax.text(v + 0.5, y, f"{v}項目（{a}本）", va="center", fontsize=9)
ax.set_xlabel("結論・題名・判定を動かした項目の数（1項目に複数の種類がつく）")
ax.set_title(f"見直しで結論を動かした{len(T)}項目は、何を見落としていたか", fontsize=12)
ax.set_xlim(0, cs["項目"].max() * 1.35)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a251_causes.png"), dpi=150); plt.close()

# ---- 逆向き・弱めの内訳 ----
rv = T.text.str.contains(r"逆|符号")
wk = T.text.str.contains(r"弱め|言い過ぎ|言いすぎ|外し|外した|限っ|限定|消し|削除")
extra = {"touch_reversed_words": int(rv.sum()), "touch_weakened_words": int(wk.sum())}
summary.update(extra)
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(extra)

# ---- 図3：実際の例（README の記述から作成者が選んだ） ----
cases = [
    ("F289", "ICT資本と生産性", "1部門（石炭製品）が、欠けた年を飛ばした平均で\n一部の比較にだけ入っていた", "「2007年以降はむしろ逆向き」→\n「結びつきが見えなかった」"),
    ("F264", "事故率と高齢化", "保険との相関0.77が2020年の1年に\nほぼ頼っていた（除くと0.45）", "「向きはよく合う」を消し、\nH4を「頑健でない」に"),
    ("F261", "潜在成長率", "「幅がいちばん狭い」は、比べた\n手法の数が年で違ったため", "題名と結論から外した"),
    ("F273", "訪日客の地方分散", "2017年の山が、有利な比べる相手\nになっていた", "題名と結論に2019年を足した"),
    ("F291", "死亡率の改善", "世代の説明の数字が、実際の\n値と合わなかった", "題名から世代の部分を外し\n（推測）とした"),
    ("F161", "似た街のグループ", "乱数の種だけを変えて、標本の\n入れ替えを見ていなかった", "ARI 0.95 → 標本を入れ替えると\n中央値0.64。結論が変わった"),
]
pd.DataFrame(cases, columns=["記事", "題材", "見落としていたこと", "直したこと"]).to_csv(os.path.join(OUT, "data", "cases.csv"), index=False)
fig, ax = plt.subplots(figsize=(10, 6.2)); ax.axis("off")
tb = ax.table(cellText=[list(c) for c in cases], colLabels=["記事", "題材", "見落としていたこと", "直したこと"],
              colWidths=[0.07, 0.17, 0.40, 0.36], loc="center", cellLoc="left")
tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 3.4)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor("#CCCCCC")
    if r == 0:
        cell.set_facecolor("#4C78A8"); cell.set_text_props(color="white", weight="bold")
ax.set_title("見直しで結論を直した例（各記事の README から）", fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a251_cases.png"), dpi=150); plt.close()
