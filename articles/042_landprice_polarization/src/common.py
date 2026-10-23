"""共通：国土数値情報「地価公示データ」（L01、2026年版）を読む。各標準地に1983〜2026年の価格の履歴がついている"""
from pathlib import Path
import logging, warnings, json, zipfile
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
PREF = dict(zip([f"{i:02d}" for i in range(1, 48)], "北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県".split()))
SOURCE = "出典：「国土数値情報（地価公示データ）」（国土交通省）（https://nlftp.mlit.go.jp/ksj/）をもとに作成者が加工して作成（CC BY 4.0）"
YEARS = list(range(1983, 2027))
USE = {"000": "住宅地", "005": "商業地", "009": "工業地", "003": "宅地見込地", "013": "林地"}
# 圏域は都道府県で近似（公式の三大都市圏は市町村単位）
AREA = {**{p: "東京圏" for p in ["11", "12", "13", "14"]}, **{p: "大阪圏" for p in ["26", "27", "28", "29"]}, **{p: "名古屋圏" for p in ["23", "24"]}}


def load(name="L01-26_GML.zip"):
    with zipfile.ZipFile(RAW / name) as z:
        g = json.loads(z.read("L01-26_GML/L01-26.geojson").decode("utf-8"))
    rows = []
    for f in g["features"]:
        p = f["properties"]; lon, lat = f["geometry"]["coordinates"][:2]
        r = {"code": p["L01_001"], "use": USE.get(p["L01_002"], "その他"), "pref": p["L01_001"][:2], "address": p["L01_025"], "station": p["L01_048"],
             "station_m": p["L01_050"], "zoning": p["L01_051"], "lon": lon, "lat": lat}
        for i, y in enumerate(YEARS):
            v = p[f"L01_{62 + i:03d}"]
            r[y] = v if (v is not None and v > 0) else np.nan
        rows.append(r)
    d = pd.DataFrame(rows)
    d["area"] = d.pref.map(AREA).fillna("地方圏")
    return d


def chain_index(d, base=2026, min_n=30):
    """連鎖指数：毎年、前年と当年の両方に価格がある標準地の対数変化の平均をつなぐ（基準年＝100）。
    基準年から過去にさかのぼってつなぎ、両方の年に価格がある地点が min_n 未満になったところで止める"""
    lv = {base: 0.0}
    for y in range(base, YEARS[0], -1):
        b = d[y].notna() & d[y - 1].notna()
        if b.sum() < min_n: break
        lv[y - 1] = lv[y] - (np.log(d.loc[b, y]) - np.log(d.loc[b, y - 1])).mean()
    s = pd.Series(lv).sort_index().reindex(YEARS)
    return np.exp(s) * 100
