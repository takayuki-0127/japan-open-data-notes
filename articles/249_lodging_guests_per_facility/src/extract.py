"""観光庁「宿泊旅行統計調査」年の確定値（2015〜2025年）の Excel から、全国の行だけを取り出して CSV にする。
使い方: python extract.py <Excel のあるフォルダ> <出力フォルダ>
Excel は fetch.py で観光庁のサイトから取得する（ファイル名 y<年>_<番号>.xlsx）。"""
import sys, re, glob, pathlib, csv
import openpyxl

SIZE = ["total", "tour", "biz", "s0_9", "s0_9_tour", "s0_9_biz", "s10_29", "s10_29_tour", "s10_29_biz",
        "s30_99", "s30_99_tour", "s30_99_biz", "s100", "s100_tour", "s100_biz"]
TYPES = ["ryokan", "resort", "business", "city", "kani", "kaisha"]
COLS = {
    1: SIZE + TYPES,                                     # 施設数（月別）
    2: SIZE + ["foreign", "foreign_tour", "foreign_biz"],  # 延べ宿泊者数
    3: SIZE + ["foreign", "foreign_tour", "foreign_biz"],  # 実宿泊者数
    4: ["total"] + TYPES + ["foreign"] + ["foreign_" + t for t in TYPES],  # タイプ別 延べ
    5: ["total"] + TYPES + ["foreign"] + ["foreign_" + t for t in TYPES],  # タイプ別 実
    6: SIZE + TYPES,                                     # 定員稼働率
    8: SIZE + TYPES,                                     # 客室稼働率
}

def num(v):
    if v is None: return ""
    if isinstance(v, (int, float)): return v
    s = str(v).strip().replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else ""

def national(ws):
    for row in ws.iter_rows(min_row=5, max_row=12, values_only=True):
        if row[0] and ("年" in str(row[0])) and isinstance(num(row[1]), (int, float)):
            return row
    raise ValueError("national row not found: " + ws.title)

def main(src, out):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = {t: [] for t in COLS}
    for f in sorted(glob.glob(str(pathlib.Path(src) / "y20*.xlsx"))):
        y = int(re.search(r"y(\d{4})_", f).group(1))
        if y < 2015: continue
        wb = openpyxl.load_workbook(f, read_only=True)
        for t, names in COLS.items():
            periods = ["年計"] + [f"{m}月" for m in range(1, 13)]
            if t == 1: periods = periods[1:]
            for p in periods:
                sh = f"第{t}表({p})"
                if sh not in wb.sheetnames: continue
                r = national(wb[sh])
                vals = [num(v) for v in r[1:1 + len(names)]]
                m = 0 if p == "年計" else int(p[:-1])
                rows[t].append([y, m] + vals)
        wb.close()
    for t, names in COLS.items():
        with open(out / f"table{t}_national.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["year", "month"] + names); w.writerows(rows[t])
        print(t, len(rows[t]))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
