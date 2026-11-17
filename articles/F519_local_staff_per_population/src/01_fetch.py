"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「地方公共団体定員管理調査」団体別の部門別職員数（市町村・指定都市、2020年・2025年4月1日）と、
総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」市区町村別人口（2020年・2025年1月1日）。e-Stat の Excel。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [("teiin_2025_municipal.xlsx", "000040421371", 4, "定員管理調査 2025年 市町村 部門別職員数"),
         ("teiin_2025_designated.xlsx", "000040421370", 4, "定員管理調査 2025年 指定都市 部門別職員数"),
         ("teiin_2020_municipal.xlsx", "000032067814", 4, "定員管理調査 2020年 市区町村 部門別職員数"),
         ("teiin_2020_designated.xlsx", "000032067813", 4, "定員管理調査 2020年 指定都市 部門別職員数"),
         ("jukijin_2025_municipal.xlsx", "000040306653", 0, "住民基本台帳 2025年1月1日 【総計】市区町村別人口、人口動態及び世帯数"),
         ("jukijin_2020_municipal.xls", "000031971203", 0, "住民基本台帳 2020年1月1日 【総計】市区町村別人口、人口動態及び世帯数")]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, k, desc in FILES:
        url = E.format(sid, k)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        stem = name.rsplit(".", 1)[0]
        ext = "xls" if b[:4] == b"\xd0\xcf\x11\xe0" else "xlsx"
        name = f"{stem}.{ext}"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 地方公共団体定員管理調査：https://www.e-stat.go.jp/stat-search/files?toukei=00200216",
              "- 住民基本台帳に基づく人口、人口動態及び世帯数調査：https://www.e-stat.go.jp/stat-search/files?toukei=00200241&tstat=000001039591",
              "", "出典：総務省「地方公共団体定員管理調査」「住民基本台帳に基づく人口、人口動態及び世帯数調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
