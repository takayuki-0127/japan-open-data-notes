"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
厚生労働省「就労条件総合調査」各年の「産業・企業規模、年間休日総数階級別適用労働者割合及び労働者１人平均年間休日総数」
（2002〜2025年の調査、各年1月1日現在。e-Stat の Excel）。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
IDS = {2002: ("000002021320", 0), 2003: ("000002018064", 0), 2004: ("000002015081", 0), 2005: ("000002012906", 0),
       2006: ("000001211486", 0), 2007: ("000001211129", 0), 2008: ("000002042597", 0), 2009: ("000008315389", 0),
       2010: ("000008549747", 0), 2011: ("000012674011", 0), 2012: ("000018609703", 0), 2013: ("000023628204", 0),
       2014: ("000028691899", 0), 2015: ("000031362357", 0), 2016: ("000031605919", 0), 2017: ("000031692594", 0),
       2018: ("000031778233", 0), 2019: ("000031898906", 0), 2020: ("000032034520", 4), 2021: ("000040009052", 4),
       2022: ("000040013088", 4), 2023: ("000040149748", 4), 2024: ("000040260714", 4), 2025: ("000040425672", 4)}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, (sid, kind) in IDS.items():
        url = EST.format(sid, kind)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        ext = "xls" if b[:4] == b"\xd0\xcf\x11\xe0" else "xlsx"
        name = f"holidays_worker_{y}.{ext}"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 就労条件総合調査 {y}年 産業・企業規模、年間休日総数階級別適用労働者割合及び労働者1人平均年間休日総数 | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "- 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450099&tstat=000001014004",
              "", "出典：厚生労働省「就労条件総合調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
