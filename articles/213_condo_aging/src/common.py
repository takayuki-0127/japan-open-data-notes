"""共通：厚生労働省「介護保険事業状況報告（年報）」全国計の要介護（要支援）認定者数（年度末現在）"""
from pathlib import Path
import logging, warnings
import pandas as pd
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
DATA = ROOT / "data"; FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：国土交通省「マンション総合調査」（平成30年度・令和5年度、e-Stat）をもとに作成者が加工して作成"
ERAS = ["～昭和54年", "～昭和59年", "～平成元年", "～平成６年", "～平成11年", "～平成16年", "～平成21年", "～平成26年"]
# 完成年次の区分の最後の年（西暦）
ERA_END = {"昭和44年以前": 1969, "昭和49年以前": 1974, "～昭和49年": 1974, "～昭和54年": 1979, "～昭和59年": 1984, "～平成元年": 1989, "～平成６年": 1994,
           "～平成11年": 1999, "～平成16年": 2004, "～平成21年": 2009, "～平成26年": 2014, "平成27年以降": 2018, "～令和元年": 2019, "令和２年以降": 2023}


def sections():
    txt = (DATA / "mansion_survey_extract_2018_2023.txt").read_text(encoding="utf-8")
    out = {}
    for blk in txt.split("### ")[1:]:
        name, body = blk.split("\n", 1)
        out[name.strip()] = body
    return out


def era_rows(body, start_label="完成年次別", value_line="first", ncol=None):
    """完成年次別の行（区分名, 数値リスト）。value_line='pct' は回答数の次の行（％）を返す"""
    lines = body.split("\n"); res = {}; on = False
    for i, l in enumerate(lines):
        c = l.split(",")
        if c[0] == start_label: on = True
        elif on and c[0] and c[0] != start_label: break
        if on and len(c) > 1 and c[1] in ERA_END:
            row = lines[i + 1].split(",") if value_line == "pct" else c
            vals = [x for x in row[2:] if x != ""] if value_line != "pct" else [x for x in row[3:] if x != ""]
            res[c[1]] = [float(x.replace("-", "0").replace('"', "")) for x in vals][:ncol]
    return res
