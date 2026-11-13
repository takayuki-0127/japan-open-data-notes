"""日本郵便の郵便番号データ（raw）から、分析に使う小さな表を作る。
data/raw/ に次の4つを置いてから動かす（README の「データ」を参照）:
  utf_ken_all.zip（住所の郵便番号・UTF-8 版）, jigyosyo.zip（事業所の個別番号）,
  del_all.csv（utf_del_YYMM.csv を月を先頭に付けてつないだもの）, jdel_all.csv（jdelYYMM.csv を同様につないで UTF-8 にしたもの）
事業所の名前・番地は使わない（番号・都道府県・市区町村だけを残す）。
"""
import zipfile
import pandas as pd
from common import DATA

RAW = DATA / "raw"
k = pd.read_csv(zipfile.ZipFile(RAW / "utf_ken_all.zip").open("utf_ken_all.csv"), header=None, dtype=str)
addr = k[[2, 0, 6, 7]].set_axis(["code", "jis", "pref", "city"], axis=1).drop_duplicates()
addr["kind"] = "住所"
j = pd.read_csv(zipfile.ZipFile(RAW / "jigyosyo.zip").open("JIGYOSYO.CSV"), header=None, dtype=str, encoding="cp932")
biz = j[[7, 0, 3, 4]].set_axis(["code", "jis", "pref", "city"], axis=1).drop_duplicates()
biz["kind"] = "事業所"
cur = pd.concat([addr, biz]).sort_values(["kind", "code", "jis"])
cur.to_csv(DATA / "zip_current.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})

d = pd.read_csv(RAW / "del_all.csv", header=None, dtype=str)
dd = d[[0, 3, 1, 7, 8]].set_axis(["month", "code", "jis", "pref", "city"], axis=1)
dd["kind"] = "住所"
jd = pd.read_csv(RAW / "jdel_all.csv", header=None, dtype=str)
jj = jd[[0, 8, 1, 4, 5]].set_axis(["month", "code", "jis", "pref", "city"], axis=1)
jj["kind"] = "事業所"
dele = pd.concat([dd, jj]).drop_duplicates().sort_values(["kind", "month", "code"])
dele.to_csv(DATA / "zip_deleted.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
print(len(cur), len(dele))
