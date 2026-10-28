"""F12 で取得した消費者物価指数（2020年基準、中分類、月次・原数値）を使う。
元は e-Stat「消費者物価指数 2020年基準 中分類指数（全国）」の長期時系列 CSV。"""
import urllib.request
from common import RAW
URL = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F12_stats_pipeline/data/raw/cpi.csv"
out = RAW / "cpi_2020base_chubunrui.csv"
if not out.exists():
    urllib.request.urlretrieve(URL, out)
print(out, out.stat().st_size)
