"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 文部科学省「学校基本調査」年次統計「卒業者に占める就職者の割合」（e-Stat）
- 厚生労働省「一般職業紹介状況（職業安定業務統計）」有効求人倍率・新規求人倍率（e-Stat、長期時系列）"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("gakko_shushoku_rate", "000031852305", "学校基本調査 年次統計「卒業者に占める就職者の割合（昭和25年～）」"),
    ("shokuan_yuko_kyujin_bairitsu", "000040518983", "一般職業紹介状況 第3表「有効求人倍率（実数、季節調整値）」"),
    ("shokuan_shinki_kyujin_bairitsu", "000040518982", "一般職業紹介状況 第2表「新規求人倍率（実数、季節調整値）」"),
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
    lines += ["", "出典：文部科学省「学校基本調査」（https://www.e-stat.go.jp/stat-search/files?toukei=00400001）、",
              "厚生労働省「一般職業紹介状況（職業安定業務統計）」（https://www.e-stat.go.jp/stat-search/files?toukei=00450222）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
