"""共通の設定（パス・フォント・統計表ID・年齢の区分）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(exist_ok=True)

# 家計調査 詳細結果表 年次 第3-2表「世帯主の年齢階級別」（二人以上の世帯・勤労者世帯）
STAT_IDS_3_2 = {
    2008: "000002209380", 2009: "000007370316", 2010: "000008635815", 2011: "000012687856",
    2012: "000019023706", 2013: "000023621361", 2014: "000028352450", 2015: "000031370116",
    2016: "000031534679", 2017: "000031674321", 2018: "000031795455", 2019: "000031909542",
    2020: "000032048822", 2021: "000032167618", 2022: "000040015248", 2023: "000040140545",
    2024: "000040247076", 2025: "000040409533",
}
# 家計調査 長期時系列 品目分類（小分類まで）支出金額（月）2000年1月〜（F11 と同じ）
STAT_ID_LONG = "000040270646"
# 消費者物価指数 2020年基準 中分類 月次（F12 と同じ）
STAT_ID_CPI = "000032103842"

# どの年にもある「再掲」の6区分（世帯主の年齢）
AGE6 = ["～29歳", "30～39", "40～49", "50～59", "60～69", "70歳～"]
AGE6_LABEL = ["29歳以下", "30代", "40代", "50代", "60代", "70歳以上"]


def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "Noto Sans CJK" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
