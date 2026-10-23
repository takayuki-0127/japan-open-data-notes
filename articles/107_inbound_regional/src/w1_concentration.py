"""W1：外国人の宿泊は東京・大阪から地方に広がったのか（都道府県別の割合、集中度、国籍別）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load_monthly, load_nationality, gini, note, SOURCE, PREFS, METRO, FIG, RES, BLUE, ORANGE, GRAY, GREEN, PURPLE, INK

m = load_monthly()
ann = m.groupby(["year", "pref"])[["total", "foreign", "japanese"]].sum().reset_index()

# 1. 都道府県別の割合
rows = []
for y, g in ann.groupby("year"):
    for col in ("foreign", "japanese"):
        s = g.set_index("pref")[col]
        sh = s / s.sum()
        top = sh.sort_values(ascending=False)
        rows.append(dict(year=y, group=col, total=int(s.sum()), tokyo=sh["東京都"], osaka=sh["大阪府"], kyoto=sh["京都府"],
                         hokkaido=sh["北海道"], okinawa=sh["沖縄県"], fukuoka=sh["福岡県"],
                         tokyo_osaka=sh["東京都"] + sh["大阪府"], top3=top.iloc[:3].sum(), top5=top.iloc[:5].sum(),
                         metro8=sh[METRO].sum(), outside_metro=1 - sh[METRO].sum(),
                         gini=gini(s.values), hhi=float((sh ** 2).sum()), n_eff=float(1 / (sh ** 2).sum())))
conc = pd.DataFrame(rows)
conc.to_csv(RES / "w1_concentration.csv", index=False, float_format="%.4f")

sh = ann.assign(share_foreign=ann.foreign / ann.groupby("year").foreign.transform("sum"),
                share_japanese=ann.japanese / ann.groupby("year").japanese.transform("sum"),
                foreign_ratio=ann.foreign / ann.total)
wide = sh.pivot(index="pref", columns="year", values="share_foreign").loc[PREFS]
out = pd.DataFrame({"share_2015": wide[2015], "share_2019": wide[2019], "share_2025": wide[2025],
                    "foreign_2015": ann[ann.year == 2015].set_index("pref").foreign,
                    "foreign_2019": ann[ann.year == 2019].set_index("pref").foreign,
                    "foreign_2025": ann[ann.year == 2025].set_index("pref").foreign,
                    "foreign_ratio_2025": sh[sh.year == 2025].set_index("pref").foreign_ratio})
out["growth_2019_2025"] = out.foreign_2025 / out.foreign_2019
out["pt_change_2015_2025"] = (out.share_2025 - out.share_2015) * 100
out.to_csv(RES / "w1_pref_share.csv", float_format="%.4f")

# 2. 国籍別：三大都市圏（8都府県）以外での宿泊の割合
nat = load_nationality()
nat["metro"] = nat.pref.isin(METRO)
g = nat.groupby(["year", "nationality"]).apply(lambda d: pd.Series({"foreign": d.foreign.sum(),
                                                                       "outside_metro": d.loc[~d.metro, "foreign"].sum() / d.foreign.sum(),
                                                                       "tokyo": d.loc[d.pref == "東京都", "foreign"].sum() / d.foreign.sum()})).reset_index()
g.to_csv(RES / "w1_nationality.csv", index=False, float_format="%.4f")

# --- 図1：主な都道府県の割合の推移 ---
f = conc[conc.group == "foreign"].set_index("year")
fig, ax = plt.subplots(figsize=(8, 4.6))
for col, lab, c in [("tokyo", "東京都", BLUE), ("osaka", "大阪府", ORANGE), ("hokkaido", "北海道", GREEN),
                    ("kyoto", "京都府", PURPLE), ("okinawa", "沖縄県", GRAY)]:
    ax.plot(f.index, f[col] * 100, marker="o", ms=3, color=c, label=lab)
ax.plot(f.index, f.outside_metro * 100, marker="o", ms=3, color=INK, lw=2.2, label="三大都市圏8都府県以外の計")
ax.axvspan(2019.5, 2022.5, color="#eeeeee", zorder=0)
ax.text(2021, 43.5, "コロナ禍", ha="center", fontsize=9, color="#666666")
ax.set_ylabel("外国人延べ宿泊者数に占める割合（%）"); ax.set_xticks(range(2011, 2026, 2))
ax.set_title("外国人の延べ宿泊者数：都道府県の割合（2011〜2025年）")
ax.legend(fontsize=9, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1)); ax.set_ylim(0, 45)
note(ax)
fig.savefig(FIG / "w1_share.png"); plt.close(fig)

# --- 図2：集中度（ジニ係数）外国人と日本人 ---
fig, ax = plt.subplots(figsize=(8, 4.3))
for grp, lab, c in [("foreign", "外国人", BLUE), ("japanese", "日本人", ORANGE)]:
    d = conc[conc.group == grp].set_index("year")
    ax.plot(d.index, d.gini, marker="o", ms=3, color=c, label=lab)
ax.axvspan(2019.5, 2022.5, color="#eeeeee", zorder=0)
ax.set_ylabel("都道府県間のジニ係数（0＝均等）"); ax.set_xticks(range(2011, 2026, 2)); ax.set_ylim(0.3, 0.8)
ax.set_title("延べ宿泊者数の都道府県への集中度")
ax.legend(frameon=False)
note(ax)
fig.savefig(FIG / "w1_gini.png"); plt.close(fig)

# --- 図3：国籍別の「三大都市圏以外」の割合 2019 と 2025 ---
k = g[g.year.isin([2019, 2025])].pivot(index="nationality", columns="year", values="outside_metro")
v = g[g.year == 2025].set_index("nationality").foreign
k = k.loc[v.drop(["計", "その他"]).sort_values(ascending=False).index[:14]]
k = k.sort_values(2025)
fig, ax = plt.subplots(figsize=(7.5, 5.4))
y = np.arange(len(k))
ax.hlines(y, k[2019] * 100, k[2025] * 100, color="#cccccc")
ax.scatter(k[2019] * 100, y, color=GRAY, label="2019年", zorder=3)
ax.scatter(k[2025] * 100, y, color=BLUE, label="2025年", zorder=3)
tot = g[(g.nationality == "計")].set_index("year").outside_metro
ax.axvline(tot[2025] * 100, color=BLUE, ls=":", lw=1)
ax.text(tot[2025] * 100 + 0.4, len(k) - 0.6, f"全体（2025年）{tot[2025]*100:.0f}%", fontsize=8.5, color=BLUE)
ax.set_yticks(y, k.index); ax.set_xlabel("三大都市圏8都府県以外での宿泊の割合（%）")
ax.set_title("国籍別：地方での宿泊の割合（延べ宿泊者数が多い14か国・地域）")
ax.legend(frameon=False, loc="lower right")
note(ax, SOURCE + "（参考第1表、従業者数10人以上の施設）", y=-0.13)
fig.savefig(FIG / "w1_nationality.png"); plt.close(fig)

# 要約
print(conc[conc.group == "foreign"][["year", "total", "tokyo", "osaka", "kyoto", "tokyo_osaka", "top5", "outside_metro", "gini", "hhi", "n_eff"]].round(3).to_string(index=False))
print(conc[conc.group == "japanese"][["year", "tokyo", "outside_metro", "gini"]].round(3).to_string(index=False))
print(out.sort_values("pt_change_2015_2025").round(3).to_string())
print(g[g.year.isin([2019, 2025])].pivot(index="nationality", columns="year", values=["foreign", "outside_metro", "tokyo"]).round(3).to_string())
