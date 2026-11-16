"""01 取得：住宅・土地統計調査の表を e-Stat から取る（run_all.sh からは呼ばない）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "jutaku_ts_t21-1_1968_2018_000031959639.xlsx": "000031959639",  # 平成30年調査 時系列 第21-1表（全国、1968〜2018年）
    "jutaku_2023_t44-1_000040209922.xlsx": "000040209922",          # 令和5年調査 第44-1表（全国）
}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, sid in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(URL.format(sid), headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
        assert b[:2] == b"PK", name
        (RAW / name).write_bytes(b)
        print(name, len(b))
        time.sleep(1)

if __name__ == "__main__":
    main()
