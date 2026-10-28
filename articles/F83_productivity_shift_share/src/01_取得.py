"""F83 01 取得
内閣府 経済社会総合研究所「2024年度国民経済計算（2020年基準・2008SNA）」付表から
  2024s2n_jp.xlsx  経済活動別の国内総生産・要素所得（名目、暦年ごとのシート）
  2024s2rn_jp.xlsx 同（実質・連鎖方式、2020暦年=100 の指数）
  2024s3_jp.xlsx   経済活動別の就業者数・雇用者数、労働時間数
を取得し、全シートを CSV 文字列にして data/raw/f83_sna_raw.json に保存する。
esri.cao.go.jp はこのコンテナからは届かないため、実際の取得はブラウザのページ内（SheetJS）で行った。
届く環境なら、以下でも同じものが作れる。
"""
import io, json, urllib.request
from common import RAW
BASE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/kakuhou/files/2024/tables/"
FILES = ["2024s2n_jp.xlsx", "2024s2rn_jp.xlsx", "2024s3_jp.xlsx"]

if __name__ == "__main__":
    import pandas as pd
    out = {}
    for f in FILES:
        b = urllib.request.urlopen(BASE + f, timeout=60).read()
        xl = pd.read_excel(io.BytesIO(b), sheet_name=None, header=None, dtype=str)
        out[f] = {n: df.fillna("").to_csv(index=False, header=False) for n, df in xl.items()}
    RAW.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(RAW, "w", encoding="utf-8"), ensure_ascii=False)
    print("saved", RAW)
