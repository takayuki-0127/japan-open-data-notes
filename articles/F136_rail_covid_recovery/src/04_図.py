"""04 図：figures/ に PNG を5枚書き出す。"""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "axes.spines.top": False, "axes.spines.right": False})
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results"); F = os.path.join(ROOT, "figures"); os.makedirs(F, exist_ok=True)
SRC = "出典：国土交通省「鉄道輸送統計調査」（e-Stat、月次 表2-2）を加工して作成"
C1, C2, C3, CG = "#1f5fa8", "#d9822b", "#2e9e6a", "#8a8a8a"
P = pd.read_csv(os.path.join(R, "recovery_paths.csv"), parse_dates=["date"])
S = pd.read_csv(os.path.join(R, "recovery_summary.csv")).set_index("series")
RB = pd.read_csv(os.path.join(R, "robustness.csv")).set_index("series")
def foot(fig): fig.text(0.01, 0.005, SRC, fontsize=7, color=CG)
def g(name): return P[P.series == name].set_index("date")

# 図1 全国の旅客数：実績と「コロナがなければ」
x = g("全国（計）")
fig, ax = plt.subplots(figsize=(9, 4.8))
r12 = x["actual"].rolling(12).sum() / 1e6; c12 = x["cf"].rolling(12).sum() / 1e6
ax.plot(x.index, x["actual"] / 1e3, color=C1, lw=0.8, alpha=0.35)
ax.plot(x.index, x["actual"].rolling(12).mean() / 1e3, color=C1, lw=2.2, label="実績（12か月移動平均）")
cf = x[x.index >= "2020-02-01"]
ax.plot(cf.index, x["cf"].rolling(12).mean()[x.index >= "2020-02-01"] / 1e3, color=C2, lw=2, ls="--", label="コロナ前の傾向が続いた場合（2015〜2020年1月から推定）")
m19 = x[x.index.year == 2019]["actual"].mean() / 1e3
ax.axhline(m19, color=CG, lw=1, ls=":"); ax.text(x.index[2], m19 + 15, "2019年の月平均", color=CG, fontsize=9)
ax.axvspan(pd.Timestamp("2015-01-01"), pd.Timestamp("2020-01-31"), color="#eeeeee", zorder=0)
ax.text(pd.Timestamp("2016-01-01"), 1150, "推定に使った期間", color=CG, fontsize=9)
ax.set_ylabel("旅客数（百万人／月）"); ax.set_ylim(1000, 2450); ax.legend(loc="lower left", fontsize=9, frameon=False)
ax.set_title("全国の鉄道旅客数：直近1年は2019年の95%、コロナ前の傾向と比べると86%", fontsize=12, loc="left")
fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig); fig.savefig(os.path.join(F, "fig1_national_actual_vs_cf.png"), dpi=150); plt.close()

# 図2 回復率の推移：定期と定期外
fig, ax = plt.subplots(figsize=(9, 4.8))
for nm, c, lab in [("全国（定期外）", C2, "定期外"), ("全国（計）", C1, "計"), ("全国（定期）", C3, "定期")]:
    y = g(nm); y = y[y.index >= "2019-01-01"]
    rec = (y["actual"].rolling(3).sum() / y["cf"].rolling(3).sum()) * 100
    ax.plot(y.index, rec, color=c, lw=2, label=lab)
    ax.text(y.index[-1] + pd.DateOffset(days=20), rec.iloc[-1], f"{lab} {rec.iloc[-1]:.0f}%", color=c, fontsize=9, va="center")
ax.axhline(100, color=CG, lw=1); ax.axhline(90, color=CG, lw=0.7, ls=":")
ax.set_ylabel("回復率（実績÷コロナ前の傾向、%、3か月合計）"); ax.set_ylim(20, 110)
ax.set_xlim(pd.Timestamp("2019-01-01"), pd.Timestamp("2027-03-01"))
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.set_title("定期外は9割台まで戻ったが、定期は8割で伸びがゆるい", fontsize=12, loc="left")
fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig); fig.savefig(os.path.join(F, "fig2_recovery_teiki_vs_teikigai.png"), dpi=150); plt.close()

# 図3 業態別：定期と定期外の回復率（直近12か月）
segs = ["JR在来線", "新幹線", "大手民鉄", "中小・公営"]
fig, ax = plt.subplots(figsize=(9, 4.6))
w = 0.36; xs = np.arange(len(segs))
for i, (suf, c, lab) in enumerate([("（定期）", C3, "定期"), ("（定期外）", C2, "定期外")]):
    v = [S.loc[s + suf, "rec_last12"] * 100 for s in segs]
    lo = [S.loc[s + suf, "rec_last12_lo"] * 100 for s in segs]; hi = [S.loc[s + suf, "rec_last12_hi"] * 100 for s in segs]
    b = ax.bar(xs + (i - 0.5) * w, v, w, color=c, label=lab, yerr=[np.array(v) - lo, np.array(hi) - v], capsize=3, ecolor="#555")
    for xx, vv in zip(xs + (i - 0.5) * w, v): ax.text(xx, 40, f"{vv:.0f}", ha="center", color="white", fontsize=10)
v19 = [S.loc[s, "vs2019_last12"] * 100 for s in segs]
ax.scatter(xs, v19, marker="D", color="k", zorder=5, label="計（2019年の同じ月と比べた値）")
ax.axhline(100, color=CG, lw=1); ax.set_xticks(xs, segs); ax.set_ylim(30, 120)
ax.set_ylabel("回復率（%、直近12か月）"); ax.legend(fontsize=9, frameon=False, loc="upper left", ncol=3)
ax.set_title("新幹線以外の3業態では、定期の戻りが定期外より10ポイント以上遅い", fontsize=12, loc="left")
fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig); fig.savefig(os.path.join(F, "fig3_segments.png"), dpi=150); plt.close()

# 図4 運輸局別（地理の順に並べる。順位づけはしない）
REG = ["北海道", "東北", "関東", "北陸信越", "中部", "近畿", "中国", "四国", "九州"]
fig, ax = plt.subplots(figsize=(9, 4.6))
xs = np.arange(len(REG))
for suf, c, lab, mk in [("（定期）", C3, "定期", "o"), ("（定期外）", C2, "定期外", "s")]:
    v = np.array([S.loc[r + suf, "rec_last12"] * 100 for r in REG])
    lo = np.array([S.loc[r + suf, "rec_last12_lo"] * 100 for r in REG]); hi = np.array([S.loc[r + suf, "rec_last12_hi"] * 100 for r in REG])
    off = -0.12 if suf == "（定期）" else 0.12
    ax.errorbar(xs + off, v, yerr=[v - lo, hi - v], fmt=mk, color=c, label=lab, capsize=3, ms=7)
ax.axhline(100, color=CG, lw=1); ax.set_xticks(xs, REG); ax.set_ylim(60, 120)
ax.set_ylabel("回復率（%、直近12か月、95%予測区間）"); ax.legend(fontsize=9, frameon=False, loc="upper right")
ax.set_title("9つの地方区分のうち7つで、定期の戻りが定期外より低い（東北・四国は逆）", fontsize=12, loc="left")
fig.text(0.01, 0.035, "沖縄は2019年10月のモノレール延伸で前の傾向が大きく（年6%）、比べにくいため図から外した", fontsize=7.5, color=CG)
fig.tight_layout(rect=(0, 0.05, 1, 1)); foot(fig); fig.savefig(os.path.join(F, "fig4_regions.png"), dpi=150); plt.close()

# 図5 頑健性：基準の取り方で回復率がどれだけ動くか
cols = ["主（2015-01〜2020-01, 傾向あり, 1日あたり）", "基準 2017-04〜2020-01（傾向あり）", "基準 2014-01〜2020-01（傾向あり）",
        "1日あたりにしない", "基準 2018-04〜2019-12（傾向なし）", "基準 2015-01〜2020-01（傾向なし＝平均）"]
labs = ["主：2015〜20年1月\n傾向あり", "2017年4月〜\n傾向あり", "2014年〜\n傾向あり", "月の日数で\n割らない", "2018年4月〜19年\n傾向なし", "2015〜20年1月\n傾向なし（平均）"]
fig, ax = plt.subplots(figsize=(9, 4.8)); xs = np.arange(len(cols)); w = 0.26
for i, (nm, c, lab) in enumerate([("全国（定期）", C3, "定期"), ("全国（計）", C1, "計"), ("全国（定期外）", C2, "定期外")]):
    v = [RB.loc[nm, cc] * 100 for cc in cols]
    ax.bar(xs + (i - 1) * w, v, w, color=c, label=lab)
    for xx, vv in zip(xs + (i - 1) * w, v): ax.text(xx, vv + 0.8, f"{vv:.0f}", ha="center", fontsize=8)
ax.axhline(100, color=CG, lw=1); ax.set_ylim(70, 110); ax.set_xticks(xs, labs, fontsize=8.5)
ax.set_ylabel("回復率（%、直近12か月）"); ax.legend(fontsize=9, frameon=False, loc="upper left", ncol=3)
ax.set_title("「傾向を延ばすか」で水準は約10ポイント動くが、定期＜定期外の順は変わらない", fontsize=12, loc="left")
fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig); fig.savefig(os.path.join(F, "fig5_robustness.png"), dpi=150); plt.close()
print("ok")
