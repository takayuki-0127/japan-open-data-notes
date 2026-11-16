"""観光庁「訪日外国人消費動向調査」（2024年から「インバウンド消費動向調査」）の暦年の集計表を取得して data/raw/ に保存する。
2014〜2019年は e-Stat、2023〜2025年は観光庁のサイトから。.xls は大きいので取得したバイト列をそのまま gzip（mtime=0）で圧縮して保存。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, gzip, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
KK = "https://www.mlit.go.jp/kankocho/content/{}"
FILES = [(2014, ES.format("000031366561")), (2015, ES.format("000031509470")), (2016, ES.format("000031562371")),
         (2017, ES.format("000031958631")), (2018, ES.format("000031958632")), (2019, ES.format("000031958633")),
         (2023, KK.format("002020300.xls")), (2024, KK.format("002022649.xls")), (2025, KK.format("002025515.xls"))]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, url in FILES:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
            b = r.read()
        name = f"inbound_{y}.xls.gz"
        with gzip.GzipFile(RAW / name, "wb", mtime=0) as f:
            f.write(b)
        lines.append(f"| {name} | {y}年 暦年 集計表（一般客） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", name, len(b))
    lines += ["", "- 2014〜2019年：政府統計の総合窓口 e-Stat「訪日外国人消費動向調査（年確定値）」https://www.e-stat.go.jp/stat-search/files?toukei=00601030&tstat=000001079655",
              "- 2023〜2025年：観光庁「インバウンド消費動向調査」https://www.mlit.go.jp/kankocho/tokei_hakusyo/gaikokujinshohidoko.html",
              "- .xls.gz は取得した .xls をそのまま gzip で圧縮したもの。出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
