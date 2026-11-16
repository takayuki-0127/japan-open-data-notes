"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
厚生労働省「能力開発基本調査」企業調査 第1表・第2表（2009〜2025年度調査、e-Stat）と、総務省「消費者物価指数」特殊分類（全国、月次）。
statInfId は nouryoku_file_ids.json（e-Stat のファイル一覧から、表の名前で探したもの）。"""
import json, pathlib, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
DL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for y, no, sid in json.load(open(HERE / "nouryoku_file_ids.json")):
        r = urllib.request.urlopen(urllib.request.Request(DL.format(sid, 0), headers=UA), timeout=120)
        ext = urllib.parse.unquote(r.headers.get("Content-Disposition", "")).rsplit(".", 1)[-1]
        (RAW / f"nouryoku_{y}_t{no}.{ext}").write_bytes(r.read())
    r = urllib.request.urlopen(urllib.request.Request(DL.format("000040482943", 1), headers=UA), timeout=120)
    (RAW / "cpi_zenkoku_special_monthly.csv").write_bytes(r.read())


if __name__ == "__main__":
    main()
