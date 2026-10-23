"""共通：警察庁「交通事故統計情報のオープンデータ」（本票）を読む"""
from pathlib import Path
import glob, re, logging, warnings
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
SOURCE = "出典：警察庁「交通事故統計情報のオープンデータ」（https://www.npa.go.jp/publications/statistics/koutsuu/opendata/index_opendata.html）をもとに作成者が加工して作成"
NIGHT = {"11": "昼", "12": "昼", "13": "昼", "21": "夜", "22": "夜", "23": "夜"}
WEATHER = {"1": "晴", "2": "曇", "3": "雨", "4": "霧", "5": "雪"}
SURFACE = {"1": "乾燥", "2": "湿潤", "3": "凍結", "4": "積雪", "5": "非舗装"}
TYPE = {"01": "人対車両", "21": "車両相互", "41": "車両単独", "61": "列車"}
AGE = {"01": "24歳以下", "25": "25〜34歳", "35": "35〜44歳", "45": "45〜54歳", "55": "55〜64歳", "65": "65〜74歳", "75": "75歳以上", "00": "不明"}
SPEED = {"01": "20以下", "02": "30以下", "03": "40以下", "04": "50以下", "05": "60以下", "06": "70以下", "07": "80以下", "08": "100以下", "11": "120以下", "12": "120超", "10": "指定なし", "00": "対象外"}


def party(c):
    c = str(c).zfill(2)
    if c in ("01", "02", "03", "04", "05", "07"): return "乗用車"
    if c in ("11", "12", "13", "14", "17"): return "貨物車"
    if c in ("31", "32", "33", "34", "35"): return "自動二輪"
    if c in ("36", "43"): return "原付等"
    if c in ("51", "52", "59"): return "自転車等"
    if c == "61": return "歩行者"
    if c in ("75", "76", "00"): return "相手なし等"
    return "その他"


def road(c):
    c = str(c).zfill(2)
    if c in ("01", "31"): return "交差点"
    if c in ("07", "37"): return "交差点付近"
    if c == "13": return "カーブ"
    if c in ("11", "12", "14"): return "単路"
    if c in ("21", "22", "23"): return "踏切"
    return "その他"


def dms(v):
    """ddd mm ss sss（例 431412959 → 43度14分12.959秒）を十進の度に"""
    v = pd.to_numeric(v, errors="coerce")
    s = (v % 100000) / 1000; m = (v // 100000) % 100; d = v // 10000000
    return d + m / 60 + s / 3600


def load(year):
    d = pd.read_csv(RAW / f"honhyo_{year}.csv", encoding="cp932", dtype=str)
    d.columns = [c.replace("\u3000", "").replace("　", "").replace(" ", "") for c in d.columns]
    x = pd.DataFrame({"year": year, "pref": d["都道府県コード"], "fatal": (d["事故内容"] == "1").astype(int),
                      "dead": pd.to_numeric(d["死者数"]), "injured": pd.to_numeric(d["負傷者数"]),
                      "month": pd.to_numeric(d["発生日時月"]), "hour": pd.to_numeric(d["発生日時時"]),
                      "night": d["昼夜"].map(NIGHT), "weather": d["天候"].map(WEATHER), "surface": d["路面状態"].map(SURFACE),
                      "urban": d["地形"].map({"1": "市街地", "2": "市街地", "3": "非市街地"}), "road": d["道路形状"].map(road),
                      "type": d["事故類型"].map(TYPE), "ageA": d["年齢（当事者A）"].map(AGE), "ageB": d["年齢（当事者B）"].map(AGE),
                      "partyA": d["当事者種別（当事者A）"].map(party), "partyB": d["当事者種別（当事者B）"].map(party),
                      "speedA": d["速度規制（指定のみ）（当事者A）"].map(SPEED), "dow": pd.to_numeric(d["曜日(発生年月日)"]),
                      "holiday": d["祝日(発生年月日)"], "lat": dms(d["地点緯度（北緯）"]), "lon": dms(d["地点経度（東経）"])})
    x.loc[~x.lat.between(20, 46) | ~x.lon.between(122, 154), ["lat", "lon"]] = np.nan
    return x
