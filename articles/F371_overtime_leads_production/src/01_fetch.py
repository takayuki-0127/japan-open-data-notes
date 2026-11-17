"""01_fetch.py : 公式サイトから元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元
- 厚生労働省「毎月勤労統計調査」全国調査 長期時系列表 季節調整済指数（e-Stat, statInfId 000040259772）
- 内閣府「景気動向指数」一致系列の個別系列（e-Stat, statInfId 000040520967）… C1 生産指数（鉱工業）を使う
- 内閣府経済社会総合研究所「景気基準日付」ページ（HTML）
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("maikin_sa_index.xlsx", EST.format("000040259772", 4), "000040259772", 4),
    ("ci_coincident_series.xlsx", EST.format("000040520967", 0), "000040520967", 0),
    ("esri_hiduke.html", "https://www.esri.cao.go.jp/jp/stat/di/hiduke.html", "-", "-"),
]


def main():
    rows = []
    for name, url, sid, kind in FILES:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=180) as r:
            disp = r.headers.get("Content-Disposition", "")
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append((name, sid, kind, len(b), hashlib.sha256(b).hexdigest()[:12], disp))
        print(name, len(b))
        time.sleep(1)
    with open(RAW / "fetch_log.tsv", "w", encoding="utf-8") as f:
        f.write("file\tstatInfId\tfileKind\tbytes\tsha256_12\tcontent_disposition\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")


if __name__ == "__main__":
    main()
