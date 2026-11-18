"""ESRI の暦年 CSV（cp932）と CPI 中分類（暦年）から data/annual.csv を作る（オフライン）。"""
import pathlib, io, csv
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def read(name):
    rows = list(csv.reader(io.StringIO((RAW / name).read_bytes().decode("cp932"))))
    return rows[2], rows[3], rows[4], [r for r in rows if r and r[0].endswith("/1-12.")]


def num(s):
    s = str(s).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def idx(hdr, name, start=0):
    for i in range(start, len(hdr)):
        if hdr[i].strip() == name:
            return i
    raise KeyError(name)


def main():
    out = {}
    j2, j3, j4, d = read("esri_qe2026q2_2nd_def-cy2622.csv")
    hh = idx(j3, "家計最終消費支出")
    cd = {"defl_gdp": idx(j2, "国内総生産(支出側)"), "defl_pce": idx(j2, "民間最終消費支出"), "defl_hh": hh,
          "defl_hh_xrent": idx(j4, "除く持ち家の帰属家賃"), "defl_dd": idx(j2, "国内需要"),
          "defl_x": idx(j3, "輸出"), "defl_m": idx(j3, "輸入")}
    for r in d:
        out.setdefault(int(r[0][:4]), {}).update({k: num(r[c]) for k, c in cd.items()})
    j2, j3, j4, d = read("esri_qe2026q2_2nd_gaku-mcy2622.csv")
    cols = lambda j2, j3, j4: {"gdp": idx(j2, "国内総生産(支出側)"), "pce": idx(j2, "民間最終消費支出"), "hh": idx(j3, "家計最終消費支出"),
                               "hh_xrent": idx(j4, "除く持ち家の帰属家賃"), "dd": idx(j2, "国内需要"), "x": idx(j3, "輸出"), "m": idx(j3, "輸入")}
    for r in d:
        out.setdefault(int(r[0][:4]), {}).update({"nom_" + k: num(r[c]) for k, c in cols(j2, j3, j4).items()})
    j2, j3, j4, d = read("esri_qe2026q2_2nd_gaku-jcy2622.csv")
    for r in d:
        out.setdefault(int(r[0][:4]), {}).update({"real_" + k: num(r[c]) for k, c in cols(j2, j3, j4).items()})
    df = pd.DataFrame([dict(year=y, **v) for y, v in sorted(out.items())])
    # 名目÷実質×100（表のデフレーターは小数1桁に丸めてあるため、前年比はこちらで計算する）
    for k in ["gdp", "pce", "hh", "hh_xrent", "dd", "x", "m"]:
        df["impl_" + k] = df["nom_" + k] / df["real_" + k] * 100
    # CPI（暦年の表 000040482829）
    c = pd.read_csv(RAW / "cpi2025_middle_annual_cy.csv", encoding="cp932", header=None, dtype=str)
    code = c.iloc[2].tolist()
    yrs = c.iloc[6:, 0].str.strip()
    cpi = pd.DataFrame({"year": yrs.astype(int).values,
                        "cpi_all": c.iloc[6:, code.index("0001")].astype(float).values,
                        "cpi_xrent": c.iloc[6:, code.index("0163")].astype(float).values})
    assert c.iloc[0, code.index("0163")] == "持家の帰属家賃を除く総合"
    df = df.merge(cpi, on="year", how="left")
    df.to_csv(ROOT / "data" / "annual.csv", index=False)
    print(df.shape, df.year.min(), df.year.max())
    for k, t in [("gdp", "defl_gdp"), ("pce", "defl_pce"), ("hh", "defl_hh"), ("hh_xrent", "defl_hh_xrent"), ("dd", "defl_dd"), ("x", "defl_x"), ("m", "defl_m")]:
        print(k, "max|名目/実質*100-表|", round(float((df["impl_" + k] - df[t]).abs().max()), 3))


if __name__ == "__main__":
    main()
