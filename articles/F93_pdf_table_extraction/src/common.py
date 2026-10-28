"""F93 共通：パス・表の定義・数の取り出し・図の体裁"""
from pathlib import Path
import logging, warnings, re, unicodedata, json
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
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
GT, EXT = DATA / "ground_truth", DATA / "extracted"
FIG, RES = ROOT / "figures", ROOT / "results"
for d in (GT, EXT, FIG, RES): d.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#8a5cc2", "#d64545"
SEED = 20261028
SOURCE = "出典：厚生労働省「新規学卒就職者の離職状況」、総務省統計局「労働力調査 標本抽出方法、結果の推定方法及び推定値の標本誤差」をもとに作成者が加工して作成"

# 4つの表：PDF・ページ（0始まり）・1行の数の個数・説明
TABLES = {
    "T1": dict(pdf="mhlw_education.pdf", pages=[0], ncol=[9], name="学歴別の離職（縦に長い表・罫線あり）"),
    "T2": dict(pdf="mhlw_industry_univ.pdf", pages=list(range(6)), ncol=[16, 9], name="大卒の産業別の離職（横に広い表・6ページ）"),
    "T3": dict(pdf="mhlw_size_univ.pdf", pages=[0], ncol=[15], name="大卒の規模別の離職（数と率が交互）"),
    "T4": dict(pdf="stat_lfs_method.pdf", pages=[2], ncol=[5], name="労働力調査の基準切替の段差（符号つき・罫線なし）"),
}
SHORT = {"T1": "T1 学歴別", "T2": "T2 産業別", "T3": "T3 規模別", "T4": "T4 符号つき"}

# 行の見出しにある数（年・月など）は表の値ではないので、数を取り出す前に消す
LABEL_RE = [r"(平成|令和|昭和)\s*(\d+|元)\s*年\s*\d*\s*月?\s*卒?", r"\d{4}\s*年\s*\d+\s*月\s*切替え?", r"\(\d{4}\s*年[^)]*\)",
            r"（\d{4}\s*年[^）]*）", r"[１２３123]\s*年目(まで)?", r"[①②③]", r"\d+\s*人(未満|以上)?", r"\d+\s*[～~]\s*\d+\s*人"]

def nk(s):
    return unicodedata.normalize("NFKC", str(s)) if s is not None else ""

def numbers(text, careful=True, signs=True):
    """セル（または行）の文字列から数を順に取り出す。'-' は欠測（nan）。
    careful=True：全角を半角にし、符号と数のあいだの空白を詰め、桁区切りのカンマを外す。
    signs=True：「－ 4」を -4 と読む。表によっては「-」が秘匿・該当なしの記号で、「- 675」は「欠測、675」なので、
    符号を持たない表（T1〜T3）では signs=False で読む（03b_評価.py 参照）。
    careful=False：そのまま半角の数字だけを拾う（よくある素朴なやり方）。"""
    s = str(text) if text is not None else ""
    if careful:
        s = re.sub(r"[①②③]", " ", s)
        s = nk(s).replace("－", "-").replace("−", "-").replace("‐", "-")
        for r in LABEL_RE: s = re.sub(r, " ", nk(s))
        if signs: s = re.sub(r"([+\-])\s+(?=\d)", r"\1", s)
        else: s = re.sub(r"(?<![\w.])([+\-])(?=\s)", r" \1 ", s)
        toks = re.findall(r"[+\-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[+\-]?\d+(?:\.\d+)?|(?<![\w.])-(?![\w.])", s)
        out = []
        for t in toks:
            out.append(np.nan if t == "-" else float(t.replace(",", "")))
        return out
    for r in LABEL_RE: s = re.sub(r, " ", s)
    return [float(t) for t in re.findall(r"\d+(?:\.\d+)?", s)]

def note(fig, text=SOURCE):
    fig.text(0.01, -0.02, text, fontsize=8, color=GRAY, ha="left", va="top")
