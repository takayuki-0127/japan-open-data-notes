"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
財務省 財務総合政策研究所「法人企業統計調査」四半期別調査の時系列データ（全項目、Excel）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = [
    ("mof_ssc_quarterly_all.xls", "https://www.mof.go.jp/english/pri/reference/ssc/historical/all.xls",
     "法人企業統計調査 四半期別調査 時系列データ「All items」（全項目。設備投資・ソフトウェア・減価償却費・有形固定資産などを含む。億円、原数値、1954年4-6月期〜2026年4-6月期）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        print(name, len(b))
    rows += ["",
             "- 掲載ページ（英語版の時系列データ）：https://www.mof.go.jp/english/pri/reference/ssc/historical.htm",
             "  （日本語版の同じページ https://www.mof.go.jp/pri/reference/ssc/historical.htm は 2026-11-18 に 404 だった。数値は同じ調査の時系列表）",
             "- 規模の区分：A 全規模、B 資本金10億円以上、C 1億円以上10億円未満、D 1千万円以上1億円未満（掲載ページの注記による）",
             "- 業種：全産業（金融業・保険業を除く）、製造業、非製造業（金融業・保険業を除く）、全産業（金融業・保険業を含む）、金融業・保険業",
             "", "出典：財務省「法人企業統計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
