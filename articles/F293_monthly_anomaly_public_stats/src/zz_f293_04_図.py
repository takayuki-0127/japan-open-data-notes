"""F293 04 図（6枚）。"""
import importlib.util, json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a", BASE / "src" / "zz_f293_03_分析.py")
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
R, F = BASE / "results", BASE / "figures"
F.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 150})
SRCN = {"S1": "商業動態統計（6業態）", "S2": "消費者物価（537品目）", "S3": "家計調査（11品目）"}
COL = {"S1": "#2b6cb0", "S2": "#2f855a", "S3": "#c05621"}
df = pd.read_csv(BASE / "data" / "series_long.csv")
clean = pd.read_csv(R / "B_clean_flags.csv.gz")
A = pd.read_csv(R / "A_detection.csv")
main = json.load(open(R / "main.json"))
reask = json.load(open(R / "D_reask.json"))
to_dt = lambda ym: pd.to_datetime([f"{v//100}-{v%100:02d}-01" for v in ym])

# 図1 例：百貨店（S1）と新聞代（S2）
fig, axes = plt.subplots(2, 1, figsize=(10, 7))
for ax, (src, sid, unit) in zip(axes, [("S1", "百貨店", "販売額（百万円）"),
                                        ("S2", [s for s in df[df.src == "S2"].sid.unique() if s.startswith("新聞代（全国紙）")][0], "物価指数（2020年=100）")]):
    g = df[(df.src == src) & (df.sid == sid)]
    ax.plot(to_dt(g.ym), g.x, color="#444", lw=1.2)
    ev = sorted(a.event_months(src, sid))
    for m in ev:
        d = pd.Timestamp(f"{m//100}-{m%100:02d}-01")
        ax.axvspan(d, d + pd.offsets.MonthEnd(1), color="#f6e05e", alpha=0.35, lw=0)
    c = clean[(clean.src == src) & (clean.sid == sid) & clean.M2]
    gg = g.set_index("ym").x
    ax.scatter(to_dt(c.ym), gg.loc[c.ym], color="#e53e3e", zorder=3, s=30, label="M2 が鳴った月")
    ax.set_title(f"{SRCN[src].split('（')[0]}：{sid.split('|')[0]}（黄色＝事前に書き出した出来事の月）", fontsize=11, loc="left")
    ax.set_ylabel(unit); ax.legend(loc="upper left", fontsize=9, frameon=False)
fig.tight_layout(); fig.savefig(F / "fig1_examples.png"); plt.close(fig)

# 図2 汚れの種類ごとの見つかる割合（R(停止なし)∪M2）
order = ["E1", "E2", "E3", "E4", "E6", "E8", "E7", "E9", "E5"]
fig, ax = plt.subplots(figsize=(10, 5))
w = 0.27
for i, src in enumerate(["S1", "S2", "S3"]):
    v = A[A.src == src].set_index("err").loc[order, "R(停止なし)∪M2"] * 100
    ax.bar(np.arange(len(order)) + (i - 1) * w, v, w, color=COL[src], label=SRCN[src])
ax.set_xticks(np.arange(len(order)), [a.ERRNAME[e] for e in order], fontsize=10)
ax.set_ylabel("見つかった割合（%）"); ax.set_ylim(0, 105)
ax.set_title("入れた汚れが見つかった割合（0以下のルール＋M2、z>4）", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig(F / "fig2_detection.png"); plt.close(fig)

# 図3 汚れのない月の誤報（系列×年あたり）
fa = pd.read_csv(R / "B_false_alarm_per_series_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9, 4.5))
ms = [("R_stale", "前月と同じ値"), ("M1", "前年同月比±20%"), ("M2", "M2（季節＋傾き、z>4）"), ("M3", "M3（前月比の季節差）")]
for i, src in enumerate(["S1", "S2", "S3"]):
    ax.bar(np.arange(len(ms)) + (i - 1) * w, [fa.loc[src, m] for m, _ in ms], w, color=COL[src], label=SRCN[src])
ax.set_xticks(np.arange(len(ms)), [n for _, n in ms])
ax.set_ylabel("1系列・1年あたりに鳴った回数")
ax.set_title("汚れを入れていない本物の数字で、チェックが鳴った回数", loc="left")
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(F / "fig3_false_alarms.png"); plt.close(fig)

# 図4 系列の揺れの大きさ（M2 の外れの MAD、中央値）
sc = []
for (src, sid), g in df.groupby(["src", "sid"]):
    P = a.parts(g.sort_values("ym").x.to_numpy(float))
    sc.append((src, np.nanmedian(P["sc2"])))
sc = pd.DataFrame(sc, columns=["src", "scale"])
fig, ax = plt.subplots(figsize=(9, 4.5))
data = [sc[sc.src == s].scale * 100 for s in ["S1", "S2", "S3"]]
ax.boxplot(data, orientation="horizontal", tick_labels=[SRCN[s] for s in ["S1", "S2", "S3"]], showfliers=False)
for x_, lab, yy in [(5, "+5% の汚れ", 2.5), (15, "15% の汚れ", 1.5)]:
    ax.axvline(x_ / 4, color="#e53e3e", ls="--", lw=1)
    ax.text(x_ / 4 * 1.05, yy, f"{lab}が\nz=4 になる揺れ\n（これより右は届かない）", color="#e53e3e", fontsize=8, ha="left", va="center")
ax.set_xscale("log"); ax.set_xlabel("ふだんの揺れの大きさ（M2 の外れの MAD×1.4826、%、対数目盛り）")
ax.set_title("統計によって、ふだんの揺れの大きさがこれだけ違う", loc="left")
fig.tight_layout(); fig.savefig(F / "fig4_noise_scale.png"); plt.close(fig)
sc.groupby("src").scale.median().to_csv(R / "E_noise_scale_median.csv", float_format="%.5f")

# 図5 鳴った月のうち出来事の月の割合（統計別）と、コロナの期間
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
h4 = main["H4_by_src"]
ax = axes[0]
ax.bar([SRCN[s].split("（")[0] for s in ["S1", "S2", "S3"]], [h4[s]["share"] * 100 for s in ["S1", "S2", "S3"]],
       color=[COL[s] for s in ["S1", "S2", "S3"]])
for i, s in enumerate(["S1", "S2", "S3"]):
    ax.text(i, h4[s]["share"] * 100 + 2, f"{h4[s]['share']*100:.0f}%\n（{h4[s]['n']}回中）", ha="center", fontsize=9)
ax.axhline(50, color="#999", ls=":"); ax.set_ylim(0, 110); ax.set_ylabel("%")
ax.set_title("M2 が鳴った月のうち、出来事の月の割合", loc="left", fontsize=11)
ax = axes[1]
r = clean.groupby(["src", "covid"]).M2.mean().unstack() * 12
xx = np.arange(3)
ax.bar(xx - 0.2, r.loc[["S1", "S2", "S3"], False], 0.4, color="#a0aec0", label="コロナの期間以外")
ax.bar(xx + 0.2, r.loc[["S1", "S2", "S3"], True], 0.4, color="#805ad5", label="2020年3月〜21年9月")
ax.set_xticks(xx, [SRCN[s].split("（")[0] for s in ["S1", "S2", "S3"]])
ax.set_ylabel("1系列・1年あたりの回数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("コロナの期間に鳴った回数", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig5_events_covid.png"); plt.close(fig)

# 図6 問い直し：CPI の品目の「動かなさ」と誤報、年ごとの出来事以外の鳴り
q = pd.read_csv(R / "D_reask_by_stale.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
ax = axes[0]
ax.bar(range(5), q["出来事以外_年"], color="#2f855a")
ax.set_xticks(range(5), [f"{l}\n（{v*100:.0f}%）" for l, v in zip(["よく動く", "2", "3", "4", "ほとんど\n動かない"], q["前月と同じ値の割合"])], fontsize=9)
ax.set_ylabel("出来事以外で鳴った回数（1品目・1年）")
ax.set_title("CPI の品目を「前月と同じ値」の多さで5つに分ける", loc="left", fontsize=11)
ax = axes[1]
br = reask["全部の鳴りの内訳"]
labs = ["はじめの1回", "続き", "1年後の折り返し"]
vals = [br[k] * 100 for k in labs]
ax.bar(range(3), vals, color=["#2f855a", "#9ae6b4", "#c6f6d5"], edgecolor="#2f855a")
for i, v in enumerate(vals):
    ax.text(i, v + 1.5, f"{v:.0f}%", ha="center")
ax.set_xticks(range(3), ["はじめの1回", "続き\n（直前2か月にも鳴った）", "1年後の折り返し\n（10〜14か月前に鳴った）"], fontsize=9)
ax.set_ylabel("CPI で M2 が鳴った回数に占める割合（%）"); ax.set_ylim(0, 70)
ax.set_title("1つの段差が、何回の鳴りになるか", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig6_reask.png"); plt.close(fig)
print("ok")
