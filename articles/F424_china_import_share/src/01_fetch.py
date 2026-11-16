"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
財務省「貿易統計」輸出入額の推移（地域（国）別・主要商品別）年別 輸入の CSV。"""
import hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
BASE = "https://www.customs.go.jp/toukei/suii/html/data/{}.csv"
FILES = ["d61ca", "d62ca001", "d62ca002", "d62ca003", "d62ca004", "d62ca005", "d62ca006", "d62ca007", "d62ca008"]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        b = urllib.request.urlopen(urllib.request.Request(BASE.format(f), headers=UA), timeout=120).read()
        (RAW / f"{f}.csv").write_bytes(b)
        print(f, hashlib.sha256(b).hexdigest()[:12])


if __name__ == "__main__":
    main()
