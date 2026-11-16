"""02 整形：全国・都道府県の一般世帯数・一般世帯人員（1960・1970〜2025年）を縦長の CSV にする（オフライン）。
出力：data/households.csv（year, pref, name, total_h, total_p, gen_h, gen_p）。2025年は一般世帯だけ（総数は空）"""
import pathlib, re
import pandas as pd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def timeseries():
    ws = openpyxl.load_workbook(str(RAW / "census_ts_households_t1_1960_2020_000001086170.xlsx"), read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hdr = rows[5]
    starts = [(j, int(str(x)[:4])) for j, x in enumerate(hdr) if x and re.fullmatch(r"\d{4}年", str(x))]
    out = []
    for r in rows[9:]:
        a = str(r[0]) if r[0] else ""
        m = re.match(r"^(\d{5})_(.+)$", a)
        if not m or "人口集中" in a or not m.group(1).endswith("000"):
            continue
        code = int(m.group(1)[:2])
        for j, y in starts:
            out.append((y, code, m.group(2), num(r[j]), num(r[j + 1]), num(r[j + 2]), num(r[j + 3])))
    return pd.DataFrame(out, columns=["year", "pref", "name", "total_h", "total_p", "gen_h", "gen_p"])

def census2025():
    vals = {}
    for key, name in [("gen_h", "census_2025_t12-1_households_000040506465.xlsx"), ("gen_p", "census_2025_t12-2_members_000040506466.xlsx")]:
        ws = openpyxl.load_workbook(str(RAW / name), read_only=True).worksheets[0]
        for r in ws.iter_rows(min_row=11, values_only=True):
            if r[0] != "a" or r[2] != "0_総数" or r[3] != "0_総数" or r[4] != "00_総数":
                continue
            m = re.match(r"^(\d{5})_(.+)$", str(r[1]))
            if m and m.group(1).endswith("000"):
                vals.setdefault(int(m.group(1)[:2]), {"name": m.group(2)})[key] = float(r[5])
    return pd.DataFrame([(2025, k, v["name"], None, None, v["gen_h"], v["gen_p"]) for k, v in sorted(vals.items())],
                        columns=["year", "pref", "name", "total_h", "total_p", "gen_h", "gen_p"])

def main():
    T = timeseries(); C = census2025()
    D = pd.concat([T, C], ignore_index=True).sort_values(["year", "pref"]).reset_index(drop=True)
    assert not D.duplicated(["year", "pref"]).any()
    print(D.groupby("year").pref.nunique().to_dict())
    nat = D[D.pref == 0].set_index("year")[["gen_h", "gen_p"]]
    s = D[D.pref > 0].groupby("year")[["gen_h", "gen_p"]].sum()
    print("全国と47都道府県の合計の差の最大", float((nat - s.reindex(nat.index)).abs().max().max()))
    D.to_csv(ROOT / "data" / "households.csv", index=False)

if __name__ == "__main__":
    main()
