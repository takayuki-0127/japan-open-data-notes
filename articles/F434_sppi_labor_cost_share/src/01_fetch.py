"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
日本銀行 時系列統計データ検索サイト API：企業向けサービス価格指数（2020年基準）。
消費税を除く指数（2000年1月〜）と、消費税を含む指数（1985年1月〜）の総平均・高人件費率サービス・低人件費率サービス・大類別。"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR02&code={codes}&startDate={s}&endDate=202609"
EXTAX = ["PRCS20_4200000000", "PRCS20_42B0000000", "PRCS20_42S0000002", "PRCS20_42S0000003"] + [f"PRCS20_420001000{i}" for i in range(1, 8)]
INTAX = ["PRCS20_5200000000", "PRCS20_52S0000002", "PRCS20_52S0000003"]
FILES = {"boj_sppi_extax_monthly.json": API.format(codes=",".join(EXTAX), s="200001"),
         "boj_sppi_intax_monthly.json": API.format(codes=",".join(INTAX), s="198501")}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        assert json.loads(b)["NEXTPOSITION"] is None
        (RAW / f).write_bytes(b)
        print(f, len(b))


if __name__ == "__main__":
    main()
