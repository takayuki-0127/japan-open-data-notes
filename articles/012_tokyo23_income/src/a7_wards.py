"""A7：東京23区の中の所得の差（23区だけで見る）"""
from common import *

d = load()
w = d[d.ward23].copy()
w["foreign"] = w["A1700"] / w["A1101"] * 100
w["birth"] = w["A4101"] / w["A1302"] * 1000
w["net"] = (w["A5103"] - w["A5104"]) / w["A2301"] * 1000
w = w.sort_values("inc", ascending=False)
nat = d["inc"].quantile([.1, .5, .9])
s = {"n": len(w), "max": w.inc.max(), "min": w.inc.min(), "ratio_max_min": w.inc.max() / w.inc.min(),
     "ratio_4th_min": w.inc.iloc[3] / w.inc.min(), "median_23": w.inc.median(), "national_p50": nat[.5], "national_p90": nat[.9],
     "n_below_national_p90": int((w.inc < nat[.9]).sum()), "univ_min": w.univ.min(), "univ_max": w.univ.max(), "national_univ_median": d.univ.median()}
corr = w[["log_inc", "univ", "old", "single", "foreign", "birth", "net"]].corr()["log_inc"].drop("log_inc")
s.update({"corr_" + k: v for k, v in corr.items()})
pd.Series(s).round(3).to_csv(RES / "a7_summary.csv", header=["value"]); print(pd.Series(s).round(3))
w[["name", "A2301", "inc", "univ", "old", "single", "foreign", "birth", "net"]].round(3).to_csv(RES / "a7_wards.csv", index=False, encoding="utf-8-sig")
# 全国では？（同じ相関を全市区町村で）
corr_all = d.assign(birth=d.A4101 / d.A1302 * 1000)[["log_inc", "univ", "old", "birth"]].corr()["log_inc"]
print("全国の相関", corr_all.round(2).to_dict())
pd.DataFrame({"23区": corr, "全国": corr_all}).round(3).to_csv(RES / "a7_corr.csv", encoding="utf-8-sig")

# 図1：23区の所得（全国の分布の目安つき）
fig, ax = plt.subplots(figsize=(8, 6))
y = np.arange(len(w))[::-1]
ax.barh(y, w.inc, color=[BLUE if i < 3 else LIGHT for i in range(len(w))], height=0.7)
for yi, v in zip(y, w.inc):
    ax.text(v + 15, yi, f"{v:,.0f}", va="center", fontsize=8)
for q, lab in [(.5, "全国の中央値"), (.9, "全国の上位10%")]:
    ax.axvline(nat[q], color=ORANGE if q == .9 else GRAY, lw=1, ls="--")
    ax.text(nat[q] + 12, -1.0 if q == .5 else -1.7, f"{lab} {nat[q]:.0f}万円", fontsize=8, color="#52514e")
ax.set_yticks(y, w["name"]); ax.set_xlabel("納税者1人あたり所得（万円、2024年度＝2023年分）"); ax.set_xlim(0, 2000); ax.set_ylim(-2.2, len(w) - 0.4)
ax.set_title(f"23区の中でも {s['ratio_max_min']:.1f} 倍。上位3区を除くと {s['ratio_4th_min']:.1f} 倍", loc="left")
fig.text(0.01, -0.02, SOURCE, fontsize=8, color="#8a8984"); fig.savefig(FIG / "a7_bars.png"); plt.close(fig)

# 図2：大卒の割合と所得
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(w.univ * 100, w.inc, s=np.clip(w.A2301 / 8000, 15, 140), color=BLUE, alpha=0.8, lw=0)
show = ["港区", "千代田区", "渋谷区", "中央区", "文京区", "目黒区", "世田谷区", "新宿区", "杉並区", "台東区", "足立区", "葛飾区", "江戸川区", "練馬区"]
for _, r in w[w["name"].isin(show)].iterrows():
    ax.annotate(r["name"], (r.univ * 100, r.inc), xytext=(5, 2), textcoords="offset points", fontsize=8, color="#52514e")
ax.set_yscale("log"); ax.set_xlabel("大学・大学院卒の割合（%、2020年）"); ax.set_ylabel("納税者1人あたり所得（万円、対数目盛）")
from matplotlib.ticker import FixedLocator, NullLocator
ax.yaxis.set_major_locator(FixedLocator([400, 600, 800, 1200, 1800])); ax.yaxis.set_minor_locator(NullLocator()); ax.set_yticklabels(["400", "600", "800", "1,200", "1,800"])
ax.set_title(f"23区の中では、大卒の割合が高い区ほど所得が高い（相関 {corr['univ']:.2f}）", loc="left")
fig.text(0.01, -0.03, SOURCE + "（円の大きさは人口）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "a7_univ.png"); plt.close(fig)

# 図3：23区と全国で、所得との相関がどう違うか
lab = {"univ": "大卒の割合", "old": "65歳以上の割合", "birth": "出生率（15〜64歳1,000人あたり）"}
fig, ax = plt.subplots(figsize=(8, 3.4)); k = list(lab)
yy = np.arange(len(k))[::-1]
ax.barh(yy + 0.18, [corr[c] for c in k], height=0.36, color=BLUE, label="23区（23区のみで計算）")
ax.barh(yy - 0.18, [corr_all[c] for c in k], height=0.36, color=GRAY, label="全国（1,740市区町村）")
for c, yi in zip(k, yy):
    ax.text(corr[c] + (0.03 if corr[c] > 0 else -0.03), yi + 0.18, f"{corr[c]:+.2f}", va="center", ha="left" if corr[c] > 0 else "right", fontsize=8)
    ax.text(corr_all[c] + (0.03 if corr_all[c] > 0 else -0.03), yi - 0.18, f"{corr_all[c]:+.2f}", va="center", ha="left" if corr_all[c] > 0 else "right", fontsize=8)
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(yy, [lab[c] for c in k]); ax.set_xlim(-1, 1); ax.set_xlabel("所得（対数）との相関係数")
ax.legend(frameon=False, loc="upper left", fontsize=9); ax.set_title("出生との関係は、23区の中のほうがずっと強い", loc="left")
fig.text(0.01, -0.07, SOURCE + "（出生は2023年、ほかは2020年）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "a7_corr.png"); plt.close(fig)
