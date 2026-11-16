"""02 整形：地点ごとの年間日照時間と全天日射量（日合計の年平均）"""
import gzip, pathlib, re
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(s):
    s = s.strip()
    if s.endswith(")"):                      # 準正常値は使う
        s = s[:-1].strip()
    try:
        return float(s)
    except ValueError:
        return np.nan                        # ]（資料不足）・×・/// ・空欄は欠測


def main():
    out = []
    for f in sorted((RAW / "annual").glob("47*.html.gz")):
        t = gzip.decompress(f.read_bytes()).decode("utf-8", "replace")
        m = re.search(r"([^>\s　]+)（([^）]+)）\s*年ごとの値", re.sub(r"<[^>]+>", " ", t))
        name = m.group(1) if m else ""
        for r in re.split(r"<tr[^>]*>", t):
            c = [re.sub(r"<[^>]+>", "", x).strip() for x in re.split(r"<td[^>]*>", r.split("</table>")[0])[1:]]
            if len(c) != 28 or not c[0].isdigit():
                continue
            out.append((f.name[:5], name, int(c[0]), num(c[19]), num(c[20])))
    d = pd.DataFrame(out, columns=["st", "name", "year", "sun", "rad"])
    d.to_csv(ROOT / "data" / "panel.csv", index=False)
    x = d[(d.year >= 1961) & (d.year <= 2025)]
    print(len(d), (x.groupby("st").sun.count() >= 60).sum(), (x.groupby("st").rad.count() >= 50).sum())


if __name__ == "__main__":
    main()
