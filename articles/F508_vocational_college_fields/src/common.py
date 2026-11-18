"""共通の関数と決まり。表から値を読むときは、行の見出しの文字で選ぶ。"""
import pathlib, re
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
YEARS = [1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]
# 分野：短い名前、見出しで探す文字（「関係」と一緒に出る文字）、記事での名前、取り上げるか
FIELDS = [("kogyo", "工業", "工業", True), ("nogyo", "農業", "農業", True), ("iryo", "医療", "（取り上げない分野A）", False),
          ("eisei", "衛生", "衛生（調理・理容・美容など）", True), ("kyoiku", "福祉", "（取り上げない分野B）", False),
          ("shogyo", "商業実務", "商業実務", True), ("kasei", "家政", "服飾・家政", True), ("bunka", "文化・教養", "文化・教養", True)]
SHOWN = [f[0] for f in FIELDS if f[3]]
NAME = {f[0]: f[2] for f in FIELDS}


def clean(s):
    return re.sub(r"[\s　]+", "", str(s)) if s is not None else ""


def isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def sheets(fname):
    p = RAW / fname
    if p.suffix == ".xls":
        import xlrd
        b = xlrd.open_workbook(p)
        return [[b.sheet_by_index(i).row_values(j) for j in range(b.sheet_by_index(i).nrows)] for i in range(b.nsheets)]
    wb = openpyxl.load_workbook(p, data_only=True)
    return [[list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets]


def label_nums(r):
    """数のセルより前の文字をつないだ見出しと、数の並び（「－」は0）を返す。"""
    lab, nums, started = [], [], False
    for c in r:
        if isnum(c) or (isinstance(c, str) and c.strip() in ("－", "-")):
            started = True
            nums.append(float(c) if isnum(c) else 0.0)
        elif not started and c not in (None, ""):
            lab.append(str(c))
    return clean("".join(lab)), nums


def field_of(label):
    if "関係" not in label:
        return None
    p = label.index("関係")
    hit = []
    for k, key, _, _ in FIELDS:  # 「関係」のすぐ前か、すぐ後ろにある分野の文字だけを見る（例：医療関係歯科衛生 → 医療）
        for m in re.finditer(re.escape(key), label):
            if m.end() == p or m.start() == p + 2 or (key == "福祉" and label[:p].endswith("社会福祉")):
                hit.append(k)
    hit = sorted(set(hit))
    return hit[0] if len(hit) == 1 else None
