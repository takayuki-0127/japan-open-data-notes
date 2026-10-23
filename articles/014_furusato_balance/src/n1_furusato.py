"""N1：ふるさと納税の「収支」は、どんな街で赤字になるか（令和7年度受入額・令和8年度課税の控除額）"""
from common import *
SRC2 = "出典：総務省「ふるさと納税に関する現況調査」、e-Stat「統計でみる市区町村のすがた2026」ほかを加工して作成"

d = load_extra()
d["bal"] = d.fn_recv - d.fn_cost - d.fn_ded_city          # 受入額 − 募集費用 − 市町村民税の控除額（円）
d["bal_pc"] = d.bal / d.A2301                              # 住民1人あたり（円）
d["donor_rate"] = d.fn_donors / d.C120120 * 100            # 納税者のうち、ふるさと納税をした人の割合（%）
d["ded_pc"] = d.fn_ded_city / d.A2301
s = {"n": len(d), "recv_total_oku": d.fn_recv.sum() / 1e8, "cost_total_oku": d.fn_cost.sum() / 1e8, "cost_ratio": d.fn_cost.sum() / d.fn_recv.sum(),
     "ded_city_total_oku": d.fn_ded_city.sum() / 1e8, "share_muni_positive": (d.bal > 0).mean(),
     "share_pop_in_negative": d.loc[d.bal < 0, "A2301"].sum() / d.A2301.sum(),
     "top10pct_share_of_recv": d.fn_recv.nlargest(int(len(d) * .1)).sum() / d.fn_recv.sum(),
     "median_donor_rate": d.donor_rate.median(), "corr_loginc_donor_rate": np.corrcoef(d.log_inc, d.donor_rate)[0, 1],
     "donor_rate_23ku_median": d.loc[d.ward23, "donor_rate"].median()}
pd.Series(s).round(3).to_csv(RES / "n1_summary.csv", header=["value"]); print(pd.Series(s).round(3))
cols = ["pref_name", "name", "A2301", "fn_recv", "fn_cost", "fn_ded_city", "bal", "bal_pc", "donor_rate"]
d.nsmallest(15, "bal")[cols].round(1).to_csv(RES / "n1_bottom.csv", index=False, encoding="utf-8-sig")
d.nlargest(15, "bal")[cols].round(1).to_csv(RES / "n1_top.csv", index=False, encoding="utf-8-sig")
# 条件をそろえても、所得とふるさと納税の利用率は結びついているか
r = smf.ols("donor_rate ~ z_log_inc + z_old + z_univ + z_log_density + z_mfg + z_primary + z_single + C(pref_code)", d).fit(cov_type="HC3")
pd.DataFrame({"coef": r.params, "p": r.pvalues}).filter(like="z_", axis=0).round(3).to_csv(RES / "n1_donor_model.csv", encoding="utf-8-sig")
print(r.params.filter(like="z_").round(2).to_dict(), round(r.rsquared, 2))

# 図1：所得と、ふるさと納税をした人の割合
fig, ax = plt.subplots(figsize=(8, 5))
o, w = d[~d.ward23], d[d.ward23]
ax.scatter(o.inc, o.donor_rate, s=9, color=GRAY, alpha=0.55, lw=0, label="市町村")
ax.scatter(w.inc, w.donor_rate, s=20, color=BLUE, label="東京23区")
for n in ["港区", "千代田区", "世田谷区", "足立区"]:
    q = d[d["name"] == n].iloc[0]; ax.annotate(n, (q.inc, q.donor_rate), xytext=(5, 2), textcoords="offset points", fontsize=8, color="#52514e")
ax.set_xscale("log")
from matplotlib.ticker import FixedLocator, NullLocator
ax.xaxis.set_major_locator(FixedLocator([250, 300, 400, 600, 1000, 1800])); ax.xaxis.set_minor_locator(NullLocator()); ax.set_xticklabels(["250", "300", "400", "600", "1,000", "1,800"])
ax.set_xlabel("納税者1人あたり所得（万円、対数目盛）"); ax.set_ylabel("納税者のうち、ふるさと納税の控除を受けた人（%）")
ax.legend(frameon=False, loc="lower right"); ax.set_title(f"所得が高い街ほど、ふるさと納税をする人が多い（相関 {s['corr_loginc_donor_rate']:.2f}）", loc="left")
fig.text(0.01, -0.03, SRC2 + "（寄附は2025年中、所得は2023年分）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "n1_donor_rate.png"); plt.close(fig)

# 図2：市区町村の数で見るか、人の数で見るか
fig, ax = plt.subplots(figsize=(8, 2.8))
vals = [("市区町村の数", (d.bal > 0).mean()), ("住んでいる人の数", 1 - s["share_pop_in_negative"])]
for i, (lab, pos) in enumerate(vals[::-1]):
    ax.barh(i, pos * 100, color=BLUE, height=0.55); ax.barh(i, (1 - pos) * 100, left=pos * 100, color=ORANGE, height=0.55)
    ax.text(pos * 50, i, f"黒字 {pos * 100:.0f}%", ha="center", va="center", color="white", fontsize=10)
    ax.text(pos * 100 + (1 - pos) * 50, i, f"赤字 {(1 - pos) * 100:.0f}%", ha="center", va="center", color="white", fontsize=10)
ax.set_yticks([0, 1], [v[0] for v in vals[::-1]]); ax.set_xlim(0, 100); ax.set_xticks([])
for sp in ["bottom", "left"]: ax.spines[sp].set_visible(False)
ax.set_title("7割の市区町村は黒字。でも7割の人は、赤字の街に住んでいる", loc="left")
fig.text(0.01, -0.08, SRC2 + "（収支＝受入額 − 募集の費用 − 市町村民税の控除額）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "n1_share.png"); plt.close(fig)

# 図3：赤字・黒字が大きい市区町村
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, sub, col, ttl in [(axes[0], d.nsmallest(10, "bal"), ORANGE, "赤字が大きい10市区"), (axes[1], d.nlargest(10, "bal"), BLUE, "黒字が大きい10市町")]:
    y = np.arange(len(sub))[::-1]
    ax.barh(y, sub.bal / 1e8, color=col, height=0.65); ax.set_yticks(y, sub["name"])
    for yi, v in zip(y, sub.bal / 1e8):
        ax.text(v + (4 if v > 0 else -4), yi, f"{v:+,.0f}", va="center", ha="left" if v > 0 else "right", fontsize=8)
    ax.set_title(ttl, loc="left", fontsize=11); ax.axvline(0, color=INK, lw=0.8)
axes[0].set_xlim(-420, 0); axes[1].set_xlim(0, 150); axes[0].set_xlabel("収支（億円）"); axes[1].set_xlabel("収支（億円）")
fig.suptitle("赤字は大都市、黒字は地方の市町", x=0.01, ha="left", fontsize=13)
fig.text(0.01, -0.03, SRC2 + "（受入は令和7年度、控除は令和8年度課税＝2025年中の寄附）", fontsize=8, color="#8a8984")
fig.tight_layout(); fig.savefig(FIG / "n1_top_bottom.png"); plt.close(fig)
