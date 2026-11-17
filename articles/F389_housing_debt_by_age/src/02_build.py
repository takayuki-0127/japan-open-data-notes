"""data/raw の Excel（第8-5表・第8-24表、2008〜2025年）を、年×世帯区分×表×年齢×項目の縦長の表にする。"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AGES = ["平均", "〜29歳", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳〜"]
ITEMS = {"世帯数分布(抽出率調整)": "dist", "集計世帯数": "n_hh", "持家率": "own_rate", "年間収入": "income",
         "貯蓄": "savings", "負債": "debt", "住宅・土地のための負債": "housing_debt", "調整集計世帯数": "adj_n"}


def norm(s):
    s = re.sub(r"[\s　]", "", str(s))
    return re.sub(r"\((人|％|%|歳)\)$", "", s)


def parse_sheet(d):
    d = d.astype(object)
    # 見出しの行：「平均」と「29」を含むセルがある行
    hr = None
    for i in range(min(25, len(d))):
        cells = [norm(v) for v in d.iloc[i].tolist()]
        if any(c in ("平均",) for c in cells) and any("29" in c for c in cells):
            hr = i
            break
    cells = [norm(v) for v in d.iloc[hr].tolist()]
    c_avg = cells.index("平均")
    cols = [c_avg + k for k in range(7)]
    assert "29" in cells[cols[1]] and "70" in cells[cols[6]], cells
    out = {}
    for i in range(hr + 1, len(d)):
        row = d.iloc[i].tolist()
        labs = [norm(v) for v in row[:c_avg] if isinstance(v, str)]
        key = None
        for lab in labs:
            if lab in ITEMS:
                key = ITEMS[lab]
        if key is None or key in out:
            continue
        out[key] = [pd.to_numeric(str(row[c]).replace(",", ""), errors="coerce") for c in cols]
    return out


def main():
    recs = []
    for f in sorted(RAW.glob("sav_*_t8_*.xls*")):
        m = re.match(r"sav_(\d{4})_t8_(\d+)\.", f.name)
        year, tab = int(m.group(1)), m.group(2)
        group = "all" if tab == "5" else "holders"
        sheets = pd.read_excel(f, header=None, sheet_name=None)
        for sname, d in sheets.items():
            hh = "workers" if "勤労" in sname else "two_plus"
            parsed = parse_sheet(d)
            for key in ITEMS.values():
                assert key in parsed, (f.name, sname, key)
                for age, v in zip(AGES, parsed[key]):
                    recs.append((year, hh, group, age, key, v))
    df = pd.DataFrame(recs, columns=["year", "household", "group", "age", "item", "value"])
    df = df.sort_values(["household", "group", "item", "age", "year"], kind="mergesort").reset_index(drop=True)
    df.to_csv(ROOT / "data" / "panel_long.csv", index=False)
    print(len(df), "rows")


if __name__ == "__main__":
    main()
