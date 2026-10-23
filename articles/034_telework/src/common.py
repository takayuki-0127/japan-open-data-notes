"""共通：通信利用動向調査（世帯構成員編）の統計表を読む"""
from pathlib import Path
import logging, warnings, re
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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：総務省「通信利用動向調査」（令和7年、世帯構成員編）（e-Stat）をもとに作成者が加工して作成"


def read_table(sheet, path=RAW / "r7_kosein.xls", header_rows=(6, 7, 8)):
    """割合の表（前半のブロック）を、行＝属性・列＝選択肢の DataFrame にする"""
    d = pd.read_excel(path, sheet_name=sheet, header=None)
    lab = d[2].astype(str).str.replace("　", "").str.strip()
    end = lab[lab.str.contains("回答数")].index.min()
    body = d.iloc[10:end]
    names = []
    for c in range(5, d.shape[1] - 1):
        parts = [str(d.iat[r, c]).replace("\n", "") for r in header_rows if str(d.iat[r, c]) != "nan"]
        names.append(parts[-1] if parts else f"col{c}")
    out = body.iloc[:, 5:d.shape[1] - 1].apply(pd.to_numeric, errors="coerce")
    out.columns = names
    out.insert(0, "label", lab.loc[body.index].values)
    # 区分（[ 本人の性別・年齢 ] など）と、男女計／男性／女性 を付ける
    sec, sex, secs, sexes = None, None, [], []
    for l in out.label:
        if l.startswith("[") or l.startswith("［"): sec = l.strip("[]［］ ")
        if l in ("男女計：", "男性：", "女性："): sex = l.strip("：")
        secs.append(sec); sexes.append(sex if sec == "本人の性別・年齢" else None)
    out["section"], out["sex"] = secs, sexes
    return out.dropna(subset=[names[0]])


def z2h(s):
    return s.translate(str.maketrans("０１２３４５６７８９～", "0123456789〜"))
