"""A217 自校方式とセンター方式の県差：公立小・中学校の単独調理場方式の割合（2010・2025年度）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import load, TILE, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

d = load()
for g in ["es", "jh"]:
    d[f"{g}_single_pct"] = d[f"{g}_single"] / d[f"{g}_n"] * 100
d["all_n"] = d.es_n + d.jh_n; d["all_single_pct"] = (d.es_single + d.jh_single) / d.all_n * 100
w = d.pivot(index="pref", columns="year")
t = d.groupby("year")[["es_n", "es_single", "es_joint", "es_other", "jh_n", "jh_single", "jh_joint", "jh_other"]].sum()
res = pd.DataFrame({"es_single_2025": w[("es_single_pct", 2025)], "jh_single_2025": w[("jh_single_pct", 2025)], "all_single_2025": w[("all_single_pct", 2025)],
                    "es_single_2010": w[("es_single_pct", 2010)], "jh_single_2010": w[("jh_single_pct", 2010)], "all_single_2010": w[("all_single_pct", 2010)],
                    "es_n_2025": w[("es_n", 2025)], "es_n_2010": w[("es_n", 2010)]})
res["chg_es"] = res.es_single_2025 - res.es_single_2010
res.round(2).to_csv(RES / "single_kitchen_share_pref.csv"); t.to_csv(RES / "national_totals.csv")

L = []
for y in [2010, 2025]:
    r = t.loc[y]
    L.append(f"{y}年度 全国 小学校 {r.es_n:,}校のうち単独 {r.es_single/r.es_n*100:.1f}%・共同 {r.es_joint/r.es_n*100:.1f}%・その他 {r.es_other/r.es_n*100:.1f}%；中学校 {r.jh_n:,}校 単独 {r.jh_single/r.jh_n*100:.1f}%・共同 {r.jh_joint/r.jh_n*100:.1f}%・その他 {r.jh_other/r.jh_n*100:.1f}%")
s = res.es_single_2025.sort_values(ascending=False)
L.append("小学校の単独方式の割合 上位: " + ", ".join(f"{p} {v:.1f}%" for p, v in s.head(8).items()))
L.append("下位: " + ", ".join(f"{p} {v:.1f}%" for p, v in s.tail(8)[::-1].items()))
L.append(f"小学校単独方式の割合 中央値 {s.median():.1f}%、50%以上の都道府県 {(s>=50).sum()}、20%未満 {(s<20).sum()}")
L.append(f"中学校が小学校より単独方式が少ない都道府県 {(res.jh_single_2025<res.es_single_2025).sum()}/47、小中の相関 {np.corrcoef(res.es_single_2025,res.jh_single_2025)[0,1]:.2f}")
c = res.chg_es.sort_values()
L.append(f"2010→2025 小学校の単独方式の割合が下がった都道府県 {(c<0).sum()}/47、平均 {c.mean():+.1f}pt。大きく下がった: " + ", ".join(f"{p} {v:+.1f}" for p, v in c.head(6).items()) + "；上がった: " + ", ".join(f"{p} {v:+.1f}" for p, v in c.tail(4)[::-1].items()))
L.append(f"小学校数 2010 {t.loc[2010,'es_n']:,} → 2025 {t.loc[2025,'es_n']:,}；単独方式の小学校 {t.loc[2010,'es_single']:,} → {t.loc[2025,'es_single']:,}、共同 {t.loc[2010,'es_joint']:,} → {t.loc[2025,'es_joint']:,}")
open(RES / "summary.txt", "w").write("\n".join(L) + "\n"); print("\n".join(L))

from matplotlib.colors import LinearSegmentedColormap, Normalize
cmap = LinearSegmentedColormap.from_list("bo", [BLUE, "#f2f2f2", ORANGE]); norm = Normalize(0, 100)
fig, ax = plt.subplots(figsize=(8, 6.5))
for p, (x, y) in TILE.items():
    v = res.es_single_2025[p]
    ax.add_patch(plt.Rectangle((x, -y), 0.92, 0.92, color=cmap(norm(v))))
    col = "white" if v > 75 or v < 25 else INK
    ax.text(x + 0.46, -y + 0.58, (p if p == "北海道" else p[:-1]), ha="center", va="center", fontsize=8.5, color=col)
    ax.text(x + 0.46, -y + 0.24, f"{v:.0f}%", ha="center", va="center", fontsize=8, color=col)
ax.set_xlim(-0.2, 13.2); ax.set_ylim(-9.3, 1.1); ax.axis("off"); ax.set_aspect("equal")
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); cb = fig.colorbar(sm, ax=ax, shrink=0.45, orientation="horizontal", pad=0.02)
cb.set_label("単独調理場（自校）方式の小学校の割合（%）。0%に近いほどセンター方式")
ax.set_title("自校方式の小学校の割合（公立、令和7年度）")
fig.text(0.01, 0.0, SOURCE, fontsize=8, color=GRAY); fig.savefig(FIG / "a217_tilemap.png"); plt.close()

fig, ax = plt.subplots(figsize=(8, 10))
o = res.sort_values("es_single_2025")
y = np.arange(len(o))
ax.barh(y, o.es_single_2025, color=ORANGE, height=0.6, label="小学校")
ax.scatter(o.jh_single_2025, y, color=BLUE, s=18, zorder=3, label="中学校")
ax.set_yticks(y); ax.set_yticklabels(o.index, fontsize=7.5); ax.set_xlim(0, 100)
ax.axvline(t.loc[2025, "es_single"] / t.loc[2025, "es_n"] * 100, color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("単独調理場（自校）方式の割合（%）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("都道府県別 自校方式の割合（令和7年度、点線は全国の小学校）")
fig.text(0.01, 0.0, SOURCE, fontsize=8, color=GRAY); fig.savefig(FIG / "a217_rank.png"); plt.close()

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(res.es_single_2010, res.es_single_2025, color=ORANGE, s=30)
ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8, ls="--")
lab = list(c.head(5).index) + list(c.tail(3).index) + list(s.head(3).index) + list(s.tail(3).index)
OFF = {"宮崎県": (-38, -4), "島根県": (6, -8)}
for p in dict.fromkeys(lab):
    ax.annotate(p, (res.es_single_2010[p], res.es_single_2025[p]), textcoords="offset points", xytext=OFF.get(p, (4, 3)), fontsize=8.5)
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal")
ax.set_xlabel("平成22年度（2010）の自校方式の割合（%）"); ax.set_ylabel("令和7年度（2025）の自校方式の割合（%）")
ax.set_title(f"15年間の変化（点線より下は自校方式が減った県：{(c<0).sum()}/47）")
fig.text(0.01, -0.02, SOURCE + "。公立小学校", fontsize=8, color=GRAY); fig.savefig(FIG / "a217_change.png"); plt.close()
