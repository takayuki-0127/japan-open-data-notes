"""国土交通省「全国貨物純流動調査（物流センサス）」の表を e-Stat から取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
FILES = [
    ("t1_5_15_2021", "000040041013", "2021年調査 表1-5-15 代表輸送機関別流動量・流動ロットの推移（2005〜2021年）"),
    ("t1_5_15_2015", "000031596952", "2015年調査 表1-5-15 代表輸送機関別流動量・流動ロットの推移（2000〜2015年）"),
    ("t1_5_12_2021", "000040041010", "2021年調査 表1-5-12 発産業業種別流動量・流動ロットの推移（2005〜2021年）"),
    ("t2_7_1_2021", "000040041123", "2021年調査 表2-7-1 発産業業種・流動ロット階層別流動量（代表輸送機関別）－重量－"),
    ("t2_7_2_2021", "000040041124", "2021年調査 表2-7-2 発産業業種・流動ロット階層別流動量（代表輸送機関別）－件数－"),
    ("t2_7_1_2015", "000031597002", "2015年調査 表2-7-1 発産業業種・流動ロット階層別流動量（代表輸送機関別）－重量－"),
    ("t2_7_2_2015", "000031597003", "2015年調査 表2-7-2 発産業業種・流動ロット階層別流動量（代表輸送機関別）－件数－"),
]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = BASE.format(sid)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"{name}.{ext}").write_bytes(b)
        lines.append(f"| {name}.{ext} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", name, len(b))
    lines += ["", "- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600620&tstat=000001103136",
              "- 出典：国土交通省「全国貨物純流動調査（物流センサス）」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "- 流動量は「3日間調査」（調査した3日間の出荷）の拡大推計。流動ロット = 重量 ÷ 件数（トン／件）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
