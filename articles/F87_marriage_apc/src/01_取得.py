"""国立社会保障・人口問題研究所『人口統計資料集（2025年版）』第6章の Excel を取得して JSON にする。

使う表（https://www.ipss.go.jp/syoushika/tohkei/Popular/Popular2025.asp?chap=6）
- 表6-9  性，年齢（5歳階級）別未婚者に対する初婚率：1930～2020年（10年おき）
- 表6-23 性別，50歳時の未婚割合など：1920～2020年
- 表6-24 性，年齢（5歳階級），配偶関係別割合：1920～2020年（シート(1)が未婚）

記事を作ったときは、ブラウザのページの中で SheetJS を使って読み、data/raw/ に JSON で保存した。
このスクリプトは同じことを pandas で行う（研究所のサイトに直接つながる環境で動かす）。
"""
import json
import pandas as pd
from common import RAW

BASE = "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2025/"

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    out = {}
    for t in ["T06-24", "T06-09", "T06-23"]:
        x = pd.read_excel(BASE + t + ".xlsx", sheet_name=None, header=None)
        out[t] = {k: v.where(v.notna(), None).values.tolist() for k, v in x.items()}
    json.dump(out, open(RAW / "ipss_T06-09_T06-23_T06-24.json", "w", encoding="utf-8"), ensure_ascii=False, default=str)
    print("saved")
