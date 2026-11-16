"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
経済産業省「特定サービス産業動態統計調査」長期データ（平成27年調査から）情報サービス業（e-Stat の Excel）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000028875875&fileKind=0"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=120) as r:
        b = r.read()
    (RAW / "tokusabi_info_service_long.xls").write_bytes(b)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|",
             f"| tokusabi_info_service_long.xls | 特定サービス産業動態統計調査 長期データ 表2 情報サービス業（1988〜2024年。年・年度・四半期・月の実数と伸び率。2025-03-19 公開） | {URL} | {hashlib.sha256(b).hexdigest()[:12]} |",
             "", "- 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550050&tstat=000001014007",
             "", "出典：経済産業省「特定サービス産業動態統計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
