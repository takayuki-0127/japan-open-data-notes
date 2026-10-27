"""データの取得。

1) 総務省「住民基本台帳人口移動報告」（日本人移動者、都道府県×都道府県）
   - 長期時系列表 第11表「移動前の住所地別転入者数及び移動後の住所地別転出者数」
       1989年（平成元年）〜2011年（平成23年）：statInfId=000014898777〜000014898799（1年1ファイル、連番）
       2012年〜2025年：statInfId=000040430819（1ファイルに年ごとのシート）
   e-Stat の file-download（https://www.e-stat.go.jp/stat-search/file-download?statInfId=<id>&fileKind=0）で
   Excel を取り、ブラウザの中で SheetJS を使って各シートを CSV にし、
   {年: CSV文字列} の1つの JSON にまとめて data/raw/f33_migration_raw.json に置いた。
   （このコンテナからは e-Stat に直接つながらないため。下の fetch_estat() は、直接つながる環境で同じものを作るためのもの）
2) 境界：smartnews-smri/japan-topography（国土数値情報 行政区域 2021 の簡略版、CC BY 4.0）
"""
import io, csv, json, urllib.request
from common import RAW

RAW.mkdir(parents=True, exist_ok=True)

TOPO = ("https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/"
        "data/municipality/topojson/s0010/N03-21_210101.json")
dst = RAW / "N03-21_210101.json"
if not dst.exists():
    urllib.request.urlretrieve(TOPO, dst)


def fetch_estat(out=RAW / "f33_migration_raw.json"):
    """e-Stat に直接つながる環境用。openpyxl（pandas.read_excel）で同じ JSON を作る。"""
    import pandas as pd
    base = "https://www.e-stat.go.jp/stat-search/file-download?fileKind=0&statInfId="
    res = {}
    for k in range(777, 800):
        y = 1989 + (k - 777)
        b = urllib.request.urlopen(base + f"000014898{k}").read()
        df = pd.read_excel(io.BytesIO(b), header=None, dtype=str).fillna("")
        res[str(y)] = df.to_csv(index=False, header=False)
    b = urllib.request.urlopen(base + "000040430819").read()
    for name, df in pd.read_excel(io.BytesIO(b), header=None, dtype=str, sheet_name=None).items():
        res[str(name)] = df.fillna("").to_csv(index=False, header=False)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)


for f in ["f33_migration_raw.json", "N03-21_210101.json"]:
    print(f, (RAW / f).exists())
