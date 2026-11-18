"""02 整形：同梱の年ごとの値（view=a1）の HTML から、51地点・年ごとの年降水量と階級ごとの日数を取り出す。
出力：data/annual.csv（地点・年。値と、資料不足値「]」などの印つきかどうか）
列の位置（td の順）：0 年、5 年降水量、14〜21 日降水量の階級ごとの日数（≧0.0・≧0.5・≧1.0・≧10・≧30・≧50・≧70・≧100mm）
"""
import gzip, html, pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
COLS = {"total": 5, "d1": 16, "d10": 17, "d30": 18, "d50": 19, "d70": 20, "d100": 21}
Y0, Y1 = 1901, 2025


def parse(v):
    """値と印。「]」＝資料不足値（使わない）、「)」＝準正常値（使う）、「×」＝欠測。"""
    v = v.replace("　", " ").strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*([\]\)])?", v)
    if not m:
        return None, "missing"
    flag = {"]": "insufficient", ")": "quasi"}.get(m.group(2), "ok")
    return float(m.group(1)), flag


def main():
    st = pd.read_csv(RAW / "stations.csv", dtype={"block_no": str, "prec_no": str})
    rows = []
    for _, r in st.sort_values("order").iterrows():
        s = gzip.decompress((RAW / f"jma_a1_{r.block_no}.html.gz").read_bytes()).decode("utf-8")
        assert r.station in re.sub(r"<[^>]+>", "", s)[:20000], r.station  # 地点名がページにあるか
        for tr in re.findall(r'<tr class="mtx2?"[^>]*>(.*?)</tr>', s, flags=re.S):
            c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
            if len(c) != 22 or not c[0].isdigit():
                continue
            y = int(c[0])
            if not (Y0 <= y <= Y1):
                continue
            row = {"station": r.station, "region": r.region, "order": int(r.order), "year": y}
            for k, i in COLS.items():
                val, flag = parse(c[i])
                row[k], row[f"{k}_flag"] = val, flag
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "annual.csv", index=False)
    print(len(df), df.station.nunique())
    print(df[[c for c in df.columns if c.endswith("_flag")]].apply(lambda s: s.value_counts()).fillna(0).astype(int))


if __name__ == "__main__":
    main()
