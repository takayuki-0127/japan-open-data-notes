"""01 取得：国勢調査の表を e-Stat から取る（run_all.sh からは呼ばない）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "census_ts_household_marital_1985_2005_000001086181.xlsx": "000001086181",  # 時系列 世帯 第4表【参考】その1 一般世帯数（旧分類）
    "census_2020_t12-1_household_marital_000040317884.xlsx": "000040317884",   # 令和2年 人口等基本集計 第12-1表（不詳補完値）
    "census_ts_pop_marital_1920_2020_000001085974.xlsx": "000001085974",        # 時系列 第4表 配偶関係・年齢・男女別15歳以上人口
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
