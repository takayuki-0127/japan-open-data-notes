"""01 取得：国交省「不動産価格指数（住宅）」「不動産取引件数・面積」と総務省「消費者物価指数」を取る（run_all.sh からは呼ばない）。"""
import hashlib, pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "rppi_residential_001473668.xlsx": "https://www.mlit.go.jp/totikensangyo/content/001473668.xlsx",
    "transactions_001465569.xlsx": "https://www.mlit.go.jp/common/001465569.xlsx",
    "cpi_middle_class_index.csv": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482943&fileKind=1",
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        b = urllib.request.urlopen(url, timeout=120).read()
        (RAW / name).write_bytes(b)
        print(name, len(b), hashlib.sha256(b).hexdigest()[:12])
        time.sleep(1)

if __name__ == "__main__":
    main()
