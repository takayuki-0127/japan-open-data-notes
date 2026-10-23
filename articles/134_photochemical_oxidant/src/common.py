"""共通：環境省「令和5年度 大気汚染状況報告書」の表を読む（PDF → 整えた CSV）"""
from pathlib import Path
import re, subprocess, logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, RAW, FIG, RES = ROOT / "data", ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：環境省「令和5年度 大気汚染状況報告書」（https://www.env.go.jp/air/osen/report/r05report_00001.html）をもとに作成者が加工して作成"
ERA = {"S": 1925, "H": 1988, "R": 2018}
FILES = {"ch1": "134_r05_ch1_gaisetsu.pdf", "ch4": "134_r05_ch4_ox.pdf", "ch10": "134_r05_ch10_longterm.pdf"}


def year(tok):
    """'S52'→1977、'H1'→1989、'R5'→2023、'19H'（表の誤記）→2007"""
    tok = tok.strip()
    m = re.fullmatch(r"([SHR])(\d+)", tok) or re.fullmatch(r"(\d+)([SHR])", tok)
    if not m:
        return None
    e, n = (m.group(1), m.group(2)) if m.group(1) in ERA else (m.group(2), m.group(1))
    return ERA[e] + int(n)


def text(key):
    """pdftotext（poppler-utils）でレイアウトを保ったまま文字にする"""
    out = subprocess.run(["pdftotext", "-layout", str(RAW / FILES[key]), "-"], capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def nums(s):
    return [float(x.replace(",", "")) for x in re.findall(r"(?<![\w.])-?\d[\d,]*\.?\d*(?![\w])", s)]


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
