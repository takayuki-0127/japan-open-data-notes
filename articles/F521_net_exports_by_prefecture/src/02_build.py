"""県民経済計算の主要系列表から、都道府県×年度の表 data/pref_year.csv を作る（単位：100万円、名目）。
列：year, code, pref, gdp_exp（県内総生産・支出側）, netexp（財貨・サービスの移出入・純）, discrepancy（統計上の不突合）, factor_income（域外からの要素所得・純）,
gdp（県内総生産・生産側）と産業別（agri, mining, manuf, utility, constr, trade, transport, accom, ict, finance, realestate, prof, public, educ, othsvc_b, othsvc）"""
import pathlib, re
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
# 列の位置は見出しの文字で確かめてから使う
EXP = {"netexp_sum": (44, "移出入"), "netexp": (45, "移出入（純）"), "discrepancy": (46, "統計上の不突合"), "gdp_exp": (47, "県内総生産（支出側）"), "factor_income": (48, "域外からの要素所得")}
IND = {"agri": (3, "農林水産業"), "mining": (7, "鉱業"), "manuf": (8, "製造業"), "utility": (29, "電気・ガス"), "constr": (32, "建設業"),
       "trade": (33, "卸売・小売業"), "transport": (41, "運輸・郵便業"), "accom": (42, "宿泊・飲食"), "ict": (43, "情報通信業"),
       "finance": (46, "金融・保険業"), "realestate": (47, "不動産業"), "prof": (50, "専門・科学技術"), "public": (51, "公務"),
       "educ": (52, "教育"), "othsvc_b": (53, "社会事業"), "othsvc": (54, "その他のサービス"), "gdp": (63, "県内総生産")}


def num(v):
    if v is None or (isinstance(v, str) and v.strip() in ("-", "x", "…", "")):
        return float("nan")
    return float(v)


def read(path, spec):
    wb = openpyxl.load_workbook(path, read_only=True)
    out = []
    for sn in wb.sheetnames:
        y = int(re.match(r"(\d{4})", sn).group(1))
        rows = list(wb[sn].iter_rows(values_only=True))
        head = {j: "".join(str(rows[i][j]).replace("\n", "") for i in range(3, 7) if j < len(rows[i]) and rows[i][j] is not None) for j in range(len(rows[3]))}
        for k, (j, lab) in spec.items():
            assert lab in head[j], (path.name, sn, k, head[j])
        for r in rows:
            if isinstance(r[0], str) and re.fullmatch(r"\d{2}", r[0].strip()):
                out.append({"year": y, "code": r[0].strip(), "pref": str(r[1]).strip(), **{k: num(r[j]) for k, (j, _) in spec.items()}})
    d = pd.DataFrame(out)
    assert (d.groupby("year").size() == 47).all()
    return d


def main():
    a = read(RAW / "syuyo4.xlsx", EXP)
    b = read(RAW / "syuyo1.xlsx", IND)
    d = a.merge(b, on=["year", "code", "pref"], how="inner", validate="1:1")
    assert len(d) == 47 * 13
    d.sort_values(["year", "code"]).to_csv(ROOT / "data" / "pref_year.csv", index=False, float_format="%.0f")
    print(d.isna().sum()[d.isna().sum() > 0]); print(d[d.year == 2023][["pref", "netexp", "discrepancy", "netexp_sum", "gdp_exp", "gdp"]].head(14))
    print((abs(d.gdp - d.gdp_exp)).max(), (abs(d.netexp + d.discrepancy - d.netexp_sum)).max())


if __name__ == "__main__":
    main()
