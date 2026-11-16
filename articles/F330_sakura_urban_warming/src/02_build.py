"""02 整形：さくらの開花日（ソメイヨシノ）と、地点の1〜3月の月平均気温、全国の偏差を1つの表に"""
import pathlib, re
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def sakura():
    L = (RAW / "004.csv").read_bytes().decode("cp932").split("\n")
    hdr = L[1].rstrip("\r").split(",")
    rows = []
    for l in L[2:]:
        c = l.rstrip("\r").split(",")
        if not c[0].strip().isdigit():
            continue
        st, name = c[0].strip(), c[1].replace("　", "").strip()
        for j, h in enumerate(hdr):
            if h.isdigit() and 1953 <= int(h) <= 2026 and j + 1 < len(c):
                v, rm = c[j].strip(), c[j + 1].strip()
                if v.isdigit() and int(v) > 0:
                    rows.append((st, name, int(h), int(v), rm))
    d = pd.DataFrame(rows, columns=["st", "name", "year", "mmdd", "rm"])
    d = d[~d.rm.isin(["6", "7"])].copy()            # ソメイヨシノ以外を除く
    m, dd = d.mmdd // 100, d.mmdd % 100
    d = d[(m >= 2) & (m <= 5)].copy()               # 2〜5月の開花だけ（ソメイヨシノの範囲）
    dt = pd.to_datetime(dict(year=d.year, month=d.mmdd // 100, day=d.mmdd % 100))
    d["doy"] = dt.dt.dayofyear - (dt.dt.is_leap_year & (dt.dt.month >= 3)).astype(int)  # うるう年をそろえる
    return d[["st", "name", "year", "doy", "rm"]]


def num(s):
    s = s.strip()
    if s.endswith(")"):                              # 準正常値は使う
        s = s[:-1].strip()
    try:
        return float(s)
    except ValueError:
        return np.nan                                # ]（資料不足）・×・/// などは欠測


def temps():
    out = []
    for f in sorted((RAW / "temp").glob("47*.html")):
        t = f.read_bytes().decode("utf-8", "replace")
        for r in re.split(r'<tr class="mtx"[^>]*>', t)[1:]:
            r = r.split("</table>")[0]
            cells = [re.sub(r"<[^>]+>", "", x) for x in re.split(r"<td[^>]*>", r)[1:]]
            if len(cells) < 13 or not cells[0].strip().isdigit():
                continue
            y = int(cells[0].strip())
            out.append((f.stem[2:], y, num(cells[1]), num(cells[2]), num(cells[3])))
    return pd.DataFrame(out, columns=["st", "year", "t1", "t2", "t3"])


def national():
    t = pd.read_csv(RAW / "mon_jpn.csv", encoding="cp932")
    t.columns = ["year"] + [f"n{i}" for i in range(1, 13)]
    t = t.apply(pd.to_numeric, errors="coerce")
    return t[["year", "n1", "n2", "n3"]]


def main():
    s, t, n = sakura(), temps(), national()
    d = s.merge(t, on=["st", "year"], how="left").merge(n, on="year", how="left")
    d = d.sort_values(["st", "year"]).reset_index(drop=True)
    d.round(3).to_csv(ROOT / "data" / "panel.csv", index=False)
    print(len(d), d.st.nunique())


if __name__ == "__main__":
    main()
