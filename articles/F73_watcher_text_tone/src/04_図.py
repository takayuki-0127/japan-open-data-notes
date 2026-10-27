"""04_図：figures/ に6枚の図を書き出す"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, RAW

m = pd.read_csv(RES / "monthly_index.csv", index_col=0)
m.index = pd.to_datetime(m.index + "-01")
S = json.load(open(RES / "summary.json"))
cyc = pd.read_csv(RAW / "cycle_dates.csv")
cyc["month"] = pd.to_datetime(cyc.month + "-01")
peaks = cyc[cyc.type == "peak"].month.tolist(); troughs = cyc[cyc.type == "trough"].month.tolist()

def shade(ax):
    for p in peaks:
        t = [x for x in troughs if x > p]
        if t and t[0] > m.index.min():
            ax.axvspan(max(p, m.index.min()), t[0], color="0.88", zorder=0)

z = lambda x: (x - x.mean()) / x.std()

# 1. テキスト指数と DI
fig, ax = plt.subplots(figsize=(9, 4.2))
shade(ax)
ax.plot(m.index, z(m.raw_gen_di), color="0.35", lw=1.4, label="現状判断DI（原数値）")
ax.plot(m.index, z(m.score_gen), color="#c0392b", lw=1.4, label="コメントのテキスト指数（現状・辞書）")
ev = {"2011-03": "震災", "2014-04": "消費税8%", "2019-10": "消費税10%", "2020-04": "コロナ"}
for i, (k, v) in enumerate(ev.items()):
    t = pd.Timestamp(k + "-01"); ax.axvline(t, color="0.5", lw=0.7, ls="--")
    ax.text(t, 2.55 - 0.35 * (i % 2), v, ha="center", fontsize=8, color="0.25", bbox=dict(fc="white", ec="none", pad=1))
ax.set_ylabel("平均0・標準偏差1にそろえた値"); ax.set_ylim(-6, 2.9); ax.legend(loc="lower right", fontsize=9)
ax.set_title(f"景気ウォッチャーのコメントの語り口とDI（2010年1月〜2026年9月、相関{S['base']['corr_text_di_gen']:.2f}）\n灰色は景気後退期", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f73_index.png"); plt.close(fig)

# 2. 判断の記号ごとのテキストスコア
order = ["◎", "○", "□", "▲", "×"]
fig, ax = plt.subplots(figsize=(7.5, 4))
w = 0.38
for i, (k, lab, col) in enumerate([("gen", "現状", "#c0392b"), ("saki", "先行き", "#2e86c1")]):
    v = [S["comment_level"][k]["mean_by_mark"][o] for o in order]
    ax.bar(np.arange(5) + (i - 0.5) * w, v, w, label=lab, color=col)
ax.axhline(0, color="0.3", lw=0.8)
ax.set_xticks(range(5)); ax.set_xticklabels(["◎ 良く\nなっている", "○ やや良く", "□ 変わらない", "▲ やや悪く", "× 悪く\nなっている"])
ax.set_ylabel("テキストスコアの平均（−1〜+1）")
a = S["comment_level"]["gen"]["auc_pos_vs_neg"]
ax.set_title(f"回答者が付けた記号ごとの、コメントの語り口\n（良い側◎○と悪い側▲×をテキストで見分けるAUC：現状{a:.2f}）", fontsize=11)
ax.legend(); fig.tight_layout(); fig.savefig(FIG / "f73_by_mark.png"); plt.close(fig)

# 3. 相互相関
fig, ax = plt.subplots(figsize=(7.5, 4))
for key, lab, col in [("xcorr_di_ci3", "現状判断DI", "0.35"), ("xcorr_text_ci3", "テキスト指数（現状）", "#c0392b"), ("xcorr_saki_ci3", "テキスト指数（先行き）", "#2e86c1")]:
    d = S["base"][key]; L = sorted(int(k) for k in d)
    ax.plot(L, [d[str(l)] for l in L], marker="o", color=col, label=lab)
ax.axvline(0, color="0.6", lw=0.8); ax.axhline(0, color="0.6", lw=0.8)
ax.set_xlabel("ずれ（か月）：プラスは、ウォッチャー側が景気動向指数より先に動く")
ax.set_ylabel("CI一致指数の3か月前比との相関")
ax.set_title("景気動向指数とのずれ：どれも1か月先行が最大で、テキストはDIより弱い", fontsize=11)
ax.legend(fontsize=9); fig.tight_layout(); fig.savefig(FIG / "f73_xcorr.png"); plt.close(fig)

# 4. 話題の語
t = pd.read_csv(RES / "topic_share.csv", index_col=0); t.index = pd.to_datetime(t.index + "-01")
fig, ax = plt.subplots(figsize=(9, 4.2))
cols = {"物価・値上げ": "#c0392b", "インバウンド": "#16a085", "人手不足": "#8e44ad", "コロナ": "0.3", "天候": "#2e86c1", "消費税": "#d68910"}
for k, c in cols.items():
    ax.plot(t.index, t[k].rolling(3, min_periods=1).mean(), color=c, lw=1.3, label=k)
ax.set_ylabel("コメントのうち語が出てくる割合（%、3か月平均）")
ax.set_title("現状のコメントに出てくる話題の割合", fontsize=11); ax.legend(ncol=3, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f73_topics.png"); plt.close(fig)

# 5. 記号では表せない語り口と、翌月のDIの変化
d = pd.DataFrame({"resid": m.tone_resid, "ddi": m.raw_gen_di.shift(-1) - m.raw_gen_di}).dropna()
r = S["base"]["resid_to_next_di"]
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.scatter(d.resid, d.ddi, s=12, color="#c0392b", alpha=0.6)
ax.axhline(0, color="0.6", lw=0.8); ax.axvline(0, color="0.6", lw=0.8)
ax.set_xlabel("記号では表せない語り口（テキスト指数を記号の平均で回帰した残差）")
ax.set_ylabel("翌月の現状判断DIの変化（ポイント）")
ax.set_title(f"語り口の「上乗せ」は翌月のDIを当てない\n（今月のDIをそろえた係数 {r['coef']:.1f}、95%区間 {r['lo']:.1f}〜{r['hi']:.1f}）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f73_resid.png"); plt.close(fig)

# 6. 頑健性
rb = pd.read_csv(RES / "robustness.csv")
rb = rb[rb["テキストとDIの相関"].notna()]
fig, ax = plt.subplots(figsize=(8, 4.6))
y = np.arange(len(rb))
ax.barh(y - 0.2, rb["テキストとDIの相関"], 0.4, color="#c0392b", label="水準の相関")
ax.barh(y + 0.2, rb["変化どうしの相関"], 0.4, color="#f1948a", label="前月からの変化の相関")
ax.set_yticks(y); ax.set_yticklabels(rb["設定"], fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 1.3); ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_xlabel("テキスト指数と現状判断DIの相関"); ax.legend(fontsize=9, loc="lower right")
ax.set_title("設定を変えても、テキスト指数はDIとよく合う（雇用だけは弱い）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f73_robust.png"); plt.close(fig)
print("ok")
