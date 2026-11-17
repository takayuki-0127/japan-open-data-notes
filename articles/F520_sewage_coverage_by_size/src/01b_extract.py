"""data/download/municipal_keinen.xlsx（約45MB、同梱しない）から「八 下水道等」の列だけを data/raw/sewage_extract.csv に抜き出す。
ネットにはつながない。run_all.sh からは呼ばない。"""
import csv, pathlib
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "download" / "municipal_keinen.xlsx"
OUT = ROOT / "data" / "raw" / "sewage_extract.csv"
COLS = {"public_sewer": 44, "agri": 50, "fishery": 57, "forest": 64, "simple": 71, "small": 78, "community_plant": 83, "johkaso": 84}


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True)
    ws = wb[wb.sheetnames[0]]
    hdr = [r for r in ws.iter_rows(max_row=12, values_only=True)]
    # 列の見出しを確かめる（現在処理区域内人口・処理人口）
    lab = {k: " ".join(str(hdr[i][j]) for i in range(1, 12) if hdr[i][j] is not None) for k, j in COLS.items()}
    assert "処理" in lab["public_sewer"] and "区域内人口" in lab["public_sewer"], lab
    assert "合併処理" in lab["johkaso"] and "コミュニ" in lab["community_plant"], lab
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "kubun", "code", "pref", "name"] + list(COLS))
        for r in ws.iter_rows(values_only=True):
            if r and r[0] is not None and str(r[0]).strip().isdigit() and len(str(r[0]).strip()) == 4:
                w.writerow([("" if v is None else str(v).strip()) for v in r[:5]] + [r[j] for j in COLS.values()])


if __name__ == "__main__":
    main()
