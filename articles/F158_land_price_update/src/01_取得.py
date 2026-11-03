"""元データの取得メモ（実行は手作業）
- 地価公示 2026年（国土数値情報 L01-26）：https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-2026.html
  L01-26.geojson には、各標準地の 1983〜2026 年の価格（L01_062〜L01_105）、選定年次ビット（L01_061）、
  年ごとの属性移動（L01_106〜L01_148）が入っている。ここから 2016〜2026 年の価格と 2017〜2026 年の属性移動だけを
  data/raw/l01_price_history.csv に抜き出した（下の関数）。
- 地点の属性・駅・市区町村の特徴量は F03 と同じもの（data/raw/F03_features.csv、F03 の data/features.csv の写し）。
"""
import csv, json, sys


def extract(geojson_path, out_path):
    d = json.load(open(geojson_path, encoding="utf-8"))
    w = csv.writer(open(out_path, "w", newline="", encoding="utf-8"))
    yrs = list(range(2016, 2027))
    w.writerow(["code", "bits"] + [f"p{y}" for y in yrs] + [f"chg{y}" for y in range(2017, 2027)])
    for f in d["features"]:
        p = f["properties"]
        code = f"{p['L01_001']}-{p['L01_002']}-{p['L01_003']}"
        w.writerow([code, p["L01_061"]] + [p["L01_%03d" % (62 + y - 1983)] for y in yrs]
                   + [p["L01_%03d" % (106 + y - 1984)] for y in range(2017, 2027)])


if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2])
