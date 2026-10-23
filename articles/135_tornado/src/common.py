"""共通：気象庁「竜巻等の突風データベース」の突風事例一覧（CSV）を読む"""
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
BLUE, ORANGE, GRAY, INK, LIGHT = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef"
SOURCE = "出典：気象庁「竜巻等の突風データベース」（https://www.data.jma.go.jp/stats/data/bosai/tornado/）をもとに作成者が加工して作成"
KIND = {1: "竜巻", 2: "ダウンバースト", 3: "竜巻またはダウンバースト", 4: "ガストフロント", 5: "じん旋風",
        6: "不明", 7: "竜巻または漏斗雲", 8: "ダウンバーストまたはガストフロント", 9: "その他"}
PLACE = {1: "陸上", 2: "水上（その後上陸）", 3: "水上（上陸せず）", -8888: "不明", -9999: "未設定"}
COLS = {"事例番号": "id", "現象種類": "kind", "発生年": "year", "発生月": "month", "発生日": "day", "発生時": "hour",
        "発生分": "minute", "発生県": "pref_code", "発生市町村": "muni", "Fスケール最小値": "f_min",
        "Fスケール最大値": "f_max", "発生地点区別": "place", "死者": "deaths", "負傷者合計": "injured",
        "住家全壊": "house_destroyed"}


def load():
    """整えた一覧（data/events.csv）。なければ元の CSV から作る"""
    p = DATA / "events.csv"
    if p.exists():
        return pd.read_csv(p)
    d = pd.read_csv(RAW / "ichiran.csv", encoding="cp932", header=0)
    pref_name = d.iloc[:, 18]  # 発生県の名前（コードの次の列）
    d = d.rename(columns=COLS)[list(COLS.values())]
    d["pref"] = pref_name.values
    for c in ["month", "day", "hour", "minute", "f_min", "f_max", "deaths", "injured", "house_destroyed"]:
        d[c] = d[c].where(d[c] > -8000)
    d["kind_name"] = d["kind"].map(KIND)
    d["place_name"] = d["place"].map(PLACE)
    d.to_csv(p, index=False)
    return d


def tornado(d, land_only=True):
    """気象庁の集計と同じく、現象が「竜巻」と「竜巻またはダウンバースト」を竜巻とする。
    land_only=True なら、水上で発生して上陸しなかったもの（被害がほぼない）を除く"""
    t = d[d["kind"].isin([1, 3])]
    if land_only:
        t = t[t["place"] != 3]
    return t


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
