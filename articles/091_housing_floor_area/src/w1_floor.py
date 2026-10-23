"""W1：新設住宅の1戸当たり床面積は小さくなったか（利用関係別・都道府県別）"""
from common import *

t = load("tenure_year.csv")
t["m2_per_unit"] = t.floor_m2 / t.units
w = t.pivot(index="year", columns="tenure", values="m2_per_unit")
u = t.pivot(index="year", columns="tenure", values="units")
f = t.pivot(index="year", columns="tenure", values="floor_m2")
TEN = ["持家", "貸家", "分譲マンション", "分譲一戸建"]
w.round(1).to_csv(RES / "w1_m2_per_unit.csv", encoding="utf-8")

# 戸数の構成比
share = u[["持家", "貸家", "給与住宅", "分譲住宅"]].div(u["総計"], axis=0)
share.round(4).to_csv(RES / "w1_unit_share.csv", encoding="utf-8")

# シフトシェア：平均床面積の変化＝区分の中の変化＋構成の変化
CAT = ["持家", "貸家", "給与住宅", "分譲マンション", "分譲一戸建"]
def decomp(y0, y1):
    s0 = u.loc[y0, CAT] / u.loc[y0, CAT].sum(); s1 = u.loc[y1, CAT] / u.loc[y1, CAT].sum()
    a0, a1 = w.loc[y0, CAT], w.loc[y1, CAT]
    avg0, avg1 = (s0 * a0).sum(), (s1 * a1).sum()
    within = (((s0 + s1) / 2) * (a1 - a0)).sum()
    mix = (((a0 + a1) / 2) * (s1 - s0)).sum()
    return {"from": y0, "to": y1, "avg_from": avg0, "avg_to": avg1, "change": avg1 - avg0, "within": within, "mix": mix,
            **{f"within_{c}": ((s0[c] + s1[c]) / 2) * (a1[c] - a0[c]) for c in CAT},
            **{f"mix_{c}": ((a0[c] + a1[c]) / 2) * (s1[c] - s0[c]) for c in CAT}}
dec = pd.DataFrame([decomp(1996, 2025), decomp(2006, 2025), decomp(2015, 2025)])
dec.round(2).to_csv(RES / "w1_decomposition.csv", index=False, encoding="utf-8")

# 都道府県：1戸当たり床面積
p = load("pref_year.csv"); p["m2_per_unit"] = p.floor_m2 / p.units
pv = p.pivot(index="pref", columns="year", values="m2_per_unit")
pr = pd.DataFrame({"m2_2000": pv[2000], "m2_2015": pv[2015], "m2_2025": pv[2025], "units_2025": p[p.year == 2025].set_index("pref").units})
pr["change_2000_2025"] = pr.m2_2025 - pr.m2_2000
pr = pr.drop("全国").sort_values("m2_2025")
pr.round(1).to_csv(RES / "w1_pref.csv", encoding="utf-8")

# 図1：利用関係別の1戸当たり床面積
fig, ax = plt.subplots(figsize=(8, 4.6))
cols = {"総計": INK, "持家": BLUE, "分譲一戸建": GREEN, "分譲マンション": PURPLE, "貸家": ORANGE}
for c, col in cols.items():
    s = w[c].dropna(); s = s[s.index >= 1960]
    ax.plot(s.index, s.values, color=col, lw=2.2 if c == "総計" else 1.6, label=c)
    ax.annotate(f"{s.iloc[-1]:.0f}㎡", (s.index[-1], s.iloc[-1]), xytext=(4, 0), textcoords="offset points", color=col, fontsize=9, va="center")
ax.set_ylabel("新設住宅1戸当たりの床面積（㎡）"); ax.set_title("1戸当たりの床面積：持家は1996年の141㎡から2025年に112㎡")
ax.legend(frameon=False, ncol=5, fontsize=9, loc="lower center"); ax.set_ylim(0, 150)
note(fig); fig.savefig(FIG / "w1_by_tenure.png"); plt.close(fig)

# 図2：戸数の構成と平均
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
ss = share[share.index >= 1960]
ax[0].stackplot(ss.index, *(ss[c] * 100 for c in ["持家", "分譲住宅", "給与住宅", "貸家"]),
                colors=[BLUE, GREEN, GRAY, ORANGE], labels=["持家", "分譲住宅", "給与住宅", "貸家"], alpha=.9)
ax[0].set_ylim(0, 100); ax[0].set_ylabel("新設住宅の戸数に占める割合（%）"); ax[0].legend(frameon=False, fontsize=8, loc="lower left")
ax[0].set_title("戸数の内訳")
d = dec.iloc[0]
bars = [("持家の\n中の変化", d["within_持家"]), ("貸家の\n中の変化", d["within_貸家"]), ("分譲の\n中の変化", d["within_分譲マンション"] + d["within_分譲一戸建"]),
        ("構成の\n変化", d["mix"]), ("合計", d["change"])]
ax[1].bar([b[0] for b in bars], [b[1] for b in bars], color=[BLUE, ORANGE, GREEN, GRAY, INK])
for i, b in enumerate(bars):
    ax[1].text(i, b[1] + (0.3 if b[1] >= 0 else -0.3), f"{b[1]:+.1f}", ha="center", va="bottom" if b[1] >= 0 else "top", fontsize=9)
ax[1].axhline(0, color=GRAY, lw=.8); ax[1].set_ylabel("㎡"); ax[1].set_title(f"平均床面積の変化の分解（{int(d['from'])}→{int(d['to'])}年）")
note(fig); fig.savefig(FIG / "w1_decomposition.png"); plt.close(fig)

# 図3：都道府県
fig, ax = plt.subplots(figsize=(8, 8.5))
y = np.arange(len(pr))
ax.hlines(y, pr.m2_2000, pr.m2_2025, color=LIGHT, lw=2)
ax.scatter(pr.m2_2000, y, color=GRAY, s=16, label="2000年", zorder=3); ax.scatter(pr.m2_2025, y, color=BLUE, s=18, label="2025年", zorder=3)
ax.set_yticks(y, pr.index, fontsize=8); ax.set_xlabel("新設住宅1戸当たりの床面積（㎡）")
ax.axvline(pv.loc["全国", 2025], color=INK, lw=.8, ls="--"); ax.legend(frameon=False, loc="lower right")
ax.set_title("都道府県別の1戸当たり床面積（全国の点線は2025年）")
note(fig); fig.savefig(FIG / "w1_pref.png"); plt.close(fig)

# 表示
print(w.loc[[1970, 1980, 1990, 1996, 2000, 2006, 2010, 2015, 2020, 2024, 2025], ["総計"] + TEN + ["分譲住宅"]].round(1).to_string())
for c in ["総計"] + TEN:
    s = w[c].dropna(); print(c, "peak", s.idxmax(), round(s.max(), 1))
print(share.loc[[1996, 2006, 2025]].round(3).to_string())
print(u.loc[[1996, 2006, 2025], ["総計", "持家", "貸家", "分譲マンション", "分譲一戸建"]].to_string())
print(dec.round(2).T.to_string())
print(pr.head(5).round(1).to_string()); print(pr.tail(5).round(1).to_string())
print("pref sd", pr.m2_2000.std().round(1), pr.m2_2025.std().round(1), "corr", pr[["m2_2025"]].join(pr.units_2025).corr().iloc[0, 1].round(2))
print("全国", pv.loc["全国", [2000, 2015, 2025]].round(1).to_dict())
