"""共通：パス・乱数の種・変数の定義"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SEED = 20261028
T = "commute_out"   # 処置：市区町村外への通勤・通学の割合（%）
Y = "tfr"           # 結果：合計特殊出生率
X = ["young_f", "income", "tertiary", "density", "aged", "nursery"]  # 条件（県ダミーは別に足す）
GRID = list(range(10, 66, 5))   # 用量反応曲線を描く処置の値（%）
LO, HI = 20, 50                 # 「20% の町と 50% の町」の差を主な比較にする
