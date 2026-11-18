"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。e-Stat の掲載ファイルをそのまま保存する。"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "ecensus2009_basic_t1.xls": ("000012510098", 0),
    "ecensus2014_basic_t2.csv": ("000031332477", 1),
    "ecensus2016_activity_t4.csv": ("000031724996", 1),
    "ecensus2021_activity_t2_1.xlsx": ("000040067802", 0),
    "ecensus2024_basic_t2.xlsx": ("000040389322", 0),
    "pop_pref_2000_2020.xlsx": ("000013168605", 4),
    "pop_pref_2020_2024.xlsx": ("000040268859", 0),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, (sid, kind) in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(URL.format(sid, kind), headers=UA), timeout=300).read()
        (RAW / name).write_bytes(b)
        print(name, len(b))


if __name__ == "__main__":
    main()
