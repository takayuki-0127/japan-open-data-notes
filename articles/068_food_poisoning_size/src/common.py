"""共通：厚生労働省「食中毒統計資料」の食中毒事件一覧（2000〜2025年、1件ごとの記録）を読む"""
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
SOURCE = "出典：厚生労働省「食中毒統計資料」（https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/shokuhin/syokuchu/04.html）の食中毒事件一覧をもとに作成者が加工して作成"
GROUPS = ["ノロウイルス", "カンピロバクター", "アニサキス", "サルモネラ", "腸管出血性大腸菌", "ウェルシュ菌", "黄色ブドウ球菌",
          "腸炎ビブリオ", "植物性自然毒", "動物性自然毒", "化学物質", "その他・不明"]
GCOL = dict(zip(GROUPS, [BLUE, ORANGE, GREEN, PURPLE, "#c23b6b", "#8a6d3b", "#d4a017", "#4bb3c4", "#6aa84f", "#7f6000", "#555555", GRAY]))


def group(s):
    s = str(s)
    if "ノロ" in s or "小型球形" in s: return "ノロウイルス"
    if "カンピロ" in s: return "カンピロバクター"
    if "アニサキス" in s: return "アニサキス"
    if "サルモネラ" in s: return "サルモネラ"
    if "腸管出血性" in s: return "腸管出血性大腸菌"
    if "ウェルシュ" in s or "ウエルシュ" in s: return "ウェルシュ菌"
    if "ぶどう球菌" in s or "ブドウ球菌" in s: return "黄色ブドウ球菌"
    if "腸炎ビブリオ" in s: return "腸炎ビブリオ"
    if "植物性" in s: return "植物性自然毒"
    if "動物性" in s: return "動物性自然毒"
    if "化学" in s: return "化学物質"
    return "その他・不明"


def facility(s):
    s = str(s)
    if s.startswith("飲食店"): return "飲食店"
    if s.startswith("家庭"): return "家庭"
    if s.startswith("旅館"): return "旅館"
    if s.startswith("仕出"): return "仕出屋"
    if "給食" in s or s.startswith(("学校", "病院", "事業場")): return "給食施設など"
    if s.startswith("販売"): return "販売店"
    if s.startswith("製造"): return "製造所"
    if s in ("不明", "nan", ""): return "不明"
    return "その他"


def read_one(path, year):
    raw = pd.read_excel(path, header=None, dtype=object)
    hi = next(i for i in range(15) if raw.iloc[i].astype(str).str.contains("発生月日").any())
    cols = raw.iloc[hi].astype(str).str.replace(r"\s", "", regex=True)
    d = raw.iloc[hi + 1:].copy(); d.columns = cols
    d = d.loc[:, ~d.columns.isin(["nan"])]
    pref_col = "都道府県名等" if "都道府県名等" in d else "報告自治体"
    x = pd.DataFrame({"year": year, "reporter": d[pref_col], "date_raw": d["発生月日"], "place": d["発生場所"],
                      "food": d["原因食品"], "agent": d["病因物質"], "facility_raw": d["原因施設"],
                      "eaters": pd.to_numeric(d["摂食者数"], errors="coerce"), "patients": pd.to_numeric(d["患者数"], errors="coerce"),
                      "deaths": pd.to_numeric(d["死者数"], errors="coerce")})
    x = x[x.patients.notna() & x.agent.notna()]
    dt = pd.to_datetime(x.date_raw, errors="coerce")
    num = pd.to_numeric(x.date_raw, errors="coerce")
    dt = dt.where(num.isna() | (num > 1e5), pd.to_datetime("1899-12-30") + pd.to_timedelta(num, unit="D"))
    x["date"] = dt; x["month"] = dt.dt.month
    x = x[x.date.notna()]
    x["group"] = x.agent.map(group); x["fac"] = x.facility_raw.map(facility)
    return x


def load(cache=True):
    p = ROOT / "data" / "outbreaks_2000_2025.csv"
    if cache and p.exists():
        return pd.read_csv(p, parse_dates=["date"])
    out = []
    for f in sorted(glob.glob(str(RAW / "*"))):
        name = Path(f).name; m = re.match(r"(\d{4})_", name)
        if not m: continue
        out.append(read_one(f, int(m.group(1))))
    x = pd.concat(out, ignore_index=True)
    x["deaths"] = x.deaths.fillna(0)
    x = x[~x.place.astype(str).str.contains("国外")]  # 国外での発生は除く（年次の公表値に合わせる）
    x.drop(columns=["date_raw"]).to_csv(p, index=False, encoding="utf-8-sig")
    return pd.read_csv(p, parse_dates=["date"])


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
