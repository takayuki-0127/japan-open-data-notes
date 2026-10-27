"""総務省統計局「家計調査（二人以上の世帯）品目別都道府県庁所在市及び政令指定都市ランキング」の Excel を取得して、
品目×都市×期間の縦長の CSV（data/raw/f47_kakei_rank.csv）にする。

- 2023〜2025年平均：https://www.stat.go.jp/data/kakei/zuhyou/rank01.xlsx 〜 rank13.xlsx（食料13分類）
- 2013〜2015年平均：https://www.stat.go.jp/data/kakei/rank/zuhyou/rank13-15.xls（シートごとに分類）
各シートは「品目ごとに、都市名と金額の2列が順位順に並ぶ」形。金額（円）の列だけを取り出す。
（記事を作ったときは、コンテナから stat.go.jp に届かなかったため、同じ処理をブラウザの中で SheetJS で行った）
境界：smartnews-smri/japan-topography の行政区域（国土数値情報 2021 をもとにした簡略版、CC BY 4.0）
"""
import io
import re
import urllib.request
import pandas as pd
from common import RAW

BASE_NEW = "https://www.stat.go.jp/data/kakei/zuhyou/"
FILES_NEW = [f"rank{i:02d}.xlsx" for i in range(1, 14)]
OLD = "https://www.stat.go.jp/data/kakei/rank/zuhyou/rank13-15.xls"
TOPO = ("https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/"
        "data/municipality/topojson/s0010/N03-21_210101.json")


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


def parse(book, fname):
    rows = []
    for sn, a in pd.read_excel(io.BytesIO(book), sheet_name=None, header=None).items():
        a = a.values.tolist()
        hi = next((i for i, r in enumerate(a) if any(isinstance(x, str) and re.search("金\\s*額|数量", x) for x in r)), -1)
        if hi < 1:
            continue
        names, units = a[hi - 1], a[hi]
        for c, u in enumerate(units):
            if not (isinstance(u, str) and "金" in u):
                continue
            for r in a[hi + 1:]:
                city, v = r[c], r[c + 1] if c + 1 < len(r) else None
                if isinstance(city, str) and isinstance(v, (int, float)) and v == v:
                    rows.append((fname, sn, names[c], re.sub(r"\s", "", city), v))
    return rows


if __name__ == "__main__":
    out = []
    for f in FILES_NEW:
        out += [("2023-2025",) + r for r in parse(get(BASE_NEW + f), f)]
    out += [("2013-2015",) + r for r in parse(get(OLD), "rank13-15.xls")]
    pd.DataFrame(out, columns=["period", "file", "sheet", "item", "city", "yen"]).to_csv(
        RAW / "f47_kakei_rank.csv", index=False, encoding="utf-8-sig")
    dst = RAW / "N03-21_210101.json"
    if not dst.exists():
        dst.write_bytes(get(TOPO))
