"""01 取得：建築着工統計調査 時系列表（利用関係別－新設住宅の戸数、床面積の合計、年計）を e-Stat から取る。"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
SID = "000040405973"
URL = f"https://www.e-stat.go.jp/stat-search/file-download?statInfId={SID}&fileKind=0"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    b = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
    (RAW / f"chakko_ts_riyou_{SID}.xls").write_bytes(b)
    print(len(b))

if __name__ == "__main__":
    main()
