"""01_fetch.py : 公式サイト（e-Stat ほか）から元データを取得して data/raw/ に保存し、SOURCES.md を書く。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。
"""
import datetime
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"

# (保存名（拡張子なし）, statInfId または URL, fileKind, 中身)
FILES = [
    ('kakei_longterm_workers_monthly', '000040270658', '4', '家計調査 長期時系列表 表2 用途分類 二人以上の世帯のうち勤労者世帯（月・四半期・年、2000年1月〜）'),
]


def fetch(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=180) as r:
                return r.read()
        except Exception:
            time.sleep(5)
    raise RuntimeError(url)


def ext_of(b, url):
    if b[:4] == b"\xd0\xcf\x11\xe0":
        return ".xls"
    if b[:2] == b"PK":
        return ".xlsx"
    return ".csv"


def main():
    rows = []
    for stem, sid, kind, desc in FILES:
        url = sid if sid.startswith("http") else EST.format(sid, kind)
        b = fetch(url)
        name = stem + ext_of(b, url)
        (RAW / name).write_bytes(b)
        rows.append((name, desc, url, hashlib.sha256(b).hexdigest()[:12], len(b)))
        print(name, len(b))
        time.sleep(1)
    lines = ["# SOURCES（元データの取得元）", "",
             f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
    lines += ["", "出典：総務省統計局「家計調査（家計収支編）」長期時系列表（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
