"""F38 取得：e-Stat（産業連関表）と観光庁（インバウンド消費動向調査）から元データを取る。
python src/01_取得.py → data/raw/f38_io.json, data/raw/f38_io_purch.json

- 令和2年（2020年）産業連関表 取引基本表（生産者価格評価、統合中分類108部門）statInfId=000040187026
- 同 取引基本表（購入者価格評価、統合中分類）                       statInfId=000040187031
- 同 雇用表（統合中分類）                                           statInfId=000040187066
- 同 部門分類コード表                                               statInfId=000040186856
- 平成27年（2015年）産業連関表 取引基本表（生産者価格評価、統合中分類107部門）statInfId=000031839447
- 観光庁「インバウンド消費動向調査」集計表 2025年暦年【確報】参考2（費目別1人1回当たり旅行消費単価、全国籍・地域）
  https://www.mlit.go.jp/kankocho/content/002025515.xls → data/raw/inbound_2025_ref2.csv（全国籍・地域の列を書き写したもの）
記事の作成時は、ネットワークの都合でブラウザの中で取得し、同じ形の JSON に保存した。
"""
import json, io, sys, urllib.request
import pandas as pd
from common import RAW

URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"


def get(ids):
    out = {}
    for i in ids:
        b = urllib.request.urlopen(URL.format(i), timeout=120).read()
        xl = pd.read_excel(io.BytesIO(b), sheet_name=None, header=None)
        out[i] = {k: v.where(v.notna(), None).values.tolist() for k, v in xl.items()}
    return out


if __name__ == "__main__":
    json.dump(get(["000040187026", "000040187066", "000040186856", "000031839447"]),
              open(RAW / "f38_io.json", "w", encoding="utf-8"), ensure_ascii=False, default=str)
    json.dump(get(["000040187031"]), open(RAW / "f38_io_purch.json", "w", encoding="utf-8"), ensure_ascii=False, default=str)
    print("ok")
