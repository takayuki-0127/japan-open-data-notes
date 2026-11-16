"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
日本銀行 時系列統計データ検索サイトの API（JSON）から、国際収支統計（BP01）月次とドル円（FM08）を取る。"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
MONTHLY = ["BPBP6JYNCB", "BPBP6JYNTB", "BPBP6JYNPIN", "BPBP6JYNPIC",
           "BPBP6JYNPIC21", "BPBP6JYNPIC2111", "BPBP6JYNPIC2112", "BPBP6JYNPIC212",
           "BPBP6JYNPID21", "BPBP6JYNPID2111", "BPBP6JYNPID2112", "BPBP6JYNPID212",
           "BPBP6JYNPIC22", "BPBP6JYNPIC29", "BPBP6JYNFA132"]
FILES = {
    "boj_bop_monthly.json": API.format(db="BP01", codes=",".join(MONTHLY), s="199601", e="202609"),
    "boj_usdjpy_monthly.json": API.format(db="FM08", codes="FXERM07", s="199601", e="202609"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        d = json.loads(b)
        assert d["NEXTPOSITION"] is None
        (RAW / f).write_bytes(b)
        print(f, len(b))


if __name__ == "__main__":
    main()
