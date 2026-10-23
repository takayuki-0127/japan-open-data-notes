"""W2：獣の捕獲は「狩猟」から「許可による捕獲」へ移ったか。狩猟免状の種類はどう変わったか"""
from common import *

hunt, permit, lic = load()
nat = hunt[hunt.area == "全国"].pivot(index="fy", columns="species", values="value")
pn = permit[permit.area == "全国"].set_index("fy").value
df = pd.DataFrame({"狩猟_獣類": nat["獣類計"], "許可_獣類": pn, "狩猟_ニホンジカ": nat["ニホンジカ"], "狩猟_イノシシ": nat["イノシシ"]})
df["合計"] = df["狩猟_獣類"] + df["許可_獣類"]
df["許可の割合%"] = 100 * df["許可_獣類"] / df["合計"]
df.round(2).to_csv(RES / "w2_hunt_vs_permit.csv")
print(df.round(1).to_string())
for a, b in [(1998, 2021), (2008, 2021), (1998, 2008)]:
    print(a, b, "許可", round(df.loc[b, "許可_獣類"] / df.loc[a, "許可_獣類"], 2), "狩猟", round(df.loc[b, "狩猟_獣類"] / df.loc[a, "狩猟_獣類"], 2))
y0 = df["許可の割合%"]
print("許可が狩猟を上回った最初の年度", y0[y0 > 50].index.min())

# 都道府県（2021年度）：許可の割合
hp = hunt[(hunt.area != "全国") & (hunt.species == "獣類計") & (hunt.fy == 2021)].set_index("area").value
pp = permit[(permit.area != "全国") & (permit.fy == 2021)].set_index("area").value
pr = pd.DataFrame({"狩猟": hp, "許可": pp}).fillna(0)
pr["許可の割合%"] = 100 * pr["許可"] / (pr["狩猟"] + pr["許可"])
pr = pr.sort_values("許可の割合%")
pr.round(2).to_csv(RES / "w2_pref_2021.csv")
print(pr.round(1).head(6).to_string()); print(pr.round(1).tail(6).to_string())
print("中央値", round(pr["許可の割合%"].median(), 1), "許可が多い県の数", int((pr["許可の割合%"] > 50).sum()))
hp0 = hunt[(hunt.area != "全国") & (hunt.species == "獣類計") & (hunt.fy == 2008)].set_index("area").value
pp0 = permit[(permit.area != "全国") & (permit.fy == 2008)].set_index("area").value
s0 = 100 * pp0 / (hp0 + pp0)
print("2008 許可が多い県の数", int((s0 > 50).sum()), "中央値", round(s0.median(), 1))

# 狩猟免状：わな（網を含む）と銃
L = lic.set_index("fy")
trap = pd.concat([L.loc[:2000, "kou"], L.loc[2001:2004, "ami_wana"], L.loc[2005:2006, "ami"], L.loc[2007:, "wana"]])
gun = L["gun1"].fillna(L["otsu"])
lt = pd.DataFrame({"総計": L["total"], "網・わな（2006年度まで）／わな（2007年度から）": trap, "網（2007年度から）": L["ami"].where(L.index >= 2007), "第一種銃猟（2000年度まで乙種）": gun, "第二種銃猟（空気銃、2000年度まで丙種）": L["gun2"].fillna(L["hei"])})
lt.to_csv(RES / "w2_license.csv")
print(lt.to_string())

# 図1：狩猟と許可
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.plot(df.index, df["許可_獣類"] / 1e4, color=ORANGE, lw=2.2, marker="o", ms=3.5, label="許可による捕獲（都道府県知事の許可）")
ax.plot(df.index, df["狩猟_獣類"] / 1e4, color=BLUE, lw=2.2, marker="o", ms=3.5, label="狩猟による捕獲")
for y in (1998, 2021):
    for col, c in (("許可_獣類", ORANGE), ("狩猟_獣類", BLUE)):
        ax.annotate(f"{df.loc[y, col]/1e4:.1f}万", (y, df.loc[y, col] / 1e4), xytext=(0, 7) if not (y == 2021 and col == "許可_獣類") else (-6, -14), textcoords="offset points", ha="center" if not (y == 2021 and col == "許可_獣類") else "right", fontsize=8.5, color=c)
ax.set_title("獣類の捕獲数：狩猟と許可による捕獲（全国、年度）")
ax.set_ylabel("万頭・匹"); ax.legend(frameon=False, loc="upper left")
ax.set_xlim(1997.3, 2021.7)
foot(fig, "許可による捕獲は表12（1）総括表の獣類の捕獲数の合計（被害防止、数の調整、学術研究など）。環境大臣の許可（表14）は含まない")
fig.savefig(FIG / "w2_hunt_permit.png"); plt.close(fig)

# 図2：都道府県（2021年度）許可の割合
fig, ax = plt.subplots(figsize=(7.4, 8.2))
ax.barh(pr.index, pr["許可の割合%"], color=[ORANGE if v > 50 else BLUE for v in pr["許可の割合%"]])
ax.axvline(50, color=GRAY, lw=1, ls="--")
ax.set_title("獣類の捕獲のうち許可による捕獲の割合（2021年度）")
ax.set_xlabel("%"); ax.set_xlim(0, 100); ax.tick_params(axis="y", labelsize=8)
foot(fig, "割合＝許可による捕獲÷（狩猟＋許可による捕獲）")
fig.savefig(FIG / "w2_pref.png"); plt.close(fig)

# 図3：狩猟免状
fig, ax = plt.subplots(figsize=(8.6, 4.4))
t = lt.iloc[:, 1]
ax.plot(t.loc[:2006].index, t.loc[:2006] / 1e4, color=ORANGE, lw=2.2, marker="o", ms=3.5, label="網・わな猟（2006年度まで。2000年度までは甲種）")
ax.plot(t.loc[2007:].index, t.loc[2007:] / 1e4, color=ORANGE, lw=2.2, marker="s", ms=3.5, ls="-", alpha=0.85, label="わな猟（2007年度から網と分かれた）")
ax.plot(lt.index, lt["第一種銃猟（2000年度まで乙種）"] / 1e4, color=BLUE, lw=2.2, marker="o", ms=3.5, label="第一種銃猟（2000年度まで乙種）")
ax.plot(lt.index, lt["総計"] / 1e4, color=GRAY, lw=1.5, ls="--", label="総計")
ax.set_title("狩猟免状の交付件数（全国、年度）")
ax.set_ylabel("万件"); ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.76), fontsize=9.5)
ax.set_xlim(1997.3, 2021.7); ax.set_ylim(0, 25)
foot(fig, "交付件数は有効な免状の件数で人数ではない（1人が複数の種類を持つことがある）。免状は3年ごとに更新。\n2007年度に網とわなが別の免許になり、両方を持つ人が2件に数えられるため、総計がこの年度に増えている")
fig.savefig(FIG / "w2_license.png"); plt.close(fig)
