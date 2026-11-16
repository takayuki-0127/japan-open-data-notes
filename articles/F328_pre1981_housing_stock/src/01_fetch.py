"""01 取得：住宅・土地統計調査の表を e-Stat から取る（run_all.sh からは呼ばない）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "jutaku_2023_t5-1_period_000040209849.xlsx": "000040209849",   # 令和5年 第5-1表（建築の時期別住宅数、全国・都道府県）
    "jutaku_2018_t6-1_period_000031865677.xlsx": "000031865677",   # 平成30年 第6-1表（同）
    "jutaku_ts_t20-1_retrofit_000031959637.xlsx": "000031959637",  # 平成30年 時系列 第20-1表（持ち家の耐震改修、2003〜2018年）
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
