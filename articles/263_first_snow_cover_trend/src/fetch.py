"""取得：気象庁「過去の気象データ検索」日ごとの値（daily_s1.php, view=p1）を14地点・1931〜2025年の全月分
2026-11-12 にブラウザの中で取得したものを data/jma_daily_14st_1931_2025.tsv.gz に置いています
（このコンテナからは政府サイトに届かないため）。ふつうのネット環境なら、このスクリプトで同じ形のものが取れます。
列：地点, 年, 月, 日, 降水量合計, 平均気温, 最高気温, 最低気温, 降雪の深さ合計, 最深積雪, 天気概況（昼）, 天気概況（夜）
値の印（')' 準正常値、']' 資料不足値、'×' 欠測、'--' 現象なし など）はそのまま残しています。"""
import gzip, io, time, requests, pandas as pd
from common import DATA, STATIONS
URL = "https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"
def main():
    S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (research script)"; out = []
    for name, prec, block in STATIONS:
        for y in range(1931, 2026):
            for m in range(1, 13):
                html = S.get(URL, params=dict(prec_no=prec, block_no=block, year=y, month=m, day="", view="p1"), timeout=60).text
                t = pd.read_html(io.StringIO(html), attrs={"id": "tablefix1"})[0].astype(str)
                for r in t.itertuples(index=False):
                    if str(r[0]).isdigit():
                        out.append("\t".join([name, str(y), str(m), r[0], r[3], r[6], r[7], r[8], r[17], r[18], r[19], r[20]]))
                time.sleep(0.5)
    with gzip.open(DATA / "jma_daily_14st_1931_2025.tsv.gz", "wt", encoding="utf-8") as f: f.write("\n".join(out) + "\n")
if __name__ == "__main__":
    main()
