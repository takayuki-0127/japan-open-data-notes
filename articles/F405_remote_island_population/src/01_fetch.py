"""01 取得：離島振興対策実施地域一覧（国交省 PDF）と国勢調査「都道府県・市区町村別の主な結果」（e-Stat）を取る。
run_all.sh からは呼ばない。"""
import pathlib, subprocess, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes-fetch/1.0 (python urllib)"}
ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "census_2025_main_000040507382.xlsx": ESTAT.format("000040507382"),
    "census_2020_main_000032143614.xlsx": ESTAT.format("000032143614"),
    "census_2015_main_000031594311.xls": ESTAT.format("000031594311"),
    "mlit_ritou_list_R8_001886615.pdf": "https://www.mlit.go.jp/kokudoseisaku/chirit/content/001886615.pdf",
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        (RAW / name).write_bytes(b)
        print(name, len(b))
        time.sleep(1)
    # PDF の文字を取り出す（poppler の pdftotext -layout）。以降はこのテキストを使う
    subprocess.run(["pdftotext", "-layout", str(RAW / "mlit_ritou_list_R8_001886615.pdf"),
                    str(RAW / "mlit_ritou_list_R8_001886615.txt")], check=True)

if __name__ == "__main__":
    main()
