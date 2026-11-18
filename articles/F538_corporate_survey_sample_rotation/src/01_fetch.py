"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
財務省「法人企業統計調査」四半期別調査 時系列データ All items（英語版の時系列データのページ）。"""
import datetime, hashlib, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
URL = "https://www.mof.go.jp/english/pri/reference/ssc/historical/all.xls"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=180) as r:
        b = r.read()
    (RAW / "mof_ssc_quarterly_all.xls").write_bytes(b)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|",
             f"| mof_ssc_quarterly_all.xls | 法人企業統計調査 四半期別調査 時系列データ「All items」（全70項目。億円・人・社、原数値、1954年4-6月期〜2026年4-6月期） | {URL} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |",
             "",
             "- 掲載ページ（英語版の時系列データ）：https://www.mof.go.jp/english/pri/reference/ssc/historical.htm",
             "- 規模の区分（掲載ページの注記）：A 全規模、B 資本金10億円以上、C 1億円以上10億円未満、D 1千万円以上1億円未満",
             "- 標本の入れ替えの説明：財務省「法人企業統計調査の標本設計の見直しについて」（2009年6月25日）https://www.mof.go.jp/pri/reference/ssc/summary/hyohon.htm 、同 標本の入替え https://www.mof.go.jp/pri/reference/ssc/summary/hyohon/b00.htm",
             "- 公表の前年同期比との照合に使った資料：財務省「法人企業統計調査結果（令和8年4〜6月期）」https://www.mof.go.jp/pri/reference/ssc/results/r8.4-6.pdf",
             "", "出典：財務省「法人企業統計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
