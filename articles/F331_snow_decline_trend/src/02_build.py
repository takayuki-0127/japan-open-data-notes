"""02 整形：地点ごとの寒候年の降雪合計・最深積雪と、全国の冬（12〜2月）の気温偏差"""
import gzip, pathlib, re
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(s):
    s = s.strip()
    if s == "--":                            # 現象なし（雪が降らなかった・積もらなかった）は0
        return 0.0
    if s.endswith(")"):                      # 準正常値は使う
        s = s[:-1].strip()
    try:
        return float(s)
    except ValueError:
        return np.nan                        # ]（資料不足）・×・/// ・空欄は欠測


def main():
    pr = pd.read_csv(RAW / "station_prec.csv", dtype=str).set_index("block_no").prec_no
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
            out.append((b, name, pref, int(pr[b]), int(c[0]), num(c[21]), num(c[23])))
    d = pd.DataFrame(out, columns=["st", "name", "pref", "prec_no", "year", "snowfall", "maxdepth"])
    # 全国の冬の気温偏差：寒候年 Y の冬＝前年12月とその年1・2月
    t = pd.read_csv(RAW / "mon_jpn.csv", encoding="cp932")
    t.columns = ["year"] + [f"m{i}" for i in range(1, 13)]
    t = t.apply(pd.to_numeric, errors="coerce").set_index("year")
    w = pd.DataFrame({"year": t.index.values, "djf": ((t.m12.shift(1) + t.m1 + t.m2) / 3).values}).dropna()
    d = d.merge(w, on="year", how="left").sort_values(["st", "year"])
    d.to_csv(ROOT / "data" / "panel.csv", index=False)
    print(len(d), d.st.nunique(), d.maxdepth.notna().sum())


if __name__ == "__main__":
    main()
