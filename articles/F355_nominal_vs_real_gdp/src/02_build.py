"""ESRI の暦年 CSV（cp932）から data/annual.csv を作る（オフライン）。単位：10億円、デフレーターは2020年＝100。"""
import pathlib, io, csv
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def read(name):
    rows = list(csv.reader(io.StringIO((RAW / name).read_bytes().decode("cp932"))))
    jp2, jp3 = rows[2], rows[3]
    data = [r for r in rows if r and r[0].endswith("/1-12.")]
    return jp2, jp3, data


def num(s):
    s = str(s).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def col(jp2, jp3, name, level=2):
    hdr = jp2 if level == 2 else jp3
    idx = [i for i, h in enumerate(hdr) if h.strip() == name]
    assert idx, name
    return idx[0]


def main():
    out = {}
    j2, j3, d = read("esri_qe2026q2_2nd_gaku-mcy2622.csv")
    cm = {"nominal_gdp": col(j2, j3, "国内総生産(支出側)"), "nominal_domestic_demand": col(j2, j3, "国内需要"), "nominal_gni": col(j2, j3, "国民総所得"),
          "nominal_pce": col(j2, j3, "民間最終消費支出")}
    for r in d:
        y = int(r[0][:4]); out.setdefault(y, {}).update({k: num(r[c]) for k, c in cm.items()})
    j2, j3, d = read("esri_qe2026q2_2nd_gaku-jcy2622.csv")
    cr = {"real_gdp": col(j2, j3, "国内総生産(支出側)"), "real_domestic_demand": col(j2, j3, "国内需要"), "trading_gains": col(j2, j3, "交易利得"),
          "real_gdi": col(j2, j3, "国内総所得"), "real_gni": col(j2, j3, "国民総所得"), "residual": col(j2, j3, "開差")}
    for r in d:
        y = int(r[0][:4]); out.setdefault(y, {}).update({k: num(r[c]) for k, c in cr.items()})
    j2, j3, d = read("esri_qe2026q2_2nd_def-cy2622.csv")
    cd = {"defl_gdp": col(j2, j3, "国内総生産(支出側)"), "defl_domestic_demand": col(j2, j3, "国内需要"), "defl_pce": col(j2, j3, "民間最終消費支出"),
          "defl_exports": col(j2, j3, "輸出", 3), "defl_imports": col(j2, j3, "輸入", 3)}
    for r in d:
        y = int(r[0][:4]); out.setdefault(y, {}).update({k: num(r[c]) for k, c in cd.items()})
    df = pd.DataFrame([dict(year=y, **v) for y, v in sorted(out.items())])
    df.to_csv(ROOT / "data" / "annual.csv", index=False)
    chk = (df.nominal_gdp / df.real_gdp * 100 - df.defl_gdp).abs().max()
    print(df.shape, df.year.min(), df.year.max(), "max |nominal/real*100 - deflator|", round(float(chk), 3))
    print(df.iloc[[0, -1]].T.to_string())


if __name__ == "__main__":
    main()
