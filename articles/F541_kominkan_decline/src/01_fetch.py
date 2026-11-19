"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「社会教育調査」（e-Stat）。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("nenji_01_facilities", "000032218535", "年次統計 表1 施設数の推移"),
    ("nenji_07_users", "000032218537", "年次統計 表7 利用者数の推移"),
    ("h14_kominkan_by_setter", "000001205720", "平成14年度 公民館 11 設置者別 公民館数（計・本館・分館、都道府県別）"),
    ("h14_municipal_setting", "000001205721", "平成14年度 公民館 12 市（区）町村立公民館の設置状況（都道府県別）"),
    ("h17_kominkan_honkan_bunkan", "000001210208", "平成17年度 公民館 設置者別本館・分館別公民館数（都道府県別）"),
    ("h17_municipal_setting", "000001210209", "平成17年度 公民館 市（区）町村立公民館の設置状況（都道府県別）"),
    ("r6_kominkan_honkan_bunkan", "000040439427", "令和6年度 公民館調査 18 設置者別所管別本館・分館別公民館数（都道府県別）"),
    ("r6_municipal_setting", "000040439428", "令和6年度 公民館調査 19 市（区）町村立公民館の設置状況（都道府県別）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        req = urllib.request.Request(URL.format(sid), headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        ext = ".xlsx" if b[:2] == b"PK" else ".xls"
        (RAW / (name + ext)).write_bytes(b)
        lines.append(f"| {name}{ext} | {desc} | {URL.format(sid)} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "出典：文部科学省「社会教育調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400004）。",
              "各調査年度の10月1日現在（利用者数は前年度間）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
