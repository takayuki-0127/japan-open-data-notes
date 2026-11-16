"""01 取得（run_all.sh からは呼ばない）：気象庁「過去の梅雨入りと梅雨明け」の CSV 2つ"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.data.jma.go.jp/cpd/baiu/"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f in ["tsuyu_prec.csv", "tsuyu_iriake.csv"]:
        b = urllib.request.urlopen(urllib.request.Request(BASE + f, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        (RAW / f).write_bytes(b)
        print(f, len(b))
        time.sleep(1)


if __name__ == "__main__":
    main()
