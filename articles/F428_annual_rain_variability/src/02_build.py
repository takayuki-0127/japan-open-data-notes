"""02 整形：地点ごとの年降水量（年ごとの値の「降水量 合計」）と、全国の年降水量偏差（51地点平均）。
「)」（準正常値）は使い、「]」（資料不足値）・「×」・「///」・空欄は欠測。
出力：data/station_annual.csv, data/national.csv
"""
import gzip, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"


def num(s):
    s = s.strip()
    if s == "--":
        return 0.0
    if s.endswith(")"):
        s = s[:-1].strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def main():
    out = []
    for f in sorted((RAW / "annual").glob("47*.html.gz")):
        b = f.name[:5]
        t = gzip.decompress(f.read_bytes()).decode("utf-8", "replace")
        m = re.search(r"([^>\s　]+)（([^）]+)）\s*年ごとの値", re.sub(r"<[^>]+>", " ", t))
        name, pref = (m.group(1), m.group(2)) if m else ("", "")
        for r in re.split(r"<tr[^>]*>", t):
            c = [re.sub(r"<[^>]+>", "", x).strip() for x in re.split(r"<td[^>]*>", r.split("</table>")[0])[1:]]
            if len(c) != 28 or not c[0].isdigit():
                continue
            out.append((b, name, pref, int(c[0]), num(c[3])))
    d = pd.DataFrame(out, columns=["st", "name", "pref", "year", "precip"]).sort_values(["st", "year"])
    d.to_csv(D / "station_annual.csv", index=False)
    h = (RAW / "an_jpn_r_list.html").read_text(encoding="utf-8", errors="replace")
    tx = re.sub(r"<[^>]+>", " ", h)
    rows = [(int(y), float(v)) for y, v in re.findall(r"(\d{4})年\s+([+-]?\d+\.\d)", tx)]
    nat = pd.DataFrame(rows, columns=["year", "anom_mm"]).drop_duplicates("year").sort_values("year")
    assert nat.year.min() == 1898 and nat.year.max() == 2025 and len(nat) == 128
    nat.to_csv(D / "national.csv", index=False)
    print(len(d), d.st.nunique(), len(nat))


if __name__ == "__main__":
    main()
