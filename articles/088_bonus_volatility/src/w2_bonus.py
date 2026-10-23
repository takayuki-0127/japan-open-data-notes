"""W2：業種別のボーナス（特別給与）の振れ幅と景気（規模5人以上、年平均の前年比、2001〜2025年）"""
import numpy as np, pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load()
g = x[(x["種別"] == "伸び率") & (x["規模"] == "T") & (x["就業形態"] == "0") & (x["月"] == "CY")]
B = g.pivot(index="年", columns="産業分類", values="特別給与") / 100
S = g.pivot(index="年", columns="産業分類", values="所定内給与") / 100
lb, ls_ = np.log1p(B), np.log1p(S)
inds = [k for k in IND if k != "TL"]
r = x[(x["種別"] == "実数") & (x["規模"] == "T") & (x["就業形態"] == "0") & (x["月"] == "CY") & (x["年"] == 2025)].set_index("産業分類")

rows = []
for k in ["TL"] + inds:
    b, s = lb[k].dropna(), ls_[k].dropna()
    b11, s11 = b.loc[2011:2025], s.loc[2011:2025]
    d = {"産業": IND[k], "記号": k, "期間": f"{b.index.min()}–{b.index.max()}",
         "ボーナス前年比の標準偏差_2011_2025": 100 * b11.std(), "所定内給与前年比の標準偏差_2011_2025": 100 * s11.std(),
         "ボーナスの年平均の伸び_2011_2025": 100 * b11.mean(),
         "2009年のボーナス変化": 100 * b.get(2009, np.nan),
         "2020_2021年のボーナス変化": 100 * (b.get(2020, np.nan) + b.get(2021, np.nan)),
         "ボーナスの割合_2025": 100 * 12 * r.loc[k, "特別給与"] / (12 * r.loc[k, "現金給与総額"]),
         "ボーナス月額_2025": r.loc[k, "特別給与"], "年間ボーナス_2025": 12 * r.loc[k, "特別給与"]}
    # 産業計のボーナスの前年比に対する感応度（2001〜2025年、または2011〜2025年）
    if k != "TL":
        yy = pd.concat([b, lb["TL"]], axis=1, keys=["y", "x"]).dropna()
        m = sm.OLS(yy["y"], sm.add_constant(yy["x"])).fit(cov_type="HC1")
        d.update({"産業計への感応度": m.params["x"], "感応度の標準誤差": m.bse["x"], "相関": yy.corr().iloc[0, 1], "年数": len(yy)})
    rows.append(d)
t = pd.DataFrame(rows)
t["振れ幅の比（ボーナス÷所定内）"] = t["ボーナス前年比の標準偏差_2011_2025"] / t["所定内給与前年比の標準偏差_2011_2025"]
t.round(3).to_csv(RES / "w2_industry_bonus.csv", index=False, encoding="utf-8-sig")
print(t.round(2).to_string())
(100 * B.loc[2001:, ["TL"] + inds]).round(1).rename(columns=IND).to_csv(RES / "w2_bonus_growth_by_industry.csv", encoding="utf-8-sig")

# 産業計：ボーナスと所定外労働時間（景気の目安）の前年比の相関
ov = g[g["産業分類"] == "TL"].set_index("年")["所定外労働時間"] / 100
cc = pd.concat([lb["TL"], np.log1p(ov), ls_["TL"]], axis=1, keys=["bonus", "overtime", "base"]).loc[2001:].dropna()
print("産業計 2001-2025：ボーナスと所定外労働時間の前年比の相関", round(cc.corr().loc["bonus", "overtime"], 2),
      " 所定内と所定外", round(cc.corr().loc["base", "overtime"], 2))
pd.DataFrame({"相関_ボーナスと所定外労働時間": [cc.corr().loc["bonus", "overtime"]],
              "相関_所定内給与と所定外労働時間": [cc.corr().loc["base", "overtime"]], "年数": [len(cc)]}).round(3)\
  .to_csv(RES / "w2_cycle_corr.csv", index=False, encoding="utf-8-sig")

# 全国の夏・冬の賞与（5人以上）
bn = load_bonus()
bn = bn[bn["規模"] == "T"].copy()
bn["季節"] = bn["月"].map({"06": "夏", "11": "冬"})
bw = bn.pivot(index="年", columns="季節", values=["賞与支給額", "支給労働者割合", "きまって支給する給与に対する支給月数"])
bw.columns = [f"{a}_{b}" for a, b in bw.columns]
bw.to_csv(RES / "w2_national_bonus.csv", encoding="utf-8-sig")
print(bw.loc[[1990, 1991, 1997, 2008, 2009, 2010, 2019, 2020, 2021, 2024, 2025]].to_string())

# --- 図1：振れ幅
tt = t[t["記号"] != "TL"].sort_values("ボーナス前年比の標準偏差_2011_2025")
fig, ax = plt.subplots(figsize=(8, 5.6))
yy = np.arange(len(tt))
ax.barh(yy + 0.2, tt["ボーナス前年比の標準偏差_2011_2025"], height=0.4, color=ORANGE, label="ボーナス（特別給与）")
ax.barh(yy - 0.2, tt["所定内給与前年比の標準偏差_2011_2025"], height=0.4, color=BLUE, label="所定内給与（基本給など）")
ax.set_yticks(yy); ax.set_yticklabels(tt["産業"])
for i, v in enumerate(tt["ボーナス前年比の標準偏差_2011_2025"]):
    ax.text(v + 0.2, i + 0.2, f"{v:.1f}", va="center", fontsize=8.5)
tl = t[t["記号"] == "TL"].iloc[0]
ax.axvline(tl["ボーナス前年比の標準偏差_2011_2025"], color=GRAY, ls="--", lw=1)
ax.set_xlabel("前年比の標準偏差（％ポイント、2011〜2025年）")
ax.set_title("業種別：ボーナスと所定内給与の前年比の振れ幅", loc="left")
ax.legend(frameon=False, loc="lower right", fontsize=9)
note(ax, SOURCE + "。点線は調査産業計のボーナス", -0.15)
fig.savefig(FIG / "w2_volatility.png"); plt.close(fig)

# --- 図2：景気後退期の落ち込み
u = t[t["記号"] != "TL"].dropna(subset=["2009年のボーナス変化"]).sort_values("2009年のボーナス変化")
u = pd.concat([u, t[t["記号"] == "TL"]])
fig, ax = plt.subplots(figsize=(8, 5.2))
yy = np.arange(len(u))
ax.barh(yy + 0.2, u["2009年のボーナス変化"], height=0.4, color=BLUE, label="2009年（前年比）")
ax.barh(yy - 0.2, u["2020_2021年のボーナス変化"], height=0.4, color=ORANGE, label="2020〜2021年（2年の合計）")
ax.set_yticks(yy); ax.set_yticklabels(u["産業"]); ax.axvline(0, color=INK, lw=0.6)
ax.set_xlabel("ボーナス（特別給与）の変化（％、対数差）")
ax.set_title("景気後退期のボーナスの落ち込み（2001年から比べられる業種）", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
note(ax, SOURCE, -0.2)
fig.savefig(FIG / "w2_shocks.png"); plt.close(fig)

# --- 図3：全国の夏・冬の賞与
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
for s, col in [("夏", ORANGE), ("冬", BLUE)]:
    ax[0].plot(bw.index, bw[f"賞与支給額_{s}"] / 1e4, color=col, lw=2, label=f"{s}の賞与")
    ax[1].plot(bw.index, bw[f"きまって支給する給与に対する支給月数_{s}"], color=col, lw=2, label=s)
ax[0].set_title("1人平均の賞与（万円、支給された人）", loc="left", fontsize=11)
ax[1].set_title("毎月の給与の何か月分か", loc="left", fontsize=11)
for a in ax: a.legend(frameon=False, fontsize=9)
for yr in (2009, 2020): 
    for a in ax: a.axvspan(yr - 0.5, yr + 0.5, color=LIGHT, alpha=0.4, lw=0)
note(ax[0], SOURCE + "。規模5人以上", -0.12)
fig.savefig(FIG / "w2_national.png"); plt.close(fig)
