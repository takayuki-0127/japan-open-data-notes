"""1世帯あたりのCO2排出量は、寒い地域ほど多いのか：地方別の比較（家庭部門のCO2排出実態統計調査 2023年度）"""
from common import *

c = load("co2_per_household_region.csv")
e = load("energy_per_household_region.csv")
REG = ["北海道", "東北", "北陸", "関東甲信", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
c23 = c[(c.fiscal_year == 2023) & (c.building == "全体")].set_index("region")
c22 = c[(c.fiscal_year == 2022) & (c.building == "全体")].set_index("region")
e23 = e[(e.fiscal_year == 2023) & (e.building == "全体")].set_index("region")
nat_c, nat_e = c23.loc["全国"], e23.loc["全国"]

t = pd.DataFrame(index=REG)
t["co2_total4"] = c23.total_4
t["co2_kerosene"] = c23.kerosene
t["co2_gasoline"] = c23.gasoline
t["co2_with_car"] = c23.total_4 + c23.gasoline + c23.diesel
t["co2_per_person"] = c23.total_4 / c23.persons
t["energy_total4_GJ"] = e23.total_4
t["energy_kerosene_GJ"] = e23.kerosene
t["kerosene_share_energy"] = e23.kerosene / e23.total_4 * 100
t["elec_t_per_MWh"] = c23.electricity / (e23.electricity / 3.6)   # 電気のCO2÷電気の消費量（GJ→MWh）
t["co2_total4_fy2022"] = c22.total_4
t.round(3).to_csv(RES / "a189_region.csv")
b = c[(c.fiscal_year == 2023) & (c.building != "全体")].pivot(index="region", columns="building", values="total_4").loc[REG]
b.to_csv(RES / "a189_building.csv")

L = [f"全国 2023: CO2(電気・ガス・灯油) {nat_c.total_4} t/世帯 / エネルギー {nat_e.total_4} GJ / ガソリン {nat_c.gasoline} t / 電気の排出係数(逆算) {nat_c.electricity/(nat_e.electricity/3.6):.3f} t/MWh",
     "CO2(4種)多い順: " + ", ".join(f"{k}{v:.2f}" for k, v in t.co2_total4.sort_values(ascending=False).items()),
     "エネルギー多い順: " + ", ".join(f"{k}{v:.1f}" for k, v in t.energy_total4_GJ.sort_values(ascending=False).items()),
     f"北海道/全国 CO2 {t.co2_total4['北海道']/nat_c.total_4:.2f}倍 エネルギー {t.energy_total4_GJ['北海道']/nat_e.total_4:.2f}倍; 灯油のCO2 北海道{t.co2_kerosene['北海道']} 東北{t.co2_kerosene['東北']} 全国{nat_c.kerosene}",
     "灯油がエネルギーに占める割合: " + ", ".join(f"{k}{v:.0f}%" for k, v in t.kerosene_share_energy.items()),
     "電気の排出係数(逆算 t/MWh): " + ", ".join(f"{k}{v:.3f}" for k, v in t.elec_t_per_MWh.items()),
     "1人あたりCO2(4種): " + ", ".join(f"{k}{v:.2f}" for k, v in t.co2_per_person.sort_values(ascending=False).items()),
     "ガソリン込み: " + ", ".join(f"{k}{v:.2f}" for k, v in t.co2_with_car.sort_values(ascending=False).items()),
     "ガソリン: " + ", ".join(f"{k}{v:.2f}" for k, v in t.co2_gasoline.sort_values(ascending=False).items()),
     "戸建: " + ", ".join(f"{k}{v:.2f}" for k, v in b["戸建"].items()),
     "集合: " + ", ".join(f"{k}{v:.2f}" for k, v in b["集合"].items()),
     "2022→2023 CO2(4種): " + ", ".join(f"{k}{t.co2_total4_fy2022[k]:.2f}→{t.co2_total4[k]:.2f}" for k in REG),
     f"北海道を除く9地方のエネルギーとCO2の相関 r={t.drop('北海道').energy_total4_GJ.corr(t.drop('北海道').co2_total4):.2f}; 10地方 r={t.energy_total4_GJ.corr(t.co2_total4):.2f}"]
(RES / "a189_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

y = np.arange(len(REG))[::-1]
COL = {"electricity": BLUE, "city_gas": GREEN, "lpg": PURPLE, "kerosene": ORANGE}
NAME = {"electricity": "電気", "city_gas": "都市ガス", "lpg": "LPガス", "kerosene": "灯油"}

def stacked(ax, df, unit, title, nat):
    left = np.zeros(len(REG))
    for k in COL:
        v = df.loc[REG, k].values
        ax.barh(y, v, left=left, color=COL[k], height=0.62, label=NAME[k])
        left += v
    for yy, tot in zip(y, df.loc[REG, "total_4"].values):
        ax.text(tot + nat * 0.01, yy, f"{tot:g}", va="center", fontsize=9)
    ax.axvline(nat, color=GRAY, lw=0.9, ls="--"); ax.text(nat * 1.01, 0.5, f"全国 {nat:g}", color=GRAY, fontsize=8.5, ha="left", va="center")
    ax.set_yticks(y); ax.set_yticklabels(REG); ax.set_xlabel(unit); ax.set_title(title)
    ax.legend(frameon=False, loc="lower right", ncol=2)

# 図1：エネルギー消費量（GJ/世帯・年）
fig, ax = plt.subplots(figsize=(10, 5.2))
stacked(ax, e23, "GJ／世帯・年", "1世帯あたりのエネルギー消費量（電気・ガス・灯油、2023年度）", nat_e.total_4)
save(fig, "a189_energy.png")

# 図2：CO2排出量（t/世帯・年）
fig, ax = plt.subplots(figsize=(10, 5.2))
stacked(ax, c23, "t-CO2／世帯・年", "1世帯あたりのCO2排出量（電気・ガス・灯油、2023年度）", nat_c.total_4)
save(fig, "a189_co2.png")

# 図3：戸建と集合
fig, ax = plt.subplots(figsize=(10, 4.4))
x = np.arange(len(REG)); w = 0.38
ax.bar(x - w / 2, b["戸建"], w, color=BLUE, label="戸建")
ax.bar(x + w / 2, b["集合"], w, color=LIGHT, label="集合住宅")
ax.set_xticks(x); ax.set_xticklabels(REG); ax.set_ylabel("t-CO2／世帯・年")
ax.set_title("住宅の建て方別のCO2排出量（電気・ガス・灯油、2023年度）")
ax.legend(frameon=False, loc="upper right")
save(fig, "a189_building.png")
