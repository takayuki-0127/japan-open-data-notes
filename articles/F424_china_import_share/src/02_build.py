"""02 整形：財務省「輸出入額の推移（地域（国）別・主要商品別）」年別 輸入の CSV（cp932）を、年×相手×品目の金額の表にする。
列は「概況品コード」の行で品目を決め、その「金額」列（千円）を使う。
出力：data/imports_long.csv（year, partner, code, item, value_thousand_yen）、data/items.csv
"""
import csv, io, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
FILES = {"world": "d61ca.csv", "china": "d62ca004.csv", "asean": "d62ca006.csv", "korea": "d62ca005.csv", "usa": "d62ca001.csv",
         "eu": "d62ca002.csv", "asia": "d62ca003.csv", "middle_east": "d62ca007.csv", "russia": "d62ca008.csv"}


def parse(path):
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("cp932"))))
    press, name, code = rows[2], rows[3], rows[4]
    # 品目の列：総額は列1が金額。ほかの品目は、コードのある列が数量、その右の列が金額（千円）。
    cols = [(1, code[1].strip(), "総額", "総額")]
    for j in range(2, len(code)):
        if code[j].strip():
            label = press[j].strip() or name[j].strip()
            cols.append((j + 1, code[j].strip().replace("''", "'"), label, name[j].strip()))
    out = []
    for r in rows[7:]:
        if not r or not r[0].strip().isdigit():
            continue
        y = int(r[0])
        for j, c, lab, nm in cols:
            v = r[j].strip() if j < len(r) else ""
            out.append((y, c, lab, nm, None if v in ("", "-") else int(v)))
    return out


def main():
    allrows, items = [], None
    for p, f in FILES.items():
        rows = parse(RAW / f)
        allrows += [(y, p, c, v) for y, c, lab, nm, v in rows]
        assert rows and True
        it = pd.DataFrame([(c, lab, nm) for _, c, lab, nm, _ in rows], columns=["code", "press_name", "name"]).drop_duplicates("code")
        items = it if items is None else items
    d = pd.DataFrame(allrows, columns=["year", "partner", "code", "value_thousand_yen"])
    d.sort_values(["partner", "code", "year"]).to_csv(D / "imports_long.csv", index=False)
    items.to_csv(D / "items.csv", index=False)
    print(d.groupby("partner").year.agg(["min", "max", "count"]))
    print(items.to_string())


if __name__ == "__main__":
    main()
