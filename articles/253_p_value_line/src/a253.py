"""253 p値0.05の線を、どう扱ってきたか（④ 振り返り R015）

使い方: python a253.py <japan-open-data-notes のクローン>
  README に書いた p の値（p=0.03 など）を拾い、
  ①値の分布 ②同じ行に区間（95%区間など）を書いたか
  ③0.05〜0.10 の p をどんな言葉で書いたか ④「有意」という言葉を使った記事の割合
  を数える。
"""
import re, sys, os, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import readmes, GROUPS, group_of

repo = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
docs = readmes(repo)

PV = re.compile(r"(?<![A-Za-z])p\s*(?:値)?\s*(=|＝|<|＜|≈|≒)\s*(0?\.\d+(?:e-?\d+)?|\d(?:\.\d+)?e-?\d+|1(?:\.0+)?)", re.I)
INTERVAL = r"区間|信頼区間|95%|90%|CI|〜.*?[)）]"
STRONG_NULL = r"有意でない|有意差なし|有意ではない|差がない|関係がない|効果がない|影響がない"
CAUTIOUS = r"言い切れ|有意にならな|はっきりした差とは|とまでは|はっきりしなく|区別できない|はっきりしない|はっきりとは|言えない|弱い|境目|見えない|確かめられ|偶然|ぎりぎり|すぐ外|すぐ内"

rows = []
for folder, t in docs:
    for ln in t.split("\n"):
        s = ln.strip()
        if not s or "http" in s:
            continue
        for m in PV.finditer(s):
            op, v = m.group(1), m.group(2)
            try:
                val = float(v)
            except ValueError:
                continue
            if val > 1:
                continue
            # 「p<0.05 の判定」のような基準の書き方は値として数えない
            is_threshold = op in "<＜" and v in ("0.05", ".05", "0.01", "0.1", "0.10")
            rows.append({"article": folder, "group": group_of(folder), "op": op, "p": val,
                         "threshold_mention": is_threshold,
                         "interval_same_line": bool(re.search(INTERVAL, s)),
                         "strong_null": bool(re.search(STRONG_NULL, s)),
                         "cautious": bool(re.search(CAUTIOUS, s)),
                         "text": s[:300]})
P = pd.DataFrame(rows)
P.to_csv(os.path.join(OUT, "data", "p_values.csv"), index=False)
V = P[(~P.threshold_mention) & (P.op.isin(["=", "＝", "≈", "≒"]))].copy()

bins = [0, 0.001, 0.01, 0.03, 0.05, 0.07, 0.10, 0.20, 0.50, 1.0001]
labels = ["<0.001", "0.001–0.01", "0.01–0.03", "0.03–0.05", "0.05–0.07", "0.07–0.10", "0.10–0.20", "0.20–0.50", "0.50–1"]
V["bin"] = pd.cut(V.p, bins=bins, labels=labels, right=False)
hist = V.bin.value_counts().reindex(labels).fillna(0).astype(int)
hist.to_csv(os.path.join(OUT, "results", "p_hist.csv"))

near = V[(V.p >= 0.05) & (V.p < 0.10)]
just = V[(V.p >= 0.03) & (V.p < 0.05)]
words = pd.DataFrame({
    "区分": ["0.03–0.05", "0.05–0.10"],
    "値": [len(just), len(near)],
    "慎重な言葉": [int(just.cautious.sum()), int(near.cautious.sum())],
    "差がない等の強い言葉": [int(just.strong_null.sum()), int(near.strong_null.sum())],
    "同じ行に区間": [int(just.interval_same_line.sum()), int(near.interval_same_line.sum())],
})
words.to_csv(os.path.join(OUT, "results", "near_005_words.csv"), index=False)

# 記事のまとまりごと：p を書いた記事のうち、同じ行に区間も書いた値の割合／「有意」を使った記事の割合
g = pd.DataFrame({"group": GROUPS})
cnt = pd.Series([group_of(f) for f, _ in docs]).value_counts()
g["記事"] = g.group.map(cnt).fillna(0).astype(int)
g["pを書いた記事"] = g.group.map(V.groupby("group").article.nunique()).fillna(0).astype(int)
g["値"] = g.group.map(V.groupby("group").size()).fillna(0).astype(int)
g["区間も書いた割合"] = g.group.map(V.groupby("group").interval_same_line.mean()).round(3)
yu = pd.Series({f: bool(re.search(r"有意", t)) for f, t in docs})
g["「有意」を使った記事"] = g.group.map(pd.Series({f: group_of(f) for f in yu.index})[yu].value_counts()).fillna(0).astype(int)
g["「有意」の割合"] = (g["「有意」を使った記事"] / g["記事"]).round(3)
g.to_csv(os.path.join(OUT, "results", "by_group.csv"), index=False)

summary = {"readmes": len(docs), "p_mentions": int(len(P)), "threshold_mentions": int(P.threshold_mention.sum()),
           "p_values": int(len(V)), "articles_with_p": int(V.article.nunique()),
           "share_lt_005": round(float((V.p < 0.05).mean()), 3),
           "share_interval_same_line": round(float(V.interval_same_line.mean()), 3),
           "articles_using_yuui": int(yu.sum()),
           "hist": {k: int(v) for k, v in hist.items()}}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False)); print(words.to_string(index=False)); print(g.to_string(index=False))

# ---- 図1：書いた p の値の分布 ----
fig, ax = plt.subplots(figsize=(8.5, 3.8))
col = ["#4C78A8"] * 4 + ["#E45756"] * 2 + ["#BAB0AC"] * 3
ax.bar(labels, hist.values, color=col)
for i, v in enumerate(hist.values):
    ax.text(i, v + 1, str(v), ha="center", fontsize=9)
ax.axvline(3.5, color="#333333", ls="--", lw=1); ax.text(3.55, hist.max() * 0.92, "0.05", fontsize=9)
ax.set_ylabel("値の数"); ax.set_xlabel("README に書いた p の値")
ax.set_title(f"README に書いた p の値 {len(V)}個（{V.article.nunique()}本）の分布", fontsize=12)
plt.xticks(fontsize=8.5)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a253_p_hist.png"), dpi=150); plt.close()

# ---- 図2：まとまりごとに、区間も書いた割合と「有意」を使った割合 ----
gg = g[g["pを書いた記事"] >= 3]
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(len(gg)); w = 0.38
ax.bar(x - w / 2, gg["区間も書いた割合"] * 100, w, color="#4C78A8", label="p と同じ行に区間も書いた割合（値ごと）")
ax.bar(x + w / 2, gg["「有意」の割合"] * 100, w, color="#F2B701", label="「有意」という言葉を使った記事の割合")
for i, (a, b) in enumerate(zip(gg["区間も書いた割合"], gg["「有意」の割合"])):
    ax.text(i - w / 2, a * 100 + 1, f"{a*100:.0f}%", ha="center", fontsize=8.5)
    ax.text(i + w / 2, b * 100 + 1, f"{b*100:.0f}%", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(gg.group, fontsize=8.5); ax.set_ylabel("%")
ax.set_title("記事のまとまりごとの書き方（p を書いた記事が3本以上のまとまり）", fontsize=11.5)
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
ax.set_ylim(0, max(gg["区間も書いた割合"].max(), gg["「有意」の割合"].max()) * 100 * 1.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a253_by_group.png"), dpi=150); plt.close()

# ---- 図3：0.05〜0.10 の p を書いた言い方の例（README から作成者が選んだ） ----
cases = [
    ("F172", "p=0.075", "はっきりした差とは言えません"),
    ("F29", "片側 p=0.06〜0.12", "「偶然では出ない」とまでは言い切れない"),
    ("F195", "p=0.09", "見分けられる大きさの目安は±0.09で、0.1以上の正の関係は\nなさそう、とまでは言える"),
    ("F289", "p=0.065", "支持（後半は基準の境目に近い）"),
    ("F236", "p=0.09", "式どおりに集めても、5回に1回はこうなる"),
    ("F277", "p=0.07（1年除く）", "見直しで、言い切りを「映している可能性がある」に弱めた"),
]
pd.DataFrame(cases, columns=["記事", "p", "書き方"]).to_csv(os.path.join(OUT, "data", "cases.csv"), index=False)
fig, ax = plt.subplots(figsize=(10, 5)); ax.axis("off")
tb = ax.table(cellText=[list(c) for c in cases], colLabels=["記事", "p", "書いた言い方"],
              colWidths=[0.08, 0.2, 0.72], loc="center", cellLoc="left")
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 2.9)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor("#CCCCCC")
    if r == 0:
        cell.set_facecolor("#4C78A8"); cell.set_text_props(color="white", weight="bold")
ax.set_title("p が0.05〜0.10 のときの書き方の例（各記事の README から）", fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a253_wording.png"), dpi=150); plt.close()

# ---- 手で確かめた：0.03〜0.05 の p を書いた行（重複を除く29行）に、弱める確かめが同じ行にあるか ----
M = pd.read_csv(os.path.join(OUT, "data", "manual_003_005_lines.csv"))
summary["manual_003_005"] = {k: int(v) for k, v in M.label.value_counts().items()}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
