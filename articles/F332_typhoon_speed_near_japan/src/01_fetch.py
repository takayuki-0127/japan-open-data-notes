"""01 取得（run_all.sh からは呼ばない）：気象庁 RSMC Tokyo ベストトラック（bst_all.zip）"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/Besttracks/bst_all.zip"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    b = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
    assert b[:2] == b"PK"
    (RAW / "bst_all.zip").write_bytes(b)
    print(len(b))


if __name__ == "__main__":
    main()
