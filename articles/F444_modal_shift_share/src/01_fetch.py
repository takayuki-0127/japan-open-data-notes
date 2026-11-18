"""元データを e-Stat から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
- 内航船舶輸送統計年報（年度）：第1表 推移表、第5表 大型鋼船の専用船等用途別（RORO船・コンテナ船）、2015〜2025年度
- 鉄道輸送統計年報（年度）：3-1-2 鉄道貨物輸送総括表（貨物トンキロ）、2020〜2024年度。2025年度は月報（2026年3月分）
- 自動車輸送統計月報：各年4月分の 総括表（１）輸送トン数・（２）輸送トンキロ、2021〜2026年"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
SHIP = {  # 年度: (第1表 推移表, 第5表 大型鋼船品目別専用船等用途別輸送実績)
    2015: ("000031480029", "000031480034"), 2016: ("000031609552", "000031609557"), 2017: ("000031733141", "000031733146"),
    2018: ("000031842631", "000031842636"), 2019: ("000031959409", "000031959414"), 2020: ("000032109882", "000032109887"),
    2021: ("000032211557", "000032211562"), 2022: ("000040077009", "000040077014"), 2023: ("000040188705", "000040188710"),
    2024: ("000040290054", "000040290059"), 2025: ("000040470456", "000040470461"),
}
RAIL = {2020: "000032120280", 2021: "000032233979",
        2022: "000040130719", 2023: "000040222237", 2024: "000040366700"}
RAIL_MONTHLY = {"202603": "000040463728"}
TRUCK = {  # 自動車輸送統計月報 各年4月分の 総括表（１）輸送トン数・（２）輸送トンキロ
    2021: ("000032124998", "000032124999"), 2022: ("000032218539", "000032218540"), 2023: ("000040081521", "000040081522"),
    2024: ("000040198041", "000040198042"), 2025: ("000040304566", "000040304567"), 2026: ("000040527076", "000040527077"),
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def save(name_base, sid, desc, lines):
    url = BASE.format(sid, 0)
    b = get(url)
    ext = "xlsx" if b[:2] == b"PK" else "xls"
    name = f"{name_base}.{ext}"
    (RAW / name).write_bytes(b)
    lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print("saved", name, len(b))


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for fy, (t1, t5) in SHIP.items():
        save(f"ship_{fy}_t1", t1, f"内航船舶輸送統計年報 {fy}年度 第1表 内航船舶輸送統計推移表", lines)
        save(f"ship_{fy}_t5", t5, f"内航船舶輸送統計年報 {fy}年度 第5表 大型鋼船品目別専用船等用途別輸送実績（営業用）", lines)
    for fy, sid in RAIL.items():
        save(f"rail_{fy}_tkm", sid, f"鉄道輸送統計年報 {fy}年度 3-1-2 鉄道貨物輸送総括表（２）貨物トンキロ", lines)
    for ym, sid in RAIL_MONTHLY.items():
        save(f"rail_m{ym}", sid, f"鉄道輸送統計月報 {ym[:4]}年{int(ym[4:])}月分 3-1 鉄道貨物輸送総括表", lines)
    for y, (ton, tkm) in TRUCK.items():
        save(f"truck_ton_{y}04", ton, f"自動車輸送統計月報 {y}年4月分 総括表（１）輸送トン数の推移", lines)
        save(f"truck_tonkm_{y}04", tkm, f"自動車輸送統計月報 {y}年4月分 総括表（２）輸送トンキロの推移", lines)
    lines += ["", "- 内航船舶輸送統計調査：https://www.e-stat.go.jp/stat-search/files?toukei=00600340&tstat=000001018595",
              "- 鉄道輸送統計調査：https://www.e-stat.go.jp/stat-search/files?toukei=00600350&tstat=000001011026",
              "- 自動車輸送統計調査：https://www.e-stat.go.jp/stat-search/files?toukei=00600330&tstat=000001017236",
              "- いずれも国土交通省の統計を、政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
