"""データの取得について
国立社会保障・人口問題研究所『人口統計資料集（2025年版）』表12-33「都道府県別合計特殊出生率：1925～2023年」の
Excel（https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2025/T12-33.xlsx）の2枚目のシート（年ごとの表）を
CSV にしたものを data/raw/ipss_T12-33_tfr_pref.csv に置いています。
元は厚生労働省『人口動態統計』と総務省『国勢調査』『人口推計』に基づく値です。

このスクリプトは Excel を取り直して同じ CSV を作ります（ネットにつながる環境で実行してください）。
"""
import io
import urllib.request
import pandas as pd
from common import RAW

URL = "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2025/T12-33.xlsx"

if __name__ == "__main__":
    b = urllib.request.urlopen(URL, timeout=60).read()
    xl = pd.ExcelFile(io.BytesIO(b))
    df = pd.read_excel(xl, sheet_name=xl.sheet_names[1], header=None, dtype=str)
    df.to_csv(RAW / "ipss_T12-33_tfr_pref.csv", header=False, index=False, encoding="utf-8-sig")
    print("saved", df.shape)
