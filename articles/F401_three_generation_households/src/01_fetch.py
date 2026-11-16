"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「国勢調査」の e-Stat 掲載ファイル。
- 都道府県・市区町村別の主な結果（2010・2015・2020・2025年）：3世代世帯数、一般世帯数、65歳以上の単独世帯、高齢夫婦世帯
  （2025年の「主な結果」の世帯の家族類型の列は不詳補完値なので、2025年の原数値は第9-1表から取る）
- 時系列データ 第3表 世帯の家族類型（16区分）別一般世帯数（新分類 1995〜2020年、旧分類 1980〜2005年）
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("000012777573", "census2010_main.xls", "平成22年 都道府県・市区町村別の主な結果"),
    ("000031594311", "census2015_main.xls", "平成27年 都道府県・市区町村別の主な結果"),
    ("000032143614", "census2020_main.xlsx", "令和2年 都道府県・市区町村別の主な結果"),
    ("000040507382", "census2025_main.xlsx", "令和7年 都道府県・市区町村別の主な結果"),
    ("000040506456", "census2025_t9_1.xlsx", "令和7年 人口等基本集計 第9-1表 世帯の家族類型、世帯員の年齢による世帯の種類別一般世帯数及び3世代世帯数（原数値）－全国、都道府県、市区町村"),
    ("000012671095", "census_ts_t3_family_new.xlsx", "時系列データ 第3表 世帯の家族類型（16区分）別一般世帯数－全国，都道府県（平成7年～令和2年）新分類区分 その1"),
    ("000001086173", "census_ts_t3_family_old.xlsx", "時系列データ 第3表【参考】世帯の家族類型（16区分）別一般世帯数－全国，都道府県，政令指定都市（昭和55年～平成17年）旧分類区分 その1"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for sid, name, desc in FILES:
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | 総務省「国勢調査」{desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：総務省「国勢調査」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
