"""共通：気象庁 RSMC Tokyo 台風センター「Best Track Data」（1951〜2025年、bst_all.txt）を読む"""
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
SOURCE = "出典：気象庁 RSMC Tokyo 台風センター「Best Track Data」（https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/besttrack.html）をもとに作成者が加工して作成"
Y0, Y1 = 1951, 2025
# 都道府県庁所在地の気象台（おおよその位置）。「接近」の判定に使う
OBS = {"札幌": (43.06, 141.33), "青森": (40.82, 140.77), "盛岡": (39.70, 141.17), "仙台": (38.26, 140.90), "秋田": (39.72, 140.10),
       "山形": (38.26, 140.35), "福島": (37.76, 140.47), "水戸": (36.38, 140.47), "宇都宮": (36.55, 139.87), "前橋": (36.40, 139.06),
       "熊谷": (36.15, 139.38), "銚子": (35.74, 140.86), "東京": (35.69, 139.75), "横浜": (35.44, 139.65), "新潟": (37.89, 139.02),
       "富山": (36.71, 137.20), "金沢": (36.59, 136.63), "福井": (36.06, 136.22), "甲府": (35.67, 138.55), "長野": (36.66, 138.19),
       "岐阜": (35.40, 136.76), "静岡": (34.98, 138.40), "名古屋": (35.17, 136.97), "津": (34.73, 136.52), "彦根": (35.28, 136.24),
       "京都": (35.01, 135.73), "大阪": (34.68, 135.52), "神戸": (34.70, 135.21), "奈良": (34.69, 135.83), "和歌山": (34.23, 135.16),
       "鳥取": (35.49, 134.24), "松江": (35.46, 133.07), "岡山": (34.66, 133.92), "広島": (34.40, 132.46), "下関": (33.95, 130.93),
       "徳島": (34.07, 134.57), "高松": (34.32, 134.05), "松山": (33.84, 132.78), "高知": (33.57, 133.55), "福岡": (33.58, 130.38),
       "佐賀": (33.27, 130.30), "長崎": (32.73, 129.87), "熊本": (32.81, 130.71), "大分": (33.24, 131.62), "宮崎": (31.94, 131.41),
       "鹿児島": (31.55, 130.55), "那覇": (26.21, 127.69), "名瀬": (28.38, 129.50), "石垣島": (24.34, 124.16), "南大東島": (25.83, 131.23)}
TS_GRADES = {3, 4, 5, 9}  # 3=TS, 4=STS, 5=TY, 9=TS以上（初期のデータ）


def load(cache=True):
    """1行＝1観測時刻のデータフレーム（sid, year, time, grade, lat, lon, pres, wind）"""
    p = ROOT / "data" / "track.pkl"
    if cache and p.exists(): return pd.read_pickle(p)
    rows, sid, name = [], None, None
    import zipfile, io
    z = zipfile.ZipFile(RAW / "bst_all.zip")
    for line in io.TextIOWrapper(z.open("bst_all.txt"), encoding="ascii", errors="ignore"):
        if line.startswith("66666"):
            parts = line.split()
            sid = parts[1]; name = line[30:50].strip(); continue
        t = line[0:8]; grade = int(line[13]); lat = int(line[15:18]) / 10; lon = int(line[19:23]) / 10
        pres = int(line[24:28]); w = line[33:36].strip()
        yy = int(t[:2]); year = 1900 + yy if yy >= 51 else 2000 + yy
        rows.append((sid, name, pd.Timestamp(year=year, month=int(t[2:4]), day=int(t[4:6]), hour=int(t[6:8])), grade, lat, lon, pres, int(w) if w else np.nan))
    d = pd.DataFrame(rows, columns=["sid", "name", "time", "grade", "lat", "lon", "pres", "wind"])
    d["wind"] = d.wind.where(d.wind > 0)
    d.to_pickle(p)
    return d


def hav(lat1, lon1, lat2, lon2):
    r = np.pi / 180
    a = np.sin((lat2 - lat1) * r / 2) ** 2 + np.cos(lat1 * r) * np.cos(lat2 * r) * np.sin((lon2 - lon1) * r / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def storms(d):
    """台風（TS以上）になった嵐の一覧。年は台風になった時刻の年"""
    ts = d[d.grade.isin(TS_GRADES)]
    g = ts.groupby("sid")
    s = pd.DataFrame({"t_form": g.time.min(), "lat_form": g.lat.first(), "lon_form": g.lon.first()})
    s["year"] = s.t_form.dt.year; s["month"] = s.t_form.dt.month
    s = s[(s.year >= Y0) & (s.year <= Y1)]
    return s


def hourly(d):
    """台風（TS以上）の時間帯だけ、1時間ごとに直線補間した位置と気圧"""
    out = []
    for sid, g in d.groupby("sid"):
        g = g.set_index("time").sort_index()
        g = g[~g.index.duplicated()]
        idx = pd.date_range(g.index.min(), g.index.max(), freq="h")
        h = g[["lat", "lon", "pres"]].reindex(g.index.union(idx)).interpolate("time").reindex(idx)
        h["ts"] = g.grade.isin(TS_GRADES).reindex(g.index.union(idx)).ffill().reindex(idx).astype(bool)
        h["sid"] = sid
        out.append(h.reset_index().rename(columns={"index": "time"}))
    return pd.concat(out, ignore_index=True)


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
