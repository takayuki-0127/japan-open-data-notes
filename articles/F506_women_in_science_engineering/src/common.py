"""共通の関数。学校基本調査の高等教育の表（.xls と .xlsx、年によって形が違う）を、
見出しの文字（計・入学者・男・女）で列を、分野の文字で行を選んで読む。行の順番には頼らない。"""
import pathlib, re
import openpyxl
import xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"

FIELDS = ["人文科学", "社会科学", "理学", "工学", "農学", "保健", "商船", "家政", "教育", "芸術", "その他"]


def norm(v):
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[\s　]+", "", str(v))
    s = s.replace("･", "・").replace("（", "(").replace("）", ")")
    s = s.replace("土木・建築工学", "土木建築工学").replace("生物学", "生物")
    if len(s) > 2 and s.endswith("関係") and not s.startswith("関係"):
        s = s[:-2]
    return s


def year_token(v):
    if isinstance(v, float):
        n = int(v)
        return 1988 + n if 1 <= n <= 31 else None
    m = re.fullmatch(r"(平成|令和)(元|\d+)年度?", v)
    if not m:
        return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return (1988 if m.group(1) == "平成" else 2018) + n


def sheets(path):
    path = pathlib.Path(path)
    if path.suffix == ".xls":
        wb = xlrd.open_workbook(str(path))
        for sh in wb.sheets():
            yield [[norm(sh.cell_value(i, j)) for j in range(sh.ncols)] for i in range(sh.nrows)]
    else:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            rows = [[norm(v) for v in r] for r in ws.iter_rows(values_only=True)]
            n = max((len(r) for r in rows), default=0)
            yield [r + [""] * (n - len(r)) for r in rows]


def sheet_title(g):
    return "".join(v for r in g[:4] for v in r if isinstance(v, str))


def parse_entrants(g):
    """1枚のシートから {分野のタプル: (計, 男, 女)}（入学者、国公私の計）と、その年の年度を返す。"""
    # いちばん下の見出しの行：「男」「女」を含む最初の行
    bot = next(i for i, r in enumerate(g) if "男" in r and "女" in r)
    top = max(0, bot - 3)
    hdr = g[top:bot + 1]
    ncol = len(g[0])
    has_mid = any("入学者" in h for h in hdr)
    # 列の見出しを左から右へ伸ばして読む（いちばん下の行は伸ばさない）
    filled = []
    for h in hdr[:-1]:
        cur, row = "", []
        for j in range(ncol):
            v = h[j] if isinstance(h[j], str) else ""
            if v:
                cur = v
            row.append(cur)
        filled.append(row)
    jf = None
    for j in range(ncol):
        if hdr[-1][j] != "女":
            continue
        if has_mid and not any(f[j] == "入学者" for f in filled):
            continue
        jf = j
        break
    assert hdr[-1][jf - 2] == "計" and hdr[-1][jf - 1] == "男", hdr[-1][jf - 2:jf + 1]
    # 計の列が国公私の「計」の塊であること（その上の見出しが「計」か空）を確かめる
    tops = {f[jf] for f in filled if not re.match(r"^\d", f[jf])} - {"", "入学者", "区分"}
    assert tops <= {"計"}, tops
    c0 = jf - 2 if not has_mid else jf - 5
    out, year = {}, None
    path = [None] * c0
    for i in range(bot + 1, len(g)):
        r = g[i]
        nums = [r[j] for j in (jf - 2, jf - 1, jf)]
        if not all(isinstance(v, float) for v in nums):
            continue
        labels = r[:c0]
        first = next((c for c in range(c0) if labels[c] != ""), None)
        if first is not None:
            path[first] = labels[first]
            for d in range(first + 1, c0):
                path[d] = None
            for c in range(first + 1, c0):
                if labels[c] != "":
                    path[c] = labels[c]
        key = [v for v in path if v not in (None, "")]
        ys = [year_token(v) for v in key]
        ys = [y for y in ys if y]
        key = [v for v in key if not year_token(v) and isinstance(v, str)]
        while key and key[-1] == "計":
            key.pop()
        if ys and not key:  # 年の行（計）
            y = ys[0]
            if year is None or y > year:
                year = y
                out[("計", y)] = tuple(nums)
            continue
        if ys and ys[0] != max(ys):
            continue
        out[tuple(key)] = tuple(nums)
    total = out.pop(("計", year))
    for k in [k for k in out if len(k) == 2 and k[0] == "計" and isinstance(k[1], int)]:
        out.pop(k)
    out[("計",)] = total
    for k in list(out):
        if len(k) == 2 and k[1] == "計":
            raise ValueError(k)
    return out, year
