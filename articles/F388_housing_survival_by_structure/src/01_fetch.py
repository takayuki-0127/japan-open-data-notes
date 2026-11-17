"""01 取得：住宅・土地統計調査の「住宅の種類、構造、建築の時期別住宅数－全国」を各回 e-Stat から取る（run_all.sh からは呼ばない）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "jutaku_1998_kind_structure_period_000000050006": "000000050006",
    "jutaku_2003_kind_structure_period_000008195205": "000008195205",
    "jutaku_2008_kind_structure_period_000007372588": "000007372588",
    "jutaku_2013_kind_structure_period_000028504306": "000028504306",
    "jutaku_2018_kind_structure_period_000031865680": "000031865680",
    "jutaku_2023_kind_structure_period_000040209852": "000040209852",
}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, sid in FILES.items():
        req = urllib.request.Request(URL.format(sid), headers={"User-Agent": "japan-open-data-notes-fetch/1.0 (python urllib)"})
        b = urllib.request.urlopen(req, timeout=120).read()
        ext = ".xlsx" if b[:2] == b"PK" else ".xls"
        (RAW / (name + ext)).write_bytes(b)
        print(name + ext, len(b))
        time.sleep(1)

if __name__ == "__main__":
    main()
