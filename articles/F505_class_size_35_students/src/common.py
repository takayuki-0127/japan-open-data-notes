"""共通の関数。学校基本調査の Excel（.xls と .xlsx、年によって形が違う）を、
見出しの文字で列を、区分の文字で行を選んで読む。行の順番には頼らない。"""
import pathlib, re
import openpyxl
import xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"

# 都道府県（全国地方公共団体コードの順＝北から南）と地方
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
REGION = {}
for r, ps in [("北海道", ["北海道"]), ("東北", PREFS[1:7]), ("関東", PREFS[7:14]), ("中部", PREFS[14:23]),
              ("近畿", PREFS[23:30]), ("中国", PREFS[30:35]), ("四国", PREFS[35:39]), ("九州・沖縄", PREFS[39:47])]:
    for p in ps:
        REGION[p] = r
REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]


def norm(v):
    """文字は空白・全角空白・改行を除き、全角の数字・記号の一部をそろえる。数は float。"""
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[\s　]+", "", str(v))
    s = s.replace("･", "・").replace("~", "～")
    return s


def pref_name(s):
    if s in PREFS:
        return s
    t = re.sub(r"(都|府|県)$", "", s)
    return t if t in PREFS else None


def year_token(v):
    """区分の欄にある年（平成20、令和4年度、令和元年度 など）を西暦に。年でなければ None。"""
    if isinstance(v, float):
        n = int(v)
        return 1988 + n if 1 <= n <= 31 else None
    m = re.fullmatch(r"(平成|令和)(元|\d+)年度?", v)
    if not m:
        return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return (1988 if m.group(1) == "平成" else 2018) + n


def _sheets(path):
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


def _parse_sheet(g):
    # 見出しの行：「区分」を含む行から、データ（数）の最初の行の前まで
    hdr_start = next((i for i, r in enumerate(g) if "区分" in r), None)
    if hdr_start is None:
        return {}
    first_data = None
    for i in range(hdr_start + 1, len(g)):
        nums = [v for v in g[i] if isinstance(v, float)]
        if len(nums) >= 3:
            first_data = i
            break
    hdr = g[hdr_start:first_data]
    ncol = len(g[0])
    # データの列：見出しの行に「区分」以外の文字がある最初の列から
    cand = [j for j in range(ncol) if any(isinstance(h[j], str) and h[j] and h[j] != "区分" for h in hdr)]
    c0 = min(cand)
    # 右の端にもう一度「区分」の列がある表（古い年の形）は、そこから右を読まない
    right = [j for j in range(c0, ncol) if any(h[j] == "区分" for h in hdr)]
    if right:
        ncol = min(right)
    names = {}
    for j in range(c0, ncol):
        parts = []
        for h in hdr:
            v = h[j] if isinstance(h[j], str) else ""
            if not v:  # 結合セルの左の値を右へ
                k = j
                while k > c0 and not (isinstance(h[k], str) and h[k]):
                    k -= 1
                v = h[k] if isinstance(h[k], str) and h[k] and k < j and _is_group(hdr, h, k, j) else ""
            if v and v != "区分" and (not parts or parts[-1] != v):
                parts.append(v)
        if parts:
            names[j] = "|".join(parts)
    out = {}
    path = [None] * c0
    for i in range(first_data, len(g)):
        r = g[i]
        labels = r[:c0]
        if any(v != "" for v in labels):
            for c in range(c0):
                if labels[c] != "":
                    path[c] = labels[c]
                    for d in range(c + 1, c0):
                        path[d] = None
                    break
            for c in range(c0):  # 同じ行に下の階層もあれば入れる
                if labels[c] != "":
                    path[c] = labels[c]
        vals = {names[j]: r[j] for j in names if j < len(r) and isinstance(r[j], float)}
        if not vals:
            continue
        key = tuple(v for v in path if v not in (None, ""))
        out.setdefault(key, {}).update(vals)
    return out


def _is_group(hdr, h, k, j):
    """見出しの上の行（まとめの見出し）だけ右へ伸ばす。いちばん下の行は伸ばさない。"""
    return h is not hdr[-1]



def parse_table(path):
    """{(年, 区分のタプル): {列名: 値}} を返す。年のない行（公立の内訳など）は直前の年を引き継ぐ。"""
    res = {}
    for g in _sheets(path):
        recs = _parse_sheet(g)
        cur_year = None
        for key, vals in recs.items():
            ys = [year_token(v) for v in key]
            ys = [y for y in ys if y]
            if ys:
                cur_year = ys[0]
            rest = [v for v in key if not (year_token(v) if isinstance(v, (str, float)) else None)]
            rest = [v for v in rest if isinstance(v, str)]
            # 重なりと末尾の「計」を除く
            r2 = []
            for v in rest:
                if not r2 or r2[-1] != v:
                    r2.append(v)
            while r2 and r2[-1] == "計":
                r2.pop()
            k = (cur_year, tuple(r2))
            res.setdefault(k, {}).update(vals)
    return res


def entity(key):
    """区分のタプルを「全国（計）・国立・公立・私立・公立|単式学級・都道府県名」などにする。"""
    if key == ():
        return "計"
    if key[0] == "公立の内訳" and len(key) >= 2:
        return pref_name(key[1])
    if key[0] in ("国立", "公立", "私立"):
        return "|".join(dict.fromkeys(key))
    return None
