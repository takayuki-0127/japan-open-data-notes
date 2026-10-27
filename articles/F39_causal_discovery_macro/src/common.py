"""F39 共通の設定と関数"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 39

# 変数の名前（記事・図で使う）
LABELS = {
    "fx": "為替（円安）",
    "imp": "輸入物価（契約通貨）",
    "imp_yen": "輸入物価（円）",
    "cpi": "消費者物価（生鮮除く）",
    "wage": "賃金（現金給与総額）",
    "wage_sched": "賃金（所定内）",
    "rate": "長期金利",
    "unemp": "失業率",
}
MAIN_VARS = ["fx", "imp", "cpi", "wage", "rate", "unemp"]

# 消費税の引き上げ（生鮮除く総合の前年比が12か月だけ押し上げられる期間）
TAX_WINDOWS = [("1997-04-01", "1998-03-01"), ("2014-04-01", "2015-03-01"), ("2019-10-01", "2020-09-01")]
TAX_MONTHS = ["1997-04-01", "2014-04-01", "2019-10-01"]


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


def residualize(y: pd.Series, dummies: pd.DataFrame) -> pd.Series:
    """y から定数とダミーの効果を取り除き、平均は元のまま残す"""
    X = np.column_stack([np.ones(len(y)), dummies.values])
    ok = y.notna().values
    beta, *_ = np.linalg.lstsq(X[ok], y.values[ok], rcond=None)
    out = y - dummies.values @ beta[1:]
    return out


def tax_window_dummies(index: pd.DatetimeIndex) -> pd.DataFrame:
    d = {}
    for i, (a, b) in enumerate(TAX_WINDOWS):
        d[f"tax{i}"] = ((index >= a) & (index <= b)).astype(float)
    return pd.DataFrame(d, index=index)


def tax_month_dummies(index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({f"t{i}": (index == m).astype(float) for i, m in enumerate(TAX_MONTHS)}, index=index)
