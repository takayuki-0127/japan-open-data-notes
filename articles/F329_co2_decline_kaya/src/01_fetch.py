"""01 取得：国立環境研究所 GIO「日本の温室効果ガス排出量データ（1990〜2024年度）」を取る（run_all.sh からは呼ばない）。
一覧ページ：https://www.nies.go.jp/gio/archive/ghgdata/index.html"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.nies.go.jp/gio/archive/ghgdata/k6efli000007q2e2-att/L5-7gas_2026_gioweb_ver1.0.xlsx"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    b = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
    assert b[:2] == b"PK"
    (RAW / "nies_ghg_1990_2024_L5-7gas_2026_gioweb_ver1.0.xlsx").write_bytes(b)
    print(len(b))

if __name__ == "__main__":
    main()
