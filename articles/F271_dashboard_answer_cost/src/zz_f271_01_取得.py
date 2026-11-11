"""F271 01 取得：F231 の商業動態統計（業態別・月次）を写す。新しい取得はしない。
元：articles/F231_sales_forecast_horizon/data/sales_monthly_6types.csv
（経済産業省「商業動態統計調査」業態別販売額、2014-01〜2026-08）
GitHub から取り直す場合は FROM_WEB=1 で raw を取得する。"""
import hashlib, os, shutil, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
dst = os.path.join(ROOT, "data", "raw", "sales_monthly_6types.csv")
os.makedirs(os.path.dirname(dst), exist_ok=True)
MD5 = "SEE_RESULTS"
if not os.path.exists(dst):
    src = os.path.join(ROOT, "..", "F231_sales_forecast_horizon", "data", "sales_monthly_6types.csv")
    if os.path.exists(src) and not os.environ.get("FROM_WEB"):
        shutil.copy(src, dst)
    else:
        url = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F231_sales_forecast_horizon/data/sales_monthly_6types.csv"
        urllib.request.urlretrieve(url, dst)
print("md5", hashlib.md5(open(dst, "rb").read()).hexdigest(), dst)
