"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「家計調査」二人以上の世帯 詳細結果表 第3-12表（高齢者のいる世帯）世帯主の就業状態別（月別、2015年1月〜2026年9月）、
長期時系列 表2 用途分類（二人以上の世帯、月）。いずれも e-Stat。
月別の表のファイル番号（statInfId）は src/ids_3_12.json（e-Stat のファイル検索で集めたもの）。"""
import pathlib, urllib.request, hashlib, datetime, time, json

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def main():
    (RAW / "t3_12").mkdir(parents=True, exist_ok=True)
    rows = []
    ids = json.loads((ROOT / "src" / "ids_3_12.json").read_text())
    for ym, i in ids.items():
        b = get(E.format(i, 0))
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        name = f"t3_12/kakei_3-12_{ym}.{ext}"
        (RAW / name).write_bytes(b)
        rows.append((name, f"家計調査 二人以上の世帯 第3-12表（高齢者のいる世帯）世帯主の就業状態別 {ym}", E.format(i, 0), hashlib.sha256(b).hexdigest()[:12]))
        time.sleep(0.3)
    b = get(E.format("000040270657", 4))
    (RAW / "kakei_ts2_youto_monthly.xlsx").write_bytes(b)
    rows.append(("kakei_ts2_youto_monthly.xlsx", "家計調査 長期時系列 表2 用途分類（二人以上の世帯、月・四半期・年・年度、2000年〜）", E.format("000040270657", 4), hashlib.sha256(b).hexdigest()[:12]))
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", "出典：総務省統計局「家計調査（家計収支編）」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00200561）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
