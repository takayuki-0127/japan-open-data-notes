"""貿易統計の CSV（世界・中国・ASEAN・米国）から、電算機類（含周辺機器）と電話機の年別の金額（千円）・数量（台）を取り出す。
日本銀行のドル円（月中平均）を年平均と12月の値にする。data/imports.csv、data/usdjpy.csv"""
import csv, io, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AREAS = {"d61ca.csv": "世界", "d62ca004.csv": "中国", "d62ca006.csv": "ASEAN", "d62ca001.csv": "米国"}
ITEMS = {"電算機類(含周辺機器)": "computers", "（電話機）": "phones"}


def num(s):
    s = s.strip().replace(",", "")
    return None if s in ("", "-") else float(s)


def main():
    out = []
    for f, area in AREAS.items():
        rows = list(csv.reader(io.StringIO((RAW / f).read_bytes().decode("cp932"))))
        hdr = rows[2]
        for j, h in enumerate(hdr):
            if h.strip() in ITEMS:
                assert rows[5][j] == "数量" and rows[5][j + 1] == "金額", (f, h)
                for r in rows[6:]:
                    if r and r[0].strip().isdigit():
                        out.append((area, ITEMS[h.strip()], int(r[0]), num(r[j]), num(r[j + 1])))
    d = pd.DataFrame(out, columns=["area", "item", "year", "qty", "value_thousand_yen"])
    d.sort_values(["area", "item", "year"]).to_csv(ROOT / "data" / "imports.csv", index=False)

    lines = (RAW / "boj_fxerm07.csv").read_bytes().decode("cp932").splitlines()
    i0 = next(i for i, l in enumerate(lines) if l.startswith("SERIES_CODE"))
    fx = pd.read_csv(io.StringIO("\n".join(lines[i0:])))
    fx["ym"] = fx.SURVEY_DATES.astype(str)
    fx["year"] = fx.ym.str[:4].astype(int)
    ann = fx.groupby("year").VALUES.mean().round(4).rename("usdjpy_avg").to_frame()
    ann["usdjpy_dec"] = fx[fx.ym.str[4:] == "12"].set_index("year").VALUES
    ann.to_csv(ROOT / "data" / "usdjpy.csv")


if __name__ == "__main__":
    main()
