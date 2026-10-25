"""共通：インバウンド消費動向調査（観光庁）の国籍別1人当たり旅行消費単価と、FRB H.10 の年平均為替レート（FRED）を読む"""
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
DATA = ROOT / "data"; FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：観光庁「インバウンド消費動向調査」、FRB「H.10」（FRED）をもとに作成者が加工して作成"
# 国籍 → (通貨, FREDの系列, 向き)  向き "per_usd"=1ドルあたり現地通貨, "usd_per"=1現地通貨あたりドル
CUR = {"韓国": ("KRW", "AEXKOUS", "per_usd"), "台湾": ("TWD", "AEXTAUS", "per_usd"), "香港": ("HKD", "AEXHKUS", "per_usd"),
       "中国": ("CNY", "AEXCHUS", "per_usd"), "タイ": ("THB", "AEXTHUS", "per_usd"), "シンガポール": ("SGD", "AEXSIUS", "per_usd"),
       "マレーシア": ("MYR", "AEXMAUS", "per_usd"), "インド": ("INR", "AEXINUS", "per_usd"), "英国": ("GBP", "AEXUSUK", "usd_per"),
       "ドイツ": ("EUR", "AEXUSEU", "usd_per"), "フランス": ("EUR", "AEXUSEU", "usd_per"), "イタリア": ("EUR", "AEXUSEU", "usd_per"),
       "スペイン": ("EUR", "AEXUSEU", "usd_per"), "米国": ("USD", None, "usd"), "カナダ": ("CAD", "AEXCAUS", "per_usd")}
YEARS = [2019, 2022, 2023, 2024, 2025]


def load():
    """国籍×年のパネル。spend＝1人1回当たり旅行消費単価（円）、jpy_per＝現地通貨1単位あたりの円（年平均）"""
    s = pd.read_csv(DATA / "spend_per_person.csv").set_index("nationality")
    f = pd.read_csv(DATA / "fred_annual_fx_raw.csv")
    f["year"] = f.observation_date.str[:4].astype(int); f = f.set_index("year")
    rows = []
    for n, (cur, sid, kind) in CUR.items():
        for y in YEARS:
            jp = f.loc[y, "AEXJPUS"]
            r = jp if kind == "usd" else (jp / f.loc[y, sid] if kind == "per_usd" else jp * f.loc[y, sid])
            rows.append({"nationality": n, "currency": cur, "year": y, "spend": s.loc[n, str(y)], "jpy_per": r})
    d = pd.DataFrame(rows)
    d["spend_local"] = d.spend / d.jpy_per
    return d


def save(fig, name, y=-0.02):
    fig.text(0.01, y, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
