"""F96 04 図1〜6"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, BLUE, ORANGE, GREEN, RED, GRAY, PURPLE
from queries import NEEDS

tab = pd.read_csv(DATA / "tables.csv.gz", dtype={"id": str})
summ = json.load(open(DATA / "tables_summary.json"))
sm = pd.read_csv(RES / "summary.csv")
pq = pd.read_csv(RES / "per_query.csv")
LAB = {"kw_and": "キーワード全部一致", "bm25": "単語の一致（BM25）", "char": "文字の一致（2〜3文字）",
       "ruri30": "文埋め込み（ruri 30m）", "ruri70": "文埋め込み（ruri 70m）", "hybrid": "組み合わせ（BM25＋30m）",
       "ruri30_noprefix": "30m・接頭辞なし"}
COL = {"kw_and": GRAY, "bm25": ORANGE, "char": "#c9a26b", "ruri30": BLUE, "ruri70": PURPLE, "hybrid": GREEN}
WL = {"kw": "キーワード\n（統計の言葉）", "pro": "文\n（統計の言葉）", "plain": "文\n（日常の言葉）"}

# 図1 対象の表
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw=dict(width_ratios=[1, 1.5]))
vals = [1494286, summ["files"], summ["tables"]]
labs = ["e-Stat のファイル\n（全体）", "2026年1〜10月に\n公開・更新", "同じ表題を\nまとめた表"]
ax[0].barh(labs[::-1], vals[::-1], color=[BLUE, "#7fa6d6", "#b8cde8"][::-1], height=0.55)
ax[0].set_xscale("log")
for i, v in enumerate(vals[::-1]):
    ax[0].text(v * 1.1, i, f"{v:,}", va="center", fontsize=10)
ax[0].set_xlim(1e4, 8e6)
ax[0].set_title("検索の対象にした表", fontsize=11, loc="left")
vc = tab.toukei.value_counts()
top = vc.head(15)[::-1]
ax[1].barh([s[:16] for s in top.index], top.values, color=BLUE, height=0.6)
for i, v in enumerate(top.values):
    ax[1].text(v + 40, i, f"{v:,}", va="center", fontsize=8.5)
ax[1].set_title(f"表の多い政府統計（全{summ['toukei']}統計のうち上位15）", fontsize=11, loc="left")
ax[1].tick_params(labelsize=8.5)
ax[1].set_xlim(0, top.max() * 1.15)
fig.suptitle("e-Stat の統計表の一覧：2026年1〜10月に公開・更新された 44,533 ファイル → 31,383 表", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "fig1_corpus.png"); plt.close(fig)

# 図2 上位10件に正解が入る割合
methods = ["kw_and", "bm25", "char", "ruri30", "ruri70", "hybrid"]
fig, ax = plt.subplots(figsize=(11, 4.8))
W = 0.13
for j, m in enumerate(methods):
    for i, w in enumerate(["kw", "pro", "plain"]):
        r = sm[(sm.method == m) & (sm.wording == w) & (sm.metric == "hit10")].iloc[0]
        x = i + (j - 2.5) * W
        ax.bar(x, r["mean"] * 100, W * 0.9, color=COL[m], label=LAB[m] if i == 0 else None)
        ax.plot([x, x], [r.lo * 100, r.hi * 100], color="#333", lw=0.8)
        if w == "plain":
            ax.text(x, r.hi * 100 + 2, f"{r['mean']*100:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(range(3)); ax.set_xticklabels([WL[w] for w in ["kw", "pro", "plain"]])
ax.set_ylabel("上位10件に正解の表が入った割合（%）")
ax.set_ylim(0, 110)
ax.legend(ncol=3, fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.17))
ax.set_title("探しもの44件×質問3通り。統計の言葉で聞けばどの方法も9割超、日常の言葉では大きな差（縦線は95%区間）", fontsize=11, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig2_hit10.png"); plt.close(fig)

# 図3 日常の言葉：探しものごとの最初の正解の順位
p = pq[pq.wording == "plain"].pivot_table(index="need", columns="method", values="first")
ms3 = ["bm25", "ruri30", "hybrid"]
p = p[ms3]
order = p.fillna(2000).sort_values(["ruri30", "bm25"]).index
p = p.loc[order]
names = {nd["id"]: nd["plain"] for nd in NEEDS}
fig, ax = plt.subplots(figsize=(10, 11))
y = np.arange(len(p))
for k, m in enumerate(ms3):
    v = p[m].fillna(1500).values
    ax.scatter(v, y + (k - 1) * 0.22, s=28, color=COL[m], label=LAB[m], zorder=3,
               marker="o" if m != "hybrid" else "D")
ax.axvline(10.5, color=RED, lw=1, ls="--"); ax.text(11.5, -1.3, "10位", color=RED, fontsize=9)
ax.set_xscale("log"); ax.set_xlim(0.8, 2000)
ax.set_xticks([1, 10, 100, 1000, 1500]); ax.set_xticklabels(["1", "10", "100", "1000", "圏外"])
ax.set_yticks(y); ax.set_yticklabels([names[i][:26] for i in p.index], fontsize=8)
ax.invert_yaxis()
ax.grid(axis="x", color="#ddd", lw=0.6)
ax.legend(loc="upper right", fontsize=9, frameon=True)
ax.set_xlabel("最初に正解の表が出てきた順位（対数。1000位までに出なければ圏外）")
ax.set_title("日常の言葉で聞いたとき、正解は何位に出たか（44件）", fontsize=11, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig3_rank_plain.png"); plt.close(fig)

# 図4 件数を増やすと
rs = pd.read_csv(RES / "robust_size.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
for a, w in zip(ax, ["pro", "plain"]):
    for m in ["bm25", "ruri30", "hybrid"]:
        d = rs[(rs.method == m) & (rs.wording == w)].sort_values("n_docs")
        a.plot(d.n_docs, d.hit10 * 100, "-o", color=COL[m], lw=2, ms=5, label=LAB[m])
        a.text(d.n_docs.iloc[-1] * 1.04, d.hit10.iloc[-1] * 100, f"{d.hit10.iloc[-1]*100:.0f}", va="center", fontsize=9, color="#333")
    a.set_xscale("log"); a.set_xlim(4000, 45000)
    a.set_xticks([5000, 10000, 20000, 31383]); a.set_xticklabels(["5千", "1万", "2万", "3.1万"])
    a.xaxis.set_minor_formatter(plt.NullFormatter()); a.xaxis.set_minor_locator(plt.NullLocator())
    a.set_title(WL[w].replace("\n", ""), fontsize=11, loc="left")
    a.set_xlabel("検索の対象の表の数（正解以外を間引く、乱数5通りの平均）")
    a.grid(axis="y", color="#eee")
ax[0].set_ylabel("上位10件に正解が入った割合（%）")
ax[0].set_ylim(0, 105)
ax[1].legend(fontsize=9, frameon=False, loc="lower left")
fig.suptitle("ほかの表が増えるほど、日常の言葉での検索は当たりにくくなる", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig4_corpus_size.png"); plt.close(fig)

# 図5 例：同じ質問への上位3件
T = np.load(RES / "top50.npy", allow_pickle=True).item()
ex = ["real_wage", "toothbrush", "consumer_conf"]
rows = []
for need in ex:
    q = names[need]
    nd = [n for n in NEEDS if n["id"] == need][0]
    for m in ["bm25", "ruri30"]:
        for k, i in enumerate(T[f"{need}|plain|{m}"][:3]):
            ok = tab.toukei[i] == nd["toukei"] and all(pd.Series([tab.title[i]]).str.contains(pt, regex=True)[0] for pt in nd["title"])
            rows.append((q, LAB[m], k + 1, tab.toukei[i], tab.title[i], ok))
fig, ax = plt.subplots(figsize=(12, 7.6)); ax.axis("off")
yy = 1.0
cur = None
for q, m, k, tk, tt, ok in rows:
    if q != cur:
        yy -= 0.035
        ax.text(0, yy, f"質問：「{q}」", fontsize=10.5, weight="bold", transform=ax.transAxes)
        yy -= 0.045; cur = q; curm = None
    if m != curm:
        ax.text(0.01, yy, m, fontsize=9.5, color=COL["bm25" if "BM25" in m else "ruri30"], transform=ax.transAxes, weight="bold")
        curm = m
    mark = "○" if ok else "×"
    ax.text(0.22, yy, f"{k}位 {mark} {tk[:12]}｜{tt[:44]}", fontsize=8.8, transform=ax.transAxes,
            color="#1a1a1a" if ok else "#555")
    yy -= 0.04
ax.text(0, yy - 0.02, "○＝正解の表（統計名と表題の条件に合う）、×＝それ以外。表題は長いものを途中で切った", fontsize=8.5, color="#555", transform=ax.transAxes)
ax.set_title("日常の言葉で聞いたときの上位3件の例", fontsize=12, loc="left")
fig.savefig(FIG / "fig5_examples.png"); plt.close(fig)

# 図6 頑健性
rd = pd.read_csv(RES / "robust_doctext.csv")
st = pd.read_csv(RES / "stat_level.csv")
items = []
g = lambda m, w: sm[(sm.method == m) & (sm.wording == w) & (sm.metric == "hit10")]["mean"].iloc[0] * 100
items.append(("基本（30m・接頭辞あり・表題＋統計名＋分類）", g("ruri30", "plain"), BLUE))
items.append(("モデルを 70m に（2.5倍の大きさ）", g("ruri70", "plain"), PURPLE))
items.append(("接頭辞（検索クエリ:／検索文書:）なし", g("ruri30_noprefix", "plain"), "#7fa6d6"))
items.append(("文書を表題だけに", rd[(rd.doctext == "表題だけ") & (rd.method == "ruri30") & (rd.wording == "plain")].hit10.iloc[0] * 100, "#7fa6d6"))
items.append(("正解をゆるく（正しい統計の表なら可）", st[(st.method == "ruri30") & (st.wording == "plain")].hit10_stat.iloc[0] * 100, "#7fa6d6"))
items.append(("参考：BM25 基本", g("bm25", "plain"), ORANGE))
items.append(("参考：BM25 正解をゆるく", st[(st.method == "bm25") & (st.wording == "plain")].hit10_stat.iloc[0] * 100, "#e9b87f"))
fig, ax = plt.subplots(figsize=(10, 4.4))
yv = np.arange(len(items))[::-1]
ax.barh(yv, [v for _, v, _ in items], color=[c for _, _, c in items], height=0.6)
for yi, (l, v, c) in zip(yv, items):
    ax.text(v + 1, yi, f"{v:.0f}%", va="center", fontsize=9.5)
ax.set_yticks(yv); ax.set_yticklabels([l for l, _, _ in items], fontsize=9)
ax.set_xlim(0, 100); ax.set_xlabel("日常の言葉で聞いたとき、上位10件に正解が入った割合（%）")
ax.set_title("条件を変えても、文埋め込みが単語の一致を上回る（日常の言葉・44件）", fontsize=11, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig6_robustness.png"); plt.close(fig)
print("ok")
