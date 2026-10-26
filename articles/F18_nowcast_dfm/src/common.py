"""共通の設定（パス・フォント・乱数の種・系列の定義）"""
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

# 月次の系列：名前, 景気動向指数のファイル, 列, 変換, 公表の遅れ（月）, 分類
#   変換 dlog = 前月比（対数差×100）, diff = 前月差, level = そのまま（すでに前年比のもの）
#   公表の遅れ L = その月末の時点で、L か月前の値まで出ている、とみなす（おおよその公表日から決めた）
SERIES = [
    ("鉱工業生産",           "ci2", 3,  "dlog", 1, "一致"),
    ("生産財出荷",           "ci2", 4,  "dlog", 1, "一致"),
    ("耐久消費財出荷",       "ci2", 5,  "dlog", 1, "一致"),
    ("労働投入量",           "ci2", 6,  "dlog", 2, "一致"),
    ("投資財出荷",           "ci2", 7,  "dlog", 1, "一致"),
    ("小売販売額（前年比）", "ci2", 8,  "level", 1, "一致"),
    ("卸売販売額（前年比）", "ci2", 9,  "level", 1, "一致"),
    ("有効求人倍率",         "ci2", 11, "diff", 1, "一致"),
    ("輸出数量",             "ci2", 12, "dlog", 1, "一致"),
    ("在庫率（最終需要財）", "ci1", 3, "dlog", 1, "先行"),
    ("在庫率（生産財）", "ci1", 4,  "dlog", 1, "先行"),
    ("新規求人数",           "ci1", 5,  "dlog", 1, "先行"),
    ("機械受注",             "ci1", 6,  "dlog", 2, "先行"),
    ("住宅着工床面積",       "ci1", 7,  "dlog", 1, "先行"),
    ("消費者態度指数",       "ci1", 8,  "diff", 0, "先行"),
    ("日経商品指数",         "ci1", 9,  "dlog", 0, "先行"),
    ("マネーストック（前年比）", "ci1", 10, "level", 1, "先行"),
    ("株価（TOPIX）",        "ci1", 11, "dlog", 0, "先行"),
    ("長期金利",             "ci1", 14, "diff", 0, "先行"),
    ("完全失業率",           "f13", "u_sa", "diff", 1, "一致"),
]
GDP_NAME = "実質GDP（前期比）"
START = "1994-01-01"
EOF_MARK = None
