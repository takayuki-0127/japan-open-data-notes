"""A3：人が流入している市区町村は、所得が高い街か（2024年の転入・転出）"""
from common import *

d = load()
d["net_mig"] = (d["A5103"] - d["A5104"]) / d["A2301"] * 1000        # 住民1,000人あたりの転入超過（2024年）
t = steps(d, "net_mig", "log_inc", "所得")
t.round(3).to_csv(RES / "a3_steps.csv", index=False, encoding="utf-8-sig")
fm = full_model(d, "net_mig"); fm.round(3).to_csv(RES / "a3_full.csv", index=False, encoding="utf-8-sig")
s = {"n": len(d), "share_positive": (d.net_mig > 0).mean(), "median": d.net_mig.median(),
     "corr_inc": np.corrcoef(d.log_inc, d.net_mig)[0, 1]}
pd.Series(s).round(3).to_csv(RES / "a3_summary.csv", header=["value"])
d.nlargest(10, "net_mig")[["pref_name", "name", "net_mig", "inc", "A2301"]].round(1).to_csv(RES / "a3_top.csv", index=False, encoding="utf-8-sig")
print(pd.Series(s).round(3)); print(t.round(3)); print(fm.round(3))

fig, ax = plt.subplots(figsize=(8, 5))
o = d[~d.ward23]; w = d[d.ward23]
ax.scatter(o.inc, o.net_mig, s=np.clip(o.A2301 / 5000, 4, 120), color=GRAY, alpha=0.5, lw=0)
ax.scatter(w.inc, w.net_mig, s=np.clip(w.A2301 / 5000, 4, 120), color=BLUE, alpha=0.8, lw=0, label="東京23区")
ax.axhline(0, color=INK, lw=0.8); ax.set_xscale("log")
ax.set_xticks([250, 300, 400, 500, 700, 1000, 1500], ["250", "300", "400", "500", "700", "1,000", "1,500"])
from matplotlib.ticker import NullFormatter; ax.xaxis.set_minor_formatter(NullFormatter())
ax.set_ylim(-40, 40); ax.set_xlabel("納税者1人あたり所得（万円、対数目盛）"); ax.set_ylabel("転入超過（住民1,000人あたり、2024年）")
ax.set_title(f"所得が高い街ほど転入が多い…ように見える（相関 {s['corr_inc']:.2f}）", loc="left"); ax.legend(frameon=False, loc="lower right")
fig.text(0.01, -0.03, SOURCE + "（縦軸は±40で切った。円の大きさは人口）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "a3_scatter.png"); plt.close(fig)
plot_steps(t, "所得の係数は、条件をそろえるほど小さくなり、最後は0と区別できない", "所得が1標準偏差高いと、転入超過は1,000人あたり何人違うか", FIG / "a3_steps.png")
plot_coefs(fm, f"転入超過と関係していたのは大卒の割合と人口密度（決定係数 {fm.r2.iloc[0]:.2f}）", "1標準偏差あたり、転入超過が1,000人あたり何人違うか", FIG / "a3_coefs.png")
