"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「国勢調査」時系列データ 第5表（産業大分類×都道府県、2005〜2020年）と、
総務省・経済産業省「令和3年経済センサス‐活動調査」速報集計 第2-2表（産業大分類×都道府県の民営事業所の従業者数）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
B = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("census_ts_t05_industry_pref.xlsx", "000040119873", "国勢調査 時系列データ 第5表 産業（大分類），男女別就業者数及び人口構成比（15歳以上就業者）－都道府県（2005〜2020年、常住地）"),
    ("ecensus2021_t2_2_pref.xlsx", "000032203468", "令和3年経済センサス‐活動調査 速報集計 第2-2表 産業(大分類)別民営事業所数・従業者数－全国、都道府県（2021年6月1日、事業所の所在地）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = B.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 国勢調査 時系列データ：https://www.e-stat.go.jp/stat-search/files?toukei=00200521&tstat=000001011777",
              "- 令和3年経済センサス‐活動調査：https://www.e-stat.go.jp/stat-search/files?toukei=00200553&tstat=000001145590",
              "", "出典：総務省「国勢調査」、総務省・経済産業省「経済センサス‐活動調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
