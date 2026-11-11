# F259 01 取得：F231（同じリポジトリの articles/F231_sales_forecast_horizon、コミット 613a8c7）の
# 予測結果と元データをそのまま使う。新しい予測は作らない。
# 手元にない場合は GitHub から取る：
#   https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/613a8c7/articles/F231_sales_forecast_horizon/results/forecasts_main.csv.gz
#   https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/613a8c7/articles/F231_sales_forecast_horizon/data/sales_monthly_6types.csv
# 元の統計：経済産業省「商業動態統計調査」業態別の月次販売額（2014年1月〜2026年8月）
import os, shutil, sys, urllib.request
SRC = sys.argv[1] if len(sys.argv) > 1 else "../F231_sales_forecast_horizon"
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/613a8c7/articles/F231_sales_forecast_horizon/"
os.makedirs("data", exist_ok=True)
for rel, out in [("results/forecasts_main.csv.gz", "data/f231_forecasts_main.csv.gz"), ("data/sales_monthly_6types.csv", "data/sales_monthly_6types.csv")]:
    p = os.path.join(SRC, rel)
    if os.path.exists(p): shutil.copyfile(p, out)
    elif not os.path.exists(out): urllib.request.urlretrieve(BASE + rel, out)
    print(out, os.path.getsize(out))
