"""W2：木造の非住宅は増えたか（構造別×用途別の床面積、民間非居住の用途別）"""
from common import *

# 1) 構造別（暦年、1951〜）
s = load("structure_year.csv")
sv = s.pivot(index="year", columns="structure", values="floor_1000m2").fillna(0)
sh = sv.drop(columns="総計").div(sv["総計"], axis=0)
sh.round(4).to_csv(RES / "w2_structure_share.csv", encoding="utf-8")

# 2) 構造×用途（年度、1988〜）
d = load("structure_use_fy.csv")
NONRES = ["事務所", "店舗", "工場・作業場", "倉庫", "学校", "病院・診療所", "その他の非住宅"]
d["group"] = np.where(d.use.isin(NONRES), "非住宅", np.where(d.use == "居住専用", "居住専用", "居住産業併用"))
g = d.groupby(["fy", "group", "structure"]).floor_m2.sum().unstack("structure")
wood = (g["木造"] / g["総計"]).unstack("group")
nr = d[d.use.isin(NONRES)].groupby(["fy", "structure"]).floor_m2.sum().unstack()
wood["非住宅_木造_千m2"] = nr["木造"] / 1e3; wood["非住宅_計_千m2"] = nr["総計"] / 1e3
wood.round(4).to_csv(RES / "w2_wood_share_fy.csv", encoding="utf-8")
byuse = d[d.use.isin(NONRES)].pivot_table(index="fy", columns=["use", "structure"], values="floor_m2", aggfunc="sum")
wu = pd.DataFrame({u: byuse[(u, "木造")] / byuse[(u, "総計")] for u in NONRES})
wu.round(4).to_csv(RES / "w2_wood_share_by_use.csv", encoding="utf-8")
wood_m2 = pd.DataFrame({u: byuse[(u, "木造")] / 1e3 for u in NONRES})
wood_m2.round(1).to_csv(RES / "w2_wood_floor_by_use_1000m2.csv", encoding="utf-8")

# トレンド（2010〜2025年度の非住宅の木造率、年あたりの変化）
import statsmodels.api as sm
yy = wood.loc[2010:2025, "非住宅"]
X = sm.add_constant(yy.index.values - 2010); m = sm.OLS(yy.values * 100, X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
tr = pd.DataFrame({"slope_pt_per_year": [m.params[1]], "se": [m.bse[1]], "from": [2010], "to": [2025]})
tr.round(3).to_csv(RES / "w2_trend.csv", index=False, encoding="utf-8")

# 3) 民間非居住の用途別（暦年に合計、2005〜2025）
p = load("private_nonres_month.csv")
py = p[(p.year >= 2005) & (p.year <= 2025)].groupby(["year", "use"]).floor_1000m2.sum().unstack()
py.round(1).to_csv(RES / "w2_private_nonres_year.csv", encoding="utf-8")

# 図1：構造別の割合（暦年）
fig, ax = plt.subplots(figsize=(8, 4.4))
cs = sh[["木造", "鉄骨造", "鉄筋コンクリート造", "鉄骨鉄筋コンクリート造"]]
ax.stackplot(cs.index, *(cs[c] * 100 for c in cs), colors=[GREEN, BLUE, ORANGE, PURPLE], labels=cs.columns, alpha=.9)
ax.set_ylim(0, 100); ax.set_ylabel("着工床面積に占める割合（%）"); ax.legend(frameon=False, fontsize=8, loc="lower left", ncol=2)
ax.set_title(f"構造別の割合：木造は{sh['木造'].idxmin()}年の{sh['木造'].min()*100:.0f}%から2025年に{sh.loc[2025,'木造']*100:.0f}%")
note(fig); fig.savefig(FIG / "w2_structure.png"); plt.close(fig)

# 図2：非住宅の木造率（年度）
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2))
ax[0].plot(wood.index, wood["非住宅"] * 100, color=GREEN, lw=2.2, label="非住宅（7用途の合計）")
ax[0].plot(wood.index, wood["居住専用"] * 100, color=BLUE, lw=1.5, label="居住専用（住宅）")
ax[0].set_ylabel("床面積の木造率（%）"); ax[0].legend(frameon=False, fontsize=9); ax[0].set_ylim(0, 80); ax[0].set_title("木造率（年度）")
last = wu.loc[2025].sort_values()
ax[1].barh(last.index, wu.loc[2010, last.index] * 100, color=LIGHT, label="2010年度", height=.4, align="edge")
ax[1].barh(last.index, last * 100, color=GREEN, label="2025年度", height=-.4, align="edge")
for i, (k, v) in enumerate(last.items()):
    ax[1].text(max(v, wu.loc[2010, k]) * 100 + .5, i, f"{wu.loc[2010,k]*100:.1f}→{v*100:.1f}%", va="center", fontsize=8)
ax[1].set_xlabel("床面積の木造率（%）"); ax[1].legend(frameon=False, fontsize=8, loc="lower right"); ax[1].set_title("用途別の木造率"); ax[1].set_xlim(0, 45)
note(fig); fig.savefig(FIG / "w2_wood_nonres.png"); plt.close(fig)

# 図3：民間非居住の用途別
fig, ax = plt.subplots(figsize=(8, 4.4))
for c, col in [("倉庫", ORANGE), ("工場", BLUE), ("店舗", PURPLE), ("事務所", INK), ("医療，福祉用", GREEN)]:
    ax.plot(py.index, py[c] / 1e3, color=col, lw=1.8, label=c)
ax.set_ylabel("着工床面積（百万㎡、民間、暦年）"); ax.legend(frameon=False, ncol=5, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.08)); ax.set_ylim(0, None)
ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax.set_title("民間の非居住建築物：倉庫が工場・店舗を上回る")
note(fig); fig.savefig(FIG / "w2_private_use.png"); plt.close(fig)

# 表示
print(sh.loc[[1951, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025]].round(3).to_string())
print("wood min", sh["木造"].idxmin(), sh["木造"].min().round(3))
print(sv.loc[[1973, 1990, 1996, 2006, 2010, 2025], ["総計", "木造", "鉄骨造", "鉄筋コンクリート造"]].round(0).to_string())
print(wood.loc[[1988, 1995, 2000, 2005, 2010, 2015, 2020, 2023, 2024, 2025]].round(3).to_string())
print(wu.loc[[1988, 2000, 2010, 2015, 2020, 2025]].round(3).to_string())
print(wood_m2.loc[[1988, 2000, 2010, 2015, 2020, 2025]].round(0).to_string())
print(tr.round(3).to_string())
print(py.loc[[2005, 2010, 2015, 2020, 2024, 2025], ["非居住計", "倉庫", "工場", "店舗", "事務所", "医療，福祉用"]].round(0).to_string())
print((py["倉庫"] > py["工場"]).loc[lambda s: s].index.tolist())
