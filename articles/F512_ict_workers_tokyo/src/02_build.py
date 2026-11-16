"""国勢調査（常住地）と経済センサス（事業所の所在地）から、都道府県×産業の人数の表を作る。
data/census.csv：pref_code, pref, sex, ind, y2005, y2010, y2015, y2020, y2015c, y2020c（c は不詳補完値）
data/ecensus2021.csv：pref_code, pref, ind, workers"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
IND = {"総数": "total", "G": "G", "J": "J", "L": "L"}


def main():
    d = pd.read_excel(RAW / "census_ts_t05_industry_pref.xlsx", header=None)
    d = d[d[0].astype(str).str.match(r"^\d{5}_")]
    d = d.assign(code=d[3].where(d[3].notna(), d[4]).astype(str).str.strip())
    d = d[d.code.isin(IND)]
    out = pd.DataFrame({
        "pref_code": d[0].str[:2].astype(int), "pref": d[0].str[6:], "sex": d[1], "ind": d.code.map(IND),
        "y2005": d[5], "y2010": d[6], "y2015": d[7], "y2020": d[8], "y2015c": d[9], "y2020c": d[10]})
    for c in ["y2005", "y2010", "y2015", "y2020", "y2015c", "y2020c"]:
        out[c] = pd.to_numeric(out[c]).astype(int)
    out = out.sort_values(["pref_code", "sex", "ind"]).reset_index(drop=True)
    assert out.groupby(["sex", "ind"]).size().eq(47).all()
    out.to_csv(ROOT / "data" / "census.csv", index=False)

    e = pd.read_excel(RAW / "ecensus2021_t2_2_pref.xlsx", header=None)
    e = e[e[1].astype(str).str.match(r"^\d{2}_") & e[3].astype(str).str.match(r"^(AR|G|J|L)_")]
    eo = pd.DataFrame({"pref_code": e[1].str[:2].astype(int), "pref": e[1].str[3:],
                       "ind": e[3].str.split("_").str[0].replace({"AR": "total"}), "workers": pd.to_numeric(e[5]).astype(int)})
    eo = eo[eo.pref_code > 0].sort_values(["pref_code", "ind"]).reset_index(drop=True)
    assert eo.groupby("ind").size().eq(47).all()
    eo.to_csv(ROOT / "data" / "ecensus2021.csv", index=False)


if __name__ == "__main__":
    main()
