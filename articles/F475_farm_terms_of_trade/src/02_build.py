"""data/raw の Excel を読み、年（暦年）・月・ウエイトの CSV を作る。列の名前は表の見出しの文字で付ける。"""
import pathlib, re
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"


def to_num(v):
    if v is None or isinstance(v, str):
        try:
            return float(v)
        except (TypeError, ValueError):
            return float("nan")
    return float(v)


def read_index(fname, group):
    ws = openpyxl.load_workbook(RAW / fname, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    # 見出し：「階層」の行と、その3行下（いちばん細かい名前）を探す
    hi = next(i for i, r in enumerate(rows) if r[5] == "階層")
    lvl, name = rows[hi], rows[hi + 3]
    assert rows[hi + 6][4] == "月別・年次別（西暦）", rows[hi + 6]
    cols = [(j, name[j], int(lvl[j])) for j in range(6, len(name)) if name[j] is not None]
    names = [c[1] for c in cols]
    assert len(names) == len(set(names)), "列の名前が重複"
    out = []
    for r in rows[hi + 7:]:
        if r[1] not in ("年平均", "月"):
            continue
        lab = str(r[4])
        if r[1] == "年平均":
            m = re.fullmatch(r"(\d{4})年(度?)", lab)
            kind = "fiscal_year" if m.group(2) else "calendar_year"
            y, mo = int(m.group(1)), 0
        else:
            m = re.fullmatch(r"(\d{4})年(\d{1,2})月", lab)
            kind, y, mo = "month", int(m.group(1)), int(m.group(2))
        for j, nm, lv in cols:
            out.append((group, kind, y, mo, nm, lv, to_num(r[j])))
    return pd.DataFrame(out, columns=["group", "kind", "year", "month", "class", "level", "index"])


def read_weights(fname, group):
    ws = openpyxl.load_workbook(RAW / fname, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r[1] == "階層")
    lvl, name2 = rows[hi], rows[hi + 2]
    yr = next(r for r in rows[hi:] if r[0] == "年")
    out = []
    for j in range(2, len(lvl)):
        if lvl[j] in (1, 2):
            out.append((group, name2[j], int(lvl[j]), to_num(yr[j])))
    return pd.DataFrame(out, columns=["group", "class", "level", "weight"])


idx = pd.concat([read_index("agri_products_class_index.xlsx", "products"),
                 read_index("agri_inputs_class_index.xlsx", "inputs")], ignore_index=True)
idx = idx.sort_values(["group", "kind", "year", "month", "class"]).reset_index(drop=True)
idx.to_csv(D / "index_long.csv", index=False, float_format="%.1f")

w = pd.concat([read_weights("agri_products_weights.xlsx", "products"),
               read_weights("agri_inputs_weights.xlsx", "inputs")], ignore_index=True)
w.to_csv(D / "weights_class.csv", index=False, float_format="%.0f")
print(idx.groupby(["group", "kind"]).year.agg(["min", "max", "count"]))
print(w)
