"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「地方公務員給与実態調査」地方公共団体別給与等の比較 (1) ラスパイレス指数（e-Stat）と、住民基本台帳人口 2025年。"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
IDS = {2008: ("000007375621", "000007375622", "000007375623"), 2013: ("000026411760", "000026411761", "000026411762"),
       2018: ("000031815931", "000031815932", "000031815933"), 2025: ("000040442229", "000040442230", "000040442231")}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    files = []
    for y, ids in IDS.items():
        for kind, sid in zip(["pref", "seirei", "muni"], ids):
            files.append((f"laspeyres_{y}_{kind}", ES.format(sid), f"{y}年 地方公共団体別給与等の比較 ラスパイレス指数（{ {'pref': '都道府県', 'seirei': '指定都市', 'muni': '市区町村'}[kind] }）"))
    files.append(("jukijin_2025_municipal.xlsx", ES.format("000040306653"), "住民基本台帳に基づく人口 2025年1月1日 市区町村別人口"))
    for name, url, desc in files:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        if "." not in name:  # 中身で拡張子を決める（xlsx は zip で、先頭が PK）
            name += ".xlsx" if b[:2] == b"PK" else ".xls"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["",
              "出典：総務省「地方公務員給与実態調査」「住民基本台帳に基づく人口、人口動態及び世帯数調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
