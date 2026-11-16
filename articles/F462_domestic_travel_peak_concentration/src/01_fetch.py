"""観光庁「宿泊旅行統計調査」の推移表（Excel）を取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.mlit.go.jp/kankocho/content/002028776.xlsx"
PAGE = "https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=180) as r:
        b = r.read()
    (RAW / "shukuhaku_suiihyo.xlsx").write_bytes(b)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|",
             f"| shukuhaku_suiihyo.xlsx | 宿泊旅行統計調査 推移表（2026年9月分の公表時点の版。使うのはシート「旧2-2」都道府県別 日本人延べ宿泊者数 月別 2011年1月〜2025年12月、確定値） | {URL} | {hashlib.sha256(b).hexdigest()[:12]} |",
             "", f"- 掲載ページ：{PAGE}",
             "- 出典：観光庁「宿泊旅行統計調査」。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
             "- 2026年1月分から調査の層の分け方が変わったため、2026年の値（シート「2-1」）は使わない。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("saved", len(b))


if __name__ == "__main__":
    main()
