"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
気象庁「生物季節観測累年値ファイル（CSV）」：かえで紅葉（015）・かえで落葉（016）・いちょう黄葉（013）・いちょう落葉（014）。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
B = "https://www.data.jma.go.jp/sakura/data/ruinenchi/{}.csv"
FILES = {"015": "かえで紅葉", "016": "かえで落葉", "013": "いちょう黄葉", "014": "いちょう落葉"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for code, desc in FILES.items():
        url = B.format(code)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        (RAW / f"phenology_{code}.csv").write_bytes(b)
        lines.append(f"| phenology_{code}.csv | {desc}（地点別、1953年〜） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.3)
    lines += ["", "出典：気象庁「生物季節観測の情報」生物季節観測累年値ファイル（https://www.data.jma.go.jp/sakura/data/download_ruinenchi.html）。",
              "値は月日（例：1105＝11月5日）、0 は観測なし。各年の右の rm 列は気象庁のファイルフォーマットの説明による注記の符号。CSV は Shift_JIS。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
