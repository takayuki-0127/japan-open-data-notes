"""図を作る（6枚）。"""
import sys, pathlib, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, bb
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    try:
        font_manager.fontManager.addfont(f)
    except Exception:
        pass
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
SA = pd.read_csv(R / "sa_series.csv", index_col=0, parse_dates=True)
C = {"pub": "#1f4e79", "x11": "#d1495b", "seats": "#edae49", "stl13": "#00798c", "yoy": "#7a7a7a", "ma12": "#9b5de5"}

# 1. 例：鉱工業生産 2016〜2020年
fig, ax = plt.subplots(figsize=(9, 4.8))
lab = {"pub": "公表の季節調整値", "x11": "X-13（X-11法）", "stl13": "STL"}
for m in ["pub", "x11", "stl13"]:
    s = SA[f"iip|{m}"]
    w = s["2016-06":"2020-06"]
    ax.plot(w.index, w.values, color=C[m], lw=1.6, label=lab[m])
    for d, t in bb(s):
        if t == "peak" and pd.Timestamp("2017-06") <= d <= pd.Timestamp("2019-06"):
            ax.scatter([d], [s[d]], color=C[m], s=70, zorder=5, edgecolor="white")
            ax.annotate(f"{d.year}年{d.month}月", (d, s[d]), textcoords="offset points", xytext=(0, 9), ha="center", color=C[m], fontsize=10)
ax.axvline(pd.Timestamp("2018-10-01"), color="gray", ls="--", lw=1)
ax.text(pd.Timestamp("2018-10-15"), ax.get_ylim()[0] + 1, "景気の山\n（2018年10月）", color="gray", fontsize=9)
ax.set_title("鉱工業生産：季節調整の方法で「山」の月が10か月動いた（2016〜2020年）", fontsize=12)
ax.set_ylim(83, 124); ax.set_ylabel("指数（2020年＝100）"); ax.legend(loc="lower left", fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(F / "f199_example_iip2018.png", dpi=150); plt.close(fig)

# 2. 公表値と同じ月になった割合
s = pd.read_csv(R / "summary_by_method.csv")
s = s[s.method != "pub"].copy()
order = ["x11", "seats", "x11_noout", "stl7", "stl13", "stl35", "ma12", "yoy"]
s = s.set_index("method").loc[order]
fig, ax = plt.subplots(figsize=(9, 4.8))
y = np.arange(len(s))
ax.barh(y, s.within3_pub * 100, color="#cfd8e3", label="±3か月以内")
ax.barh(y, s.within1_pub * 100, color="#7fa1c3", label="±1か月以内")
ax.barh(y, s.same_as_pub * 100, color="#1f4e79", label="同じ月")
for i, (a, b, c) in enumerate(zip(s.same_as_pub, s.within1_pub, s.within3_pub)):
    ax.text(c * 100 + 1, i, f"{a*100:.0f}% / {b*100:.0f}% / {c*100:.0f}%", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(s.label); ax.invert_yaxis(); ax.set_xlim(0, 115)
ax.set_xlabel("公表の季節調整値で決めた山・谷と比べた割合（%）")
ax.set_title("同じ原数値・同じ判定ルールでも、山・谷の月が公表値と同じになるのは半分ほど", fontsize=12)
ax.legend(loc="lower right", fontsize=9); ax.grid(axis="x", alpha=0.3)
fig.tight_layout(); fig.savefig(F / "f199_agreement.png", dpi=150); plt.close(fig)

# 3. ずれの幅：季節調整4方法 vs 判定ルール5通り
mt = pd.read_csv(R / "match_to_reference.csv")
def spread(sub, by):
    p = sub.pivot_table(index=["series", "ref", "type"], columns=by, values="offset").dropna()
    return p.max(axis=1) - p.min(axis=1)
a = spread(mt[(mt.rule == "base") & mt.method.isin(["pub", "x11", "seats", "stl13"])], "method")
b = spread(mt[mt.method == "pub"], "rule")
bins = [0, 1, 2, 4, 7, 100]; labs = ["0か月", "1か月", "2〜3か月", "4〜6か月", "7か月以上"]
ca = pd.cut(a, bins=[-0.5, 0.5, 1.5, 3.5, 6.5, 100], labels=labs).value_counts(normalize=True).reindex(labs) * 100
cb = pd.cut(b, bins=[-0.5, 0.5, 1.5, 3.5, 6.5, 100], labels=labs).value_counts(normalize=True).reindex(labs) * 100
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(len(labs)); wdt = 0.38
ax.bar(x - wdt / 2, ca, wdt, color="#d1495b", label=f"季節調整の方法を4通りに変える（{len(a)}点）")
ax.bar(x + wdt / 2, cb, wdt, color="#00798c", label=f"山谷の判定ルールを5通りに変える（{len(b)}点）")
for i in range(len(labs)):
    ax.text(x[i] - wdt / 2, ca.iloc[i] + 1, f"{ca.iloc[i]:.0f}", ha="center", fontsize=9)
    ax.text(x[i] + wdt / 2, cb.iloc[i] + 1, f"{cb.iloc[i]:.0f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylabel("基準日付の数に占める割合（%）")
ax.set_xlabel("同じ景気の山・谷について、判定した月のいちばん早いものと遅いものの差")
ax.set_title("4か月以上ずれた割合は、季節調整の方法を変えたほうが大きかった", fontsize=12)
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
fig.tight_layout(); fig.savefig(F / "f199_spread.png", dpi=150); plt.close(fig)

# 4. ほぼ同じ高さの山があるとずれる
g = pd.read_csv(R / "check_near_tie.csv")
rb = json.load(open(R / "robustness.json"))
sad = np.median([v["pub_x11"] for k, v in rb["near_tie"]["sa_diff"].items() if k != "emp"])
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.axvspan(0, sad, color="#f4d6da", alpha=0.7, label=f"公表値とX-11法の季節調整値の差の中央値（約{sad:.1f}%）までの範囲")
ax.scatter(g.gap_pct.clip(upper=8), g.spread + np.random.RandomState(199).uniform(-0.15, 0.15, len(g)), color="#1f4e79", alpha=0.75)
ax.set_xlabel("公表値で、判定した山（谷）と、4か月以上離れた次に高い（低い）月との差（%、8%で打ち切り）")
ax.set_ylabel("季節調整4方法での判定月のずれの幅（か月）")
ax.set_title("大きくずれたのは、高さがほぼ同じ山（谷）がもう1つあったとき", fontsize=12)
ax.legend(fontsize=9, loc="upper right"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(F / "f199_near_tie.png", dpi=150); plt.close(fig)

# 5. データの終わりを切ると
e = pd.read_csv(R / "check_endpoint_summary.csv")
fig, ax = plt.subplots(figsize=(9, 4.8))
for m, col, lb in [("x11", C["x11"], "X-13（X-11法）"), ("stl13", C["stl13"], "STL")]:
    d = e[e.method == m]
    ax.plot(d.h, d.found * 100, color=col, ls="--", marker="o", label=f"{lb}：山・谷が見つかった")
    ax.plot(d.h, d.same_as_final * 100, color=col, marker="s", label=f"{lb}：最終的な判定と同じ月")
ax.set_xticks([6, 9, 12, 24]); ax.set_xlabel("景気の山・谷から何か月後までのデータで季節調整・判定したか")
ax.set_ylabel("割合（%）"); ax.set_ylim(0, 105)
ax.set_title("山・谷から2年たっても、4つに1つは最終的な判定と月が違った（鉱工業2系列と雇用2系列・43点）", fontsize=11)
ax.legend(fontsize=9, loc="lower right"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(F / "f199_endpoint.png", dpi=150); plt.close(fig)

# 6. 前年比で判定すると
base = mt[(mt.rule == "base") & mt.method.isin(["pub", "yoy"])]
p = base.pivot_table(index=["series", "ref", "type"], columns="method", values="offset").dropna()
d = (p.yoy - p.pub).reset_index()
fig, ax = plt.subplots(figsize=(9, 4.8))
rs = np.random.RandomState(1)
for i, t in enumerate(["peak", "trough"]):
    v = d[d.type == t][0]
    ax.scatter(v, i + rs.uniform(-0.18, 0.18, len(v)), color=["#d1495b", "#00798c"][i], alpha=0.75, s=40)
    ax.plot([v.median()] * 2, [i - 0.3, i + 0.3], color="black", lw=2)
    ax.text(v.median(), i + 0.36, f"中央値 {v.median():+.0f}か月（{len(v)}点）", ha="center", fontsize=9)
ax.axvline(0, color="gray", lw=1)
ax.set_yticks([0, 1]); ax.set_yticklabels(["山", "谷"]); ax.set_ylim(-0.6, 1.7)
ax.set_xlabel("前年比で判定した月 − 公表の季節調整値で判定した月（か月、マイナス＝前年比のほうが早い）")
ax.set_title("前年比の「山」は、水準の山より早く来た", fontsize=12); ax.grid(axis="x", alpha=0.3)
fig.tight_layout(); fig.savefig(F / "f199_yoy.png", dpi=150); plt.close(fig)
print("ok")
