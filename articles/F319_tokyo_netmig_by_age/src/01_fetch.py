"""01 取得：住民基本台帳人口移動報告 年報 第3-3表（年齢5歳階級・男女別 転入超過数）を e-Stat から取る。
run_all.sh からは呼ばない（ネットにつなぐのはこのファイルだけ）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
IDS = {  # 年: statInfId（F131 の取得メモと e-Stat の一覧で確認）
    2010: "000008636883", 2011: "000012678261", 2012: "000018800108", 2013: "000023617822",
    2014: "000028107507", 2015: "000031360559", 2016: "000031524394", 2017: "000031666857",
    2018: "000031788880", 2019: "000031905334", 2020: "000032047085", 2021: "000032163818",
    2022: "000040008244", 2023: "000040139264", 2024: "000040243450", 2025: "000040407042",
}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for y, sid in IDS.items():
        req = urllib.request.Request(URL.format(sid), headers={"User-Agent": "Mozilla/5.0"})
        b = urllib.request.urlopen(req, timeout=60).read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"jumin_3-3_{y}_{sid}.{ext}").write_bytes(b)
        print(y, sid, ext, len(b))
        time.sleep(1)

if __name__ == "__main__":
    main()
