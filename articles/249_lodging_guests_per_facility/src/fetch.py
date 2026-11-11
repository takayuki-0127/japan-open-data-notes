"""data/ の CSV を観光庁のサイトから作り直す（記事の作成時は 2026-11-12 に同じ URL から取得した）。
観光庁「宿泊旅行統計調査」各年の「1月〜12月分（年の確定値）集計結果」Excel を data/raw/ に落とし、
extract.py で全国の行だけを data/table<n>_national.csv に書き出す。
使い方：python fetch.py（ネットにつながる環境で）"""
import time, requests
from common import RAW, DATA
from extract import main as extract
BASE = "https://www.mlit.go.jp/kankocho/content/"
FILES = {2015: "002026815.xlsx", 2016: "002026813.xlsx", 2017: "002026811.xlsx", 2018: "002026795.xlsx",
         2019: "002026792.xlsx", 2020: "002026786.xlsx", 2021: "002026777.xlsx", 2022: "002026772.xlsx",
         2023: "002026766.xlsx", 2024: "002026764.xlsx", 2025: "002026762.xlsx"}
if __name__ == "__main__":
    RAW.mkdir(exist_ok=True)
    for y, f in FILES.items():
        r = requests.get(BASE + f, timeout=120); r.raise_for_status()
        (RAW / f"y{y}_{f}").write_bytes(r.content); time.sleep(2)
    extract(RAW, DATA)
