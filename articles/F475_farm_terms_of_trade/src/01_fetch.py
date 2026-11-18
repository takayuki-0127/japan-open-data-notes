"""元データの取得（ネットにつなぐのはこのファイルだけ。run_all.sh からは呼ばない）。"""
import hashlib, pathlib, urllib.request, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "agri_products_class_index.xlsx": ("000040479235", "表1(1)ア 農産物 類別月別年次別価格指数（令和2年=100）"),
    "agri_products_weights.xlsx": ("000040479242", "表1(4) 農産物 品目別ウエイト"),
    "agri_inputs_class_index.xlsx": ("000040479243", "表2(1)ア 農業生産資材 類別月別年次別価格指数（令和2年=100）"),
    "agri_inputs_weights.xlsx": ("000040479250", "表2(4) 農業生産資材 品目別ウエイト"),
}
rows = []
for name, (sid, desc) in FILES.items():
    url = BASE.format(sid)
    with urllib.request.urlopen(url) as r:
        b = r.read()
    (RAW / name).write_bytes(b)
    rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
today = datetime.date.today().isoformat()
(RAW / "SOURCES.md").write_text(
    "# SOURCES（元データの取得元）\n\n"
    f"取得日：{today}（01_fetch.py で取得）\n\n"
    "| ファイル | 中身 | URL | sha256 の先頭12字 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "- 掲載ページ：農林水産省「農業物価統計調査」確報 令和7年（令和2年基準）https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist&lid=000001485296\n"
    "- 調査のページ：https://www.maff.go.jp/j/tokei/kouhyou/noubukka/index.html\n"
    "- 表の注：1994年以前の年平均は年度の指数、1995年以降は暦年の指数。\n\n"
    "出典：農林水産省「農業物価統計調査」。\n", encoding="utf-8")
print("\n".join(rows))
