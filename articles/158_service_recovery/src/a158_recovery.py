"""サービス産業の売上は、コロナ後どこまで戻ったか（サービス産業動向調査 2018〜2024年の月次）"""
from common import *

d = load("service_sales_monthly.csv")  # 単位：億円（消費税込み売上高、百万円を100で割って四捨五入）
d["date"] = pd.to_datetime(d.ym + "-01"); d["year"] = d.date.dt.year; d["month"] = d.date.dt.month
S = [c for c in d.columns if c not in ("ym", "date", "year", "month")]
LAB = {"service_total": "サービス産業計", "G_info": "情報通信業", "H_transport": "運輸業，郵便業", "K_realestate": "不動産業，物品賃貸業",
       "L_professional": "学術研究，専門・技術サービス業", "M_accom_food": "宿泊業，飲食サービス業", "N_living_amuse": "生活関連サービス業，娯楽業",
       "O_education": "教育，学習支援業", "P_medical_welfare": "医療，福祉", "R_other_services": "サービス業（他に分類されないもの）",
       "i42_rail": "鉄道業", "i43_road_passenger": "道路旅客運送業（バス・タクシー）", "i4x_air": "航空運輸業，郵便業", "i75_hotel": "宿泊業",
       "i76_restaurant": "飲食店", "i78_laundry_beauty_bath": "洗濯・理容・美容・浴場業", "i79_other_living": "その他の生活関連サービス業（旅行業など）",
       "i80_amusement": "娯楽業", "i83_medical": "医療業", "i85_welfare_care": "社会保険・社会福祉・介護事業"}
base = d[d.year == 2019].set_index("month")[S]
r = d.set_index("date")[S].copy()
for c in S:
    r[c] = d.set_index("date")[c].values / base.loc[d.month.values, c].values * 100  # 2019年同月=100
r.round(1).to_csv(RES / "a158_vs2019_same_month.csv", encoding="utf-8")
ann = d.groupby("year")[S].sum()
rec = (ann / ann.loc[2019] * 100).T
rec["trough"] = r.loc["2020":"2022", S].min()
rec["trough_month"] = r.loc["2020":"2022", S].idxmin().dt.strftime("%Y-%m")
rec["label"] = [LAB[c] for c in rec.index]
rec.round(1).to_csv(RES / "a158_recovery.csv", encoding="utf-8")
L = [f"サービス産業計 年計（兆円）: " + "、".join(f"{y} {v/1e4:.1f}" for y, v in ann.service_total.items())]
L.append("2019年=100 の年計:\n" + "\n".join(f"  {r_.label} 2020 {r_[2020]:.1f} 2021 {r_[2021]:.1f} 2022 {r_[2022]:.1f} 2023 {r_[2023]:.1f} 2024 {r_[2024]:.1f}  最低 {r_.trough:.1f}（{r_.trough_month}）" for _, r_ in rec.iterrows()))
L.append("2024年12月 2019年同月比: " + "、".join(f"{LAB[c]} {r.loc['2024-12-01', c]:.1f}" for c in S))
first = {}
for c in S:
    x = r.loc["2020-04":, c]; ok = x[x >= 100]
    first[c] = ok.index[0].strftime("%Y-%m") if len(ok) else "未"
L.append("2019年同月を初めて上回った月（2020年4月以降）: " + "、".join(f"{LAB[c]} {first[c]}" for c in S))
(RES / "a158_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：2019年同月比の推移
fig, ax = plt.subplots(figsize=(10, 5.4))
for c, col, lw in [("service_total", INK, 2.4), ("M_accom_food", ORANGE, 1.8), ("N_living_amuse", PURPLE, 1.8), ("H_transport", BLUE, 1.8), ("P_medical_welfare", GREEN, 1.8)]:
    x = r.loc["2020-01":, c]
    ax.plot(x.index, x.values, color=col, lw=lw, label=LAB[c])
ax.axhline(100, color=GRAY, lw=1, ls="--")
ax.set_ylabel("2019年の同じ月＝100"); ax.set_ylim(30, 125)
ax.legend(frameon=False, ncol=3, loc="lower right", fontsize=9.5)
ax.set_title("サービス産業の売上（2019年の同じ月との比較）")
save(fig, "a158_trend.png")

# 図2：2024年の年計（2019年=100）中分類・大分類
sel = ["i4x_air", "i75_hotel", "i42_rail", "i43_road_passenger", "i76_restaurant", "i79_other_living", "i80_amusement", "i78_laundry_beauty_bath", "i83_medical", "i85_welfare_care",
       "O_education", "G_info", "K_realestate", "L_professional", "H_transport", "R_other_services", "service_total"]
t = rec.loc[sel].sort_values(2024)
fig, ax = plt.subplots(figsize=(9.5, 6.6))
y = np.arange(len(t))
ax.barh(y, t[2024], color=[INK if i == "service_total" else (ORANGE if v < 100 else BLUE) for i, v in zip(t.index, t[2024])], height=0.62)
ax.scatter(t[2021], y, color=GRAY, zorder=3, s=22, label="2021年")
for yy, v in zip(y, t[2024]):
    ax.text(max(v, 0) + 1.5, yy, f"{v:.0f}", va="center", fontsize=9)
ax.axvline(100, color=GRAY, lw=1, ls="--")
ax.set_yticks(y); ax.set_yticklabels(t.label, fontsize=9)
ax.set_xlabel("1年間の売上（2019年＝100）。棒は2024年、点は2021年"); ax.set_xlim(0, 175)
ax.legend(frameon=False, loc="lower right"); ax.set_title("2024年の売上は2019年と比べてどこまで戻ったか")
save(fig, "a158_recovery.png")

# 図3：落ち込みの深さと2024年の戻り
z = rec.loc[[c for c in sel if c != "service_total"]]
fig, ax = plt.subplots(figsize=(9, 6))
ax.scatter(z.trough, z[2024], s=50, color=BLUE)
for i, row in z.iterrows():
    ax.annotate(row.label.split("（")[0], (row.trough, row[2024]), xytext=(5, 3), textcoords="offset points", fontsize=8.5)
ax.axhline(100, color=GRAY, lw=1, ls="--")
ax.set_xlabel("2020〜22年で最も落ち込んだ月（2019年同月＝100）"); ax.set_ylabel("2024年の年計（2019年＝100）")
ax.set_title("深く落ち込んだ業種ほど、戻りも遅かったか")
save(fig, "a158_scatter.png")
