"""政令市ごとに、2020年の町丁・字の境界に 2000年と2020年の人口・65歳以上人口をのせる。
- 2020年：秘匿（X）の区域は、合算先（HTKSAKI）の区域に境界ごとまとめる
- 2000年：2000年の境界から 2020年の境界へ、面積の重なりで按分する（面積按分）
"""
import pandas as pd, geopandas as gpd, numpy as np
from common import RAW, DATA, CITIES


def read_tbl(name, code_prefix):
    p = next((RAW / name).glob("*.txt"))
    df = pd.read_csv(p, encoding="cp932", dtype=str, skiprows=[1])
    return df


def num(s):
    return pd.to_numeric(s.replace({"-": "0", "X": np.nan}), errors="coerce")


def load_2020(pref):
    df = read_tbl(f"tblT001082C{pref}", "T001082")
    out = pd.DataFrame({
        "KEY_CODE": df["KEY_CODE"], "HYOSYO": df["HYOSYO"].astype(int), "HTKSYORI": df["HTKSYORI"],
        "HTKSAKI": df["HTKSAKI"].fillna(""), "NAME": df["NAME"],
        "tot": num(df["T001082001"]), "u15": num(df["T001082017"]), "a1564": num(df["T001082018"]), "o65": num(df["T001082019"]),
    })
    return out


def load_2000(pref):
    df = read_tbl(f"tblT000002C{pref}", "T000002")
    return pd.DataFrame({
        "KEY_CODE": df["KEY_CODE"], "HYOSYO": df["HYOSYO"].astype(int), "HTKSYU": df["HTKSYU"],
        "u15": num(df["T000002017"]), "a1564": num(df["T000002018"]), "o65": num(df["T000002019"]),
    })


def shapes(year, pref, wards):
    f = next((RAW / f"A00200521{year}DDSWC{pref}").glob("*.shp"))
    g = gpd.read_file(f)
    g = g[g["CITY"].astype(int).isin(list(wards))]
    g = g[g["HCODE"].astype(str) == "8101"]          # 8101＝通常の区域（水面などを除く）
    g = g[["KEY_CODE", "geometry"]].dissolve(by="KEY_CODE").reset_index()
    return g


def build(city, cfg):
    pref, wards, epsg = cfg["pref"], cfg["wards"], cfg["epsg"]
    g20 = shapes("2020", pref, wards).to_crs(epsg)
    d20 = load_2020(pref)
    d20 = d20[d20["KEY_CODE"].isin(g20["KEY_CODE"])]
    # 秘匿区域は合算先の区域にまとめる（合算先＝同じ市区町村で S_AREA の下6桁が HTKSAKI）
    key_map = {}
    for _, r in d20.iterrows():
        if pd.isna(r["o65"]) and r["HTKSAKI"]:
            tgt = r["KEY_CODE"][:5] + r["HTKSAKI"].split(";")[0][:6]
            key_map[r["KEY_CODE"]] = tgt
    g20["KEY"] = g20["KEY_CODE"].map(lambda k: key_map.get(k, k))
    g20 = g20.dissolve(by="KEY").reset_index()[["KEY", "geometry"]]
    d20 = d20.dropna(subset=["o65"]).rename(columns={"KEY_CODE": "KEY"})
    d20["pop"] = d20[["u15", "a1564", "o65"]].sum(axis=1)
    d20["unk_share"] = 1 - d20["pop"] / d20["tot"]
    g = g20.merge(d20[["KEY", "NAME", "pop", "o65", "tot", "unk_share"]], on="KEY", how="left")
    g = g.rename(columns={"pop": "pop20", "o65": "o6520"})
    # 列：002〜016＝5歳階級（0〜4歳〜70〜74歳）、017＝15歳未満、018＝15〜64歳、019＝65歳以上
    # 2000年：境界に人口をのせ、面積按分で 2020年の境界へ
    g00 = shapes("2000", pref, wards).to_crs(epsg)
    d00 = load_2000(pref)
    d00 = d00[d00["HTKSYU"] == "0"].dropna(subset=["o65"])  # 秘匿・合算の区域（HTKSYU≠0）は除く
    d00["pop"] = d00[["u15", "a1564", "o65"]].sum(axis=1)
    g00 = g00.merge(d00[["KEY_CODE", "pop", "o65"]], on="KEY_CODE", how="inner")
    g00["a00"] = g00.area
    ov = gpd.overlay(g00, g[["KEY", "geometry"]], how="intersection", keep_geom_type=True)
    ov["w"] = ov.area / ov["a00"]
    agg = ov.assign(pop00=ov["pop"] * ov["w"], o6500=ov["o65"] * ov["w"]).groupby("KEY")[["pop00", "o6500"]].sum()
    g = g.merge(agg, left_on="KEY", right_index=True, how="left")
    g["city"] = city
    return g, g00


if __name__ == "__main__":
    rows = []
    for city, cfg in CITIES.items():
        g, g00 = build(city, cfg)
        g.to_file(DATA / "units.gpkg", layer=city, driver="GPKG")
        g00[["KEY_CODE", "pop", "o65", "geometry"]].to_file(DATA / "units2000_own.gpkg", layer=city, driver="GPKG")
        g.drop(columns="geometry").to_csv(DATA / f"units_{city}.csv", index=False, encoding="utf-8-sig")
        rows.append(dict(city=city, n2020=len(g), pop20=g["pop20"].sum(), pop00_interp=g["pop00"].sum(), n2000_own=len(g00), pop00_own=g00["pop"].sum()))
    print(pd.DataFrame(rows).to_string())
