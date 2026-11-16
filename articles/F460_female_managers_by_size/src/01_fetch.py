"""厚生労働省「雇用均等基本調査」の「役職別女性管理職（等）割合」の表を e-Stat から取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
IDS = {2003: "000014282664", 2009: "000014304203", 2011: "000017074194", 2013: "000027398616", 2015: "000031495814",
       2016: "000031642922", 2017: "000031773423", 2018: "000031852415", 2019: "000031969762", 2020: "000032108520",
       2021: "000032218442", 2022: "000040082653", 2023: "000040194846", 2024: "000040302144", 2025: "000040480856"}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, sid in IDS.items():
        url = BASE.format(sid)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"managers_{y}.{ext}").write_bytes(b)
        lines.append(f"| managers_{y}.{ext} | {y}年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", y, len(b))
    lines += ["", "- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450281&tstat=000001051898",
              "- 出典：厚生労働省「雇用均等基本調査」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "- 2010・2012・2014年度は、この名前の表が見つからなかったため取得していない。",
              "- 2017年度のファイルは1枚目のシートが別の表（コース別雇用管理制度）で、2枚目のシート「第8表」が役職別女性管理職割合。02_build.py は表題に「役職別女性管理職」がある方のシートを読む。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
