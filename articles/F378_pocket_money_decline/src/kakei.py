"""kakei.py : 家計調査（家計収支編）の詳細結果表（xls / xlsx）を、行の名前と列の番号で読む共通の関数。
表の形は年で少し違う（2019年までは行の名前が段下げで複数の列に分かれ、2020年からは「用途分類」の1列）。
"""
import re

import pandas as pd

UNIT = re.compile(r"\((人|円|％|%|歳|畳|万円)\)$")
CODE = re.compile(r"^[0-9.]+$")


def norm(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"[\s　]", "", str(s)).replace("（", "(").replace("）", ")")


def to_num(x):
    if isinstance(x, (int, float)) and not pd.isna(x):
        return float(x)
    s = norm(x).replace(",", "")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def read_sheet(df):
    """1枚の表を読む。戻り値：(行の名前→{列番号: 値} の dict（同じ名前は最初の行）, {列番号: 列の見出し})"""
    r0 = df.iloc[0]
    cols = {}
    for j in range(df.shape[1]):
        t = norm(r0.iloc[j])
        if t.isdigit():
            cols[int(t)] = j
    first_data_col = min(cols.values())
    fr = next(i for i in range(len(df)) if norm(df.iloc[i, 0]).startswith("3"))
    new = any(norm(df.iloc[i, 11]) == "用途分類" for i in range(fr) if df.shape[1] > 11)
    heads = {}
    for k, j in cols.items():
        heads[k] = "".join(norm(df.iloc[i, j]) for i in range(2, fr) if norm(df.iloc[i, j]) not in ("", "nan"))
    rows = {}
    for i in range(fr, len(df)):
        if new:
            lab = norm(df.iloc[i, 11])
        else:
            parts = [norm(df.iloc[i, j]) for j in range(6, first_data_col)]
            parts = [p for p in parts if p and p != "nan" and not CODE.match(p)]
            lab = parts[-1] if parts else ""
        lab = UNIT.sub("", lab)
        if not lab or lab in rows:
            continue
        rows[lab] = {k: to_num(df.iloc[i, j]) for k, j in cols.items()}
    return rows, heads


def read_book(path, sheet_pattern):
    """sheet_pattern（正規表現）に合う最初のシートを読む。"""
    x = pd.read_excel(path, header=None, sheet_name=None)
    for name, df in x.items():
        if re.search(sheet_pattern, name):
            return read_sheet(df)
    raise KeyError(f"{path}: {sheet_pattern}")


# 年で名前が変わった行（2006年までの名前 → 今の名前）
ALIASES = {
    "実収入以外の受取(繰入金を除く)": ["実収入以外の収入"],
    "実支出以外の支払(繰越金を除く)": ["実支出以外の支出"],
    "保険金": ["保険取金"],
    "保険料": ["保険掛金"],
}


def get(rows, item, k):
    """行 item の列 k の値。今の名前がなければ昔の名前で探す。"""
    if item in rows:
        return rows[item][k]
    for alt in ALIASES.get(item, []):
        if alt in rows:
            return rows[alt][k]
    raise KeyError(item)
