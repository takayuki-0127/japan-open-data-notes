"""共通：国土数値情報「駅別乗降客数データ」（S12、2024年度版：2011〜2024年度）を読み、1行＝駅×事業者×路線の表にする"""
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
SOURCE = "出典：「国土数値情報（駅別乗降客数データ）」（国土交通省）（https://nlftp.mlit.go.jp/ksj/）をもとに作成者が加工して作成（CC BY 4.0）"
YEARS = list(range(2011, 2025))
OPTYPE = {1: "JR新幹線", 2: "JR在来線", 3: "公営鉄道", 4: "民営鉄道", 5: "第三セクター"}
TOKYO = (139.7671, 35.6812)          # 東京駅
OSAKA = (135.4959, 34.7024)          # 大阪駅


def km(lon, lat, ref):
    """2点の距離（km、球面の近似）"""
    lon0, lat0 = np.radians(ref); lon1, lat1 = np.radians(lon), np.radians(lat)
    a = np.sin((lat1 - lat0) / 2) ** 2 + np.cos(lat0) * np.cos(lat1) * np.sin((lon1 - lon0) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def load(name="S12-25_GML.zip"):
    with zipfile.ZipFile(RAW / name) as z:
        g = json.loads(z.read("S12-25_GML/UTF-8/S12-25_NumberOfPassengers.geojson").decode("utf-8"))
    rows = []
    for f in g["features"]:
        p = f["properties"]; c = np.array(f["geometry"]["coordinates"]).mean(0)
        r = {"name": p["S12_001"], "code": p["S12_001c"], "group": p["S12_001g"], "op": p["S12_002"], "line": p["S12_003"],
             "rail": p["S12_004"], "optype": OPTYPE.get(p["S12_005"], "その他"), "lon": c[0], "lat": c[1]}
        for i, y in enumerate(YEARS):
            b = 6 + 4 * i
            ok = (p[f"S12_{b:03d}"] == 1) and (p[f"S12_{b + 1:03d}"] == 1)      # 重複なし（この行に数字がある）かつ データ有
            r[f"p{y}"] = p[f"S12_{b + 3:03d}"] if ok else np.nan
        rows.append(r)
    d = pd.DataFrame(rows)
    d["km_tokyo"] = km(d.lon, d.lat, TOKYO); d["km_osaka"] = km(d.lon, d.lat, OSAKA)
    return d


def flag_breaks(d, thr=0.3, thr_covid=0.6, thr_op=0.2):
    """数字の定義が変わったとみられる「段差」を見つける（2016〜2024年度の前年比で判定）。
    1) 駅ごと：前年比（対数）から、同じ事業者・同じ年の前年比の中央値を引き、差が thr（約35%）を超えた年があれば段差。
       コロナで駅ごとの動きが本当に大きく違った2020〜2022年度は、基準をゆるめて thr_covid（約1.8倍）にする
    2) 事業者ごと：2020〜2023年度以外で、事業者全体（両方の年に数字がある駅の合計）の前年比が thr_op（約22%）を超えて動いたら、その事業者のその年は段差"""
    years = list(range(2016, 2025)); covid = {2020, 2021, 2022}
    L = np.log(d[[f"p{y}" for y in YEARS]].where(lambda v: v > 0)); L.columns = YEARS
    g = pd.DataFrame({y: L[y] - L[y - 1] for y in years})
    resid = g - g.groupby(d.op).transform("median")
    lim = pd.Series({y: (thr_covid if y in covid else thr) for y in years})
    st = resid.abs() > lim
    op_flag = pd.DataFrame(False, index=d.index, columns=years)
    P = d[[f"p{y}" for y in YEARS]].where(lambda v: v > 0); P.columns = YEARS
    for y in years:
        if y in covid or y == 2023: continue                 # 2023年度は回復の年で、観光路線などは本当に大きく増えた
        both = P[y].notna() & P[y - 1].notna()
        tot = P[both].groupby(d.op[both])[[y - 1, y]].sum()
        bad = tot.index[(np.log(tot[y] / tot[y - 1])).abs() > thr_op]
        op_flag[y] = d.op.isin(bad)
    big = st | op_flag
    return pd.DataFrame({"n_break": big.sum(1), "break_years": big.apply(lambda r: ",".join(str(c) for c in r.index[r]), axis=1),
                         "op_break": op_flag.any(axis=1), "max_abs_resid": resid.abs().max(1)})
