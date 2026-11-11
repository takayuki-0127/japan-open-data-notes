"""04 図：6枚。"""
import json, sys, pathlib, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f279_common import *
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "svg.hashsalt": "f279", "figure.dpi": 110})
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
H = json.load(open(R / "main.json")); A = pd.read_csv(R / "A_snapshots.csv"); B = pd.read_csv(R / "B_segments.csv", index_col=0)
C = pd.read_csv(R / "C_transition.csv", index_col=0); D = pd.read_csv(R / "D_h4_stability.csv", index_col=0)
E = pd.read_csv(R / "E_reask_lift.csv"); Fj = json.load(open(R / "F_reask.json"))
lab = [f"{JA[s]}\n({s})" for s in SEGS]; lab1 = [JA[s] for s in SEGS]
md = {"metadata": {"Software": None}}
def save(fig, name):
    fig.tight_layout(); fig.savefig(F / name, **{"metadata": {"Software": None}}); plt.close(fig)

# 図1 区分の大きさと、次の6か月にもう一度買った割合
fig, ax = plt.subplots(1, 2, figsize=(11, 5))
y = np.arange(len(SEGS))[::-1]
ax[0].barh(y, B["share"] * 100, color="#8aa4c8"); ax[0].set_yticks(y, lab1); ax[0].set_xlabel("7時点の対象顧客に占める割合（%）")
for yi, v in zip(y, B["share"] * 100): ax[0].text(v + 0.3, yi, f"{v:.0f}%", va="center", fontsize=9)
ax[1].barh(y, B["rebuy"] * 100, color="#d98b4a"); ax[1].set_yticks(y, [""] * len(y)); ax[1].set_xlabel("次の6か月にもう一度買った割合（%）")
for yi, v, fmean in zip(y, B["rebuy"] * 100, B["fut_mean"]): ax[1].text(v + 1, yi, f"{v:.0f}%（平均{fmean:,.0f}£）", va="center", fontsize=9)
ax[1].set_xlim(0, 115); fig.suptitle("RFM の10区分：大きさと、次の6か月の動き（2010年12月〜2011年6月の7時点の合計）")
save(fig, "f279_1_segments.png")

# 図2 R の点ともう一度買う割合
fig, ax = plt.subplots(figsize=(8, 5))
cm = plt.cm.viridis(np.linspace(0, 0.85, len(A)))
for (i, r), c in zip(A.iterrows(), cm):
    v = json.loads(r["rebuy_by_r"]) if isinstance(r["rebuy_by_r"], str) else r["rebuy_by_r"]
    ax.plot(range(1, 6), np.array(v) * 100, marker="o", color=c, label=r["t"][:7])
ax.set_xticks(range(1, 6), ["1\n（最も前）", "2", "3", "4", "5\n（最も最近）"]); ax.set_xlabel("R の点（最後に買った日が近いほど高い）")
ax.set_ylabel("次の6か月にもう一度買った割合（%）"); ax.legend(title="時点", fontsize=9); ax.set_ylim(0, 100)
ax.set_title("最後に買った日が近い顧客ほど、また買う（7時点すべてで右上がり）")
save(fig, "f279_2_recency.png")

# 図3 遷移
M = C.copy(); M.columns = [JA.get(c, c) for c in M.columns]
fig, ax = plt.subplots(figsize=(11, 6.2))
im = ax.imshow(M.values * 100, cmap="Blues", vmin=0, vmax=70, aspect="auto")
ax.set_xticks(range(M.shape[1]), M.columns, rotation=45, ha="right"); ax.set_yticks(range(len(SEGS)), lab1)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M.values[i, j] * 100
        if v >= 1: ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 40 else "black")
ax.set_xlabel("6か月後の区分（離脱＝過去12か月に1回も買っていない）"); ax.set_ylabel("時点 t の区分")
fig.colorbar(im, ax=ax, label="行の中の割合（%）")
ax.set_title("6か月後にどの区分にいるか（7時点の合計）")
save(fig, "f279_3_transition.png")

# 図4 捕捉率
fig, ax = plt.subplots(figsize=(8, 5))
x = np.arange(len(A))
ax.plot(x, A["capA"] * 100, marker="o", label="A：過去12か月の購入額で上位20%")
ax.plot(x, A["capB"] * 100, marker="s", label="B：RFM の合計点で上位20%")
c = H["methodC_2011_06"]["C"] * 100
ax.scatter([len(A) - 1], [c], marker="^", s=80, color="#c0504d", zorder=5, label="C：区分の平均（2010年12月の結果で学ぶ）")
ax.set_xticks(x, [t[:7] for t in A["t"]], rotation=30); ax.set_ylim(60, 80)
ax.set_ylabel("次の6か月の売上のうち、選んだ20%が占める割合（%）"); ax.legend(fontsize=9, loc="lower left")
ax.set_title("次の6か月の売上を当てる力：購入額だけのほうが少し高い")
save(fig, "f279_4_capture.png")

# 図5 区分ごとの割合 2010-12 と 2011-06
fig, ax = plt.subplots(figsize=(8.5, 5.5))
y = np.arange(len(SEGS))[::-1]
for yi, s in zip(y, SEGS):
    a, b = D.loc[s, "r_2010_12"] * 100, D.loc[s, "r_2011_06"] * 100
    col = "#4a7ab5" if abs(b - a) <= 10 else "#c0504d"
    ax.plot([a, b], [yi, yi], color=col, lw=2); ax.scatter([a], [yi], color="#999", zorder=3); ax.scatter([b], [yi], color=col, zorder=3)
    ax.text(max(a, b) + 1.5, yi, f"{b - a:+.1f}pt", va="center", fontsize=9, color=col)
ax.set_yticks(y, lab1); ax.set_xlim(10, 100); ax.set_xlabel("次の6か月にもう一度買った割合（%）  灰：2010年12月時点 → 色：2011年6月時点")
ax.set_title("区分ごとの割合は時点で動いた（±10pt を超えたのは赤の4区分）")
save(fig, "f279_5_stability.png")

# 図6 問い直し：全体に対する倍率
P = E.pivot(index="seg", columns="t", values="lift").reindex(SEGS)
fig, ax = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1.3, 1]})
y = np.arange(len(SEGS))[::-1]
f0, f1 = P.columns[0], P.columns[-1]
for yi, s in zip(y, SEGS):
    a, b = P.loc[s, f0], P.loc[s, f1]
    ax[0].plot([a, b], [yi, yi], color="#4a7ab5", lw=2); ax[0].scatter([a], [yi], color="#999", zorder=3); ax[0].scatter([b], [yi], color="#4a7ab5", zorder=3)
ax[0].axvline(1, color="#888", ls=":"); ax[0].set_yticks(y, lab1); ax[0].set_xlabel("全体の割合に対する倍率  灰：2010年12月 → 青：2011年6月")
ov = pd.Series(Fj["overall_rate"]) * 100
ax[1].plot(range(len(ov)), ov.values, marker="o", color="#d98b4a"); ax[1].set_xticks(range(len(ov)), [t[:7] for t in ov.index], rotation=30)
ax[1].set_ylabel("全体のもう一度買った割合（%）"); ax[1].set_ylim(40, 62)
fig.suptitle("もう一度問う：全体の割合は上がったが、区分の倍率と順番はおおむね保たれた")
save(fig, "f279_6_reask_lift.png")
print("ok", sorted(p.name for p in F.iterdir()))
