"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「住宅・土地統計調査」（e-Stat）：
- 令和5年 時系列統計表 第19表 住宅の所有の関係・省エネルギー設備等別 住宅数（2003〜2023年、全国・都道府県・大都市）
- 各回の主要統計表・全国編：住宅の種類・所有の関係・建て方・構造・省エネルギー設備等別 住宅数（2008・2013・2018・2023年、全国）
- 令和5年 基本集計：住宅の所有の関係・建築の時期・省エネルギー設備等別 住宅数（全国・都道府県・市区町村）"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "jutaku_timeseries_t19_2003_2023.xlsx": (E.format("000040354051", 4), "令和5年 時系列統計表 第19表 所有の関係(2区分)・省エネルギー設備等(7区分)別 住宅数 2003〜2023年"),
    "jutaku_2023_tatekata.xlsx": (E.format("000040353877", 4), "令和5年 主要統計表 第13表 建て方・構造・省エネルギー設備等別 住宅数（全国）"),
    "jutaku_2018_tatekata.xls": (E.format("000031866006", 0), "平成30年 主要統計表 建て方・構造・省エネルギー設備等別 住宅数（全国）"),
    "jutaku_2013_tatekata.xls": (E.format("000028504462", 0), "平成25年 確報集計 全国編 建て方・構造・省エネルギー設備等別 住宅数（全国）"),
    "jutaku_2008_tatekata.xls": (E.format("000007372606", 0), "平成20年 確報集計 全国編 建て方・構造・省エネルギー設備等別 住宅数（全国）"),
    "jutaku_2023_jiki.xlsx": (E.format("000040209892", 0), "令和5年 基本集計 所有の関係・建築の時期(14区分)・省エネルギー設備等別 住宅数"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "出典：総務省統計局「住宅・土地統計調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00200522）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
