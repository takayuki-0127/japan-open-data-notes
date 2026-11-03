"""04 図：figures/ に PNG を5枚書き出す。"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results"); F = os.path.join(ROOT, "figures"); os.makedirs(F, exist_ok=True)
SRC = "出典：財務省「貿易統計」（UN Comtrade 経由の米ドル建て）、IMF「World Economic Outlook」、世界銀行を加工して作成"
C1, C2, C3, CG = "#1f5fa8", "#d9822b", "#2e9e6a", "#8a8a8a"
JP = {"USA": "米国", "CHN": "中国", "KOR": "韓国", "TWN": "台湾", "HKG": "香港", "THA": "タイ", "SGP": "シンガポール", "DEU": "ドイツ",
      "VNM": "ベトナム", "AUS": "オーストラリア", "MYS": "マレーシア", "IDN": "インドネシア", "NLD": "オランダ", "GBR": "英国",
      "IND": "インド", "MEX": "メキシコ", "PHL": "フィリピン", "CAN": "カナダ", "ARE": "アラブ首長国連邦", "FRA": "フランス",
      "BEL": "ベルギー", "RUS": "ロシア", "SAU": "サウジアラビア", "PAN": "パナマ", "ITA": "イタリア", "BRA": "ブラジル", "LBR": "リベリア"}
pan = pd.read_csv(os.path.join(ROOT, "data", "panel.csv"))
o = json.load(open(os.path.join(R, "results.json"), encoding="utf-8"))

def foot(fig):
    fig.text(0.01, 0.005, SRC, fontsize=7, color=CG)

# 図1 2024年：距離と輸出額（円の大きさ＝GDP）
d = pan[(pan.cmd == "TOTAL") & (pan.year == 2024) & (pan.exports_usd > 0)].copy()
fig, ax = plt.subplots(figsize=(9, 5.4))
ax.scatter(d.dist_km, d.exports_usd / 1e9, s=np.sqrt(d.gdp_imf_bn) * 2.2, alpha=0.45, color=C1, edgecolor="white", lw=0.5)
ax.set_xscale("log"); ax.set_yscale("log")
from matplotlib.ticker import NullFormatter, FixedLocator
ax.xaxis.set_major_locator(FixedLocator([1000, 2000, 5000, 10000, 20000])); ax.set_xticklabels(["1,000", "2,000", "5,000", "10,000", "20,000"]); ax.xaxis.set_minor_formatter(NullFormatter())
for _, r in d.nlargest(10, "exports_usd").iterrows():
    ax.annotate(JP.get(r.iso3, r.iso3), (r.dist_km, r.exports_usd / 1e9), fontsize=8, xytext=(3, -11) if r.iso3 == "IND" else (3, 3), textcoords="offset points")
ax.set_xlabel("東京から相手国の首都までの距離（km、対数）"); ax.set_ylabel("日本からの輸出額（十億ドル、対数）")
ax.set_title("2024年：近い国・経済規模の大きい国ほど、輸出は多い（円の大きさ＝GDP）", fontsize=11)
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig1_distance_scatter.png"), dpi=150); plt.close(fig)

# 図2 実績 ÷ 重力モデルの予測（2015〜2024年の合計、輸出額の上位20か国）
a = pd.read_csv(os.path.join(R, "actual_vs_pred_top25.csv")).head(20).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.6, 6.2))
cols = [C2 if v > 1 else C1 for v in a.ratio]
ax.barh([JP.get(i, i) for i in a.iso3], a.ratio, color=cols)
ax.set_xscale("log"); ax.axvline(1, color="k", lw=0.8)
from matplotlib.ticker import NullFormatter, FixedLocator
ax.xaxis.set_major_locator(FixedLocator([0.25, 0.5, 1, 2, 4, 8])); ax.set_xticklabels(["0.25", "0.5", "1", "2", "4", "8"]); ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xlim(0.25, 8)
for i, v in enumerate(a.ratio):
    ax.text(v * 1.05 if v > 1 else v / 1.05, i, f"{v:.2f}", va="center", ha="left" if v > 1 else "right", fontsize=8)
ax.set_xlabel("実績 ÷ 予測（1より大きい＝経済規模と距離から見込むより多い、対数目盛）")
ax.set_title("輸出額の上位20か国：重力モデルの予測と比べた実績（2015〜2024年の合計）", fontsize=11)
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig2_actual_vs_pred.png"), dpi=150); plt.close(fig)

# 図3 品目別の距離の弾力性
c = pd.read_csv(os.path.join(R, "by_commodity.csv")).sort_values("ldist")
fig, ax = plt.subplots(figsize=(8.6, 4.8))
y = np.arange(len(c))
ax.errorbar(c.ldist, y, xerr=[c.ldist - c.ldist_lo, c.ldist_hi - c.ldist], fmt="o", color=C1, ecolor=C1, capsize=3)
for i, (_, r) in enumerate(c.iterrows()):
    if r.cmd == "TOTAL": ax.plot(r.ldist, i, "o", color=C2, ms=9)
ax.set_yticks(y); ax.set_yticklabels(c.name); ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("距離の弾力性（距離が1%長いと輸出が何%変わるか、95%区間）")
ax.set_title("品目別：鉄鋼・プラスチックは距離で大きく減り、自動車はほとんど減らない", fontsize=11)
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig3_by_commodity.png"), dpi=150); plt.close(fig)

# 図4 年ごとの距離の弾力性
yr = pd.read_csv(os.path.join(R, "by_year.csv"))
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.fill_between(yr.year, yr.dist_lo, yr.dist_hi, color=C1, alpha=0.15)
ax.plot(yr.year, yr.dist_b, color=C1, marker="o", ms=4)
ax.axhline(o["M1_pooled"]["ldist"]["b"], color=CG, ls="--", lw=1)
ax.text(2000.2, o["M1_pooled"]["ldist"]["b"] - 0.07, "全期間の推定", fontsize=8, color=CG)
ax.set_ylim(-1.6, 0); ax.set_xlabel("年"); ax.set_ylabel("距離の弾力性")
ax.set_title("距離の効き方は、25年でほとんど変わっていない（コロナの2020・21年だけ強まった）", fontsize=11)
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(os.path.join(F, "fig4_by_year.png"), dpi=150); plt.close(fig)

# 図5 頑健性
rb = pd.read_csv(os.path.join(R, "robustness.csv")).iloc[::-1]
fig, axes = plt.subplots(1, 2, figsize=(10, 5.4), sharey=True)
y = np.arange(len(rb))
for ax, v, t, col in [(axes[0], "ldist", "距離の弾力性", C1), (axes[1], "lgdp", "GDP の弾力性", C3)]:
    ax.errorbar(rb[v + "_b"], y, xerr=[rb[v + "_b"] - rb[v + "_lo"], rb[v + "_hi"] - rb[v + "_b"]], fmt="o", color=col, capsize=3)
    ax.axvline(rb[v + "_b"].iloc[-1], color=CG, ls="--", lw=1); ax.set_title(t, fontsize=11)
axes[0].set_yticks(y); axes[0].set_yticklabels(rb.name, fontsize=8)
fig.suptitle("条件を変えても、距離は輸出を減らし、GDP は増やす（OLS と地域の固定効果では大きさが動く）", fontsize=11)
foot(fig); fig.tight_layout(rect=(0, 0.02, 1, 0.95)); fig.savefig(os.path.join(F, "fig5_robustness.png"), dpi=150); plt.close(fig)
print("ok")
