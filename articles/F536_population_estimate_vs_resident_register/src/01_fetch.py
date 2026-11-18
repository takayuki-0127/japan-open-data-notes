"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省統計局「人口推計」と、総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」の都道府県別の表（e-Stat）。"""
import datetime, hashlib, pathlib, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
SUIKEI = [
    ("suikei_long_2000_2020", "000013168605", 4, "人口推計 長期時系列 第5表 都道府県別人口（各年10月1日、総人口・日本人、2000〜2020年、補間補正人口）"),
    ("suikei_t5_2019", "000031921674", 0, "人口推計 2019年版 第5表 都道府県、男女別人口（2015〜2019年、公表時の値）"),
    ("suikei_t5_2024", "000040268859", 0, "人口推計 2024年版 第5表 都道府県、男女別人口（2020〜2024年）"),
    ("suikei_t10_2020", "000032153670", 4, "人口推計 2020年版 都道府県、年齢（5歳階級）、男女別人口（2020年10月1日）"),
    ("suikei_t10_2024", "000040268918", 0, "人口推計 2024年版 第10表 都道府県、年齢（5歳階級）、男女別人口（2024年10月1日）"),
]
# 住民基本台帳：年 → (総計 都道府県別, 日本人住民 都道府県別, 総計 都道府県別年齢階級別)
JUKI = {
    2014: ("000025710767", "000025710904", None), 2015: ("000030438567", "000030438531", None),
    2016: ("000031429217", "000031429219", None), 2017: ("000031598550", "000031598540", None),
    2018: ("000031736911", "000031736915", None), 2019: ("000031843906", "000031843910", None),
    2020: ("000031971201", "000031971211", "000031971202"), 2021: ("000040306655", "000040306663", "000040306657"),
    2022: ("000032224634", "000032224638", None), 2023: ("000040306645", "000040306649", None),
    2024: ("000040306668", "000040306675", "000040306670"), 2025: ("000040306651", "000040306656", "000040306652"),
    2026: ("000040479047", "000040479051", None),
}


def get(sid, kind):
    req = urllib.request.Request(ES.format(sid, kind), headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=180) as r:
        b = r.read()
    time.sleep(1)
    return b


def save(stem, b):
    ext = ".xls" if b[:4] == b"\xd0\xcf\x11\xe0" else ".xlsx"
    (RAW / (stem + ext)).write_bytes(b)
    return stem + ext


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "URL の形：https://www.e-stat.go.jp/stat-search/file-download?statInfId=<statInfId>&fileKind=<0 または 4>", "",
             "| ファイル | 中身 | statInfId | fileKind | sha256 の先頭12字 |", "|---|---|---|---|---|"]
    for stem, sid, kind, desc in SUIKEI:
        b = get(sid, kind); name = save(stem, b)
        lines.append(f"| {name} | {desc} | {sid} | {kind} | {hashlib.sha256(b).hexdigest()[:12]} |")
    for y, (tot, jp, age) in JUKI.items():
        for stem, sid, desc in [(f"juki_total_{y}", tot, f"住民基本台帳 {y}年1月1日 【総計】都道府県別人口、人口動態及び世帯数"),
                                (f"juki_japanese_{y}", jp, f"住民基本台帳 {y}年1月1日 【日本人住民】都道府県別人口、人口動態及び世帯数"),
                                (f"juki_age_{y}", age, f"住民基本台帳 {y}年1月1日 【総計】都道府県別年齢階級別人口")]:
            if sid is None:
                continue
            b = get(sid, 0); name = save(stem, b)
            lines.append(f"| {name} | {desc} | {sid} | 0 | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 人口推計の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200524&tstat=000000090001",
              "- 住民基本台帳に基づく人口の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200241&tstat=000001039591",
              "", "出典：総務省統計局「人口推計」、総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
