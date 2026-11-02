"""共通：パス・数値の読み方・距離・図の設定"""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"
SEED = 128

# 中心（都庁・市役所）。住宅・土地統計調査の「距離帯」の中心と同じにする
# 東京70キロ圏＝東京都庁、名古屋50キロ圏＝名古屋市役所、大阪50キロ圏＝大阪市役所
CENTERS = {
    "東京": (139.6917, 35.6895),
    "名古屋": (136.9066, 35.1815),
    "大阪": (135.5023, 34.6937),
}
RADIUS = {"東京": 70, "名古屋": 50, "大阪": 50}

# 頑健性：政令指定都市などの市役所も中心に加える（地方の都市圏）
CENTERS_WIDE = dict(CENTERS, **{
    "札幌": (141.3544, 43.0621), "仙台": (140.8694, 38.2682), "新潟": (139.0236, 37.9162),
    "静岡": (138.3831, 34.9756), "浜松": (137.7261, 34.7108), "岡山": (133.9198, 34.6551),
    "広島": (132.4553, 34.3853), "北九州": (130.8742, 33.8834), "福岡": (130.4017, 33.5902),
    "熊本": (130.7417, 32.8032), "宇都宮": (139.8836, 36.5551), "松山": (132.7656, 33.8392),
    "鹿児島": (130.5571, 31.5966),
})


def num(s):
    """'1,329 ' → 1329.0。'-' や空欄は NaN"""
    s = str(s).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def xy_to_lonlat(x_km, y_km):
    """F20・F107 の簡易投影（経度137度・緯度36度中心）を経緯度に戻す"""
    lon = np.asarray(x_km) / (111.32 * np.cos(np.radians(36.0))) + 137.0
    lat = np.asarray(y_km) / 110.57 + 36.0
    return lon, lat


def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def setup_fig():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
    return plt
