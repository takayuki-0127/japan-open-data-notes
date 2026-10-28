"""共通の設定（パス・フォント・単位の換算に使う定数）"""
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

# 換算に使う値（F01 のパネル 2008〜2019年の平均。02_整形.py で計算し直して確かめる）
EMP_RATE_MEAN = None   # 就業率の平均（%）
BITE_MEAN = None       # 最低賃金 ÷ 短時間労働者の平均時給（2015年）

# 海外の研究でよく報告される雇用の弾力性の目安（参考として図に帯で描くだけ。統合には入れない）
REF_BAND = (-0.3, 0.0)

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

COL = {"F01": "#1f77b4", "F15": "#2ca02c", "F17": "#d62728", "pool": "#333333"}
