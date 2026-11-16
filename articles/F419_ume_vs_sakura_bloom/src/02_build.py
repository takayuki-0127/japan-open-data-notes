"""02 整形：うめ・さくらの開花（累年値 CSV）を、地点×年×種目の長い表にする。
- 値は月日（例 214 = 2月14日）。冬・春の種目を前年12月に観測した値（例 1215）は翌年の欄に入るので、
  1月1日からの日数を負にする（12月15日 → −17）。
- rm：8・9 は正規の種目（うめ・ソメイヨシノ）、6・7 は代わりの種目。0 は観測なし。
- 地点の緯度は、気象庁のアメダス地点表（官署）から地点名で引く。
出力：data/bloom_long.csv, data/stations.csv
"""
import datetime, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
FILES = {"ume": "001_ume_kaika.csv", "sakura": "004_sakura_kaika.csv"}


def doy(year, mmdd):
    m, d = divmod(mmdd, 100)
    if m == 12:   # 前年12月
        return (datetime.date(year - 1, 12, d) - datetime.date(year, 1, 1)).days + 1
    return (datetime.date(year, m, d) - datetime.date(year, 1, 1)).days + 1


def parse(path, kind):
    lines = path.read_bytes().decode("cp932").splitlines()
    hdr = lines[1].split(",")
    years = [(i, int(h)) for i, h in enumerate(hdr) if h.isdigit() and len(h) == 4]
    rows = []
    for l in lines[2:]:
        c = l.split(",")
        if not c[0].strip().isdigit():
            continue
        st = int(c[0]); name = c[1].strip().replace("　", "")
        for i, y in years:
            v, rm = c[i].strip(), c[i + 1].strip()
            if v in ("", "0") or rm in ("", "0"):
                continue
            rows.append((kind, st, name, y, int(v), rm, doy(y, int(v))))
    return rows


def main():
    rows = []
    for k, f in FILES.items():
        rows += parse(RAW / f, k)
    d = pd.DataFrame(rows, columns=["kind", "st", "name", "year", "mmdd", "rm", "doy"])
    d["regular"] = d.rm.isin(["8", "9"]).astype(int)
    d = d.sort_values(["kind", "st", "year"]).reset_index(drop=True)
    d.to_csv(D / "bloom_long.csv", index=False)

    m = pd.read_csv(RAW / "ame_master_20260324.csv", encoding="cp932")
    m = m[(m["種類"] == "官") & ~m["所在地"].astype(str).str.contains("航空")]
    m = m.assign(lat=m["緯度(度)"] + m["緯度(分)"] / 60, lon=m["経度(度)"] + m["経度(分)"] / 60)
    m = m.drop_duplicates("観測所名", keep="first").set_index("観測所名")
    alias = {"南大東島": "南大東"}
    st = d[["st", "name"]].drop_duplicates().sort_values("st")
    st["lat"] = [round(float(m.loc[alias.get(n, n), "lat"]), 3) for n in st.name]
    st["pref"] = [m.loc[alias.get(n, n), "都府県振興局"] for n in st.name]
    st.to_csv(D / "stations.csv", index=False)
    print(len(d), len(st))


if __name__ == "__main__":
    main()
