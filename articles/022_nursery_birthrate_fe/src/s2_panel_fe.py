"""S2：都道府県×年のパネルで、保育所の定員・有効求人倍率と合計特殊出生率の関係を固定効果モデルで見る（2012〜2022年）"""
from common import *
import statsmodels.formula.api as smf

d, lab = read("SSDSE-B-2026")
d = d.rename(columns={d.columns[0]: "year", d.columns[1]: "code", d.columns[2]: "pref"})
d = d[(d.code != "R00000")].copy()
yr = d.groupby("year").apply(lambda g: (g.J2505 / g.A1301).mean() * 100)
yr.round(2).to_csv(RES / "s2_capacity_by_year.csv", header=["capacity_per_100_under15"])
d = d[d.year <= 2022].copy()            # 2023年は保育所等定員の水準が前年から大きく下がっており、定義の変更の可能性があるので除く
d["tfr"] = d.A4103
d["cap"] = d.J2505 / d.A1301 * 100                  # 15歳未満100人あたりの保育所等定員
d["job"] = d.F3103 / d.F3102                        # 有効求人倍率（一般）
d["marr"] = d.A9101 / d.A1302 * 1000                # 15〜64歳1,000人あたり婚姻件数
specs = [("そのまま（プールした OLS）", "{y} ~ {x}"), ("＋都道府県の固定効果", "{y} ~ {x} + C(pref)"), ("＋年の固定効果（二方向）", "{y} ~ {x} + C(pref) + C(year)")]
rows = []
for y, x in [("tfr", "cap"), ("tfr", "job"), ("marr", "job")]:
    for name, f in specs:
        r = smf.ols(f.format(y=y, x=x), d).fit(cov_type="cluster", cov_kwds={"groups": d["pref"]})
        rows.append({"y": y, "x": x, "model": name, "coef": r.params[x], "lo": r.conf_int().loc[x, 0], "hi": r.conf_int().loc[x, 1], "p": r.pvalues[x], "r2": r.rsquared, "n": int(r.nobs)})
t = pd.DataFrame(rows); t.round(4).to_csv(RES / "s2_models.csv", index=False, encoding="utf-8-sig"); print(t.round(4))
both = smf.ols("tfr ~ cap + job + C(pref) + C(year)", d).fit(cov_type="cluster", cov_kwds={"groups": d["pref"]})
s = {"n": len(d), "years": f"{d.year.min()}-{d.year.max()}", "tfr_2012": d[d.year == 2012].tfr.mean(), "tfr_2022": d[d.year == 2022].tfr.mean(),
     "cap_2012": d[d.year == 2012].cap.mean(), "cap_2022": d[d.year == 2022].cap.mean(),
     "both_cap": both.params["cap"], "both_cap_p": both.pvalues["cap"], "both_job": both.params["job"], "both_job_p": both.pvalues["job"],
     "cap_sd_within": (d.cap - d.groupby("pref").cap.transform("mean")).std(), "job_sd_within": (d.job - d.groupby("pref").job.transform("mean") - d.groupby("year").job.transform("mean") + d.job.mean()).std()}
pd.Series(s).to_csv(RES / "s2_summary.csv", header=["value"]); print(pd.Series(s))
SRC = source("SSDSE-県別推移（SSDSE-B-2026）")

# 図1：県どうしで比べると（2022年）
g = d[d.year == 2022]
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(g.cap, g.tfr, color=BLUE, s=22)
for _, r in g.iterrows():
    if r.pref in ["東京都", "沖縄県", "宮崎県", "福井県", "北海道", "高知県", "大阪府", "島根県"]:
        ax.annotate(r.pref, (r.cap, r.tfr), xytext=(4, 2), textcoords="offset points", fontsize=8, color="#52514e")
b = np.polyfit(g.cap, g.tfr, 1); xs = np.linspace(g.cap.min(), g.cap.max(), 10); ax.plot(xs, np.polyval(b, xs), color=GRAY, lw=1)
ax.set_xlabel("15歳未満100人あたりの保育所等の定員（2022年）"); ax.set_ylabel("合計特殊出生率（2022年）")
ax.set_title("県どうしで比べると、保育所の定員が多い県ほど出生率が高い", loc="left")
fig.text(0.01, -0.03, SRC, fontsize=8, color="#8a8984"); fig.savefig(FIG / "s2_between.png"); plt.close(fig)

# 図2：モデルを変えると係数はどう変わるか
fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
for ax, (y, x, ttl, unit) in zip(axes, [("tfr", "cap", "出生率 ← 保育所の定員", "定員＋10人あたり"), ("tfr", "job", "出生率 ← 有効求人倍率", "倍率＋0.1あたり"), ("marr", "job", "婚姻 ← 有効求人倍率", "倍率＋0.1あたり")]):
    sub = t[(t.y == y) & (t.x == x)].reset_index(drop=True); k = 10 if x == "cap" else 0.1
    yy = np.arange(len(sub))[::-1]
    for yi, (_, r) in zip(yy, sub.iterrows()):
        c = (BLUE if r.coef > 0 else ORANGE) if r.p < 0.05 else GRAY
        ax.hlines(yi, r.lo * k, r.hi * k, color=c, lw=2.5); ax.scatter(r.coef * k, yi, color=c, zorder=3)
        ax.text(r.hi * k, yi + 0.18, f"{r.coef * k:+.3f}", fontsize=8, ha="right")
    ax.axvline(0, color=INK, lw=0.8); ax.set_title(ttl, fontsize=11, loc="left"); ax.set_xlabel(unit, fontsize=9)
axes[0].set_yticks(np.arange(3)[::-1], [s_[0] for s_ in specs])
fig.suptitle("県の固定効果だけだと「定員が増えると出生率が下がる」、年の固定効果も入れると0に近づく", x=0.01, ha="left", fontsize=13)
fig.text(0.01, -0.06, SRC + "（2012〜2022年・47都道府県×11年。都道府県クラスター頑健標準誤差。灰色は95%区間が0をまたぐ）", fontsize=7.5, color="#8a8984")
fig.tight_layout(); fig.savefig(FIG / "s2_coefs.png"); plt.close(fig)

# 図3：年ごとの推移（全国の流れ）
m = d.groupby("year")[["tfr", "cap", "job"]].mean()
fig, ax = plt.subplots(figsize=(8, 3.8)); ax2 = ax.twinx()
ax.plot(m.index, m.tfr, color=BLUE, marker="o", ms=4, label="合計特殊出生率（左）")
ax2.plot(m.index, m.cap, color=ORANGE, marker="s", ms=4, label="保育所等の定員（右、15歳未満100人あたり）")
ax.set_ylabel("合計特殊出生率（47都道府県の平均）"); ax2.set_ylabel("保育所等の定員"); ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="lower left")
ax.set_title("定員は毎年増えたが、出生率は2015年をピークに下がった", loc="left")
fig.text(0.01, -0.05, SRC, fontsize=8, color="#8a8984"); fig.savefig(FIG / "s2_trend.png"); plt.close(fig)
