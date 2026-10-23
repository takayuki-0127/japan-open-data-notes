"""W1：日本沿岸の海面水位は何cm上がったか（期間別のトレンド、自己相関の補正、地点差、十年規模の変動）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

sl = load_sl()
# ---- 期間別のトレンド（mm/年）。90%信頼区間：OLS（気象庁の表と同じ）、Newey-West、AR(1)の有効標本数
periods = [("pt4", 1906, 2023, "4地点 1906–2023（全期間）"), ("pt4", 1906, 2018, "4地点 1906–2018（IPCCとほぼ同じ期間）"),
           ("area4", 1960, 2025, "4海域 1960–2025"), ("area4", 1980, 2025, "4海域 1980–2025"),
           ("area4", 1990, 2025, "4海域 1990–2025"),
           ("area4", 2004, 2025, "4海域 2004–2025"), ("area4", 2006, 2018, "4海域 2006–2018")]
rows = []
for col, a, b, lab in periods:
    t = trend(sl[col], a, b); t.update(series=col, label=lab); rows.append(t)
tide, tideo = load_tide(), load_tide(org=True)
t = trend(tide["Average"], 2004, 2025); t.update(series="13地点（地盤補正後）", label="GPS併設13地点 2004–2025"); rows.append(t)
tr = pd.DataFrame(rows)[["label", "series", "start", "end", "n", "slope", "lo_ols", "hi_ols", "lo_hac", "hi_hac", "ar1", "lo_ar1", "hi_ar1"]]
tr.round(3).to_csv(RES / "w1_trends.csv", index=False)
print(tr.round(2).to_string())

# ---- 何cm上がったか：10年平均の差
a4 = sl["area4"]
lv = pd.DataFrame({"期間": ["1980–1989", "1990–1999", "2000–2009", "2010–2019", "2016–2025"],
                   "4海域平均の偏差_mm": [a4.loc[1980:1989].mean(), a4.loc[1990:1999].mean(), a4.loc[2000:2009].mean(),
                                       a4.loc[2010:2019].mean(), a4.loc[2016:2025].mean()]})
lv.round(1).to_csv(RES / "w1_decade_means.csv", index=False)
print(lv.round(1))
pt = sl["pt4"]
print("4地点の上位年", pt.sort_values(ascending=False).head(5).to_dict())
print("4海域の上位年", a4.sort_values(ascending=False).head(5).to_dict())

# ---- 十年規模の変動：4地点の5年移動平均の極大（1906–1999）
ma = pt.rolling(5, center=True).mean()
peaks = [y for y in range(1910, 2000) if ma.loc[y] == ma.loc[y - 7:y + 7].max()]
print("5年移動平均の極大", [(y, round(ma.loc[y], 1)) for y in peaks])
# 線形トレンドを除いた残差の標準偏差（年値・5年平均）
tt = trend(pt, 1906, 2023)
res = pt.loc[1906:2023] - (tt["slope"] * (pt.loc[1906:2023].index - 1964.5) + pt.loc[1906:2023].mean())
print("残差SD 年値", round(res.std(), 1), " 5年平均", round(res.rolling(5, center=True).mean().std(), 1))
pd.DataFrame({"year": ma.index, "pt4_ma5": ma.values}).dropna().to_csv(RES / "w1_ma5.csv", index=False)

# ---- 13地点：地盤補正前後の上昇率
st = []
for c in tide.columns:
    if c == "Average": continue
    a, b = trend(tide[c], 2004, 2025), trend(tideo[c], 2004, 2025)
    st.append(dict(station=c, name=STATIONS[c], corrected=a["slope"], lo=a["lo_ols"], hi=a["hi_ols"], uncorrected=b["slope"],
                   land=b["slope"] - a["slope"], rise_2025_mm=tide.loc[2025, c]))
st = pd.DataFrame(st).sort_values("corrected")
st.round(2).to_csv(RES / "w1_stations.csv", index=False)
print(st.round(2).to_string())

# ---- 図1：長期の推移
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.scatter(pt.index, pt, s=10, color=LIGHT, label="4地点（年）")
ax.plot(ma.index, ma, color=BLUE, lw=2, label="4地点 5年移動平均")
ax.scatter(a4.index, a4, s=10, color="#f5b79b", label="4海域（年）")
ax.plot(a4.index, a4.rolling(5, center=True).mean(), color=ORANGE, lw=2, label="4海域 5年移動平均")
r = trend(a4, 1980, 2025); x = np.array([1980, 2025])
ax.plot(x, r["slope"] * (x - 2002.5) + a4.loc[1980:2025].mean(), color=INK, ls="--", lw=1.2, label=f"1980–2025の傾向 {r['slope']:.1f}mm/年")
ax.axhline(0, color=GRAY, lw=0.6)
ax.set_title("日本沿岸の平均海面水位（1991–2020年平均との差、mm）"); ax.set_xlabel("年"); ax.set_ylabel("mm")
ax.legend(fontsize=8.5, loc="upper left", frameon=False, ncol=2)
fig.text(0, -0.03, SRC_SL, fontsize=8, color=GRAY); save(fig, "w1_long.png")

# ---- 図2：期間別の上昇率
sel = tr.iloc[[0, 2, 3, 5, 6, 7]].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.5, 4.4))
yy = np.arange(len(sel))[::-1]
ax.errorbar(sel["slope"], yy, xerr=[sel["slope"] - sel["lo_hac"], sel["hi_hac"] - sel["slope"]], fmt="o", color=BLUE, capsize=4,
            label="上昇率と90%信頼区間（Newey-West）")
ax.axvspan(3.2, 4.2, color="#fde3d7", alpha=0.8, label="世界平均 2006–2018（IPCC）3.7[3.2–4.2]")
for y, v in zip(yy, sel["slope"]): ax.text(v, y + 0.22, f"{v:.1f}", ha="center", fontsize=9)
ax.set_yticks(yy); ax.set_yticklabels(sel["label"]); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("mm/年"); ax.set_title("期間で変わる上昇率"); ax.set_xlim(-0.3, 5.0); ax.legend(fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
fig.text(0, -0.12, SRC_SL + "。世界平均はIPCC(2021)", fontsize=8, color=GRAY); save(fig, "w1_trend.png")

# ---- 図3：13地点（地盤補正後の上昇率と90%信頼区間。補正前は参考に数字で示す）
fig, ax = plt.subplots(figsize=(8.5, 4.8))
yy = np.arange(len(st))
ax.errorbar(st["corrected"], yy, xerr=[st["corrected"] - st["lo"], st["hi"] - st["corrected"]], fmt="o", color=BLUE, capsize=3)
avg = trend(tide["Average"], 2004, 2025)["slope"]
ax.axvline(avg, color=ORANGE, ls="--", lw=1.2, label=f"13地点平均 {avg:.1f}mm/年")
for y, (u, n) in enumerate(zip(st["uncorrected"], st["name"])):
    ax.text(8.6, y, f"{u:+.1f}", va="center", fontsize=8.5, color=GRAY)
ax.text(8.6, len(st) - 0.2, "補正前", fontsize=8.5, color=GRAY)
ax.set_xlim(-0.5, 9.6)
ax.set_yticks(yy); ax.set_yticklabels(st["name"]); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("2004–2025年の上昇率（mm/年、地盤上下変動の補正後、90%信頼区間）"); ax.set_title("GPSを併設した13地点の上昇率")
ax.legend(fontsize=9, frameon=False, loc="lower center", bbox_to_anchor=(0.62, 0.0))
fig.text(0, -0.03, SRC_SL + "。右端の灰色の数字は補正前の記録で計算した上昇率", fontsize=8, color=GRAY); save(fig, "w1_stations.png")
