"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
日本銀行 時系列統計データ検索サイト API：実効為替レート（名目・実質、2020年＝100、1970年1月〜）、
更新停止の旧系列（1973年3月＝100、2010年1月まで）、ドル円（月中平均）。"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
FILES = {
    "boj_effective_monthly.json": API.format(db="FM09", codes="FX180110001,FX180110002,FXCP7JP,FXCP8JP", s="197001", e="202609"),
    "boj_usdjpy_monthly.json": API.format(db="FM08", codes="FXERM07", s="197001", e="202609"),
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
