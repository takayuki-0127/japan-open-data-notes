"""01 取得：気象庁「過去の気象データ検索」年ごとの値（気温・日数のページ view=a2）を30地点分

2026-11-04 にブラウザの中で取得したものを data/raw/jma_annual_a2.csv に置いています
（このコンテナからは政府サイトに届かないため）。ふつうのネット環境なら、このスクリプトで同じものが取れます。

  https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no=..&block_no=..&year=&month=&day=&view=a2

取る列：年平均気温、日最高気温の年平均、日最高気温の年最高（値と月日）、
日最高気温が25℃以上・30℃以上（真夏日）・35℃以上（猛暑日）の日数。
値の後ろの「 ]」は資料不足値、「×」は欠測です（02_整形.py で除きます）。
"""
import io, time
import requests
import pandas as pd
from common import RAW, STATIONS

def main():
    S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (research script)"
    out = []
    for name, prec, block, group in STATIONS:
        html = S.get("https://www.data.jma.go.jp/stats/etrn/view/annually_s.php",
                     params=dict(prec_no=prec, block_no=block, year="", month="", day="", view="a2"), timeout=60).text
        t = pd.read_html(io.StringIO(html), attrs={"id": "tablefix1"})[0]
        t = t[t.iloc[:, 0].astype(str).str.fullmatch(r"\d{4}")]
        for r in t.itertuples(index=False):
            out.append([name, group, r[0], r[1], r[2], r[3], r[4], r[17], r[18], r[19]])
        time.sleep(1.5)
    pd.DataFrame(out, columns=["station", "group", "year", "tmean", "tmax_mean", "tmax_abs", "tmax_date", "d25", "d30", "d35"]) \
      .to_csv(RAW / "jma_annual_a2.csv", index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    main()
