"""令和8年調査（単年の第1・2・7表、厚生労働省 hyou.xlsx）から2026年の値を取り、時系列表（令和7年調査）の続きに足す。
e-Stat に令和8年の時系列表がまだないため（2026-11-12 時点）。表にある2025年の値が時系列表と一致するかも確かめる。"""
import re
import numpy as np, pandas as pd, openpyxl
from common import DATA, num

R8 = DATA / "r8_hyou.xlsx"
NORM = {"5,000人以上": "5,000人以上", "1,000～4,999人": "1,000～4,999人", "300～999人": "300～999人", "100～299人": "100～299人", "計": "計"}


def _ws(prefix):
    wb = openpyxl.load_workbook(R8, read_only=True, data_only=True)
    ws = [w for w in wb.worksheets if w.title.strip().startswith(prefix)][0]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _size(s):
    s = re.sub(r"[\s　]", "", str(s)).replace("人以上", "人以上")
    s = s.replace("5,000人以上", "5,000人以上")
    for k in NORM:
        if s == k.replace(" ", ""): return NORM[k]
    return None


def _year(s):
    s = re.sub(r"[\s　]", "", str(s)).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    m = re.match(r"令和(\d+)年", s)
    return 2018 + int(m.group(1)) if m else None


def r8_table2():
    """第2表：1人平均賃金の改定額・改定率（令和8年・令和7年の2列ずつ）"""
    out = []
    for r in _ws("８年第２表"):
        i = next((j for j, x in enumerate(r) if x is not None), None)
        if i is None: continue
        r = r[i:]
        lab = re.sub(r"[\s　]", "", str(r[0]))
        size = "計" if lab == "計" else _size(lab)
        if size is None: continue
        v = [x for x in r[1:] if x is not None]
        if len(v) < 4: continue
        out += [{"year": 2026, "size": size, "amount_yen": num(v[0]), "rate_pct": num(v[2])},
                {"year": 2025, "size": size, "amount_yen": num(v[1]), "rate_pct": num(v[3])}]
    return pd.DataFrame(out)


def _blocks(prefix, mapper):
    """年見出し（令和８年 等）の下に規模の行が続く表を読む"""
    out = []; year = None
    for r in _ws(prefix):
        i = next((j for j, x in enumerate(r) if x is not None), None)
        if i is None: continue
        r = r[i:]
        y = _year(r[0])
        if y:
            year = y; size = "計"
        else:
            size = _size(r[0])
        if year is None or size is None: continue
        rec = mapper(r)
        if rec is None: continue
        rec.update({"year": year, "size": size}); out.append(rec)
    return pd.DataFrame(out)


def r8_table1():
    """第1表：実施状況。列 = 全企業, 実施・予定 小計, 引き上げた, 引き下げた, 変わらなかった, ..."""
    def m(r):
        v = [x for x in r[1:] if x is not None]
        if len(v) < 5 or v[0] != 100: return None
        return {"implemented": num(v[1]), "raised": num(v[2]), "cut": num(v[3]), "unchanged": num(v[4])}
    return _blocks("８年第１表", m)


T7 = ["業績", "世間相場", "雇用の維持", "労働力の確保・定着", "消費者物価", "労使関係", "親会社等", "前年度の実績", "最低賃金"]


def r8_table7():
    """第7表：最も重視した要素（単数回答）。規模の行は2列目に規模名が重ねて入っている"""
    def m(r):
        v = [x for x in r[1:] if x is not None and not (isinstance(x, str) and re.search(r"人", x))]
        # v = [〔額決定企業の割合〕, 100, 業績, 世間相場, ...]
        if len(v) < 11 or v[1] != 100: return None
        return {k: num(x) for k, x in zip(T7, v[2:11])}
    d = _blocks("８年第７表", m)
    return d


if __name__ == "__main__":
    print(r8_table2()); print(r8_table1()); print(r8_table7())
