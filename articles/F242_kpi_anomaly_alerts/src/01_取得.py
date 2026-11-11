"""01 取得：F22 のフォルダにある東京・関西の1時間ごとの電力需要（気温・祝日つき）を読む。
新しい取得はしない（F22 の data/hourly_tokyo.csv・hourly_kansai.csv を使う）。
手元に F22 のフォルダがなければ GitHub から取り直す。"""
import os, urllib.request
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F22_power_demand_forecast/data/"
LOCAL = os.path.join(os.path.dirname(__file__), "..", "..", "F22_power_demand_forecast", "data")
os.makedirs("data/raw", exist_ok=True)
for f in ["hourly_tokyo.csv", "hourly_kansai.csv"]:
    dst = os.path.join("data/raw", f)
    src = os.path.join(LOCAL, f)
    if os.path.exists(src):
        import shutil; shutil.copy(src, dst)
    else:
        urllib.request.urlretrieve(BASE + f, dst)
    print(f, os.path.getsize(dst))
