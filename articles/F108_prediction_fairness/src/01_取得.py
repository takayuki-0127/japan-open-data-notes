"""データの取得：F03（地価）の特徴量表と F92（電力）の日次予測を、GitHub の各記事フォルダから取る
（元をたどると地価公示・国土数値情報・国勢調査、でんき予報・気象庁。取り方は F03・F22・F92 の README）"""
import shutil, urllib.request
from pathlib import Path
from common import RAW
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {"F03_features.csv": "F03_land_price_ml/data/features.csv",
         "F03_oof_lgbm.csv": "F03_land_price_ml/results/oof_lgbm.csv",
         "F92_pred_tokyo.csv": "F92_power_quantile_forecast/results/pred_tokyo.csv",
         "F92_tokyo.csv": "F92_power_quantile_forecast/data/tokyo.csv"}
LOCAL = Path(__file__).resolve().parents[2]   # 手元にほかの記事のフォルダがあればそれを使う
for name, rel in FILES.items():
    out = RAW / name
    if out.exists():
        continue
    if (LOCAL / rel).exists():
        shutil.copy(LOCAL / rel, out)
    else:
        urllib.request.urlretrieve(BASE + rel, out)
    print(name, out.stat().st_size)
