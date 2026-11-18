"""Excel（xlsx・xls）を読み、結合セルを広げた見出しの文字から列の名前を作る共通の関数。"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def _grid(path):
    path = pathlib.Path(path)
    if path.suffix == ".xlsx":
        import openpyxl
        ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
        g = [[ws.cell(r, c).value for c in range(1, ws.max_column + 1)] for r in range(1, ws.max_row + 1)]
        merges = [(m.min_row - 1, m.max_row, m.min_col - 1, m.max_col) for m in ws.merged_cells.ranges]
    else:
        import xlrd
        sh = xlrd.open_workbook(path, formatting_info=True).sheet_by_index(0)
        g = [[(v if v != "" else None) for v in sh.row_values(r)] for r in range(sh.nrows)]
        merges = list(sh.merged_cells)  # (rlo, rhi, clo, chi)、hi は含まない
    for rlo, rhi, clo, chi in merges:
        v = g[rlo][clo]
        for r in range(rlo, rhi):
            for c in range(clo, chi):
                g[r][c] = v
    return g


def norm(s):
    s = re.sub(r"\s+", "", str(s)).replace("　", "")
    return s


def read_table(name, unit_pat=r"^(1000ｔ|ｔ|t|100万円)$"):
    """年次の行から単位の行までを見出しとして、列の名前（/ 区切り）を作る。戻り値：DataFrame（year 列つき）と名前の一覧"""
    g = _grid(RAW / name)
    top = next(i for i, row in enumerate(g) if row and row[0] is not None and norm(row[0]) == "年次")
    ncol = max(len(r) for r in g)
    # 単位の行（あれば）。なければ最初のデータ行の前まで
    first = next(i for i, row in enumerate(g) if i > top and re.search(r"\((\d{4})\)", str(row[0] or "")))
    unit = next((i for i in range(top + 1, first) if sum(bool(re.match(unit_pat, norm(x or ""))) for x in g[i][1:]) >= 2), first)
    names = []
    for c in range(1, ncol):
        parts = []
        for r in range(top, unit):
            v = g[r][c] if c < len(g[r]) else None
            if v is None or norm(v) == "": continue
            v = norm(v)
            if re.match(unit_pat, v) or v.startswith("単位"): continue
            if not parts or parts[-1] != v: parts.append(v)
        base = nm = "/".join(parts)
        k = 2
        while nm in names:  # 同じ見出しが繰り返すときは #2, #3 を付ける
            nm = f"{base}#{k}"; k += 1
        names.append(nm)
    recs = []
    for row in g[first:]:
        m = re.search(r"\((\d{4})\)", str(row[0] or ""))
        if not m: continue
        rec = {"year": int(m.group(1))}
        for n, v in zip(names, row[1:]):
            rec[n] = float(v) if isinstance(v, (int, float)) else None
        recs.append(rec)
    return pd.DataFrame(recs), names


def pick(df, names, *keys, exact=True):
    """見出しの各段がこの順で keys に一致する列を1つだけ選ぶ（exact=False なら先頭の一致）"""
    hit = [n for n in names if (n.split("/") == list(keys) if exact else n.split("/")[:len(keys)] == list(keys))]
    if len(hit) != 1: raise SystemExit(f"見出しが一意でない: {keys} -> {hit}")
    return df[hit[0]].to_numpy(float)


def share_decomp(a0, c0, a1, c1, steps=20000):
    """割合 s=ΣA/(ΣA+ΣC)（%）の変化を、すべての成分を同時にまっすぐ動かす経路で数値積分して成分ごとに分ける。
    a*: 養殖などの分子側の成分、c*: 分母だけに入る成分（numpy 配列）。戻り値：(分子側の寄与, 分母側の寄与)（ポイント）"""
    import numpy as np
    a0, c0, a1, c1 = (np.asarray(x, float) for x in (a0, c0, a1, c1))
    da, dc = a1 - a0, c1 - c0
    ca, cc = np.zeros_like(a0), np.zeros_like(c0)
    for t in (np.arange(steps) + 0.5) / steps:
        A = (a0 + t * da).sum(); C = (c0 + t * dc).sum(); T = A + C
        ca += C / T**2 * da / steps; cc += -A / T**2 * dc / steps
    return 100 * ca, 100 * cc
