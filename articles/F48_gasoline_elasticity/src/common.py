"""共通の設定（パス・フォント・乱数の種・出来事の日付）"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# 出来事（公表情報）
SUBSIDY_START = "2022-01"   # 燃料油価格激変緩和補助金の開始（2022年1月27日）
COVID = ("2020-03", "2021-12")  # コロナで移動が大きく落ちた期間（主分析では除外）
TAX_END = "2025-12"         # ガソリン暫定税率の廃止（2025年12月31日）
