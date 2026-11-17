"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 日本銀行 時系列統計データ検索サイト API：本邦対外資産負債残高（年末、直接投資の資産・負債と内訳、時価の参考値）、
  直接投資残高地域別（負債）、国際収支 金融収支 直接投資（負債）の月次のフロー
- 内閣府「四半期別GDP速報」2025年7-9月期2次速報 名目暦年（F358 と同じファイル）
"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code={codes}&startDate={s}&endDate={e}"
IIP = ["BPBP6KL1", "BPBP6KL11", "BPBP6KL12", "BPBP6KL13", "BPBP6KA1", "BPBP6KL38", "BPBP6KA50", "BPBP6KL", "BPBP6KA"]
REG = ["BPBP6M1", "BPBP6M1AS", "BPBP6M1CN", "BPBP6M1HK", "BPBP6M1SG", "BPBP6M1TW", "BPBP6M1KR", "BPBP6M1NA", "BPBP6M1US", "BPBP6M1CS", "BPBP6M1CI",
       "BPBP6M1EP", "BPBP6M1GB", "BPBP6M1NL", "BPBP6M1FR", "BPBP6M1CH", "BPBP6M1DE", "BPBP6M1OC", "BPBP6M1ME", "BPBP6M1AF", "BPBP6M1EU", "BPBP6M1AA"]
FLOW = ["BPBP6JYNFL13", "BPBP6JYNFL131", "BPBP6JYNFL132", "BPBP6JYNFL133"]
FILES = {"boj_iip_annual.json": API.format(codes=",".join(IIP), s="1996", e="2025"),
         "boj_fdi_region_annual.json": API.format(codes=",".join(REG), s="2014", e="2025"),
         "boj_fdi_flow_monthly.json": API.format(codes=",".join(FLOW), s="199601", e="202512")}
GDP = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2025/qe253_2/tables/gaku-mcy2532.csv"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        assert json.loads(b)["NEXTPOSITION"] is None
        (RAW / f).write_bytes(b)
    (RAW / "esri_gaku-mcy2532.csv").write_bytes(urllib.request.urlopen(urllib.request.Request(GDP, headers=UA), timeout=180).read())


if __name__ == "__main__":
    main()
