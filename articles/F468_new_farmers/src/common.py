"""新規就農者調査の表1（年ごとに様式が違う）を、見出しの文字（形の名前・年の名前）と行の名前で読む。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
FORM = {"計": "total", "自営農業就農者": "jiei", "新規自営農業就農者": "jiei", "雇用就農者": "koyo", "新規雇用就農者": "koyo", "新規参入者": "sannyu"}
ROWS = {"男女計": "all", "39歳以下": "le39", "49歳以下": "le49", "44歳以下": "le44", "15～19歳": "a15", "20～29": "a20", "30～39": "a30",
        "40～49": "a40", "40～44": "a40_44", "45～49": "a45_49", "50～59": "a50", "60～64": "a60", "65歳以上": "a65", "性別・年齢不詳": "unk"}


def _n(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s))).replace("うち", "")


def norm(s):
    return _n(s)


ROWS = {_n(k): v for k, v in ROWS.items()}
FORM = {_n(k): v for k, v in FORM.items()}


def grid(path):
    if path.suffix == ".xlsx":
        import openpyxl
        ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
        g = [[ws.cell(r, c).value for c in range(1, ws.max_column + 1)] for r in range(1, ws.max_row + 1)]
        merges = [(m.min_row - 1, m.max_row, m.min_col - 1, m.max_col) for m in ws.merged_cells.ranges]
    else:
        import xlrd
        sh = xlrd.open_workbook(path, formatting_info=True, logfile=open("/dev/null", "w")).sheet_by_index(0)
        g = [[(v if v != "" else None) for v in sh.row_values(r)] for r in range(sh.nrows)]
        merges = list(sh.merged_cells)
    out = [list(r) for r in g]
    for rlo, rhi, clo, chi in merges:  # 横に結合された見出しだけ広げる（データの縦の結合は広げない）
        if rhi - rlo == 1 or True:
            v = g[rlo][clo]
            for c in range(clo, chi):
                out[rlo][c] = v
    return out, merges


def year_of(label, era):
    s = norm(label)
    if "増減" in s or s == "": return None, era
    s = re.sub(r"^\d\)", "", s)
    m = re.match(r"^(平成|令和)?(元|\d+)(?:\.0)?年?$", s)
    if not m: return None, era
    if m.group(1): era = m.group(1)
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return (1988 if era == "平成" else 2018) + n, era


def to_num(v):
    if isinstance(v, (int, float)): return float(v)
    s = norm(v or "")
    if s in ("-", "0"): return 0.0
    return None  # 「…」や注つきの文字は使わない


def read_t1(name):
    """戻り値：DataFrame(year, form, row, value, vertical_merge)。男女計の塊（「男計」の前まで）だけ。"""
    g, merges = grid(RAW / name)
    h = next(i for i, r in enumerate(g) if any(norm(x or "") == "計" for x in r) and any("新規参入者" in norm(x or "") for x in r))
    def nyears(r):
        e, n = None, 0
        for x in r:
            if x is None: continue
            y, e = year_of(x, e)
            n += y is not None
        return n
    yrow = next(i for i in range(h + 1, h + 4) if nyears(g[i]) >= 2)
    forms = [FORM.get(norm(x or "")) for x in g[h]]
    cols = {}
    era = None
    for c, x in enumerate(g[yrow]):
        if forms[c] is None: continue
        y, era = year_of(x, era) if x is not None else (None, era)
        if y: cols[c] = (forms[c], y)
    vert = set()
    for rlo, rhi, clo, chi in merges:  # 縦に結合されたデータのセル（年齢をまとめた区分）
        if rhi - rlo > 1 and rlo > yrow:
            for r in range(rlo, rhi):
                for c in range(clo, chi): vert.add((r, c))
    recs = []
    started = False
    for i in range(yrow + 1, len(g)):
        lab = norm(g[i][0] or "")
        if lab == "男女計": started = True
        if lab in ("男計",): break
        if not started or lab not in ROWS: continue
        for c, (f, y) in cols.items():
            recs.append({"year": y, "form": f, "row": ROWS[lab], "value": to_num(g[i][c]), "vertical_merge": (i, c) in vert, "file": name})
    return pd.DataFrame(recs)
