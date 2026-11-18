"""共通の関数。年次統計の Excel を、見出しの文字で列を選んで読む。"""
import pathlib, re
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def _year(v):
    if v is None:
        return None
    s = str(v).strip()
    return int(s) if re.fullmatch(r"(19|20)\d\d", s) else None


def read_nenji(fname):
    """見出しの行（A列が「区分」の行）をつないだ列名で DataFrame を返す。年は B 列の西暦。"""
    ws = openpyxl.load_workbook(RAW / fname, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    head = [r for r in rows if r[0] == "区分"]
    ncol = max(len(r) for r in rows)
    names = []
    for j in range(ncol):
        parts = []
        for h in head:
            v = h[j] if j < len(h) else None
            if v is None:
                continue
            v = re.sub(r"\s+", "", str(v))
            if not parts or parts[-1] != v:
                parts.append(v)
        names.append("|".join(parts))
    data = []
    for r in rows:
        y = _year(r[1]) if len(r) > 1 else None
        if y is None:
            continue
        vals = {}
        for j, n in enumerate(names[2:], start=2):
            v = r[j] if j < len(r) else None
            vals[n] = float(v) if isinstance(v, (int, float)) else None
        vals["year"] = y
        data.append(vals)
    df = pd.DataFrame(data).set_index("year").sort_index()
    return df


def col(df, *keys):
    """見出しの文字をすべて含む列を1つだけ選ぶ（なければ・2つ以上あればエラー）。"""
    c = [n for n in df.columns if all(k in n.split("|") for k in keys)]
    if len(c) != 1:
        raise KeyError(f"{keys} -> {c}")
    return df[c[0]]


# ---- F503 用：古い .xls と .xlsx を同じ形で読む ----
def sheet_rows(fname, si=0):
    p = RAW / fname
    if p.suffix == ".xls":
        import xlrd
        sh = xlrd.open_workbook(p).sheet_by_index(si)
        return [sh.row_values(i) for i in range(sh.nrows)]
    ws = openpyxl.load_workbook(p, data_only=True).worksheets[si]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def label_and_first(r):
    """数のセルより前の文字をつないだ見出し（空白を除く）と、最初の数（表の「計」の列）を返す。"""
    lab = []
    for c in r:
        if isnum(c):
            return re.sub(r"\s+", "", "".join(lab)), float(c)
        if isinstance(c, str) and c.strip() in ("－", "-", "…"):
            return re.sub(r"\s+", "", "".join(lab)), 0.0
        if c is not None:
            lab.append(str(c))
    return re.sub(r"\s+", "", "".join(lab)), None
