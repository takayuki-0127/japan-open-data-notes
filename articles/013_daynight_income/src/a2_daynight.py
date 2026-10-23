"""A2：昼に人が集まる街は、所得が高い街か（昼夜間人口比、2020年国勢調査）"""
from common import *

d = load()
d["dn"] = d["A6107"] / d["A1101"] * 100                 # 昼夜間人口比（昼間人口 ÷ 夜間人口 × 100）
d["log_dn"] = np.log(d["dn"])
d["z_dn"] = (d["log_dn"] - d["log_dn"].mean()) / d["log_dn"].std()
CONTROLS.append("dn"); LABEL["dn"] = "昼夜間人口比（対数）"

def steps_dn(df):
    others = [c for c in CONTROLS if c not in ("dn", "log_inc")]
    specs = [("そのまま（何もそろえない）", "log_inc ~ z_dn"), ("＋都道府県", "log_inc ~ z_dn + C(pref_code)"),
             ("＋年齢構成", "log_inc ~ z_dn + z_old + C(pref_code)"),
             ("＋ほかの条件すべて", "log_inc ~ z_dn + " + " + ".join("z_" + c for c in others) + " + C(pref_code)")]
    rows = []
    for name, f in specs:
        r = smf.ols(f, df).fit(cov_type="HC3")
        rows.append({"model": name, "coef": (np.exp(r.params["z_dn"]) - 1) * 100, "lo": (np.exp(r.conf_int().loc["z_dn", 0]) - 1) * 100,
                     "hi": (np.exp(r.conf_int().loc["z_dn", 1]) - 1) * 100, "p": r.pvalues["z_dn"], "r2": r.rsquared, "n": int(r.nobs)})
    return pd.DataFrame(rows)

t = steps_dn(d); t.round(4).to_csv(RES / "a2_steps.csv", index=False, encoding="utf-8-sig"); print(t.round(3))
# 頑健性：外れ値・小さな町・23区を除く
rob = []
for name, sub in [("全体", d), ("昼夜間人口比 200 超を除く（千代田区・大熊町など）", d[d.dn <= 200]), ("人口5,000人未満を除く", d[d.A1101 >= 5000]),
                  ("東京23区を除く", d[~d.ward23]), ("上下1%を除く", d[d.dn.between(d.dn.quantile(.01), d.dn.quantile(.99))])]:
    r = steps_dn(sub).iloc[-1]; rob.append({"sample": name, "coef_pct": r.coef, "lo": r.lo, "hi": r.hi, "p": r.p, "n": r.n})
rob = pd.DataFrame(rob); rob.round(3).to_csv(RES / "a2_robust.csv", index=False, encoding="utf-8-sig"); print(rob.round(3))
d["type"] = np.select([d.dn >= 110, d.dn < 90], ["昼に人が集まる（110以上）", "昼に人が出ていく（90未満）"], "その間（90〜110）")
g = d.groupby("type").agg(n=("inc", "size"), median_inc=("inc", "median"), median_univ=("univ", "median"), median_old=("old", "median")).round(3)
g.to_csv(RES / "a2_type.csv", encoding="utf-8-sig"); print(g)
s = {"n": len(d), "median_dn": d.dn.median(), "n_over110": int((d.dn >= 110).sum()), "n_under90": int((d.dn < 90).sum()),
     "corr_logdn_loginc": np.corrcoef(d.log_dn, d.log_inc)[0, 1], "sd_log_dn": d.log_dn.std()}
pd.Series(s).round(3).to_csv(RES / "a2_summary.csv", header=["value"]); print(pd.Series(s).round(3))

# 図1：散布図
fig, ax = plt.subplots(figsize=(8, 5))
o = d[~d.ward23]; w = d[d.ward23]
ax.scatter(o.dn, o.inc, s=9, color=GRAY, alpha=0.55, lw=0, label="市町村")
ax.scatter(w.dn, w.inc, s=18, color=BLUE, label="東京23区")
for n in ["千代田区", "港区", "大熊町", "飛島村", "狛江市", "七ヶ浜町"]:
    r = d[d["name"] == n].iloc[0]; ax.annotate(n, (r.dn, r.inc), xytext=(5, 2), textcoords="offset points", fontsize=8, color="#52514e")
ax.set_xscale("log"); ax.set_yscale("log")
from matplotlib.ticker import FixedLocator, NullLocator
ax.xaxis.set_major_locator(FixedLocator([70, 100, 150, 200, 400, 1000])); ax.xaxis.set_minor_locator(NullLocator()); ax.set_xticklabels(["70", "100", "150", "200", "400", "1,000"])
ax.yaxis.set_major_locator(FixedLocator([250, 300, 400, 600, 1000, 1800])); ax.yaxis.set_minor_locator(NullLocator()); ax.set_yticklabels(["250", "300", "400", "600", "1,000", "1,800"])
ax.axvline(100, color=INK, lw=0.6, ls=":")
ax.set_xlabel("昼夜間人口比（昼間人口 ÷ 夜間人口 × 100、対数目盛）"); ax.set_ylabel("納税者1人あたり所得（万円、対数目盛）")
ax.legend(frameon=False, loc="upper left"); ax.set_title(f"昼に人が集まる街は、所得が高めに見える（相関 {s['corr_logdn_loginc']:.2f}）", loc="left")
fig.text(0.01, -0.03, SOURCE + "（昼夜間人口比は2020年国勢調査）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "a2_scatter.png"); plt.close(fig)

# 図2：条件をそろえても残るか
plot_steps(t, "全体で見ると、条件をそろえても係数は残った", "昼夜間人口比が1標準偏差高いと、所得が何%違うか", FIG / "a2_steps.png")

# 図3：頑健性
fig, ax = plt.subplots(figsize=(8, 3.4)); y = np.arange(len(rob))[::-1]
col = [BLUE if p < 0.05 else GRAY for p in rob.p]
ax.hlines(y, rob.lo, rob.hi, color=col, lw=2.5); ax.scatter(rob.coef_pct, y, color=col, zorder=3)
for yi, (_, r) in zip(y, rob.iterrows()):
    ax.text(r.hi + 0.15, yi, f"{r.coef_pct:+.1f}%（n={r.n:,}）" + ("" if r.p < 0.05 else "　はっきりしない"), va="center", fontsize=9)
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y, rob["sample"]); ax.set_xlim(-1, rob.hi.max() + 3.5)
ax.set_xlabel("すべての条件をそろえたときの係数（1標準偏差あたり、%）"); ax.set_title("東京23区を除くと、0と区別できなくなる", loc="left")
fig.text(0.01, -0.08, SOURCE + "／都道府県固定効果・HC3。灰色は95%区間が0をまたぐ", fontsize=8, color="#8a8984"); fig.savefig(FIG / "a2_robust.png"); plt.close(fig)
