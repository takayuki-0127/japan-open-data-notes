"""01 取得：社会生活基本調査の表を e-Stat から取る（run_all.sh からは呼ばない）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "shakai_ts_t6_1976_2021_000032229317.xlsx": "000032229317",   # 令和3年 第6表 男女・ふだんの就業状態・曜日・行動の種類別総平均時間の推移（1976〜2021年）
    "shakai_2016_t68-1_pref_000031617014.xlsx": "000031617014",   # 平成28年 生活時間－地域 第68-1表（有業者、従業上の地位・雇用形態、都道府県）
    "shakai_2021_t74-1_pref_000032224232.xlsx": "000032224232",   # 令和3年 生活時間－地域 第74-1表（同）
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
