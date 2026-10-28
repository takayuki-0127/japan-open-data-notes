"""F83 04 図"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from common import DATA, RES, FIG, MAJOR, SHORT

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
FIG.mkdir(exist_ok=True)
C = dict(within="#2a6fbb", static="#e08a2c", inter="#9a9a9a", total="#222222")
sh = lambda n: SHORT.get(n, n)

pan = pd.read_csv(DATA / "panel.csv")
R = pd.read_csv(RES / "decomp_periods.csv")
ind = pd.read_csv(RES / "industry_levels.csv", index_col=0)
rob = pd.read_csv(RES / "robustness.csv")

# 1 産業の生産性の伸びと就業者シェアの変化
fig, ax = plt.subplots(figsize=(8.5, 6))
x, y = ind.g_ann * 100, ind.ds * 100
ax.axhline(0, color="#bbb", lw=0.8); ax.axvline(0, color="#bbb", lw=0.8)
ax.scatter(x, y, s=ind.s2024 * 3000, color="#2a6fbb", alpha=0.45, edgecolor="#1d4f87")
OFF = {"不動産業": (-60, 22), "教育": (-8, 28), "運輸・郵便業": (10, 16), "鉱業": (-36, -14),
       "公務": (6, -16), "電気・ガス・水道・廃棄物処理業": (-30, 14), "建設業": (6, 8)}
for n in ind.index:
    dx, dy = OFF.get(n, (4, 4))
    ap = dict(arrowstyle="-", color="#999", lw=0.6) if n in OFF else None
    ax.annotate(sh(n), (x[n], y[n]), fontsize=8.5, xytext=(dx, dy), textcoords="offset points", arrowprops=ap)
ax.set_xlabel("1人当たり実質付加価値の伸び（年率、%、1994→2024年）")
ax.set_ylabel("就業者に占める割合の変化（ポイント）")
ax.set_title("生産性が伸びた産業ほど、働く人の割合は減っていた", loc="left", fontsize=13)
ax.text(0.99, 0.97, "円の大きさは2024年の就業者の割合", transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
fig.tight_layout(); fig.savefig(FIG / "f83_industries.png", dpi=150); plt.close(fig)

# 2 期間ごとの分解（年率）
fig, ax = plt.subplots(figsize=(8.5, 5))
lab = [f"{a}→{b}" for a, b in zip(R.y0, R.y1)]
xs = np.arange(len(R))
pos = np.zeros(len(R)); neg = np.zeros(len(R))
for k, nm in [("within", "産業の中の伸び"), ("static", "産業の入れ替わり（静学）"), ("inter", "交差項（動学）")]:
    v = R[k + "_ann"].values * 100
    b = np.where(v >= 0, pos, neg)
    ax.bar(xs, v, bottom=b, color=C[k], label=nm, width=0.6)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(xs, R.ann * 100, "o", color=C["total"], label="1人当たり生産性の伸び（合計）")
for i, v in enumerate(R.ann * 100):
    ax.text(i, max(pos[i], v) + 0.07, f"{v:.2f}%", ha="center", fontsize=9)
ax.axhline(0, color="#888", lw=0.8)
ax.set_xticks(xs, lab); ax.set_ylabel("年率（%ポイント）")
ax.set_title("2013年以降、産業の中の伸びはマイナス。入れ替わりの分だけがプラスだった", loc="left", fontsize=12)
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "f83_periods.png", dpi=150); plt.close(fig)

# 3 産業ごとの寄与（1994→2024）：産業の中の伸び と 相対的な入れ替わり
d = pd.read_csv(RES / "decomp_by_industry_1994_2024.csv", index_col=0)
P0 = (d.p0 * d.s0).sum()
d["static_rel"] = (d.p0 - P0) * (d.s1 - d.s0) / P0
d = d.sort_values("within")
fig, axs = plt.subplots(1, 2, figsize=(10, 6), sharey=True)
axs[0].barh([sh(n) for n in d.index], d.within * 100, color=C["within"])
axs[0].set_title("産業の中の伸び", fontsize=11); axs[0].set_xlabel("%ポイント（30年間の伸び18.2%の内訳）")
axs[1].barh([sh(n) for n in d.index], d.static_rel * 100, color=C["static"])
axs[1].set_title("入れ替わり（平均との差 × 割合の変化）", fontsize=11); axs[1].set_xlabel("%ポイント")
for a in axs: a.axvline(0, color="#888", lw=0.8)
fig.suptitle("30年の伸びの4分の3は製造業の中から。不動産業への入れ替わりはプラスに見える", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f83_by_industry.png", dpi=150); plt.close(fig)

# 4 1人当たりと1時間当たり（1994=100）
base = pan[pan.ind.isin(MAJOR)].copy()
g = base.groupby("year").apply(lambda x: pd.Series(dict(
    per_person=x.real.sum() / x.emp.sum(), per_hour=x.real.sum() / (x.emp * x.hours).sum(),
    hours=(x.emp * x.hours).sum() / x.emp.sum())))
tot = pan[pan.level == "total"].set_index("year")
g["official"] = tot.real / tot.emp
gi = g / g.iloc[0] * 100
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.plot(gi.index, gi.per_person, color=C["within"], lw=2, label="1人当たり（16産業の合計）")
ax.plot(gi.index, gi.per_hour, color=C["static"], lw=2, label="1時間当たり")
ax.plot(gi.index, gi.official, color="#888", lw=1.2, ls="--", label="1人当たり（公表の合計の実質GDP）")
ax.plot(gi.index, gi.hours, color="#666", lw=1, ls=":", label="1人当たり労働時間")
ax.set_ylabel("1994年=100"); ax.legend(fontsize=8.5, frameon=False)
ax.set_title("1人当たりでは30年で+18%、労働時間が減った分、1時間当たりでは+35%", loc="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f83_per_hour.png", dpi=150); plt.close(fig)

# 5 頑健性
order = ["基本（16産業・就業者）", "1年ごとに分解して積み上げ", "労働時間あたり", "不動産業を除く",
         "製造業を14業種に分ける（29産業）", "名目付加価値"]
fig, axs = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
for a, per in zip(axs, ["1994-2024", "2013-2019"]):
    r = rob[rob.period == per].set_index("variant").loc[order[::-1]]
    yy = np.arange(len(r)); h = 0.25
    a.barh(yy + h, r.within * 100, h, color=C["within"], label="産業の中")
    a.barh(yy, r.static * 100, h, color=C["static"], label="入れ替わり（静学）")
    a.barh(yy - h, r.inter * 100, h, color=C["inter"], label="交差項")
    a.scatter(r.growth * 100, yy, color=C["total"], zorder=3, s=18, label="合計")
    a.axvline(0, color="#888", lw=0.8); a.set_yticks(yy, r.index); a.set_title(per.replace("-", "→"), fontsize=11)
    a.set_xlabel("%ポイント（期間全体）")
axs[0].legend(fontsize=8, frameon=False, loc="lower right")
fig.suptitle("どの数え方でも長期は「産業の中」が主役。2013→19年の入れ替わりのプラスは不動産業を除くと消える", x=0.01, ha="left", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f83_robust.png", dpi=150); plt.close(fig)
print("ok")
