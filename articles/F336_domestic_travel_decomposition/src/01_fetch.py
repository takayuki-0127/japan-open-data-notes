"""01 取得（run_all.sh からは呼ばない）：観光庁「旅行・観光消費動向調査」主要指標の推移表
一覧ページ：https://www.mlit.go.jp/kankocho/tokei_hakusyo/shohidoko.html"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.mlit.go.jp/kankocho/content/002028738.xlsx"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    b = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
    assert b[:2] == b"PK"
    (RAW / "suii_002028738.xlsx").write_bytes(b)
    print(len(b))


if __name__ == "__main__":
    main()
