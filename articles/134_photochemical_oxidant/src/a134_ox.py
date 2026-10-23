"""134：光化学オキシダントの環境基準は、なぜほぼ達成されないのか"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, note, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

att = pd.read_csv(DATA / "attainment_2014_2023.csv")
mean = pd.read_csv(DATA / "annual_mean_2014_2023.csv")
ox = pd.read_csv(DATA / "ox_daily_max_annual_mean.csv")
al = pd.read_csv(DATA / "ox_alerts.csv")
lt = pd.read_csv(DATA / "longterm_station_mean.csv")

# ---- 1. 物質別の環境基準達成率（一般局） ----
g = att[att.station == "一般局"].pivot(index="fiscal_year", columns="substance", values="attainment_pct")
g.to_csv(RES / "a134_attainment_general.csv", encoding="utf-8-sig")
print(g.to_string())
print(att[att.substance == "光化学オキシダント"].pivot(index="fiscal_year", columns="station", values=["stations", "attainment_pct"]).to_string())
pal = {"二酸化窒素": BLUE, "浮遊粒子状物質": GREEN, "二酸化硫黄": PURPLE, "一酸化炭素": GRAY, "微小粒子状物質": LIGHT, "光化学オキシダント": ORANGE}
fig, ax = plt.subplots(figsize=(8.6, 4.4))
for s, c in pal.items():
    ax.plot(g.index, g[s], marker="o", ms=4, color=c, lw=2.6 if s == "光化学オキシダント" else 1.6, label=s)
ax.annotate("光化学オキシダント 0.1%（1,137局中1局）", (g.index[-1], g["光化学オキシダント"].iloc[-1]), xytext=(-150, 14), textcoords="offset points", fontsize=9, color=ORANGE)
ax.annotate("微小粒子状物質（PM2.5）\n2014年度 37.8%", (2014, g.loc[2014, "微小粒子状物質"]), xytext=(8, -4), textcoords="offset points", fontsize=8.5, color=BLUE)
ax.legend(frameon=False, fontsize=8.5, loc="center right")
ax.set_xlim(2013.5, 2023.5); ax.set_ylim(-4, 106)
ax.set_ylabel("環境基準の達成率（%、一般局）"); ax.set_xlabel("年度")
ax.set_title("ほかの物質は100%近く、光化学オキシダントだけ0%台", loc="left")
note(ax)
fig.savefig(FIG / "a134_attainment.png"); plt.close(fig)

# ---- 2. 長期の推移：オキシダントは上がり、原因物質は下がった ----
w = lt.pivot(index="fiscal_year", columns="substance", values="mean")
w["光化学オキシダント（昼間の日最高1時間値）"] = ox.set_index("fiscal_year")["一般局"]
base = w.loc[1978:1980].mean()
idx = (w / base * 100).loc[1978:]
cols = ["光化学オキシダント（昼間の日最高1時間値）", "二酸化窒素", "一酸化窒素", "非メタン炭化水素", "浮遊粒子状物質", "二酸化硫黄"]
idx[cols].round(1).to_csv(RES / "a134_longterm_index_1978_80.csv", encoding="utf-8-sig")
w.to_csv(RES / "a134_longterm_levels.csv", encoding="utf-8-sig")
print(idx[cols].loc[[1980, 1990, 2000, 2010, 2020, 2023]].round(0).to_string())
lab = {"光化学オキシダント（昼間の日最高1時間値）": "光化学オキシダント", "二酸化窒素": "二酸化窒素（14局）", "一酸化窒素": "一酸化窒素（22局）",
       "非メタン炭化水素": "非メタン炭化水素（6局）", "浮遊粒子状物質": "浮遊粒子状物質（29局）", "二酸化硫黄": "二酸化硫黄（9局）"}
c2 = {cols[0]: ORANGE, "二酸化窒素": BLUE, "一酸化窒素": LIGHT, "非メタン炭化水素": PURPLE, "浮遊粒子状物質": GREEN, "二酸化硫黄": GRAY}
fig, ax = plt.subplots(figsize=(8.6, 4.6))
for c in cols:
    s = idx[c].dropna()
    ax.plot(s.index, s, color=c2[c], lw=2.6 if c == cols[0] else 1.6)
    ax.annotate(f"{lab[c]} {s.iloc[-1]:.0f}", (s.index[-1], s.iloc[-1]), xytext=(5, {"一酸化窒素": -8, "二酸化硫黄": 6}.get(c, 0)), textcoords="offset points",
                fontsize=8.5, color=c2[c], va="center")
ax.axhline(100, color=GRAY, lw=0.8, ls=":")
ax.set_xlim(1977, 2036); ax.set_ylabel("1978〜80年度の平均＝100"); ax.set_xlabel("年度")
ax.set_title("原因になる物質は減ったが、オキシダントは上がって横ばい", loc="left")
note(ax, "注：光化学オキシダントは全国の一般局、ほかは長期間続けて測っている一般局の平均。\n" + note.__defaults__[0], y=-0.15)
fig.savefig(FIG / "a134_longterm.png"); plt.close(fig)

# ---- 3. 注意報の発令延日数（高い濃度は減ったか） ----
a = al.set_index("year")
a["ma3"] = a.alert_days.rolling(3, center=True).mean()
a.to_csv(RES / "a134_alerts.csv", encoding="utf-8-sig")
dec = a.alert_days.groupby((a.index // 10) * 10).mean()
dec.round(1).to_csv(RES / "a134_alerts_by_decade.csv", encoding="utf-8-sig")
print(dec.round(1).to_string()); print(a.loc[[1973, 2000, 2007, 2019, 2020, 2021, 2022, 2023]].to_string())
fig, ax = plt.subplots(figsize=(8.6, 4.2))
ax.bar(a.index, a.alert_days, color=LIGHT, width=0.8, label="発令延日数")
ax.plot(a.index, a.ma3, color=BLUE, lw=2, label="3年移動平均")
for y in (1973, 2007, 2019, 2023):
    ax.annotate(f"{y}年 {a.loc[y,'alert_days']}日", (y, a.loc[y, "alert_days"]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8.5, color=INK)
ax.set_ylabel("注意報等の発令延日数（日）"); ax.set_xlabel("年")
ax.set_title("注意報が出る日は1970年代や2000年代より少なくなった", loc="left")
ax.legend(frameon=False, fontsize=9)
note(ax)
fig.savefig(FIG / "a134_alerts.png"); plt.close(fig)
