"""共通の設定（パス・フォント・年齢区分・都道府県名）"""
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
YEARS = [2000, 2005, 2010, 2015, 2020]

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

PREF = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京",
        "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都",
        "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知",
        "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]

# 年齢区分（本体）。分解の結果をこの区分で足し上げる
BANDS = [(0, 0, "0歳"), (1, 14, "1〜14歳"), (15, 39, "15〜39歳"), (40, 64, "40〜64歳"),
         (65, 74, "65〜74歳"), (75, 84, "75〜84歳"), (85, 200, "85歳以上")]
BAND_COLORS = ["#8c564b", "#e377c2", "#bcbd22", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"]
