"""F102 共通の設定と関数"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 102

VARS = ["imp", "fx", "ppi", "cpi"]  # Cholesky の順番（主設定）
LABELS = {
    "imp": "輸入物価（契約通貨）",
    "fx": "ドル円（円安が＋）",
    "ppi": "国内企業物価",
    "cpi": "消費者物価（生鮮除く）",
}

# 前月比から取り除く特殊な月（消費税の引き上げ・制度による値下げ）
POLICY_MONTHS = {
    "1989-04-01": "消費税3%導入",
    "1997-04-01": "消費税5%",
    "2014-04-01": "消費税8%",
    "2019-10-01": "消費税10%（軽減税率・教育無償化）",
    "2021-04-01": "携帯電話の通信料の値下げ",
    "2023-02-01": "電気・ガスの負担軽減策の開始",
}


def setup_font():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "Noto Sans CJK" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return plt
