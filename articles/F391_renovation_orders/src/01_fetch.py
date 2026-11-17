"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 国土交通省「建築物リフォーム・リニューアル調査」年度計の公表資料（2016〜2025年度）
- 国土交通省「建築着工統計調査」構造別・用途別・都道府県別（年度、昭和63年度〜令和7年度）
- 国土交通省「建設工事費デフレーター（2020年度基準）」年度別
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [(f"reform_fy{y}", sid, f"建築物リフォーム・リニューアル調査 {y}年度計 公表資料") for y, sid in [
    (2016, "000031598387"), (2017, "000031732677"), (2018, "000031840843"), (2019, "000031955043"), (2020, "000032094530"),
    (2021, "000032206995"), (2022, "000040066960"), (2023, "000040186361"), (2024, "000040283867"), (2025, "000040463576")]]
FILES += [("starts_fy_struct_use_pref", "000040451302", "建築着工統計調査 【建築物】構造別 用途別 都道府県別（年度、昭和63年度〜令和7年度）"),
          ("deflator_fy2020base", "000040459205", "建設工事費デフレーター（2020年度基準）時系列（年度別）")]


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
    rows += ["", "出典：国土交通省「建築物リフォーム・リニューアル調査」「建築着工統計調査」「建設工事費デフレーター」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
