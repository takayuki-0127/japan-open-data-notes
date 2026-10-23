"""共通：厚生労働省「介護保険事業状況報告」年報の保険者別表（第2表 第1号被保険者数、第13表 保険給付支払額）を読む"""
from pathlib import Path
import logging, warnings
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
RAW, DATA, FIG, RES = ROOT / "data" / "raw", ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：厚生労働省「介護保険事業状況報告」年報（e-Stat）をもとに作成者が加工して作成"
YEARS = [2019, 2024]   # 年度


def _clean(s):
    return str(s).replace("　", "").replace(" ", "").strip()


def _ensure_raw():
    """data/raw が無ければ data/raw.zip から展開する"""
    if not RAW.exists() and (DATA / "raw.zip").exists():
        import zipfile
        RAW.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(DATA / "raw.zip").extractall(RAW)


def _read(fn, cols):
    _ensure_raw()
    x = pd.read_excel(RAW / fn, header=None)
    x = x.iloc[5:, [0, 1] + cols].copy()
    x.columns = ["pref", "insurer"] + [f"c{c}" for c in cols]
    x["pref"] = x.pref.map(_clean); x["insurer"] = x.insurer.map(_clean)
    return x


def load():
    p = DATA / "insurer_panel.csv"
    if p.exists():
        return pd.read_csv(p)
    out = []
    for y in YEARS:
        a = _read(f"132_{y}_02h.xls", [2, 3, 4, 5]).rename(columns={"c2": "insured", "c3": "age65_74", "c4": "age75_84", "c5": "age85p"})
        b = _read(f"132_{y}_13h.xls", [2]).rename(columns={"c2": "benefit_k"})   # 合計 支払義務額累計（千円）
        m = a.merge(b, on=["pref", "insurer"], how="inner")
        m["year"] = y
        out.append(m)
    df = pd.concat(out)
    for c in ["insured", "age65_74", "age75_84", "age85p", "benefit_k"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["level"] = np.where(df.insurer.isin(["nan", ""]), "全国", "保険者")
    df.loc[df.level == "全国", "insurer"] = "全国"
    df["per_capita_yen"] = (df.benefit_k * 1000 / df.insured).round(0)
    df["share75p"] = ((df.age75_84 + df.age85p) / df.insured * 100).round(2)
    df["share85p"] = (df.age85p / df.insured * 100).round(2)
    df = df[["year", "level", "pref", "insurer", "insured", "age65_74", "age75_84", "age85p", "share75p", "share85p", "benefit_k", "per_capita_yen"]]
    df.to_csv(p, index=False)
    return df
