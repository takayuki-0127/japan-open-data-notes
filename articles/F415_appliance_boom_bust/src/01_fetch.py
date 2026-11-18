"""元データを e-Stat から取る（run_all.sh では呼ばない）。
経済産業省のサイト（www.meti.go.jp/statistics/）は 403 を返すため、e-Stat の掲載ファイルを使う。"""
import hashlib, pathlib, urllib.request, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("meti_index_by_business.xlsx", "000031387999", "商業動態統計 時系列データ 業種別商業販売額指数（2020年=100、原指数・季節調整済指数、月次、2002年1月〜）"),
    ("meti_appliance_stores.xlsx", "000031387996", "商業動態統計 時系列データ 家電大型専門店 商品別販売額等（月次、2014年1月〜）"),
    ("meti_sales_by_business.xlsx", "000031387992", "商業動態統計 時系列データ 業種別商業販売額（10億円、月次、1980年1月〜）"),
]
rows = []
for name, sid, desc in FILES:
    url = URL.format(sid)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    b = urllib.request.urlopen(req, timeout=120).read()
    (RAW / name).write_bytes(b)
    rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print(name, len(b))
today = datetime.date.today().isoformat()
(RAW / "SOURCES.md").write_text(
    "# 元データ（取得日 " + today + "）\n\n"
    "経済産業省「商業動態統計」（政府統計の総合窓口 e-Stat の掲載ファイル）。経済産業省のサイトは 403 を返したため e-Stat から取得した。\n\n"
    "| ファイル | 中身 | URL | sha256（先頭12桁） |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "- e-Stat の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550030\n", encoding="utf-8")
