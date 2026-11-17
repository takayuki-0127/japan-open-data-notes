"""抜き出した市町村の CSV を都道府県×年度に合計し（data/pref_facilities.csv）、
人口推計の都道府県別人口（千人、10月1日）を年×都道府県の表にする（data/pref_population.csv）。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
NUM = ["honchosha_area", "shisho_n", "jidokan_n", "kokaido_n", "kominkan_n", "toshokan_n", "taiikukan_n", "bld_honchosha", "bld_shobo",
       "bld_gyosei_other", "bld_elem", "bld_junior", "bld_compulsory", "bld_high", "bld_secondary", "bld_housing", "bld_park",
       "bld_public_other", "bld_forest", "bld_other", "bld_admin_total", "bld_general_total"]


def main():
    m = pd.read_csv(RAW / "municipal_extract.csv", dtype=str)
    for c in NUM:
        m[c] = pd.to_numeric(m[c].replace("-", "0"), errors="coerce").fillna(0.0)
    m["year"] = m.year.astype(int)
    tot = m[m.code.isna()].set_index("year")  # 全国の合計の行（検算に使う）
    m = m[m.kubun.notna()].copy()  # 団体区分のない行（都道府県ごとの小計と全国の合計）を除く
    chk = m.groupby("year").bld_admin_total.sum()
    assert (abs(chk - tot.bld_admin_total) < 1).all(), (chk, tot.bld_admin_total)
    m["pref_code"] = m.code.str[:2].astype(int)
    g = m.groupby(["year", "pref_code"], as_index=False)[NUM].sum()
    n = m.groupby(["year", "pref_code"]).size().rename("n_municipalities").reset_index()
    g = g.merge(n, on=["year", "pref_code"]).sort_values(["year", "pref_code"])
    g.to_csv(ROOT / "data" / "pref_facilities.csv", index=False)

    rows = []
    x = pd.ExcelFile(RAW / "pop_pref_2000_2020.xlsx")
    for sheet in ["総人口（2000年～2015年）", "総人口 (2015年～2020年)"]:
        d = pd.read_excel(x, sheet, header=None)
        years = [int(re.sub(r"\D", "", str(v))) if pd.notna(v) else None for v in d.iloc[8].tolist()]
        for i in range(len(d)):
            c = d.iloc[i, 1]
            if isinstance(c, (int, float)) and not pd.isna(c) and 1 <= c <= 47:
                for j, y in enumerate(years):
                    if y:
                        rows.append((y, int(c), float(d.iloc[i, j])))
    d = pd.read_excel(RAW / "pop_pref_2020_2024.xlsx", header=None)
    hdr = d.iloc[6].tolist()
    jcode = hdr.index("都道府県コード")
    ycols = {j: int(str(v)[:4]) for j, v in enumerate(hdr) if re.fullmatch(r"\d{4}年", str(v))}
    for i in range(7, len(d)):
        if str(d.iloc[i, hdr.index("人口区分")]) == "総人口" and str(d.iloc[i, hdr.index("性別")]) == "男女計":
            c = int(str(d.iloc[i, jcode])[:2])
            if 1 <= c <= 47:
                for j, y in ycols.items():
                    rows.append((y, c, float(d.iloc[i, j])))
    p = pd.DataFrame(rows, columns=["year", "pref_code", "pop_thousand"]).drop_duplicates(["year", "pref_code"], keep="last")
    p = p[p.year.between(2006, 2024)].sort_values(["year", "pref_code"])
    assert p.groupby("year").size().eq(47).all()
    p.to_csv(ROOT / "data" / "pref_population.csv", index=False)


if __name__ == "__main__":
    main()
