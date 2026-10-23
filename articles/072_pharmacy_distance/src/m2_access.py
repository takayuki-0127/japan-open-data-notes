"""近くにあるか：薬局から最寄りの医療機関までの距離、市区町村から最寄りの小児科・産婦人科までの距離、都道府県の病院の病床"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import BallTree
from common import *

R = 6371.0
hp, hh = facilities("hospital"); cl, ch = facilities("clinic")
hp["kind"], cl["kind"] = "病院", "診療所"
med = pd.concat([hp, cl], ignore_index=True)
spec = pd.concat([hh[["ID", "診療科目名"]], ch[["ID", "診療科目名"]]]).drop_duplicates()
nm = spec["診療科目名"].fillna("")
ped = set(spec.ID[nm.str.match(r"^小児科")]); obs = set(spec.ID[nm.isin(["産科", "産婦人科", "産科婦人科"]) | nm.str.match(r"^産婦人科")])
med["ped"] = med.ID.isin(ped); med["obs"] = med.ID.isin(obs)
med = med[med.lat.between(20, 46) & med.lon.between(122, 154)]
cnt = med.groupby("kind")[["ped", "obs"]].sum(); cnt["n"] = med.groupby("kind").size(); cnt.to_csv(RES / "m2_counts.csv", encoding="utf-8-sig"); print(cnt)


def tree(df): return BallTree(np.radians(df[["lat", "lon"]].values), metric="haversine")


# 1) 薬局 → 最寄りの病院・診療所
ph = read("05_pharmacy")
ph = pd.DataFrame({"pcode": ph["都道府県コード"].str.zfill(2), "muni": ph["都道府県コード"].str.zfill(2) + ph["市区町村コード"].str.zfill(3), "addr": ph["所在地"],
                   "lat": pd.to_numeric(ph["所在地座標（緯度）"], errors="coerce"), "lon": pd.to_numeric(ph["所在地座標（経度）"], errors="coerce")})
print("薬局", len(ph), "座標あり", (ph.lat.between(20, 46) & ph.lon.between(122, 154)).sum())
ph = ph[ph.lat.between(20, 46) & ph.lon.between(122, 154) & ph.pcode.str.match(r"^\d{2}$", na=False)].copy()
ph["city"] = [city_of(m, a) for m, a in zip(ph.muni, ph.addr)]; ph["mtype"] = ph.city.map(muni_type)
dd, _ = tree(med).query(np.radians(ph[["lat", "lon"]].values), k=1)
ph["nn_m"] = dd[:, 0] * R * 1000
bins = [-1, 50, 100, 300, 1000, 1e9]; labs = ["50m未満", "50〜100m", "100〜300m", "300m〜1km", "1km以上"]
ph["band"] = pd.cut(ph.nn_m, bins, labels=labs)
pb = pd.crosstab(ph.mtype, ph.band, normalize="index") * 100
pb.loc["全国"] = ph.band.value_counts(normalize=True).reindex(labs) * 100
pb["median_m"] = list(ph.groupby("mtype").nn_m.median().reindex(pb.index[:-1])) + [ph.nn_m.median()]
pb["n"] = list(ph.mtype.value_counts().reindex(pb.index[:-1])) + [len(ph)]
pb.to_csv(RES / "m2_pharmacy_distance.csv", encoding="utf-8-sig"); print(pb.round(1))

# 2) 市区町村の「中心」（その市区町村の病院・診療所・薬局の位置の平均）から、最寄りの小児科・産婦人科・病院まで
pts = pd.concat([med[["muni", "pref", "city", "mtype", "lat", "lon"]], ph[["muni", "city", "mtype", "lat", "lon"]].assign(pref=lambda d: pd.to_numeric(d.muni.str[:2], errors="coerce").map(lambda i: PREFS[int(i) - 1] if i == i and 1 <= i <= 47 else "不明"))])
cen = pts.groupby("muni").agg(pref=("pref", "first"), city=("city", "first"), mtype=("mtype", "first"), lat=("lat", "mean"), lon=("lon", "mean"), n=("lat", "size"))
for col, sub in [("ped", med[med.ped]), ("obs", med[med.obs]), ("hosp", med[med.kind == "病院"])]:
    d_, _ = tree(sub).query(np.radians(cen[["lat", "lon"]].values), k=1)
    cen[f"d_{col}"] = d_[:, 0] * R
    cen[f"in_{col}"] = cen.index.isin(sub.muni)
cen.to_csv(RES / "m2_muni_access.csv", encoding="utf-8-sig")
S = cen.groupby("mtype").agg(n=("pref", "size"), no_ped=("in_ped", lambda s: (~s).sum()), no_obs=("in_obs", lambda s: (~s).sum()), no_hosp=("in_hosp", lambda s: (~s).sum()),
                             med_d_obs=("d_obs", "median"), over20_obs=("d_obs", lambda s: (s > 20).sum()), over30_obs=("d_obs", lambda s: (s > 30).sum()),
                             med_d_ped=("d_ped", "median"), over20_ped=("d_ped", lambda s: (s > 20).sum()))
S.loc["全体"] = [len(cen), (~cen.in_ped).sum(), (~cen.in_obs).sum(), (~cen.in_hosp).sum(), cen.d_obs.median(), (cen.d_obs > 20).sum(), (cen.d_obs > 30).sum(), cen.d_ped.median(), (cen.d_ped > 20).sum()]
S.to_csv(RES / "m2_muni_summary.csv", encoding="utf-8-sig"); print(S.round(2))

# 図1：薬局から最寄りの医療機関まで
fig, ax = plt.subplots(figsize=(8.6, 3.6))
rows = ["特別区・政令市", "市", "町村", "全国"]; cols = [BLUE, LIGHT, GREEN, "#cfe8dc", GRAY]
left = np.zeros(len(rows))
for j, l in enumerate(labs):
    v = pb.loc[rows, l].values
    ax.barh(range(len(rows))[::-1], v, left=left, color=cols[j], label=l)
    for i, (vv, ll) in enumerate(zip(v, left)):
        if vv >= 6: ax.text(ll + vv / 2, len(rows) - 1 - i, f"{vv:.0f}%", ha="center", va="center", fontsize=8.5, color="white" if j in (0, 2) else INK)
    left += v
ax.set_yticks(range(len(rows))[::-1]); ax.set_yticklabels([f"{r}（{int(pb.loc[r, 'n']):,}）" for r in rows]); ax.set_xlim(0, 100)
ax.legend(frameon=False, ncol=5, fontsize=8.5, loc="upper center", bbox_to_anchor=(.5, -.12)); ax.set_xlabel("")
ax.set_title("薬局から、いちばん近い病院・診療所までの直線距離", loc="left", fontsize=12)
note(ax, SOURCE + "\nかっこ内は薬局数。歯科診療所は含まない", -0.3); fig.savefig(FIG / "m2_pharmacy.png"); plt.close(fig)

# 図2：市区町村の中心から最寄りの産婦人科・小児科
fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.9), sharey=True)
mt = ["特別区・政令市", "市", "町村"]; mc = {"特別区・政令市": BLUE, "市": GREEN, "町村": ORANGE}
bins_ = np.r_[0, np.logspace(-1, 2, 36)]
for ax, (col, t) in zip(axes, [("d_obs", "産婦人科・産科を掲げる病院・診療所まで"), ("d_ped", "小児科を掲げる病院・診療所まで")]):
    for m_ in mt:
        s = cen[cen.mtype == m_][col]
        ax.hist(s.clip(upper=99), bins=bins_, histtype="step", lw=1.8, color=mc[m_], label=f"{m_}（中央値{s.median():.1f}km）")
    ax.set_xscale("log"); ax.set_xticks([0.1, 0.5, 1, 2, 5, 10, 20, 50]); ax.set_xticklabels(["0.1", "0.5", "1", "2", "5", "10", "20", "50"]); ax.minorticks_off()
    ax.set_title(t, loc="left", fontsize=11); ax.set_xlabel("直線距離（km）"); ax.legend(frameon=False, fontsize=8.5)
axes[0].set_ylabel("市区町村の数")
note(axes[0], SOURCE + "\n市区町村の中心は、その市区町村にある病院・診療所・薬局の位置の平均", -0.2)
fig.savefig(FIG / "m2_muni_distance.png"); plt.close(fig)

# 図3：掲載された施設が0の市区町村
fig, ax = plt.subplots(figsize=(8, 3.8))
items = [("no_hosp", "病院"), ("no_obs", "産婦人科・産科"), ("no_ped", "小児科")]
for j, m_ in enumerate(mt):
    xs = np.arange(3) + (j - 1) * .26
    v = [S.loc[m_, k] / S.loc[m_, "n"] * 100 for k, _ in items]
    ax.bar(xs, v, .25, color=mc[m_], label=f"{m_}（{int(S.loc[m_, 'n']):,}）")
    for xx, vv, (k, _) in zip(xs, v, items): ax.text(xx, vv + 1, f"{int(S.loc[m_, k])}", ha="center", fontsize=8.5)
ax.set_xticks(range(3)); ax.set_xticklabels([t for _, t in items]); ax.set_ylabel("市区町村の割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("その施設が1つも掲載されていない市区町村（棒の上は数）", loc="left", fontsize=12)
note(ax, SOURCE + "\n病院・診療所・薬局のどれかが掲載されている1,840市区町村が対象。小児科・産婦人科は病院と診療所の合計", -0.13)
fig.savefig(FIG / "m2_none.png"); plt.close(fig)
