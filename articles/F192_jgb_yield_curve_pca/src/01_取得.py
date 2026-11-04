"""財務省「国債金利情報」の CSV を取得する（Shift_JIS → UTF-8 で保存）。

- 過去分（1974年9月〜前月末）: https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv
- 当月分:                     https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv

この記事では 2026-11-05 にブラウザで取得した2ファイルを data/raw/ に置いている
（jgbcm_all.csv は 2026-10-30 まで、jgbcm_current.csv は 2026-11-02 まで）。
"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URLS = {
    "jgbcm_all.csv": "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
    "jgbcm_current.csv": "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        b = urllib.request.urlopen(url, timeout=60).read()
        (RAW / name).write_text(b.decode("shift_jis"), encoding="utf-8")
        print(name, len(b))
