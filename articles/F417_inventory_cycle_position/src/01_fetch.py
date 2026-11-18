"""元データを取る（run_all.sh では呼ばない）。
経済産業省「鉱工業生産・出荷・在庫指数」は経済産業省のサイトが 403 を返すため、e-Stat の掲載ファイルを使う。
景気の山・谷は内閣府経済社会総合研究所「景気基準日付」のページ（HTML）を保存する。"""
import hashlib, pathlib, urllib.request, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("iip_b2010_q_gyoshu_gen.xls", "000031357780", "2010年基準 業種別／四半期、年、年度／原指数（2008年〜2018年）"),
    ("iip_b2015_q_gyoshu_gen.xlsx", "000031766144", "2015年基準 業種別／四半期、年、年度／原指数（2013年〜2023年）"),
    ("iip_b2020_q_gyoshu_gen.xlsx", "000040172370", "2020年基準 業種別／四半期、年、年度／原指数（2018年〜）"),
    ("iip_b2010_m_gyoshu_gen.xls", "000031357569", "2010年基準 業種別／月次／原指数（2008年1月〜2018年）"),
    ("iip_b2015_m_gyoshu_gen.xlsx", "000031766137", "2015年基準 業種別／月次／原指数（2013年1月〜2023年）"),
    ("iip_b2020_m_gyoshu_gen.xlsx", "000040172364", "2020年基準 業種別／月次／原指数（2018年1月〜）"),
]
ESRI = ("esri_hiduke.html", "https://www.esri.cao.go.jp/jp/stat/di/hiduke.html", "内閣府経済社会総合研究所「景気基準日付」")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=120).read()


rows = []
for name, sid, desc in FILES:
    url = URL.format(sid)
    b = get(url)
    (RAW / name).write_bytes(b)
    rows.append(f"| {name} | 経済産業省「鉱工業生産・出荷・在庫指数」{desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print(name, len(b))
b = get(ESRI[1])
(RAW / ESRI[0]).write_bytes(b)
rows.append(f"| {ESRI[0]} | {ESRI[2]}（第1〜16循環の山・谷の月） | {ESRI[1]} | {hashlib.sha256(b).hexdigest()[:12]} |")
today = datetime.date.today().isoformat()
(RAW / "SOURCES.md").write_text(
    "# 元データ（取得日 " + today + "）\n\n"
    "経済産業省「鉱工業生産・出荷・在庫指数」は政府統計の総合窓口 e-Stat の掲載ファイル（経済産業省のサイトは 403 を返したため）。景気の山・谷は内閣府のページを保存した。\n\n"
    "| ファイル | 中身 | URL | sha256（先頭12桁） |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "- e-Stat の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550300&tstat=000001022877\n", encoding="utf-8")
