"""01 取得：原数値と公表の季節調整値

このリポジトリの data/raw/ には取得済みのファイルを置いている（そのまま 02 から動く）。
- lfs.xlsx：総務省「労働力調査」長期時系列表1 a-1（季節調整値・原数値・季節指数）e-Stat statInfId=000031831358（2026-10-26 取得、F13 と同じ）
- jobs.xlsx：厚生労働省「一般職業紹介状況」第3表-1 有効求人倍率（実数・季節調整値）（2026-10-26 取得、F13・F12 と同じ）
- iip_mining_manufacturing.csv：経済産業省「鉱工業指数（2020年基準）」の鉱工業総合（生産＝付加価値額生産、出荷）
    原指数 b2020_gom1j.xlsx、季節調整済指数 b2020_gsm1j.xlsx（2018年1月〜2026年8月、2026-10-15 更新）
    接続指数 b2020_sgo1j.xlsx（原指数）・b2020_sgs1j.xlsx（季節調整済）（1978年1月〜2022年12月）
    https://www.meti.go.jp/statistics/tyo/iip/b2020_result-2.html から 2026-10-27 に取得し、鉱工業総合の行だけを抜き出した

取り直すときは --download を付けて実行する（ネットワークにつながる環境で）。
X-13ARIMA-SEATS の本体は pip install x13as で入る（米国センサス局のプログラムを同梱したパッケージ）。
"""
import argparse
import io
import urllib.request
import pandas as pd
from common import RAW

METI = "https://www.meti.go.jp/statistics/tyo/iip/xls/"
ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"


def iip():
    D = {}
    for f, tag in [("b2020_sgo1j", "nsa_c"), ("b2020_sgs1j", "sa_c")]:
        x = pd.ExcelFile(io.BytesIO(urllib.request.urlopen(METI + f + ".xlsx").read()))
        for sh, p in [("生産付加価値額", "prod"), ("出荷", "ship")]:
            a = x.parse(sh, header=None)
            for _, r in a.iterrows():
                if isinstance(r[1], (int, float)) and r[1] > 197000:
                    D.setdefault(int(r[1]), {})[f"{p}_{tag}"] = r[2]
    for f, tag in [("b2020_gom1j", "nsa"), ("b2020_gsm1j", "sa")]:
        x = pd.ExcelFile(io.BytesIO(urllib.request.urlopen(METI + f + ".xlsx").read()))
        for sh, p in [("生産", "prod"), ("出荷", "ship")]:
            a = x.parse(sh, header=None)
            hdr = a[a[0] == "品目番号"].iloc[0]
            row = a[a[1] == "鉱工業"].iloc[0]
            for j in range(3, len(hdr)):
                if isinstance(hdr[j], (int, float)) and pd.notna(hdr[j]):
                    D.setdefault(int(hdr[j]), {})[f"{p}_{tag}"] = row[j]
    df = pd.DataFrame(D).T.sort_index()
    df.index.name = "ym"
    df.to_csv(RAW / "iip_mining_manufacturing.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()
    if not a.download:
        print("data/raw/ の同梱データを使います（取り直すときは --download）")
        return
    urllib.request.urlretrieve(ESTAT.format("000031831358"), RAW / "lfs.xlsx")
    print("有効求人倍率の表（jobs.xlsx）は e-Stat の一般職業紹介状況から最新の第3表-1 を探して保存してください（ID が毎月変わるため）")
    iip()


if __name__ == "__main__":
    main()
