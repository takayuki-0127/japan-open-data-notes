"""W2：都道府県の有効求人倍率は近づいているか（受理地別 1973〜2025年、就業地別 2006〜2025年）

- σ収束：47都道府県の有効求人倍率（年平均）の対数の標準偏差
- β収束：期間の初めの倍率（対数）で、その後の年率の変化を回帰（HC1標準誤差）
- 受理地別と就業地別：求人を出したハローワーク（本社など）で数えるか、実際に働く場所で数えるか
- 2021年9月から有効求職者にオンライン登録者が入った。第26表（ハローワーク利用登録者のみ）で影響を確かめる
"""
import numpy as np, pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import load_pref, PREFS, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, foot

pa, pm = load_pref()
pa = pa[pa["都道府県"].isin(PREFS)]
J = pa[pa["基準"] == "受理地"].pivot(index="年", columns="都道府県", values="有効求人倍率")[PREFS]
S = pa[pa["基準"] == "就業地"].pivot(index="年", columns="都道府県", values="有効求人倍率")[PREFS]
nat = load_pref()[0].query("基準=='受理地' and 都道府県=='全国'").set_index("年")["有効求人倍率"]

# 1) σ収束（沖縄の本土復帰後の1973年から）
def sig(X):
    L = np.log(X)
    return pd.DataFrame({"対数の標準偏差": L.std(axis=1, ddof=0), "最大": X.max(axis=1), "最小": X.min(axis=1),
                         "最大÷最小": X.max(axis=1) / X.min(axis=1), "1倍以上の県の数": (X >= 1).sum(axis=1)})
sj = sig(J.loc[1973:]).add_prefix("受理地_")
ss = sig(S).add_prefix("就業地_")
sg = sj.join(ss, how="left").join(nat.rename("全国"))
sg.round(3).to_csv(RES / "w2_sigma.csv", index_label="年")
corr = np.corrcoef(nat.loc[1973:2025], sj["受理地_対数の標準偏差"])[0, 1]

# 2) β収束：いくつかの期間で
def beta(X, a, b):
    y = np.log(X.loc[b] / X.loc[a]) / (b - a) * 100
    x = np.log(X.loc[a])
    m = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HC1")
    return {"期間": f"{a}→{b}", "β": m.params.iloc[1], "標準誤差": m.bse.iloc[1], "R2": m.rsquared, "n": int(m.nobs)}
per = [(1973, 1990), (1990, 2009), (2009, 2019), (2013, 2019), (2019, 2025), (2013, 2025)]
bt = pd.DataFrame([dict(beta(J, a, b), 基準="受理地") for a, b in per] +
                  [dict(beta(S, a, b), 基準="就業地") for a, b in [(2009, 2019), (2013, 2019), (2019, 2025), (2013, 2025)]])
bt.round(3).to_csv(RES / "w2_beta.csv", index=False)

# 3) 受理地と就業地の差（2025年）
gap = pd.DataFrame({"受理地": J.loc[2025], "就業地": S.loc[2025]})
gap["差（就業地−受理地）"] = gap["就業地"] - gap["受理地"]
gap["順位_受理地"] = gap["受理地"].rank(ascending=False).astype(int)
gap["順位_就業地"] = gap["就業地"].rank(ascending=False).astype(int)
gap.round(3).to_csv(RES / "w2_jyuri_vs_shugyo_2025.csv", index_label="都道府県")

# 4) オンライン登録者の影響（2025年の月平均）
m = pm[pm["都道府県"].isin(PREFS + ["全国"]) & pm["年月"].str.startswith("2025")]
g = m.groupby("都道府県")[["有効求人", "有効求職", "有効求職_HW利用登録者"]].mean()
g["倍率_公表と同じ定義"] = g["有効求人"] / g["有効求職"]
g["倍率_HW利用登録者のみ"] = g["有効求人"] / g["有効求職_HW利用登録者"]
g["オンライン登録者の割合"] = 1 - g["有効求職_HW利用登録者"] / g["有効求職"]
g.round(3).to_csv(RES / "w2_online_2025.csv", index_label="都道府県")
gp = g.loc[PREFS]
sd_all = np.log(gp["倍率_公表と同じ定義"]).std(ddof=0)
sd_hw = np.log(gp["倍率_HW利用登録者のみ"]).std(ddof=0)

# --- 図1：σ収束
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.6, 6.4), sharex=True, gridspec_kw={"height_ratios": [1, 1.25]})
a1.plot(nat.loc[1973:].index, nat.loc[1973:], color=INK, lw=2)
a1.axhline(1, color=GRAY, lw=0.8, ls=":")
a1.set_ylabel("全国の倍率（倍）"); a1.set_title("全国の有効求人倍率と、都道府県の差")
a2.plot(sj.index, sj["受理地_対数の標準偏差"], color=BLUE, lw=2, label="受理地別（求人を出したハローワーク）")
a2.plot(ss.index, ss["就業地_対数の標準偏差"], color=ORANGE, lw=2, label="就業地別（実際に働く場所）")
a2.axvline(2021.7, color=GRAY, ls=":", lw=1); a2.text(2021.3, 0.43, "2021年9月〜\nオンライン登録者を含む", fontsize=8, color=GRAY, ha="right", va="top")
a2.set_ylabel("47都道府県の倍率の\n対数の標準偏差"); a2.legend(frameon=False, fontsize=9, loc="upper right")
a2.set_ylim(0, None)
foot(fig, "年平均の有効求人倍率（パートを含む一般）。1973年（沖縄の本土復帰の翌年）から")
fig.savefig(FIG / "w2_sigma.png"); plt.close(fig)

# --- 図2：β収束（2013→2025年、受理地別）
a, b = 2013, 2025
x = J.loc[a]; y = np.log(J.loc[b] / J.loc[a]) / (b - a) * 100
fig, ax = plt.subplots(figsize=(7.6, 5.4))
ax.scatter(x, y, s=22, color=BLUE, alpha=0.8)
for p in ["東京都", "福井県", "沖縄県", "北海道", "大阪府", "愛知県", "岡山県", "神奈川県", "島根県", "青森県"]:
    ax.annotate(p.rstrip("都府県") if p != "北海道" else p, (x[p], y[p]), fontsize=8, xytext=(4, 2), textcoords="offset points")
bb = bt[(bt["期間"] == f"{a}→{b}") & (bt["基準"] == "受理地")].iloc[0]
xx = np.linspace(x.min(), x.max(), 50)
fit = sm.OLS(y, sm.add_constant(np.log(x))).fit()
ax.plot(xx, fit.params.iloc[0] + fit.params.iloc[1] * np.log(xx), color=ORANGE, lw=1.5)
ax.set_xscale("log"); ax.set_xticks([0.4, 0.6, 0.8, 1, 1.5]); ax.set_xticklabels(["0.4", "0.6", "0.8", "1", "1.5"])
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xlabel(f"{a}年の有効求人倍率（倍、対数目盛）"); ax.set_ylabel(f"{a}→{b}年の年率の変化（%）")
ax.set_title(f"低かった県ほど上がったか（受理地別、β＝{bb['β']:.2f}）")
foot(fig, "β：年率の変化（%）を初めの倍率の対数で回帰した傾き")
fig.savefig(FIG / "w2_beta.png"); plt.close(fig)

# --- 図3：受理地別と就業地別（2025年）
gg = gap.sort_values("就業地")
fig, ax = plt.subplots(figsize=(7.4, 9.2))
yy = np.arange(len(gg))
ax.hlines(yy, gg[["受理地", "就業地"]].min(axis=1), gg[["受理地", "就業地"]].max(axis=1), color=LIGHT, lw=2)
ax.scatter(gg["受理地"], yy, color=BLUE, s=18, label="受理地別", zorder=3)
ax.scatter(gg["就業地"], yy, color=ORANGE, s=18, label="就業地別", zorder=3)
ax.set_yticks(yy); ax.set_yticklabels(gg.index, fontsize=8)
ax.axvline(1, color=GRAY, lw=0.8, ls=":")
ax.legend(frameon=False, loc="lower right")
ax.set_xlabel("有効求人倍率（2025年平均、倍）")
ax.set_title("求人を出した場所で数えるか、働く場所で数えるか（2025年）")
foot(fig, "就業地別の順に並べた")
fig.savefig(FIG / "w2_shugyo.png"); plt.close(fig)

print(sg.loc[[1973, 1975, 1980, 1985, 1990, 1991, 1995, 1999, 2000, 2005, 2006, 2007, 2009, 2010, 2013, 2015, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]].round(3).to_string())
print("相関（全国倍率×σ）", round(corr, 3))
print(bt.round(3).to_string())
print(gap.sort_values("差（就業地−受理地）").round(2).to_string())
print(J.loc[2025].sort_values().round(2).to_string())
print(g.loc[["全国"] + PREFS].round(3).sort_values("オンライン登録者の割合").to_string())
print("SD 公表定義", round(sd_all, 3), "HWのみ", round(sd_hw, 3))
