"""01 取得：国勢調査の表を e-Stat から取る（run_all.sh からは呼ばない）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "census_ts_households_t1_1960_2020_000001086170.xlsx": "000001086170",  # 時系列 世帯 第1表 その1 一般世帯及び施設等の世帯
    "census_2025_t12-1_households_000040506465.xlsx": "000040506465",       # 令和7年 人口等基本集計 第12-1表 一般世帯数（原数値）
    "census_2025_t12-2_members_000040506466.xlsx": "000040506466",          # 令和7年 人口等基本集計 第12-2表 一般世帯人員（原数値）
}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, sid in FILES.items():
        req = urllib.request.Request(URL.format(sid), headers={"User-Agent": "Mozilla/5.0"})
        b = urllib.request.urlopen(req, timeout=120).read()
        assert b[:2] == b"PK", name
        (RAW / name).write_bytes(b)
        print(name, len(b))
        time.sleep(1)

if __name__ == "__main__":
    main()
