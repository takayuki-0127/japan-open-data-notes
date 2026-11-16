"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 日本銀行 時系列統計データ検索サイト API：国際収支統計 サービス収支（輸送・旅行・その他）月次、ドル円
- 日本政府観光局（JNTO）「国籍/月別 訪日外客数（2003年～2026年）」Excel
"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
MONTHLY = ["BPBP6JYNSN", "BPBP6JYNSN1", "BPBP6JYNSC2", "BPBP6JYNSD2", "BPBP6JYNSN2", "BPBP6JYNSC21", "BPBP6JYNSC22",
           "BPBP6JYNSD21", "BPBP6JYNSD22", "BPBP6JYNSN9"]
FILES = {
    "boj_services_monthly.json": API.format(db="BP01", codes=",".join(MONTHLY), s="199601", e="202609"),
    "boj_usdjpy_monthly.json": API.format(db="FM08", codes="FXERM07", s="199601", e="202609"),
}
JNTO = "https://www.jnto.go.jp/statistics/data/_files/20261021_1615-5.xlsx"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        assert json.loads(b)["NEXTPOSITION"] is None
        (RAW / f).write_bytes(b)
    b = urllib.request.urlopen(urllib.request.Request(JNTO, headers=UA), timeout=180).read()
    (RAW / "jnto_visitors_2003_2026.xlsx").write_bytes(b)


if __name__ == "__main__":
    main()
