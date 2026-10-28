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

# F18 と同じ20系列：名前, 公表の遅れ（月）, 分類
#   公表の遅れ L = その月末の時点で、L か月前の値まで出ている、とみなす（F18 と同じ）
SERIES = [
    ("鉱工業生産", 1, "一致"), ("生産財出荷", 1, "一致"), ("耐久消費財出荷", 1, "一致"),
    ("労働投入量", 2, "一致"), ("投資財出荷", 1, "一致"), ("小売販売額（前年比）", 1, "一致"),
    ("卸売販売額（前年比）", 1, "一致"), ("有効求人倍率", 1, "一致"), ("輸出数量", 1, "一致"),
    ("在庫率（最終需要財）", 1, "先行"), ("在庫率（生産財）", 1, "先行"), ("新規求人数", 1, "先行"),
    ("機械受注", 2, "先行"), ("住宅着工床面積", 1, "先行"), ("消費者態度指数", 0, "先行"),
    ("日経商品指数", 0, "先行"), ("マネーストック（前年比）", 1, "先行"), ("株価（TOPIX）", 0, "先行"),
    ("長期金利", 0, "先行"), ("完全失業率", 1, "一致"),
]
LAG = {s[0]: s[1] for s in SERIES}
ALL = [s[0] for s in SERIES]
COIN = [s[0] for s in SERIES if s[2] == "一致"]
VNAMES = ["1か月目", "2か月目", "3か月目", "翌月"]
