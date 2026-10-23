"""A5：外国人住民が多い市区町村は、どんな産業の街か（2020年国勢調査）"""
from common import *

d = load()
d["foreign"] = d["A1700"] / d["A1101"] * 100
fm = full_model(d, "foreign"); fm.round(3).to_csv(RES / "a5_full.csv", index=False, encoding="utf-8-sig")
s = {"n": len(d), "median": d.foreign.median(), "national": d.A1700.sum() / d.A1101.sum() * 100,
     "p90": d.foreign.quantile(.9), "n_over5": int((d.foreign >= 5).sum()),
     "corr_mfg": np.corrcoef(d.mfg, d.foreign)[0, 1], "corr_primary": np.corrcoef(d.primary, d.foreign)[0, 1]}
pd.Series(s).round(3).to_csv(RES / "a5_summary.csv", header=["value"]); print(pd.Series(s).round(3)); print(fm.round(3))
top = d.nlargest(15, "foreign")[["pref_name", "name", "foreign", "mfg", "primary", "A1101"]].round(3)
top.to_csv(RES / "a5_top.csv", index=False, encoding="utf-8-sig"); print(top)
# 産業のタイプ別
d["type"] = np.select([d.ward23, d.mfg >= d.mfg.quantile(.8), d.primary >= d.primary.quantile(.8)], ["東京23区", "製造業の街（上位20%）", "農林漁業の街（上位20%）"], "そのほか")
g = d.groupby("type").agg(n=("foreign", "size"), median=("foreign", "median"), p75=("foreign", lambda x: x.quantile(.75))).round(2)
g.to_csv(RES / "a5_type.csv", encoding="utf-8-sig"); print(g)

fig, ax = plt.subplots(figsize=(8, 5))
o = d[~d.ward23]
sc = ax.scatter(o.mfg * 100, o.foreign, s=np.clip(o.A1101 / 5000, 4, 120), c=o.primary * 100, cmap="Oranges", vmin=0, vmax=40, alpha=0.75, lw=0)
w = d[d.ward23]; ax.scatter(w.mfg * 100, w.foreign, s=20, color=BLUE, label="東京23区")
for _, r in d.nlargest(6, "foreign").iterrows():
    ax.annotate(r["name"], (r.mfg * 100, r.foreign), xytext=(4, 2), textcoords="offset points", fontsize=8, color="#52514e")
cb = fig.colorbar(sc, ax=ax, pad=0.01); cb.set_label("第1次産業で働く人の割合（%）")
ax.set_xlabel("第2次産業で働く人の割合（%）"); ax.set_ylabel("外国人の割合（%）"); ax.set_ylim(0, 20); ax.legend(frameon=False, loc="center right")
ax.set_title("外国人住民が多い街は「都心」「工場の街」「農業の村」の3タイプ", loc="left")
fig.text(0.01, -0.03, SOURCE + "（2020年国勢調査。円の大きさは人口、色は第1次産業の割合）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "a5_scatter.png"); plt.close(fig)
plot_coefs(fm, f"外国人住民の割合と関係していた条件（決定係数 {fm.r2.iloc[0]:.2f}）", "1標準偏差あたり、外国人の割合が何ポイント違うか", FIG / "a5_coefs.png")
