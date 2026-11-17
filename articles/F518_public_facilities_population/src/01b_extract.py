"""data/download/municipal_keinen.xlsx（約45MB、同梱しない）から、使う列だけを data/raw/municipal_extract.csv に抜き出す。
ネットにはつながない。run_all.sh からは呼ばない（抜き出した CSV を同梱している）。"""
import csv, pathlib
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "download" / "municipal_keinen.xlsx"
OUT = ROOT / "data" / "raw" / "municipal_extract.csv"
S1 = {"honchosha_area": 123, "shisho_n": 125, "jidokan_n": 130, "kokaido_n": 136, "kominkan_n": 139, "toshokan_n": 142, "taiikukan_n": 163}
S2 = {"bld_honchosha": 10, "bld_shobo": 16, "bld_gyosei_other": 22, "bld_elem": 28, "bld_junior": 34, "bld_compulsory": 40, "bld_high": 46,
      "bld_secondary": 52, "bld_housing": 58, "bld_park": 64, "bld_public_other": 70, "bld_forest": 76, "bld_other": 82, "bld_admin_total": 88,
      "bld_general_total": 118}


def rows(ws):
    for r in ws.iter_rows(values_only=True):
        if r and r[0] is not None and str(r[0]).strip().isdigit() and len(str(r[0]).strip()) == 4:
            yield r


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True)
    a, b = wb[wb.sheetnames[0]], wb[wb.sheetnames[1]]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "kubun", "code", "pref", "name"] + list(S1) + list(S2))
        for r1, r2 in zip(rows(a), rows(b)):
            assert r1[:5] == r2[:5], (r1[:5], r2[:5])
            w.writerow([str(x).strip() for x in r1[:5]] + [r1[j] for j in S1.values()] + [r2[j] for j in S2.values()])


if __name__ == "__main__":
    main()
