"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 経済産業省「特定サービス産業動態統計調査」長期データ 結婚式場業（2000〜2014年の旧様式、2015〜2024年の新様式）（e-Stat）
- 厚生労働省「人口動態統計」（確定数、令和7年）上巻 婚姻 第9.5表 夫妻の初婚－再婚の組合せ別 年次別婚姻件数（e-Stat）
- 総務省「消費者物価指数」2025年基準 全国 中分類指数（月次、e-Stat）
"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
FILES = [
    ("tokusabi_wedding_2000_2014.xls", "特定サービス産業動態統計調査 長期データ 25表 結婚式場業（年・年度・四半期・月の実数と伸び率、2000年1月〜2014年12月）", E.format("000025667643", 0)),
    ("tokusabi_wedding_2015_2024.xls", "特定サービス産業動態統計調査 長期データ（平成27年調査から）結婚式場業（年・年度・四半期・月の実数と伸び率、2015年1月〜2024年12月）", E.format("000028878170", 0)),
    ("vs2025_t9_5_marriage_first_re.csv", "人口動態統計（確定数、令和7年）上巻 婚姻 第9.5表 夫妻の初婚－再婚の組合せ別にみた年次別婚姻件数及び百分率（1952〜2025年）", E.format("000040503697", 1)),
    ("cpi_2025base_middle_class_monthly.csv", "消費者物価指数 2025年基準 全国 中分類指数（月次、1970年1月〜、cp932）", E.format("000040482943", 1)),
]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト |", "|---|---|---|---|---|"]
    for name, desc, url in FILES:
        b = get(url)
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        time.sleep(0.5)
    lines += ["",
              "- 特定サービス産業動態統計調査のファイル一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550530（長期データは2024年12月分の確報（2025-03-19公表）が最後）",
              "- 人口動態統計：https://www.e-stat.go.jp/stat-search/files?toukei=00450011",
              "- 消費者物価指数：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876",
              "",
              "出典：経済産業省「特定サービス産業動態統計調査」、厚生労働省「人口動態統計」、総務省統計局「消費者物価指数」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
