"""元データを e-Stat から取る（run_all.sh では呼ばない）。"""
import hashlib, pathlib, urllib.request, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("ec2021_soukatsu_t1.xlsx", "000040032840", "令和3年経済センサス‐活動調査 卸売業，小売業に関する集計 産業編（総括表）第1表 産業分類細分類別、年次別の事業所数（法人・個人別）、従業者数、年間商品販売額及び売場面積（1994〜2021年）"),
    ("ec2021_soukatsu_t9.xlsx", "000040032848", "同 第9表 小売業の産業分類細分類別、商品販売形態別の事業所数、年間商品販売額及び構成比（2021年）"),
    ("ec2021_hinmoku_t2.xlsx", "000040032866", "同 品目編 第2表 商品分類（小売）別事業所数及び年間商品販売額－全国、都道府県、市区、郡部（2021年）"),
    ("ec2021_hinmoku_t4.xlsx", "000040032868", "同 品目編 第4表 産業分類細分類、商品分類（小売）別事業所数及び年間商品販売額－全国（2021年）"),
    ("ec2016_soukatsu.xls", "000031676907", "平成28年経済センサス‐活動調査 卸売業，小売業に関する集計 産業編（総括表）（第1〜15表。第9表 小売業の産業分類細分類別、商品販売形態別（法人組織の事業所）を使う）"),
]
rows = []
for name, sid, desc in FILES:
    url = URL.format(sid)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    b = urllib.request.urlopen(req, timeout=180).read()
    (RAW / name).write_bytes(b)
    rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print(name, len(b))
today = datetime.date.today().isoformat()
(RAW / "SOURCES.md").write_text(
    "# 元データ（取得日 " + today + "）\n\n"
    "総務省・経済産業省「経済センサス‐活動調査」（政府統計の総合窓口 e-Stat の掲載ファイル）。\n\n"
    "| ファイル | 中身 | URL | sha256（先頭12桁） |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "- 令和3年経済センサス‐活動調査（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00200553&tstat=000001145590\n"
    "- 平成28年経済センサス‐活動調査（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00200553&tstat=000001095895\n", encoding="utf-8")
