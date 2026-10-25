"""Moran's I（全体の偏り）と LISA（塊の場所）を、3都市・2000年／2020年で計算する。
2000年は 2020年の境界に面積按分した値を使う（同じ区域で比べるため）。"""
import json, warnings
import numpy as np, pandas as pd, geopandas as gpd
from libpysal.weights import Queen, Rook, KNN, DistanceBand
from esda.moran import Moran, Moran_Local
from common import DATA, RES, CITIES, MIN_POP, SEED

warnings.filterwarnings("ignore")
RES.mkdir(exist_ok=True)


def prep(g, year, min_pop):
    pop, old = ("pop20", "o6520") if year == 2020 else ("pop00", "o6500")
    d = g[(g[pop] >= min_pop) & g[old].notna()].copy()
    d["rate"] = d[old] / d[pop] * 100
    return d.reset_index(drop=True)


def weights(d, kind):
    if kind == "queen":
        w = Queen.from_dataframe(d, use_index=False, silence_warnings=True)
    elif kind == "rook":
        w = Rook.from_dataframe(d, use_index=False, silence_warnings=True)
    elif kind == "knn8":
        w = KNN.from_dataframe(d.set_geometry(d.centroid), k=8)
    elif kind == "dist1500":
        w = DistanceBand.from_dataframe(d.set_geometry(d.centroid), threshold=1500, binary=True, silence_warnings=True)
    # 孤立した区域（隣がない）は KNN(1) で補う
    if w.islands:
        knn = KNN.from_dataframe(d.set_geometry(d.centroid), k=1)
        from libpysal.weights import w_union
        w = w_union(w, knn, silence_warnings=True)
    w.transform = "r"
    return w


def moran(d, w, perms=999):
    np.random.seed(SEED)
    m = Moran(d["rate"].values, w, permutations=perms)
    return dict(I=m.I, EI=m.EI, z=m.z_sim, p_sim=m.p_sim, n=len(d))


def lisa(d, w, perms=999, alpha=0.05):
    np.random.seed(SEED)
    lm = Moran_Local(d["rate"].values, w, permutations=perms, seed=SEED)
    lab = np.array(["該当なし"] * len(d), dtype=object)
    sig = lm.p_sim < alpha
    names = {1: "高高", 2: "低高", 3: "低低", 4: "高低"}
    for q, n in names.items():
        lab[sig & (lm.q == q)] = n
    return lab, lm.p_sim


def fdr_flags(p, alpha=0.05):
    o = np.argsort(p); n = len(p); th = alpha * np.arange(1, n + 1) / n
    ok = p[o] <= th
    k = np.where(ok)[0].max() + 1 if ok.any() else 0
    flag = np.zeros(n, bool); flag[o[:k]] = True
    return flag


def dist_center(d, cfg):
    c = gpd.GeoSeries(gpd.points_from_xy([cfg["center"][0]], [cfg["center"][1]]), crs=4612).to_crs(cfg["epsg"]).iloc[0]
    return d.centroid.distance(c) / 1000


if __name__ == "__main__":
    main, robust, cl_rows, change_rows, dist_rows = [], [], [], [], []
    for city, cfg in CITIES.items():
        g = gpd.read_file(DATA / "units.gpkg", layer=city)
        for year in (2000, 2020):
            d = prep(g, year, MIN_POP)
            w = weights(d, "queen")
            r = moran(d, w); r.update(city=city, year=year, mean_rate=d["rate"].mean(),
                                     wmean=d[("o6520" if year == 2020 else "o6500")].sum() / d[("pop20" if year == 2020 else "pop00")].sum() * 100)
            main.append(r)
            lab, p = lisa(d, w)
            d["lisa"] = lab; d["p"] = p; d["fdr"] = fdr_flags(p)
            vc = pd.Series(lab).value_counts()
            cl_rows.append(dict(city=city, year=year, **{k: int(vc.get(k, 0)) for k in ["高高", "低低", "高低", "低高", "該当なし"]},
                                hh_fdr=int(((lab == "高高") & d["fdr"]).sum()),
                                hh_pop_share=d.loc[lab == "高高", "pop20" if year == 2020 else "pop00"].sum() / d["pop20" if year == 2020 else "pop00"].sum()))
            d["dist_km"] = dist_center(d, cfg)
            d[["KEY", "rate", "lisa", "p", "fdr", "dist_km"]].to_csv(RES / f"lisa_{city}_{year}.csv", index=False, encoding="utf-8-sig")
            # 頑健性：重み・閾値・並べ替えの回数
            for kind in ["rook", "knn8", "dist1500"]:
                rr = moran(d, weights(d, kind)); rr.update(city=city, year=year, check=f"重み={kind}"); robust.append(rr)
            for mp in (30, 100):
                dd = prep(g, year, mp); rr = moran(dd, weights(dd, "queen")); rr.update(city=city, year=year, check=f"人口{mp}人以上"); robust.append(rr)
            if year == 2020:  # 2020年は年齢「不詳」が多い区域がある → 不詳が2割以上の区域を除いても同じか
                dd = d[d["unk_share"] < 0.2].reset_index(drop=True); rr = moran(dd, weights(dd, "queen")); rr.update(city=city, year=year, check="年齢不詳が2割以上の区域を除く"); robust.append(rr)
            rr = moran(d, w, perms=9999); rr.update(city=city, year=year, check="並べ替え9999回"); robust.append(rr)
            # 都心からの距離帯ごとの高齢化率（人口で重み付け）
            pop, old = ("pop20", "o6520") if year == 2020 else ("pop00", "o6500")
            d["band"] = pd.cut(d["dist_km"], [0, 2, 4, 6, 8, 10, 12, 15, 20, 30, 60], right=False)
            for b, x in d.groupby("band", observed=True):
                dist_rows.append(dict(city=city, year=year, band=str(b), km=b.left, rate=x[old].sum() / x[pop].sum() * 100, n=len(x)))
        # 2000年 → 2020年：同じ区域での塊の移り変わり
        a = pd.read_csv(RES / f"lisa_{city}_2000.csv", dtype={"KEY": str}); b = pd.read_csv(RES / f"lisa_{city}_2020.csv", dtype={"KEY": str})
        m = a.merge(b, on="KEY", suffixes=("_00", "_20"))
        ct = pd.crosstab(m["lisa_00"], m["lisa_20"])
        ct.to_csv(RES / f"transition_{city}.csv", encoding="utf-8-sig")
        hh00, hh20 = set(m.loc[m.lisa_00 == "高高", "KEY"]), set(m.loc[m.lisa_20 == "高高", "KEY"])
        change_rows.append(dict(city=city, hh2000=len(hh00), hh2020=len(hh20), both=len(hh00 & hh20), new=len(hh20 - hh00), gone=len(hh00 - hh20),
                                dist_hh00=m.loc[m.lisa_00 == "高高", "dist_km_00"].median(), dist_hh20=m.loc[m.lisa_20 == "高高", "dist_km_20"].median(),
                                corr_rate=np.corrcoef(m.rate_00, m.rate_20)[0, 1]))
        # 2000年の自分の境界でも Moran's I（按分の影響の確認）
        g0 = gpd.read_file(DATA / "units2000_own.gpkg", layer=city)
        g0 = g0[(g0["pop"] >= MIN_POP)].reset_index(drop=True); g0["rate"] = g0["o65"] / g0["pop"] * 100
        rr = moran(g0, weights(g0, "queen")); rr.update(city=city, year=2000, check="2000年の境界のまま（按分なし）"); robust.append(rr)
    pd.DataFrame(main).to_csv(RES / "moran_main.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(robust).to_csv(RES / "moran_robust.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cl_rows).to_csv(RES / "lisa_counts.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(change_rows).to_csv(RES / "hh_change.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(dist_rows).to_csv(RES / "rate_by_distance.csv", index=False, encoding="utf-8-sig")
    for f in ["moran_main", "lisa_counts", "hh_change", "moran_robust"]:
        print(f); print(pd.read_csv(RES / f"{f}.csv").round(3).to_string())
