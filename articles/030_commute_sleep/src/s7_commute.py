"""S7：通勤・通学に時間がかかる県では、その分、何の時間が短いのか（社会生活基本調査 2021年、1日の時間配分）"""
from common import *
import statsmodels.formula.api as smf
d, lab = read("SSDSE-D-2023")
d = d.rename(columns={d.columns[0]: "sex", d.columns[1]: "code", d.columns[2]: "pref"})
e, _ = read("SSDSE-E-2026"); e = e.rename(columns={e.columns[0]: "code", e.columns[1]: "pref"}); e = e[e.code.str.startswith("R")].copy()
for c in ["A1101", "A1303"]: e[c] = pd.to_numeric(e[c])
e["old"] = e.A1303 / e.A1101 * 100
ACT = {f"MG{i:02d}": lab[f"MG{i:02d}"] for i in range(1, 21)}       # 10歳以上の全員の平均（分／日、週全体）
SHORT = {"MG01": "睡眠", "MG02": "身の回りの用事", "MG03": "食事", "MG05": "仕事", "MG06": "学業", "MG07": "家事", "MG09": "育児", "MG10": "買い物",
         "MG11": "移動（通勤以外）", "MG12": "テレビ・ラジオ・新聞・雑誌", "MG13": "休養・くつろぎ", "MG15": "趣味・娯楽", "MG16": "スポーツ", "MG18": "交際・付き合い"}
def hm(s): h, m = str(s).split(":"); return int(h) * 60 + int(m)
for c in ["MH01", "MH04", "MH51", "MH52"]: d[c + "_min"] = d[c].map(hm)
tot = d[(d.sex == "0_総数") & (d.code != "R00000")].merge(e[["code", "old"]], on="code")
for c in list(ACT) + ["MG51", "MG52"]: tot[c] = pd.to_numeric(tot[c])
print(tot[["pref", "MG04", "MG51"]].sort_values("MG51").iloc[[0, 1, 2, -3, -2, -1]])
# 1) 通勤・通学の時間（全員平均 MG04）が10分長い県ほど、ほかの活動は何分違うか（65歳以上の割合をそろえる）
rows = []
for c, nm in SHORT.items():
    r = smf.ols(f"{c} ~ MG04 + old", tot).fit(cov_type="HC3")
    rows.append({"activity": nm, "code": c, "national": float(d[(d.sex == "0_総数") & (d.code == "R00000")][c].iloc[0]),
                 "per10min": r.params["MG04"] * 10, "lo": r.conf_int().loc["MG04", 0] * 10, "hi": r.conf_int().loc["MG04", 1] * 10, "p": r.pvalues["MG04"]})
t = pd.DataFrame(rows).sort_values("per10min"); t.round(3).to_csv(RES / "s7_tradeoff.csv", index=False, encoding="utf-8-sig"); print(t.round(2))
# 2) 起床・就寝の時刻（通勤する人の通勤時間 MG51 と）
r_wake = smf.ols("MH01_min ~ MG51 + old", tot).fit(cov_type="HC3"); r_bed = smf.ols("MH04_min ~ MG51 + old", tot).fit(cov_type="HC3")
r_home = smf.ols("MH52_min ~ MG51 + old", tot).fit(cov_type="HC3")
nat = d[(d.sex == "0_総数") & (d.code == "R00000")].iloc[0]
s = {"commute_all_nat": float(nat.MG04), "commute_users_nat": float(nat.MG51), "commute_users_min": tot.MG51.min(), "commute_users_min_pref": tot.loc[tot.MG51.idxmin(), "pref"],
     "commute_users_max": tot.MG51.max(), "commute_users_max_pref": tot.loc[tot.MG51.idxmax(), "pref"],
     "commute_all_min": tot.MG04.min(), "commute_all_max": tot.MG04.max(), "commute_all_max_pref": tot.loc[tot.MG04.idxmax(), "pref"],
     "wake_per10": r_wake.params.MG51 * 10, "wake_p": r_wake.pvalues.MG51, "bed_per10": r_bed.params.MG51 * 10, "bed_p": r_bed.pvalues.MG51,
     "home_per10": r_home.params.MG51 * 10, "home_p": r_home.pvalues.MG51,
     "corr_commute_sleep": np.corrcoef(tot.MG04, tot.MG01)[0, 1], "sum_of_slopes_all": None}
# 全部の活動の係数の合計（＝−10分になるはず。時間の合計は1,440分で一定）
allc = sum(smf.ols(f"{c} ~ MG04 + old", tot).fit().params["MG04"] * 10 for c in ACT if c != "MG04"); s["sum_of_slopes_all"] = allc
pd.Series(s).to_csv(RES / "s7_summary.csv", header=["value"]); print(pd.Series(s))
tot[["pref", "MG04", "MG51", "MG01", "MG13", "MG12", "MH01", "MH04", "MH52", "old"]].sort_values("MG51").to_csv(RES / "s7_pref.csv", index=False, encoding="utf-8-sig")

SRC = "出典：独立行政法人統計センター「SSDSE-社会生活（SSDSE-D-2023）」「SSDSE-基本素材（SSDSE-E-2026）」（https://www.nstac.go.jp/use/literacy/ssdse/）をもとに作成者が加工して作成"
fig, ax = plt.subplots(figsize=(8.5, 5)); y = np.arange(len(t))
ax.errorbar(t.per10min, y, xerr=[t.per10min - t.lo, t.hi - t.per10min], fmt="o", color=BLUE, ecolor=LIGHT, capsize=3)
sig = t.p < 0.05; ax.scatter(t.per10min[sig], y[sig], color=ORANGE, zorder=3, label="0と区別できる（5%）")
ax.axvline(0, color=INK, lw=0.7); ax.set_yticks(y, t.activity); ax.set_xlabel("通勤・通学が10分長い県で、その活動が何分違うか（1日あたり）")
ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("通勤が長い県で、はっきり短いのは睡眠（10分あたり約7分）", loc="left")
fig.text(0.01, -0.06, SRC + "\n（10歳以上の全員の平均、週全体。65歳以上の割合をそろえた重回帰、線は95%区間）", fontsize=6.8, color="#8a8984"); fig.savefig(FIG / "s7_tradeoff.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.scatter(tot.MG51, tot.MH04_min, s=24, color=LIGHT, edgecolor=BLUE, lw=0.6)
for _, r in tot[tot.pref.isin(["東京都", "神奈川県", "千葉県", "埼玉県", "奈良県", "沖縄県", "北海道", "宮崎県"])].iterrows():
    ax.annotate(r.pref, (r.MG51, r.MH04_min), xytext=(4, 2), textcoords="offset points", fontsize=8.5)
lo_, hi_ = int(tot.MH04_min.min()) // 10 * 10, int(tot.MH04_min.max()) // 10 * 10 + 10
ax.set_yticks(range(lo_, hi_ + 1, 10), [f"{m // 60}:{m % 60:02d}" for m in range(lo_, hi_ + 1, 10)])
ax.set_xlabel("通勤・通学する人の、通勤・通学の時間（分／日）"); ax.set_ylabel("平均の就寝時刻")
ax.set_title("通勤が長い県ほど、寝る時刻が遅い（起きる時刻も少し遅い）", loc="left")
fig.text(0.01, -0.04, SRC, fontsize=6.8, color="#8a8984"); fig.savefig(FIG / "s7_bed.png"); plt.close(fig)
