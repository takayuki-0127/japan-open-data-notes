"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「学校基本調査」（e-Stat の Excel）：年次統計と、高等学校（通信制）の表（5年ごと）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ('tsushin_1985_age.xls', '000029084382', '1985年度 高等学校（通信制） 年齢別生徒数（表番号 90）'),
    ('tsushin_1985_schools.xls', '000029084380', '1985年度 高等学校（通信制） 学校数・学科数（表番号 88）'),
    ('tsushin_1990_age.xls', '000029026378', '1990年度 高等学校（通信制） 年齢別生徒数（表番号 91）'),
    ('tsushin_1990_entrants.xls', '000029026381', '1990年度 高等学校（通信制） 入学者数・退学者数及び単位修得者数（表番号 94）'),
    ('tsushin_1990_schools.xls', '000029026376', '1990年度 高等学校（通信制） 学校数・学科数（表番号 89）'),
    ('tsushin_1995_age.xls', '000023596340', '1995年度 高等学校（通信制） 年齢別生徒数（表番号 92）'),
    ('tsushin_1995_entrants.xls', '000023596343', '1995年度 高等学校（通信制） 入学者数・退学者数及び単位修得者数（表番号 95）'),
    ('tsushin_1995_schools.xls', '000023596338', '1995年度 高等学校（通信制） 学校数・学科数（表番号 90）'),
    ('tsushin_2000_age.xls', '000015170315', '2000年度 高等学校（通信制） 年齢別生徒数（表番号 91）'),
    ('tsushin_2000_entrants.xls', '000015170318', '2000年度 高等学校（通信制） 入学者数・退学者数及び単位修得者数（表番号 94）'),
    ('tsushin_2000_schools.xls', '000015170313', '2000年度 高等学校（通信制） 学校数・学科数（表番号 89）'),
    ('tsushin_2005_age.xls', '000002946768', '2005年度 高等学校（通信制） 年齢別生徒数（表番号 91）'),
    ('tsushin_2005_entrants.xls', '000002946771', '2005年度 高等学校（通信制） 入学者数・退学者数（本科）及び単位修得者数（表番号 94）'),
    ('tsushin_2005_schools.xls', '000002946766', '2005年度 高等学校（通信制） 学校数・学科数（本科）（表番号 89）'),
    ('tsushin_2010_age.xls', '000008349789', '2010年度 高等学校（通信制） 年齢別生徒数（表番号 110）'),
    ('tsushin_2010_entrants.xls', '000008349792', '2010年度 高等学校（通信制） 入学者数・退学者数（本科）及び単位修得者数（表番号 113）'),
    ('tsushin_2010_schools.xls', '000008349787', '2010年度 高等学校（通信制） 学校数・学科数（本科）（表番号 108）'),
    ('tsushin_2015_age.xlsx', '000031357928', '2015年度 高等学校（通信制） 年齢別生徒数（表番号 129）'),
    ('tsushin_2015_entrants.xlsx', '000031357931', '2015年度 高等学校（通信制） 入学者数・退学者数（本科）及び単位修得者数（表番号 132）'),
    ('tsushin_2015_schools.xlsx', '000031357926', '2015年度 高等学校（通信制） 学校数・学科数（本科）（表番号 127）'),
    ('tsushin_2020_age.xlsx', '000032040541', '2020年度 高等学校（通信制） 年齢別生徒数（表番号 158）'),
    ('tsushin_2020_entrants.xlsx', '000032040544', '2020年度 高等学校（通信制） 入学者数・退学者数（本科）及び単位修得者数（表番号 161）'),
    ('tsushin_2020_schools.xlsx', '000032040539', '2020年度 高等学校（通信制） 学校数・学科数（本科）（表番号 156）'),
    ('tsushin_2025_age.xlsx', '000040393811', '2025年度 高等学校（通信制） 年齢別生徒数（表番号 158）'),
    ('tsushin_2025_entrants.xlsx', '000040393814', '2025年度 高等学校（通信制） 入学者数・退学者数（本科）及び単位修得者数（表番号 161）'),
    ('tsushin_2025_schools.xlsx', '000040393809', '2025年度 高等学校（通信制） 学校数・学科数（本科）（表番号 156）'),
    ('nenji_01.xlsx', '000031852301', '年次統計 総括表1 学校数（昭和23年～）'),
    ('nenji_02.xlsx', '000031852302', '年次統計 総括表2 在学者数（昭和23年～）'),
    ('nenji_04.xlsx', '000031852304', '年次統計 総括表4 進学率（昭和23年～）'),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：文部科学省「学校基本調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400001&tstat=000001011528）。各年度5月1日時点。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
