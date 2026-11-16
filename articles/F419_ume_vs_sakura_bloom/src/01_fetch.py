"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。"""
import hashlib, io, pathlib, urllib.request, zipfile

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
FILES = {
    "001_ume_kaika.csv": "https://www.data.jma.go.jp/sakura/data/ruinenchi/001.csv",
    "004_sakura_kaika.csv": "https://www.data.jma.go.jp/sakura/data/ruinenchi/004.csv",
    "mon_jpn.csv": "https://www.data.jma.go.jp/cpdinfo/temp/list/csv/mon_jpn.csv",
}
MASTER = "https://www.jma.go.jp/jma/kishou/know/amedas/ame_master.zip"


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        (RAW / f).write_bytes(get(u))
    z = zipfile.ZipFile(io.BytesIO(get(MASTER)))
    for n in z.namelist():
        if n.endswith(".csv"):
            (RAW / n).write_bytes(z.read(n))
    for p in sorted(RAW.glob("*.csv")):
        print(p.name, hashlib.sha256(p.read_bytes()).hexdigest()[:12])


if __name__ == "__main__":
    main()
