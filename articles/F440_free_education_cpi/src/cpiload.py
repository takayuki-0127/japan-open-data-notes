"""消費者物価指数の長期時系列 CSV（e-Stat、Shift_JIS）を読む共通関数。"""
import csv


def read_cpi(path):
    """見出し（名前・符号・ウエイト）と、行（年または年月 → 値の列）を返す。"""
    with open(path, encoding="cp932", newline="") as f:
        rows = list(csv.reader(f))
    names, codes, weights = rows[0], rows[2], rows[4]
    body = []
    for r in rows[6:]:
        if not r or not r[0].strip():
            continue
        body.append([r[0].strip()] + r[1:])
    return names, codes, weights, body


def series(path, wanted_codes):
    """wanted_codes の各符号について、(期間, 値) の表（list of dict）を返す。空欄は除く。"""
    names, codes, weights, body = read_cpi(path)
    out = []
    for code in wanted_codes:
        if code not in codes:
            continue
        j = codes.index(code)
        for r in body:
            v = r[j].strip() if j < len(r) else ""
            if v in ("", "-", "…", "***"):
                continue
            out.append({"period": r[0], "code": code, "name": names[j], "weight": float(weights[j]), "value": float(v)})
    return out


def all_items(path):
    """表のすべての列（総合を含む）の (符号, 名前, ウエイト) と行。"""
    return read_cpi(path)
