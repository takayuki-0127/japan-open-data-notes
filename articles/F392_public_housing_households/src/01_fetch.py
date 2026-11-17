"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「住宅・土地統計調査」令和5年 時系列統計表。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=4"
FILES = [
    ("ts09_1_tenure_japan", "000040354038", "時系列 第9-1表 住宅の所有の関係(5区分)別住宅数－全国（昭和38年〜令和5年）"),
    ("ts10_tenure_pref", "000040354040", "時系列 第10表 住宅の所有の関係(5区分)、建て方(3区分)別住宅数－全国・3大都市圏・都道府県・大都市（昭和58年〜令和5年）"),
    ("ts21_1_tenure_age_japan", "000040354054", "時系列 第21-1表 住宅の所有の関係(5区分)、家計を主に支える者の年齢(14区分)別主世帯数－全国（昭和43年〜令和5年）"),
    ("ts34_1_rent_japan", "000040354072", "時系列 第34-1表 住宅の種類、所有の関係(5区分)別 1か月当たり家賃及び1畳当たり家賃－全国（昭和48年〜令和5年）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = ES.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        fn = name + (".xlsx" if b[:2] == b"PK" else ".xls")
        (RAW / fn).write_bytes(b)
        rows.append(f"| {fn} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(fn, len(b))
    rows += ["", "出典：総務省統計局「住宅・土地統計調査」（令和5年 時系列統計表、e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
