"""元データの取得（ネットが必要。run_all.sh からは呼ばない）。
総務省「消費者物価指数」2025年基準 全国 長期時系列（e-Stat）を data/raw に保存する。
年の値は年平均（暦年）の表を使う（年度平均の表 000040482959・000040482958 などは使わない）。"""
import hashlib, pathlib, urllib.request, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
FILES = {
    "cpi2025_item_monthly.csv": "000040482945",       # 品目別価格指数（月次）
    "cpi2025_goods_services_monthly.csv": "000040482946",  # 財・サービス分類指数（月次）
    "cpi2025_item_annual_cy.csv": "000040482831",      # 品目別価格指数（年平均＝暦年）
    "cpi2025_goods_services_annual_cy.csv": "000040482832",  # 財・サービス分類指数（年平均＝暦年）
}
for name, sid in FILES.items():
    with urllib.request.urlopen(E.format(sid), timeout=180) as r:
        b = r.read()
    (RAW / name).write_bytes(b)
    print(datetime.date.today(), name, sid, len(b), hashlib.sha256(b).hexdigest()[:12])
