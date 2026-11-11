"""data/ を作り直す：python fetch.py [生ファイルのフォルダ]
フォルダを指定しないときは data/raw に e-Stat から取得してから作る。
ドル円の年平均は日本銀行 時系列統計データ API（FM08、FXERM07：東京市場 ドル・円 スポット 17時時点 月中平均）から計算する。
"""
import sys, json
from pathlib import Path
import pandas as pd
import tradecodes as tc
from common import DATA

FILES = {  # 統計品別表（輸入、1-12月）
    "hin_imp_2019.csv": "000031907313", "hin_imp_2020.csv": "000032046081", "hin_imp_2025.csv": "000040424891",
}
BOJ = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&startDate=201501&endDate=202512&code=FXERM07"


def usdjpy_annual():
    import requests
    d = requests.get(BOJ, timeout=60).json()["RESULTSET"][0]["VALUES"]
    s = pd.Series(d["VALUES"], index=d["SURVEY_DATES"], dtype=float)
    return s.groupby(s.index // 100).mean()


def build(raw, fx=None):
    raw = Path(raw)
    rows = []
    for name in FILES:
        y = int(name[8:12]); d = tc.hinbetu(raw / name); d.insert(0, "year", y); rows.append(d)
    a = pd.concat(rows, ignore_index=True)
    a.to_csv(DATA / "imports_hs9_2019_2020_2025.csv", index=False)
    m = tc.finest_gaikyo(sorted(a.HS.unique()), raw, "i")
    g = tc.gaikyo(raw, "i")[["code", "name"]]
    m.to_csv(DATA / "hs9_to_gaikyo_import.csv", index=False)
    g.to_csv(DATA / "gaikyo_import_names.csv", index=False)
    if fx is None:
        fx = usdjpy_annual()
    fx.rename("usdjpy").rename_axis("year").reset_index().to_csv(DATA / "usdjpy_annual.csv", index=False)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    else:
        raw = DATA / "raw"; tc.download(FILES, raw)
    fx = None
    if len(sys.argv) > 2:  # 既に取得した日本銀行APIのJSON
        v = json.load(open(sys.argv[2]))["RESULTSET"][0]["VALUES"]
        s = pd.Series(v["VALUES"], index=v["SURVEY_DATES"], dtype=float); fx = s.groupby(s.index // 100).mean()
        fx = fx.loc[2015:2025]
    build(raw, fx)
