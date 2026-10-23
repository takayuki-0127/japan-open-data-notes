"""A4：出生・婚姻が多い市区町村は、所得が高い街か（2023年の出生数・婚姻件数）"""
from common import *

d = load()
d["birth"] = d["A4101"] / d["A1302"] * 1000       # 15〜64歳人口1,000人あたりの出生数（2023年）
d["marr"] = d["A9101"] / d["A1302"] * 1000        # 同・婚姻件数
d = d[d["A1302"] >= 500].copy()                    # 15〜64歳が極端に少ない町は率が跳ねるので除く
out = {}
for y in ["birth", "marr"]:
    t = steps(d, y, "log_inc", "所得"); t.round(3).to_csv(RES / f"a4_{y}_steps.csv", index=False, encoding="utf-8-sig")
    fm = full_model(d, y); fm.round(3).to_csv(RES / f"a4_{y}_full.csv", index=False, encoding="utf-8-sig")
    out[y] = (t, fm)
    print(y); print(t.round(3)); print(fm.round(3))
s = {"n": len(d), "birth_median": d.birth.median(), "marr_median": d.marr.median(),
     "corr_birth_inc": np.corrcoef(d.log_inc, d.birth)[0, 1], "corr_birth_old": np.corrcoef(d.old, d.birth)[0, 1],
     "corr_birth_marr": np.corrcoef(d.marr, d.birth)[0, 1]}
pd.Series(s).round(3).to_csv(RES / "a4_summary.csv", header=["value"]); print(pd.Series(s).round(3))

fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, x, xl in ((axs[0], "inc", "納税者1人あたり所得（万円、対数）"), (axs[1], "old", "65歳以上の割合（%）")):
    xv = d[x] * (100 if x == "old" else 1)
    ax.scatter(xv, d.birth, s=8, color=GRAY, alpha=0.5, lw=0)
    if x == "inc":
        ax.set_xscale("log"); ax.set_xticks([250, 300, 400, 600, 1000], ["250", "300", "400", "600", "1,000"])
        from matplotlib.ticker import NullFormatter; ax.xaxis.set_minor_formatter(NullFormatter())
    c = np.corrcoef(np.log(d[x]) if x == "inc" else d[x], d.birth)[0, 1]
    ax.set_title(f"相関 {c:+.2f}", loc="left", fontsize=11); ax.set_xlabel(xl)
axs[0].set_ylabel("出生数（15〜64歳1,000人あたり、2023年）"); axs[0].set_ylim(0, 25)
fig.suptitle("出生が多い街は、所得より「若さ」と強く結びついている", x=0.01, ha="left", fontsize=13)
fig.text(0.01, -0.03, SOURCE + "（15〜64歳が500人未満の町を除く。縦軸は25で切った）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "a4_scatter.png"); plt.close(fig)
plot_steps(out["birth"][0], "出生と所得の関係は、年齢構成をそろえると消える", "所得が1標準偏差高いと、出生数は1,000人あたり何人違うか", FIG / "a4_birth_steps.png")
plot_steps(out["marr"][0], "婚姻と所得の関係も、条件をそろえると消える", "所得が1標準偏差高いと、婚姻件数は1,000人あたり何件違うか", FIG / "a4_marr_steps.png")
