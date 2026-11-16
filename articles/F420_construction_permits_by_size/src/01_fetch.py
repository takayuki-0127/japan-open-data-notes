"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。取得のあと 01b_extract.py で表を CSV にする。"""
import hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
URL = "https://www.mlit.go.jp/report/press/content/001889275.pdf"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    b = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=120).read()
    (RAW / "mlit_kyoka_2025_03.pdf").write_bytes(b)
    print(hashlib.sha256(b).hexdigest()[:12])


if __name__ == "__main__":
    main()
