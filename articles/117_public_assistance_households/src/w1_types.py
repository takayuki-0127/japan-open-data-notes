"""W1：生活保護を受けている世帯は増えているのか。世帯類型（高齢者・母子・障害者・傷病者・その他）でどう変わったか（2012〜2024年度、月次）"""
from common import *

t = load_types()
u = load_units()

# --- 年度平均（各年度の12か月の平均。公表の「1か月平均」と同じ） ---
cols = ["total"] + TYPES + ["単身計", "単身高齢者世帯"]
fy = t.groupby("fy")[cols].mean()
nat = u[u.kind == "全国"].set_index("fy")
fy["実人員"] = nat["avg"]
fy["1世帯当たり人員"] = fy["実人員"] / fy["total"]
for c in TYPES + ["単身計", "単身高齢者世帯"]:
    fy[f"{c}_割合%"] = fy[c] / fy["total"] * 100
fy["高齢者世帯のうち単身%"] = fy["単身高齢者世帯"] / fy["高齢者世帯"] * 100
fy.round(2).to_csv(RES / "w1_fy.csv", encoding="utf-8-sig")

# --- 2012→2024年度の変化（類型別）と期間別 ---
a, b, mid = fy.loc[2012], fy.loc[2024], fy.loc[2017]
ch = pd.DataFrame({"2012年度": a[cols], "2017年度": mid[cols], "2024年度": b[cols]})
ch["増減(2012→2024)"] = ch["2024年度"] - ch["2012年度"]
ch["増減率%"] = ch["増減(2012→2024)"] / ch["2012年度"] * 100
ch["増減(2012→2017)"] = ch["2017年度"] - ch["2012年度"]
ch["増減(2017→2024)"] = ch["2024年度"] - ch["2017年度"]
ch.round(1).to_csv(RES / "w1_change.csv", encoding="utf-8-sig")

# --- 3月の段差：前月からの増減を月別に平均 ---
d = t.set_index("month")[TYPES + ["total"]].diff().dropna()
step = d.groupby(d.index.month).mean().round(0)
step.index.name = "月"
step.to_csv(RES / "w1_month_step.csv", encoding="utf-8-sig")

# --- 月次の値と前年同月比 ---
m = t.set_index("month")[cols].copy()
months = []
for y in FYS:
    for j in range(12):
        months.append((pd.Timestamp(y + (j >= 9), (j + 3) % 12 + 1, 1), nat.loc[y, f"m{j + 1:02d}"]))
m["実人員"] = pd.Series(dict(months))
m.to_csv(RES / "w1_monthly.csv", encoding="utf-8-sig")
peak = m["total"].idxmax()

print("年度平均（世帯）", fy[["total", "高齢者世帯", "単身高齢者世帯", "実人員"]].round(0).astype(int).to_string(), sep="\n")
print("割合%", fy[[f"{c}_割合%" for c in TYPES] + ["単身高齢者世帯_割合%", "高齢者世帯のうち単身%"]].round(1).to_string(), sep="\n")
print(ch.round(1).to_string())
print("月次のピーク", peak.date(), int(m["total"].max()))
print("3月の段差", step.loc[3].to_dict())

# ===== 図1：世帯数と実人員の推移、類型別の月次 =====
LAB = {"高齢者世帯": "高齢者世帯", "母子世帯": "母子世帯", "障害者世帯": "障害者世帯", "傷病者世帯": "傷病者世帯", "その他の世帯": "その他の世帯"}
COL = {"高齢者世帯": BLUE, "母子世帯": PURPLE, "障害者世帯": GREEN, "傷病者世帯": ORANGE, "その他の世帯": GRAY}
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1, 1.25]})
base = m.iloc[0]
ax[0].plot(m.index, m["total"] / base["total"] * 100, color=BLUE, lw=2, label=f"世帯数（年度平均 {int(fy.loc[2012,'total'])/1e4:.0f}万→{int(fy.loc[2024,'total'])/1e4:.0f}万）")
ax[0].plot(m.index, m["実人員"] / base["実人員"] * 100, color=ORANGE, lw=2, label=f"実人員（年度平均 {fy.loc[2012,'実人員']/1e4:.0f}万→{fy.loc[2024,'実人員']/1e4:.0f}万）")
ax[0].axhline(100, color=GRAY, lw=.8, ls=":")
ax[0].set_title("世帯数は増え、人数は減った（2012年4月＝100）", loc="left")
ax[0].legend(frameon=False, fontsize=9, loc="lower left")
for c in TYPES:
    ax[1].plot(m.index, m[c] / 1e4, color=COL[c], lw=1.8)
    ax[1].text(m.index[-1] + pd.Timedelta(days=40), m[c].iloc[-1] / 1e4, f"{LAB[c]} {m[c].iloc[-1]/1e4:.1f}万", color=COL[c], va="center", fontsize=9)
ax[1].set_title("世帯類型別の被保護世帯数（万世帯、月次）", loc="left")
ax[1].set_xlim(m.index[0], m.index[-1] + pd.Timedelta(days=1000))
ax[1].set_xticks([pd.Timestamp(y, 1, 1) for y in range(2014, 2026, 2)]); ax[1].set_xticklabels(range(2014, 2026, 2))
ax[1].text(0.01, 0.62, "毎年3月に高齢者世帯が増え\nほかが減る段差がある", transform=ax[1].transAxes, fontsize=8.5, color=INK)
fig.text(0, -0.03, "注：年度は4月〜翌年3月。現に保護を受けた世帯数（保護停止中を含む）。" + SOURCE, fontsize=7.5, color="#555")
fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

# ===== 図2：構成比（年度平均）と単身高齢者世帯の割合 =====
fig, ax = plt.subplots(figsize=(10, 5))
bottom = np.zeros(len(fy))
for c in TYPES:
    v = fy[f"{c}_割合%"].values
    ax.bar(fy.index, v, bottom=bottom, color=COL[c], width=.75, label=LAB[c], alpha=.9 if c != "その他の世帯" else .7)
    for x_, b_, v_ in zip(fy.index, bottom, v):
        if x_ in (2012, 2024): ax.text(x_, b_ + v_ / 2, f"{v_:.1f}", ha="center", va="center", fontsize=8.5, color="white")
    bottom += v
ax.plot(fy.index, fy["単身高齢者世帯_割合%"], color=INK, marker="o", ms=4, lw=1.5, label="うち単身の高齢者世帯")
for x_ in (2012, 2024):
    ax.annotate(f"{fy.loc[x_, '単身高齢者世帯_割合%']:.1f}%", (x_, fy.loc[x_, "単身高齢者世帯_割合%"]), xytext=(0, -15), textcoords="offset points", ha="center", fontsize=9)
ax.set_ylim(0, 100); ax.set_ylabel("%")
ax.set_xticks(fy.index); ax.set_xticklabels([f"{y}" for y in fy.index], fontsize=9)
ax.set_title("被保護世帯の類型別の割合（年度の1か月平均）", loc="left")
ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(.5, -.08))
fig.text(0, -0.1, "注：年度。" + SOURCE, fontsize=7.5, color="#555")
fig.savefig(FIG / "w1_share.png"); plt.close(fig)

# ===== 図3：2012→2024年度の増減（類型別、期間を2つに分ける） =====
fig, ax = plt.subplots(figsize=(9, 4.6))
order = TYPES + ["total"]
names = [LAB.get(c, "合計") for c in order]
y = np.arange(len(order))[::-1]
v1 = ch.loc[order, "増減(2012→2017)"] / 1e4
v2 = ch.loc[order, "増減(2017→2024)"] / 1e4
ax.barh(y + .18, v1, height=.36, color=LIGHT, label="2012→2017年度")
ax.barh(y - .18, v2, height=.36, color=BLUE, label="2017→2024年度")
for yy, c in zip(y, order):
    tot = ch.loc[c, "増減(2012→2024)"]
    ax.text(max(v1[c], v2[c], 0) + .6, yy, f"計 {tot/1e4:+.1f}万（{ch.loc[c,'増減率%']:+.0f}%）", va="center", fontsize=9)
ax.axvline(0, color=INK, lw=.8)
ax.set_yticks(y); ax.set_yticklabels(names)
ax.set_xlabel("年度の1か月平均の増減（万世帯）")
ax.set_xlim(-14, 32)
ax.set_title("類型別の増減：2017年度までは高齢者世帯が大きく増えた", loc="left")
ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.text(0, -0.06, SOURCE, fontsize=7.5, color="#555")
fig.savefig(FIG / "w1_change.png"); plt.close(fig)
print("saved")
