"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 財務省「本邦対外資産負債残高の推移（時系列データ）」6IIP.xls（暦年末、1996〜2025年、億円）
- 財務省「本邦対外資産負債残高 増減要因（試算）」各年の概要の参考1（PDF、2019〜2025年末、10億円）
- 日本銀行 時系列統計データ検索サイト API：国際収支統計の金融収支（月次、db=BP01）、ドル円の月末レート（db=FM08）
"""
import gzip, json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
HDR = {"User-Agent": "japan-open-data-notes research script (python urllib)", "Accept-Encoding": "gzip"}
MOF = "https://www.mof.go.jp/policy/international_policy/reference/iip/"
PDFS = {y: (f"data/{y}_g1.pdf" if y >= 2025 else f"{y}_g1.pdf") for y in range(2019, 2026)}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}"
BP = ["BPBP6JYNFB", "BPBP6JYNFB1", "BPBP6JYNFB2", "BPBP6JYNFB5", "BPBP6JYNFB3", "BPBP6JYNFA4",
      "BPBP6JYNFA13", "BPBP6JYNFA2", "BPBP6JYNFA5", "BPBP6JYNFA3",
      "BPBP6JYNFL13", "BPBP6JYNFL2", "BPBP6JYNFL5", "BPBP6JYNFL3"]
FX = ["FXERM06"]


def fetch(url):
    b = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=120).read()
    return gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "6IIP.xls").write_bytes(fetch(MOF + "6IIP.xls"))
    for y, p in PDFS.items():
        (RAW / f"iip_factors_{y}.pdf").write_bytes(fetch(MOF + p))
    for name, db, codes in [("boj_bp01_financial_account.json", "BP01", BP), ("boj_fm08_usdjpy.json", "FM08", FX)]:
        d = json.loads(fetch(API.format(db=db, codes=",".join(codes))))
        assert d["STATUS"] == 200, d
        (RAW / name).write_text(json.dumps(d["RESULTSET"], ensure_ascii=False, indent=0), encoding="utf-8")


if __name__ == "__main__":
    main()
