"""133：公立と私立の学習費の差は、何に使われているか（費目別の分解、年次推移）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, FIG, RES, note, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

d = load()
ORDER = ["幼稚園", "小学校", "中学校", "高等学校（全日制）"]
SHORT = {"幼稚園": "幼稚園", "小学校": "小学校", "中学校": "中学校", "高等学校（全日制）": "高校（全日制）"}


def wide(year):
    x = d[d.year == year].pivot_table(index=["school", "setting"], columns="item", values="yen", aggfunc="first").fillna(0)
    out = pd.DataFrame(index=x.index)
    out["授業料"] = x["授業料"]
    out["学校納付金等（入学金・施設整備費など）"] = x["学校納付金等"]
    out["そのほかの学校教育費（通学費・制服・修学旅行など）"] = x["学校教育費"] - x["授業料"] - x["学校納付金等"]
    out["学校給食費"] = x["学校給食費"]
    out["学習塾費"] = x["学習塾費"]
    out["家庭内学習・通信教育など"] = x["補助学習費"] - x["学習塾費"]
    out["習い事・体験活動など"] = x["その他の学校外活動費"]
    out["総額"] = x["学習費総額"]
    chk = out.drop(columns="総額").sum(axis=1) - out["総額"]
    assert chk.abs().max() < 2, chk
    return out


# ---- 2023年度：私立−公立の差を費目に分ける ----
w = wide(2023)
cats = [c for c in w.columns if c != "総額"]
gap = pd.DataFrame({s: w.loc[(s, "私立")] - w.loc[(s, "公立")] for s in ORDER}).T
gap["比（私立÷公立）"] = [w.loc[(s, "私立"), "総額"] / w.loc[(s, "公立"), "総額"] for s in ORDER]
share = gap[cats].div(gap["総額"], axis=0) * 100
out = pd.concat([w.reset_index(), ], axis=0)
out.to_csv(RES / "a133_2023_components.csv", index=False, encoding="utf-8-sig")
gt = gap.copy()
for c in cats:
    gt[c + "_割合%"] = share[c].round(1)
gt.round(2).to_csv(RES / "a133_2023_gap.csv", encoding="utf-8-sig")
print(gap.round(0).to_string())
print(share.round(1).to_string())

cols = [BLUE, LIGHT, PURPLE, GREEN, ORANGE, "#f2b38f", GRAY]
fig, ax = plt.subplots(figsize=(9.2, 4.6))
ys = np.arange(len(ORDER))[::-1]
for y, s in zip(ys, ORDER):
    pos, neg = 0.0, 0.0
    for c, col in zip(cats, cols):
        v = gap.loc[s, c] / 1e4
        if v >= 0:
            ax.barh(y, v, left=pos, color=col, height=0.62, label=c if s == ORDER[0] else None); pos += v
        else:
            ax.barh(y, v, left=neg, color=col, height=0.62, label=c if s == ORDER[0] else None); neg += v
    ax.text(pos + 2, y, f"差 {gap.loc[s,'総額']/1e4:.0f}万円（{gap.loc[s,'比（私立÷公立）']:.1f}倍）", va="center", fontsize=9.5, color=INK)
ax.set_yticks(ys); ax.set_yticklabels([SHORT[s] for s in ORDER])
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("私立−公立（万円／年、2023年度）")
ax.set_xlim(gap[[c for c in cats]].clip(upper=0).sum(axis=1).min() / 1e4 - 5, gap["総額"].max() / 1e4 + 32)
ax.set_title("公立と私立の学習費の差は、何で開いているか（2023年度）", loc="left")
ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.15), ncol=2)
note(ax, y=-0.42)
fig.savefig(FIG / "a133_gap.png"); plt.close(fig)

# ---- 年次推移：総額と私立÷公立 ----
tot = d[d.item == "学習費総額"].pivot_table(index="year", columns=["school", "setting"], values="yen")
ratio = pd.DataFrame({s: tot[(s, "私立")] / tot[(s, "公立")] for s in ORDER})
tot.round(0).to_csv(RES / "a133_total_by_year.csv", encoding="utf-8-sig")
ratio.round(3).to_csv(RES / "a133_ratio_by_year.csv", encoding="utf-8-sig")
print(ratio.round(2).to_string())
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2))
pal = {"幼稚園": GRAY, "小学校": BLUE, "中学校": GREEN, "高等学校（全日制）": ORANGE}
for s in ORDER:
    for st, ls in (("公立", "-"), ("私立", "--")):
        sr = tot[(s, st)].dropna()
        axs[0].plot(sr.index, sr / 1e4, ls, color=pal[s], marker="o", ms=3, label=f"{SHORT[s]}・{st}")
    r = ratio[s].dropna()
    axs[1].plot(r.index, r, color=pal[s], marker="o", ms=3, label=SHORT[s])
    axs[1].annotate(f"{r.iloc[-1]:.1f}倍", (r.index[-1], r.iloc[-1]), xytext=(4, 0), textcoords="offset points", fontsize=8.5, color=pal[s], va="center")
axs[0].set_title("学習費総額（万円／年）", loc="left"); axs[0].legend(fontsize=7.5, frameon=False, ncol=2)
axs[1].set_title("私立÷公立", loc="left"); axs[1].legend(fontsize=8, frameon=False)
axs[1].set_xlim(right=2027)
for a in axs:
    a.set_xlabel("調査年度")
note(axs[0], y=-0.2)
fig.savefig(FIG / "a133_trend.png"); plt.close(fig)

# ---- 学習塾費：公立と私立 ----
juku = d[d.item == "学習塾費"].pivot_table(index="year", columns=["school", "setting"], values="yen")
hoj = d[d.item == "補助学習費"].pivot_table(index="year", columns=["school", "setting"], values="yen")
juku.round(0).to_csv(RES / "a133_juku_by_year.csv", encoding="utf-8-sig")
fig, axs = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
for a, s in zip(axs, ["小学校", "中学校", "高等学校（全日制）"]):
    for st, col in (("公立", BLUE), ("私立", ORANGE)):
        sr = juku[(s, st)].dropna()
        a.plot(sr.index, sr / 1e4, color=col, marker="o", ms=3, label=st)
        a.annotate(f"{sr.iloc[-1]/1e4:.1f}", (sr.index[-1], sr.iloc[-1] / 1e4), xytext=(4, 0), textcoords="offset points", fontsize=8.5, color=col, va="center")
    a.set_title(SHORT[s], loc="left"); a.set_xlim(right=2027)
axs[0].set_ylabel("学習塾費（万円／年）"); axs[0].legend(frameon=False, fontsize=9)
fig.suptitle("学習塾費の公私の差（私立小学校は2006年度から）", x=0.06, y=1.05, ha="left", fontsize=13)
note(axs[0], y=-0.18)
fig.savefig(FIG / "a133_juku.png"); plt.close(fig)
print(juku.round(0).to_string())
print("給食", d[(d.item=="学校給食費")&(d.year==2023)].to_string())
