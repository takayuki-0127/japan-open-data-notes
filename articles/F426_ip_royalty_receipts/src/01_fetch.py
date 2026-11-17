"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
日本銀行 時系列統計データ検索サイト API：国際収支統計 知的財産権等使用料（月次、地域別は四半期）、ドル円。"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
MONTHLY = ["BPBP6JYNSC906", "BPBP6JYNSD906", "BPBP6JYNSN906", "BPBP6JYNSC9061", "BPBP6JYNSD9061", "BPBP6JYNSN9061",
           "BPBP6JYNSC9062", "BPBP6JYNSD9062", "BPBP6JYNSN9062", "BPBP6JYNSC"]
REG = ["95", "AS95", "CN95", "HK95", "TW95", "KR95", "SG95", "TH95", "IN95", "AA95", "NA95", "US95", "CS95", "OC95", "EP95", "EU95", "GB95", "DE95", "NL95", "CH95", "ME95", "AF95", "RW95"]
QUARTERLY = [f"BPBP6QSC{r}" for r in REG]
FILES = {
    "boj_ip_monthly.json": API.format(db="BP01", codes=",".join(MONTHLY), s="199601", e="202609"),
    "boj_ip_region_quarterly.json": API.format(db="BP01", codes=",".join(QUARTERLY), s="201401", e="202602"),
    "boj_usdjpy_monthly.json": API.format(db="FM08", codes="FXERM07", s="199601", e="202609"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        assert json.loads(b)["NEXTPOSITION"] is None
        (RAW / f).write_bytes(b)
        print(f, len(b))


if __name__ == "__main__":
    main()
