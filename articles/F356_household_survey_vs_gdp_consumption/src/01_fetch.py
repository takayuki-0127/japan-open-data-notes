"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
QE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/{}.csv"
FILES = {
    "kakei_two_plus_usage_monthly_2000_2026.xlsx": (ES.format("000040270657", 4), "家計調査 長期時系列 表2 用途分類（二人以上の世帯、月・年）"),
    "kakei_total_households_items_2000_2025.csv": (ES.format("000040270663", 1), "家計調査 長期時系列 表5 総世帯 品目分類（年、2000年〜）"),
    "esri_qe2026q2_2nd_gaku-mcy2622.csv": (QE.format("gaku-mcy2622"), "四半期別GDP速報 2026年4-6月期2次速報 名目暦年"),
    "esri_qe2026q2_2nd_gaku-jcy2622.csv": (QE.format("gaku-jcy2622"), "四半期別GDP速報 2026年4-6月期2次速報 実質暦年"),
    "census_ts_households_t1_1960_2020_000001086170.xlsx": (ES.format("000001086170", 0), "国勢調査 時系列データ 世帯 第1表（1960〜2020年）"),
    "census_2025_t12-1_households_000040506465.xlsx": (ES.format("000040506465", 0), "令和7年国勢調査 人口等基本集計 第12-1表 一般世帯数"),
    "census_2025_t12-2_members_000040506466.xlsx": (ES.format("000040506466", 0), "令和7年国勢調査 人口等基本集計 第12-2表 一般世帯人員"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：総務省「家計調査」「国勢調査」（e-Stat）、内閣府「四半期別GDP速報」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
