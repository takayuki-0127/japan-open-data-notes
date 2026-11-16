"""国土交通省「自動車燃料消費量調査」の年度の第1表（燃料別・車種別 総括表）を e-Stat から取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
T1 = {2010: ("000031445143", 0), 2011: ("000031444855", 0), 2012: ("000031444892", 0), 2013: ("000031444869", 0),
      2014: ("000031444904", 0), 2015: ("000031453657", 0), 2016: ("000031607589", 0), 2017: ("000031732117", 0),
      2018: ("000031839648", 0), 2019: ("000031965137", 0), 2020: ("000032100249", 4), 2021: ("000032211801", 4),
      2022: ("000040073049", 4), 2023: ("000040190972", 4), 2024: ("000040284813", 4), 2025: ("000040468862", 4)}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, (sid, kind) in T1.items():
        url = BASE.format(sid, kind)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        name = f"fuel_t1_fy{y}.{ext}"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {y}年度 自動車燃料消費量調査 第1表 燃料別・車種別 総括表 | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", name, len(b))
    lines += ["", "- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600370&tstat=000001051698",
              "- 出典：国土交通省「自動車燃料消費量調査」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "- 用語（調査の凡例より）：1日1車当たり走行キロ = 走行キロ ÷ 実在延日車。走行1km当たり燃料消費量 = 燃料消費量 ÷ 走行キロ。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
