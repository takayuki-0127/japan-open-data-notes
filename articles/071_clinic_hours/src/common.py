"""共通：厚生労働省「医療情報ネット（ナビイ）」オープンデータ（2026年6月1日時点）を読む"""
from pathlib import Path
import re, logging, warnings
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
SOURCE = "出典：厚生労働省「医療情報ネット（ナビイ）」オープンデータ（https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryou/newpage_43373.html）をもとに作成者が加工して作成"
D = "20260601"
DAYS = ["月", "火", "水", "木", "金", "土", "日", "祝"]
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]


def read(name):
    return pd.read_csv(RAW / f"{name}_{D}.csv", dtype=str, encoding="utf-8-sig")


def mins(s):
    """'09:30' → 570（分）。空欄は NaN"""
    t = s.str.extract(r"^(\d{1,2}):(\d{2})").astype(float)
    return t[0] * 60 + t[1]


def muni_type(city):
    c = str(city)
    if c.endswith("区"): return "特別区・政令市"
    if c.endswith("市"): return "市"
    if c.endswith(("町", "村")): return "町村"
    return "不明"


_names = None
def city_of(code5, addr):
    """市区町村名：介護サービス情報公表システムから作った一覧（data/raw/muni_names.csv）→なければ所在地の文字列から"""
    global _names
    if _names is None:
        m = pd.read_csv(RAW / "muni_names.csv", dtype=str, encoding="utf-8-sig"); _names = dict(zip(m.muni, m.city))
    if code5 in _names: return _names[code5]
    a = re.sub(r"^(東京都|北海道|京都府|大阪府|.{2,3}県)", "", str(addr))
    m = re.match(r"(.+?市.+?区|.+?郡.+?[町村]|.+?[市区町村])", a)
    return m.group(1).split("郡")[-1] if m else "不明"


def facilities(kind):
    """kind: hospital / clinic。施設1行の表（市区町村・緯度経度・病床・各曜日の診療の有無と最早開始・最遅終了）"""
    f = read({"hospital": "01-1_hospital_facility_info", "clinic": "02-1_clinic_facility_info"}[kind])
    h = read({"hospital": "01-2_hospital_speciality_hours", "clinic": "02-2_clinic_speciality_hours"}[kind])
    x = pd.DataFrame({"ID": f.ID, "pcode": f["都道府県コード"].str.zfill(2), "addr": f["所在地"],
                      "lat": pd.to_numeric(f["所在地座標（緯度）"], errors="coerce"), "lon": pd.to_numeric(f["所在地座標（経度）"], errors="coerce"),
                      "beds": pd.to_numeric(f["合計病床数"], errors="coerce")})
    x["muni"] = x.pcode + f["市区町村コード"].str.zfill(3)
    x["pref"] = x.pcode.astype(int).map(lambda i: PREFS[i - 1] if 1 <= i <= 47 else "不明")
    x["city"] = [city_of(m, a) for m, a in zip(x.muni, x.addr)]
    x["mtype"] = x.city.map(muni_type)
    for d in DAYS:
        h[f"{d}_s"] = mins(h[f"{d}_診療開始時間"].fillna("")); h[f"{d}_e"] = mins(h[f"{d}_診療終了時間"].fillna(""))
    return x.drop(columns="addr"), h


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
