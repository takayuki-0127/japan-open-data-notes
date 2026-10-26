"""04 図"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, RES, FIG, COLORS, MODEL_NAMES

FIG.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "hourly_tokyo.csv", index_col="ts", parse_dates=True)
P = pd.read_csv(RES / "predictions.csv.gz", index_col=0, parse_dates=True)
M = pd.read_csv(RES / "metrics.csv")
cat = pd.read_csv(RES / "error_by_category.csv", index_col=0)
imp = pd.read_csv(RES / "shap_importance.csv", index_col=0)
R = pd.read_csv(RES / "robustness.csv")
N = pd.read_csv(RES / "robustness_temp_noise.csv")

# 1. 需要と気温（U字）
day = d.resample("D").agg({"demand": "mean", "temp_mean": "first", "holiday": "first"})
day["dow"] = day.index.dayofweek
wk = day[(day.dow < 5) & (day.holiday == 0)]
fig, ax = plt.subplots(figsize=(8.6, 5))
for (a, b), col in zip([(2016, 2019), (2020, 2022), (2023, 2026)], ["#9aa0a6", "#1a73e8", "#e37400"]):
    s = wk[(wk.index.year >= a) & (wk.index.year <= b)]
    ax.scatter(s.temp_mean, s.demand / 1000, s=5, alpha=.45, color=col, label=f"{a}〜{b}年")
ax.set_xlabel("東京の日平均気温（℃）")
ax.set_ylabel("東京エリアの需要の日平均（GW）")
ax.set_title("気温と電力需要：16〜18℃でいちばん少なく、暑くても寒くても増える（平日）")
ax.legend(frameon=False, markerscale=4)
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a22_temp_u.png"); plt.close()

# 2. 予測と実績（夏と冬の1週間）
fig, axes = plt.subplots(2, 1, figsize=(10, 6.6), sharey=False)
for ax, (s, e, t) in zip(axes, [("2026-07-20", "2026-07-26 23:00", "2026年7月20日〜26日（夏）"),
                                 ("2026-01-19", "2026-01-25 23:00", "2026年1月19日〜25日（冬）")]):
    p = P.loc[s:e]
    ax.plot(p.index, p.actual / 1000, color="black", lw=2.2, label="実績")
    for c in ("naive_week", "ridge", "lgbm"):
        ax.plot(p.index, p[c] / 1000, lw=1.3, color=COLORS[MODEL_NAMES[c]], label=MODEL_NAMES[c], alpha=.9)
    ax.set_title(t, fontsize=11)
    ax.set_ylabel("需要（GW）")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.grid(alpha=.3)
h, l = axes[0].get_legend_handles_labels()
fig.suptitle("前日の夜に出した翌日24時間の予測と実績（東京エリア）")
fig.legend(h, l, ncol=4, fontsize=9, frameon=False, loc="lower center")
fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(FIG / "a22_week.png"); plt.close()

# 3. モデル別の MAPE（全期間）と年度ごと
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.4]})
allp = M[M["期間"].str.startswith("全期間")].set_index("model")
order = ["naive_week", "naive_day", "ridge", "lgbm"]
names = [MODEL_NAMES[o] for o in order]
ax = axes[0]
x = np.arange(len(order))
ax.bar(x - .2, allp.loc[order, "MAPE(%)"], .4, color=[COLORS[n] for n in names], label="1時間ごと")
ax.bar(x + .2, allp.loc[order, "ピークのMAPE(%)"], .4, color=[COLORS[n] for n in names], alpha=.45, hatch="//", label="1日のピーク")
for i, o in enumerate(order):
    ax.text(i - .2, allp.loc[o, "MAPE(%)"] + .15, f"{allp.loc[o, 'MAPE(%)']:.1f}", ha="center", fontsize=9)
    ax.text(i + .2, allp.loc[o, "ピークのMAPE(%)"] + .15, f"{allp.loc[o, 'ピークのMAPE(%)']:.1f}", ha="center", fontsize=9)
ax.set_xticks(x, [n.replace("の同じ時刻", "\nの同じ時刻").replace("（Ridge）", "\n（Ridge）") for n in names], fontsize=9)
ax.set_ylabel("平均絶対誤差率 MAPE（%）")
ax.set_title("2020年4月〜2026年9月の全体", fontsize=11)
ax.legend(frameon=False, fontsize=9)
ax = axes[1]
fold = M[M["期間"].str.contains("年度")].copy()
fold = fold[~fold["期間"].str.contains("除く")]
fl = fold["期間"].unique()
for o in order:
    v = fold[fold.model == o].set_index("期間").loc[fl, "MAPE(%)"]
    ax.plot(range(len(fl)), v.values, marker="o", color=COLORS[MODEL_NAMES[o]], label=MODEL_NAMES[o])
ax.set_xticks(range(len(fl)), [f.replace("年度上期", "年度\n上期") for f in fl], fontsize=9)
ax.set_ylim(0, None)
ax.set_title("年度ごと（その年度より前のデータだけで学習）", fontsize=11)
ax.grid(alpha=.3)
ax.legend(frameon=False, fontsize=8, ncol=2)
fig.tight_layout(); fig.savefig(FIG / "a22_mape.png"); plt.close()

# 4. 外れた日の分類
c = cat.copy()
c = c.loc[["お盆の時期（8/10〜8/20）", "前日から日平均気温が5℃以上変化", "年末年始（12/26〜1/5）", "大型連休（4/27〜5/7）",
           "祝日とその前後1日", "猛暑（最高33℃以上）", "大雨（日降水量30mm以上）", "その他の日"]]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
y = np.arange(len(c))[::-1]
axes[0].barh(y + .18, c["全体での割合(%)"], .36, color="#9aa0a6", label="評価した全日数での割合")
axes[0].barh(y - .18, c["外れた100日での割合(%)"], .36, color="#d93025", label="誤差の大きい100日での割合")
axes[0].set_yticks(y, c.index, fontsize=9)
axes[0].set_xlabel("%")
axes[0].legend(frameon=False, fontsize=9, loc="center right")
axes[0].set_title("誤差の大きい100日は、どんな日か", fontsize=11)
axes[1].barh(y, c["平均MAPE"], color="#188038")
for yy, v in zip(y, c["平均MAPE"]):
    axes[1].text(v + .05, yy, f"{v:.1f}%", va="center", fontsize=9)
axes[1].set_xlabel("その種類の日の平均 MAPE（%、LightGBM）")
axes[1].set_title("種類ごとの誤差", fontsize=11)
for ax in axes: ax.grid(axis="x", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a22_worst.png"); plt.close()

# 5. SHAP
JP = {"lag24": "24時間前の需要", "hour": "時刻", "lag168": "1週間前の需要", "daytype": "平日・土曜・日祝",
      "temp_max": "最高気温", "dow": "曜日", "temp_mean": "日平均気温", "prevday_mean": "前日の需要の平均",
      "year": "年（長期の流れ）", "lag24_daytype": "前日の曜日区分", "humid_mean": "湿度", "temp_change": "前日からの気温の変化",
      "temp_min": "最低気温", "doy_cos": "季節（cos）", "cdd_max": "最高気温の28℃超え", "cdd": "冷房度日", "doy_sin": "季節（sin）",
      "hdd": "暖房度日", "obon": "お盆", "gw": "大型連休", "month": "月", "holiday": "祝日", "nenmatsu": "年末年始"}
top = imp.head(14)[::-1]
fig, ax = plt.subplots(figsize=(8, 5.4))
ax.barh([JP.get(i, i) for i in top.index], top["mean_abs_shap"], color="#188038")
ax.set_xlabel("SHAP の絶対値の平均（MW）")
ax.set_title("LightGBM の予測に効いていた特徴量（2026年度上期の予測、4,000時間）", fontsize=11)
ax.grid(axis="x", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a22_shap.png"); plt.close()

# 6. 頑健性
base = R.loc[R["設定"] == "基本（拡張ウィンドウ）", "MAPE(%)"].iloc[0]
items = [("基本（2016年度から拡張ウィンドウ）", base, "#188038")]
for nm in ["学習を直近3年に限る", "お盆・年末年始を広め＋休みの前後の特徴を足す", "ラグ（過去の需要）を使わない", "気温・湿度を使わない"]:
    items.append((nm, R.loc[R["設定"] == nm, "MAPE(%)"].iloc[0], "#1a73e8"))
for _, r in N.iterrows():
    items.append((f"気温に予報誤差 σ={r['σ(℃)']:.0f}℃ を足す", r["mean"], "#e37400"))
items.append(("関西エリア（学習1年半）：LightGBM", R.loc[R["設定"] == "関西エリア：LightGBM", "MAPE(%)"].iloc[0], "#a142f4"))
items.append(("関西エリア：1週間前の同じ時刻", R.loc[R["設定"] == "関西エリア：1週間前の同じ時刻", "MAPE(%)"].iloc[0], "#9aa0a6"))
fig, ax = plt.subplots(figsize=(9.5, 5.4))
y = np.arange(len(items))[::-1]
ax.barh(y, [i[1] for i in items], color=[i[2] for i in items])
for yy, i in zip(y, items):
    ax.text(i[1] + .08, yy, f"{i[1]:.2f}%", va="center", fontsize=9)
ax.set_yticks(y, [i[0] for i in items], fontsize=9)
ax.axvline(base, color="#188038", ls="--", lw=1)
ax.set_xlabel("MAPE（%）")
ax.set_title("設定を変えたときの誤差（東京は2020年4月〜2026年9月、関西は2025年10月〜2026年9月）", fontsize=10.5)
ax.grid(axis="x", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a22_robustness.png"); plt.close()
print("ok")
