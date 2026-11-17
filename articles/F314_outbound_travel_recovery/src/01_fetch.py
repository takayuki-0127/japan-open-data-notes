"""元データを公式サイトから取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
- 法務省「出入国管理統計」年報（e-Stat）：月別 主要港の出国日本人／住所地別 年齢（5歳階級）・男女別 出国日本人（2012〜2025年）
- 総務省「人口推計」第10表（2019年・2024年10月1日）：都道府県・年齢（5歳階級）・男女別の日本人人口
- 日本銀行 時系列統計データ（API）：ドル・円の月中平均、実質実効為替レート（月）
- 総務省「消費者物価指数」2025年基準 品目別（暦年の年平均・月）：航空運賃・外国パック旅行費（F311・F357 と同じ URL）
"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "f3-research-script/1.0 (python urllib)"}
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
PORT = {2012: "000021238965", 2013: "000025370826", 2014: "000030220415", 2015: "000031419172", 2016: "000031585945",
        2017: "000031724908", 2018: "000031832805", 2019: "000031961975", 2020: "000032104461", 2021: "000032216468",
        2022: "000040067675", 2023: "000040187830", 2024: "000040292950", 2025: "000040476166"}
PREF = {2012: "000021239110", 2013: "000025370990", 2014: "000030220417", 2015: "000031419360", 2016: "000031585947",
        2017: "000031724910", 2018: "000031832807", 2019: "000031961977", 2020: "000032104463", 2021: "000032216470",
        2022: "000040067677", 2023: "000040187832", 2024: "000040292952", 2025: "000040476168"}
BOJ = {"boj_usdjpy_monthly.csv": ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=FM08&code=FXERM07&startDate=201001&endDate=202610",
                                  "日本銀行 東京市場 ドル・円 スポット 17時時点／月中平均（FM08 FXERM07）"),
       "boj_reer_monthly.csv": ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=FM09&code=FX180110002&startDate=201001&endDate=202610",
                                "日本銀行 実効為替レート（実質）指数（FM09 FX180110002）")}
POP = {2019: "000031921679", 2024: "000040268918"}  # 人口推計 第10表 都道府県，年齢（5歳階級），男女別人口（10月1日）
CPI = {"cpi_item_annual.csv": ("000040482831", "総務省「消費者物価指数」2025年基準 全国 品目別価格指数（暦年の年平均）"),
       "cpi_item_monthly.csv": ("000040482945", "総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月）")}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    rows = []
    for kind, ids, label in [("port", PORT, "月別 主要港の出国日本人"), ("pref", PREF, "住所地別 年齢（5歳階級）・男女別 出国日本人")]:
        for y, sid in ids.items():
            fk = 0 if y <= 2019 else 4
            url = EST.format(sid, fk); b = get(url)
            ext = "xlsx" if b[:2] == b"PK" else "xls"
            name = f"imm_{kind}_{y}.{ext}"; (RAW / name).write_bytes(b)
            rows.append((name, f"法務省「出入国管理統計」{y}年 {label}", url, hashlib.sha256(b).hexdigest()[:12]))
            print("saved", name)
    for y, sid in POP.items():
        url = EST.format(sid, 0); b = get(url); ext = "xlsx" if b[:2] == b"PK" else "xls"
        name = f"pop_t10_{y}.{ext}"; (RAW / name).write_bytes(b)
        rows.append((name, f"総務省「人口推計」{y}年10月1日 第10表 都道府県，年齢（5歳階級），男女別人口－総人口，日本人人口", url, hashlib.sha256(b).hexdigest()[:12]))
    for name, (url, label) in BOJ.items():
        b = get(url); (RAW / name).write_bytes(b); rows.append((name, label, url, hashlib.sha256(b).hexdigest()[:12]))
    for name, (sid, label) in CPI.items():
        url = EST.format(sid, 1); b = get(url); (RAW / name).write_bytes(b); rows.append((name, label, url, hashlib.sha256(b).hexdigest()[:12]))
    L = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（src/01_fetch.py で取得）", "",
         "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    L += ["", "- 出入国管理統計の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00250011&tstat=000001012480",
          "- 人口推計の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200524&tstat=000000090001",
          "- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/",
          "- e-Stat のファイルは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。日本銀行の CSV は Shift_JIS。"]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
