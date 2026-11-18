"""元データ（xls）から分析用の CSV を作る（オフライン）。
- 表の向きは年で違う（項目が列の年と、行の年がある）。どちらも見出しの文字で項目・区分を選ぶ
- 選んだ値は「農業所得＋農業生産関連事業所得＋農外所得＋年金等の収入＝総所得」（四捨五入の差±3千円以内）で確かめる
"""
import json, pathlib, re
import numpy as np
import pandas as pd
import xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "maff"; D = ROOT / "data"; R = ROOT / "results"
R.mkdir(exist_ok=True)
ITEMS = ["n", "ag", "rel", "off", "pen", "tot"]  # 集計数、農業所得、農業生産関連事業所得、農外所得、年金等の収入、総所得
KIBO = ["平均", "0.5ha未満", "0.5～1.0", "1.0～1.5", "1.5～2.0", "2.0～3.0", "3.0～5.0", "5.0～7.0", "7.0～10.0", "10.0ha以上"]
TYPES = {"主業": "主業", "準主業": "準主業", "副業的": "副業的"}


def cl(s):
    if isinstance(s, float):
        return str(int(s)) if s.is_integer() else str(s)
    return re.sub(r"[\s　（）()①-⑳]", "", str(s))


def num(v):
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace(",", "").strip()
    if s in ("-", "－"): return 0.0  # 「-」は事実がないもの
    try: return float(s)
    except ValueError: return np.nan


def item_of_label(t):
    """項目名（行の見出し、または列の見出しを縦につないだ文字）→ 項目の記号"""
    if "集計" in t: return "n"
    if "総所得" in t and "当たり" not in t and "一人" not in t: return "tot"
    if "年金" in t: return "pen"
    if "可処分" in t or "依存度" in t or "当たり" in t or "所得率" in t: return None
    if "及び" in t: return None  # 「農業及び農業生産関連事業所得」は合計なので使わない
    if t.endswith("所得"):
        if "農外" in t: return "off"
        if "関連" in t: return "rel"
        if t.startswith("農"): return "ag"
    return None


def open_sheet(p):
    return xlrd.open_workbook(p, logfile=open("/dev/null", "w")).sheet_by_index(0)


def items_as_rows(sh):
    """項目が行にある表：{項目: 行番号}"""
    out = {}
    for i in range(sh.nrows):
        t = "".join(c for c in (cl(x) for x in sh.row_values(i)[:5]) if not re.fullmatch(r"[\d.]+", c))
        k = item_of_label(t)
        if k and k not in out: out[k] = i
    return out


def items_as_cols(sh, h0, h1):
    """項目が列にある表：見出しの行 h0〜h1 を縦につないで {項目: 列番号}"""
    out = {}
    for j in range(sh.ncols):
        parts = [cl(sh.cell_value(i, j)) for i in range(h0, h1)]
        t = "".join(c for c in parts if c and not re.fullmatch(r"[\d.,]*(千円|人|ａ|時間|歳|経営体|戸|％|円|回|〃)?|単位.*", c)
                    and not re.fullmatch(r"[\d⑤-⑳①-④/×+＋.]+", c))
        k = item_of_label(t)
        if k and k not in out: out[k] = j
    return out


def check(rec, src):
    s = rec["ag"] + rec["rel"] + rec["off"] + rec["pen"]
    rec["sum_minus_tot"] = s - rec["tot"]
    assert abs(rec["sum_minus_tot"]) <= 3, (src, rec)
    return rec


def parse_shufuku(y):
    sh = open_sheet(RAW / f"shufuku_{y}_1.xls")
    rows = [[cl(x) for x in sh.row_values(i)] for i in range(sh.nrows)]
    ir = items_as_rows(sh)
    out = []
    if "tot" in ir and ir["tot"] > 8:  # 項目が行（2018年など）
        hreg = next(i for i, r in enumerate(rows) if "全国" in r)
        reg, regs = "", []
        for j in range(sh.ncols):
            if rows[hreg][j]: reg = rows[hreg][j]
            regs.append(reg)
        for j in range(sh.ncols):
            typ = rows[hreg + 1][j]; sub = rows[hreg + 2][j] if hreg + 2 < len(rows) else ""
            if regs[j] == "全国" and typ and not sub.startswith("うち"):
                t = next((v for k, v in TYPES.items() if typ.startswith(k)), None)
                if t:
                    rec = dict(year=y, type=t, **{k: num(sh.cell_value(ir[k], j)) for k in ITEMS})
                    out.append(check(rec, f"shufuku {y}"))
    else:  # 項目が列：全国の見出しのあとの行
        i_kubun = next(i for i, r in enumerate(rows) if any(c.startswith("区分") for c in r[:4]))
        i_zen = next(i for i, r in enumerate(rows) if "全国" in r[:4])
        ic = items_as_cols(sh, i_kubun, i_zen)
        assert all(k in ic for k in ITEMS), (y, ic)
        for i in range(i_zen + 1, i_zen + 8):
            lab = "".join(rows[i][:4])
            t = next((v for k, v in TYPES.items() if lab.startswith(k)), None)
            if t:
                rec = dict(year=y, type=t, **{k: num(sh.cell_value(i, ic[k])) for k in ITEMS})
                out.append(check(rec, f"shufuku {y}"))
    assert [r["type"] for r in out] == ["主業", "準主業", "副業的"], (y, out)
    return out


def parse_kibo(y):
    sh = open_sheet(RAW / f"kibo_tofuken_{y}_1.xls")
    rows = [[cl(x) for x in sh.row_values(i)] for i in range(sh.nrows)]
    ir = items_as_rows(sh)
    out = []
    if "tot" in ir and all(k in ir for k in ITEMS if k != "n"):  # 項目が行（集計数の行がない年がある）
        hk = next(i for i, r in enumerate(rows) if "平均" in r and "0.5ha未満" in r)
        for j in range(sh.ncols):
            if rows[hk][j] in KIBO:
                rec = dict(year=y, cls=rows[hk][j], **{k: (num(sh.cell_value(ir[k], j)) if k in ir else np.nan) for k in ITEMS})
                out.append(check(rec, f"kibo {y}"))
    else:  # 項目が列。区分の見出しのブロックごとに探す
        kub = [i for i, r in enumerate(rows) if any(c.startswith("区分") for c in r[:4])]
        for b, i0 in enumerate(kub):
            i_first = next(i for i in range(i0 + 1, len(rows)) if next((c for c in rows[i][:4] if c), "") == "平均")
            ic = items_as_cols(sh, i0, i_first)
            if not all(k in ic for k in ITEMS):
                continue
            for i in range(i_first, min(i_first + 14, len(rows))):
                lab = next((c for c in rows[i][:4] if c), "")
                if lab in KIBO:
                    rec = dict(year=y, cls=lab, **{k: num(sh.cell_value(i, ic[k])) for k in ITEMS})
                    out.append(check(rec, f"kibo {y}"))
            break
    got = [r["cls"] for r in out]
    assert got == KIBO, (y, got)
    return out


def parse_long():
    sh = open_sheet(RAW / "long_1_1.xls")
    rows = [[cl(x) for x in sh.row_values(i)] for i in range(sh.nrows)]
    hy = next(i for i, r in enumerate(rows) if any(c.startswith("平成16年") for c in r))
    cols = [j for j in range(sh.ncols) if rows[hy][j]][2:]  # 区分・単位のあと
    years = list(range(2004, 2004 + len(cols)))
    ir = items_as_rows(sh)
    out = []
    for y, j in zip(years, cols):
        rec = dict(year=y, **{k: num(sh.cell_value(ir[k], j)) for k in ITEMS})
        out.append(check(rec, f"long {y}"))
    assert years[-1] == 2018
    # 2007年の＜ ＞（税制改正前の減価償却で計算した値）。項目の行のすぐ下の行に、2007年の列だけ値がある
    j07 = cols[years.index(2007)]
    alt = {}
    for k in ITEMS:
        r = ir[k] + 1
        vals = [x for x in sh.row_values(r) if x != ""]
        alt[k] = num(sh.cell_value(r, j07)) if len(vals) == 1 and sh.cell_value(r, j07) != "" else np.nan
    for rec in out:
        for k in ["ag", "rel", "off", "pen", "tot"]:
            rec[k + "_alt2007"] = alt[k] if rec["year"] == 2007 and not np.isnan(alt[k]) else rec[k]
    return out


def main():
    L = pd.DataFrame(parse_long())
    S = pd.DataFrame(sum([parse_shufuku(y) for y in range(2004, 2019)], []))
    K = pd.DataFrame(sum([parse_kibo(y) for y in range(2004, 2019)], []))
    for d in (L, S, K):
        d["n"] = d["n"].astype("Int64")
    L.to_csv(D / "national_long.csv", index=False)
    S.to_csv(D / "by_type.csv", index=False)
    K.to_csv(D / "by_scale_tofuken.csv", index=False)
    ck = pd.DataFrame([dict(table=t, rows=len(d), max_abs_sum_minus_tot=float(d.sum_minus_tot.abs().max()))
                       for t, d in [("national_long", L), ("by_type", S), ("by_scale_tofuken", K)]])
    ck.to_csv(R / "build_checks.csv", index=False)
    print(ck.to_string()); print(L.to_string()); print(S[S.year.isin([2004, 2018])].to_string()); print(K[K.year.isin([2004, 2018])].to_string())


if __name__ == "__main__":
    main()
