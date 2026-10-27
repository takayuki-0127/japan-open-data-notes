"""01 取得：全国学力・学習状況調査の都道府県別「調査結果概況」(公立)を集める。

- 2025・2026年度：国立教育政策研究所のサイト（https://www.nier.go.jp/{yy}chousakekkahoukoku/factsheet/{県フォルダ}/）
- 2019・2021〜2024年度：国立国会図書館 WARP に保存された同じページ
  （https://warp.ndl.go.jp/20251213/20251203143721/https://www.nier.go.jp/...）
- 2020年度は調査が中止。2018年度以前は国語・算数がA・Bに分かれていたので使わない。

各ファイル（小：{nn}p_{yy}r.xlsx、中：{nn}m_{yy}r.xlsx）の「国語」「算数」「数学」シートから、
児童生徒数・平均正答数・平均正答率（公表値）・中央値・標準偏差と、正答数ごとの人数（分布）を読む。
結果は data/raw/nier_pref_2019_2026.json と同じ形で保存する。

記事では、このコードと同じ処理をブラウザのページの中（SheetJS）で行って取得した。
"""
import io
import json
import re
import time
from pathlib import Path

import openpyxl
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "nier_pref_2019_2026.json"

PREFS = ("01_hokkaido,02_aomori,03_iwate,04_miyagi,05_akita,06_yamagata,07_fukushima,08_ibaraki,"
         "09_tochigi,10_gunma,11_saitama,12_chiba,13_tokyo,14_kanagawa,15_niigata,16_toyama,17_ishikawa,"
         "18_fukui,19_yamanashi,20_nagano,21_gifu,22_shizuoka,23_aichi,24_mie,25_shiga,26_kyoto,27_osaka,"
         "28_hyougo,29_nara,30_wakayama,31_tottori,32_shimane,33_okayama,34_hiroshima,35_yamaguchi,"
         "36_tokushima,37_kagawa,38_ehime,39_kouchi,40_fukuoka,41_saga,42_nagasaki,43_kumamoto,44_ohita,"
         "45_miyazaki,46_kagoshima,47_okinawa").split(",")
WARP = "https://warp.ndl.go.jp/20251213/20251203143721/"
Z2H = str.maketrans("０１２３４５６７８９", "0123456789")


def base_url(yy: str) -> str:
    if yy in ("25", "26"):
        return f"https://www.nier.go.jp/{yy}chousakekkahoukoku/factsheet/"
    if yy == "19":
        return WARP + "https://www.nier.go.jp/19chousakekkahoukoku/factsheet/19prefecture-City/"
    return WARP + f"https://www.nier.go.jp/{yy}chousakekkahoukoku/factsheet/"


def parse(book, meta):
    out = []
    for ws in book.worksheets:
        sn = ws.title.strip()
        if not re.search("国語|算数|数学", sn):
            continue
        rows = [[c if c is not None else "" for c in r] for r in ws.iter_rows(values_only=True)]
        hi = next(i for i, r in enumerate(rows) if any("平均正答率" in str(x) for x in r))
        pr = [x for x in rows[hi + 1] if x != ""][:8]
        nr = [x for x in rows[hi + 2] if x != ""][:8]
        dist = {}
        for r in rows[hi + 1:]:
            for j, x in enumerate(r):
                if re.fullmatch(r"[０-９0-9]+問", str(x).strip()) and j + 1 < len(r) and isinstance(r[j + 1], (int, float)):
                    dist[int(str(x).strip().replace("問", "").translate(Z2H))] = r[j + 1]
                    break
        out.append({**meta, "subject": sn, "name": pr[0], "raw": pr, "natraw": nr, "dist": dist})
    return out


def main():
    rows = []
    for yy in ["19", "21", "22", "23", "24", "25", "26"]:
        for f in PREFS:
            nn = f[:2]
            for lv, fn in [("小", f"{nn}p_{yy}r.xlsx"), ("中", f"{nn}m_{yy}r.xlsx")]:
                r = requests.get(base_url(yy) + f + "/" + fn, timeout=60)
                r.raise_for_status()
                book = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
                rows += parse(book, {"year": 2000 + int(yy), "level": lv, "pref": nn})
                time.sleep(1)
    OUT.write_text(json.dumps(rows, ensure_ascii=False))
    print(len(rows))


if __name__ == "__main__":
    main()
