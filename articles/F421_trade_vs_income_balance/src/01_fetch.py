"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
日本銀行 時系列統計データ検索サイトの API（JSON）から、国際収支統計（BP01）とドル円（FM08）を取る。"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
MONTHLY = ["BPBP6JYNCB", "BPBP6JYNTB", "BPBP6JYNEX", "BPBP6JYNIM", "BPBP6JYNSN", "BPBP6JYNPIN", "BPBP6JYNPIC", "BPBP6JYNPID",
           "BPBP6JYNSIN", "BPBP6JYNPIN1", "BPBP6JYNPIN2", "BPBP6JYNPIN21", "BPBP6JYNPIN2111", "BPBP6JYNPIN2112", "BPBP6JYNPIN212",
           "BPBP6JYNPIN22", "BPBP6JYNPIN221", "BPBP6JYNPIN222", "BPBP6JYNPIN29", "BPBP6JYNPIN9"]
ANNUAL = ["BPBP6RACYJYNCB", "BPBP6RACYJYNTS", "BPBP6RACYJYNTB", "BPBP6RACYJYNSN", "BPBP6RACYJYNPIN", "BPBP6RACYJYNSIN"]
FILES = {
    "boj_bop_monthly.json": API.format(db="BP01", codes=",".join(MONTHLY), s="199601", e="202609"),
    "boj_bop_annual_1985_2013.json": API.format(db="BP01", codes=",".join(ANNUAL), s="1985", e="2013"),
    "boj_usdjpy_monthly.json": API.format(db="FM08", codes="FXERM07", s="198501", e="202609"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        json.loads(b)
        (RAW / f).write_bytes(b)
        print(f, len(b))


if __name__ == "__main__":
    main()
