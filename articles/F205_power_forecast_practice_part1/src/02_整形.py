# F22 の1時間ごとのデータから、需要の2列だけを抜き出す（F22 のフォルダが隣にある前提）
import pandas as pd
from pathlib import Path
B = Path(__file__).resolve().parents[1]
src = B.parent/"F22_power_demand_forecast"/"data"/"hourly_tokyo.csv"
pd.read_csv(src, usecols=["ts", "demand"]).to_csv(B/"data"/"hourly_tokyo_demand.csv", index=False)
