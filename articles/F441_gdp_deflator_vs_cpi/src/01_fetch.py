"""元データの取得（ネットが必要。run_all.sh からは呼ばない）。
内閣府「四半期別GDP速報」2026年4-6月期2次速報の暦年の表（名目・実質・デフレーター）と、
総務省「消費者物価指数」2025年基準 全国 中分類指数（年平均＝暦年、000040482829）を data/raw に保存する。"""
import hashlib, pathlib, urllib.request, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
ESRI = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/"
FILES = {
    "esri_qe2026q2_2nd_gaku-mcy2622.csv": ESRI + "gaku-mcy2622.csv",
    "esri_qe2026q2_2nd_gaku-jcy2622.csv": ESRI + "gaku-jcy2622.csv",
    "esri_qe2026q2_2nd_def-cy2622.csv": ESRI + "def-cy2622.csv",
    "cpi2025_middle_annual_cy.csv": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482829&fileKind=1",
}
for name, url in FILES.items():
    with urllib.request.urlopen(url, timeout=120) as r:
        b = r.read()
    (RAW / name).write_bytes(b)
    print(datetime.date.today(), name, len(b), hashlib.sha256(b).hexdigest()[:12])
