"""共通：厚生労働省「雇用動向調査」の年次別推移表（Excel）を読んで、年×項目の表にする"""
from pathlib import Path
import logging, warnings, zipfile
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
RAW, FIG, RES, DATA = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results", ROOT / "data"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
if not any(RAW.glob("hyo*.xls")) and (DATA / "koyo_raw.zip").exists():
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(DATA / "koyo_raw.zip").extractall(RAW)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：厚生労働省「雇用動向調査」（e-Stat）を加工して作成"


def _num(v):
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    return np.nan  # 「…」「・」「-」などは欠測


def _years(row):
    """見出し行（平成3年, 4, …, 令和元年, 2, …）を西暦に直す。年の列番号→西暦"""
    out, era = {}, None
    for j, v in enumerate(row):
        s = str(v).replace("\n", "").strip()
        if s.startswith("平成"):
            era, n = 1988, int(s[2:].replace("年", ""))
        elif s.startswith("令和"):
            era, n = 2018, 1
        elif era is not None and isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
            n = int(v)
        else:
            continue
        out[j] = era + n
    return out


def read_table(name, sheet=0, header_row=3, label_cols=(0, 1, 2, 3, 4, 5)):
    """年次別推移の表。ラベル列を前方埋めして '|' でつなぎ、年の列を数値にした縦長の表を返す"""
    x = pd.read_excel(RAW / name, sheet_name=sheet, header=None)
    yc = _years(x.iloc[header_row].tolist())
    labs, last = [], [""] * len(label_cols)
    rows = []
    for i in range(header_row + 1, len(x)):
        r = x.iloc[i]
        vals = {y: _num(r[j]) for j, y in yc.items()}
        if all(pd.isna(v) for v in vals.values()):
            continue
        cur = []
        for k, c in enumerate(label_cols):
            v = r[c]
            s = "" if pd.isna(v) else str(v).replace("\n", "").replace("　", "").replace(" ", "").strip()
            if s:
                last[k] = s
                for kk in range(k + 1, len(label_cols)):
                    last[kk] = ""
            cur.append(last[k])
        lab = "|".join(s for s in cur if s)
        rows.append({"label": lab, **vals})
    return pd.DataFrame(rows).set_index("label")


def industry_rates():
    """第2表（平成21年〜令和7年＝2009〜2025年）の産業別 入職率・離職率（％）。製造業の内訳は除く"""
    x = pd.read_excel(RAW / "hyo02.xls", sheet_name=2, header=None)
    yc = _years(x.iloc[3].tolist())
    out = []
    block = None
    for i in range(4, len(x)):
        a = str(x.iat[i, 0]).strip()
        if a.startswith("入職率"): block = "入職率"; continue
        if a.startswith("離職率"): block = "離職率"; continue
        code, nm = x.iat[i, 1], x.iat[i, 2]
        if block is None or pd.isna(code) or pd.isna(nm):
            continue
        nm = str(nm).replace("\n", "").replace("　", "").replace(" ", "")
        for j, y in yc.items():
            out.append({"指標": block, "産業": nm, "年": y, "値": _num(x.iat[i, j])})
    d = pd.DataFrame(out).pivot_table(index=["産業", "年"], columns="指標", values="値").reset_index()
    d["産業"] = d["産業"].replace({"サービス業（他に分類されないもの）": "サービス業（他に分類されないもの）",
                                   "電気・ガス・熱供給・水道業": "電気・ガス・熱供給・水道業"})
    return d


SHORT = {"調査産業計": "全体", "鉱業，採石業，砂利採取業": "鉱業", "建設業": "建設", "製造業": "製造",
         "電気・ガス・熱供給・水道業": "電気・ガス", "情報通信業": "情報通信", "運輸業，郵便業": "運輸・郵便",
         "卸売業，小売業": "卸売・小売", "金融業，保険業": "金融・保険", "不動産業，物品賃貸業": "不動産",
         "学術研究，専門・技術サービス業": "学術・専門", "宿泊業，飲食サービス業": "宿泊・飲食",
         "生活関連サービス業，娯楽業": "生活関連・娯楽", "教育，学習支援業": "教育", "医療,福祉": "医療・福祉",
         "複合サービス事業": "複合サービス", "サービス業（他に分類されないもの）": "その他サービス"}


def note(fig, text=SOURCE):
    fig.text(0.01, -0.02, text, fontsize=8, color=GRAY, ha="left", va="top")
