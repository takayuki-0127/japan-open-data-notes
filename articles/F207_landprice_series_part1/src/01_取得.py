"""元データの取得（手作業）と抜き出し
- 地価公示 2026年（国土数値情報 L01-26）：https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-2026.html
  L01-26_GML.zip を取得して展開し、L01-26.geojson から各地点の 1996〜2026 年の価格（L01_075〜L01_105）と
  2007〜2026 年の属性移動（L01_129〜L01_148）を抜き出す（下の関数）。結果は data/ の2つの csv.gz。
- 地点の特徴量・駅の位置は F03 の data/features.csv・data/stations.csv を使う（articles/F03_land_price_ml）。
- 新しい駅の開業日は、各鉄道事業者の公表資料をもとに data/stations_new.csv に手で入力した。
使い方：python 01_取得.py L01-26.geojson data/
"""
import json, csv, sys, gzip


def extract(geo, outdir):
    d = json.load(open(geo, encoding="utf-8"))
    yrs = list(range(1996, 2027))
    with gzip.open(f"{outdir}/price_hist_1996_2026.csv.gz", "wt", newline="", encoding="utf-8") as f1, \
         gzip.open(f"{outdir}/chg_2007_2026.csv.gz", "wt", newline="", encoding="utf-8") as f2:
        w1, w2 = csv.writer(f1), csv.writer(f2)
        w1.writerow(["code", "lon", "lat", "use"] + [f"p{y}" for y in yrs])
        w2.writerow(["code", "bits"] + [f"c{y}" for y in range(2007, 2027)])
        for x in d["features"]:
            q = x["properties"]; c = x["geometry"]["coordinates"]
            code = f"{q['L01_001']}-{q['L01_002']}-{q['L01_003']}"
            w1.writerow([code, c[0], c[1], q["L01_002"]] + [q["L01_%03d" % (62 + y - 1983)] for y in yrs])
            w2.writerow([code, q["L01_061"]] + [q["L01_%03d" % (106 + y - 1984)] for y in range(2007, 2027)])


if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2])
