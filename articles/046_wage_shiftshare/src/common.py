"""共通：厚生労働省「令和7年賃金構造基本統計調査」都道府県別第1表・第2表を読む"""
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
SOURCE = "出典：「賃金構造基本統計調査」（厚生労働省）（https://www.e-stat.go.jp/stat-search/files?toukei=00450091）令和7年 都道府県別第1表・第2表をもとに作成者が加工して作成"
COLS = ["age", "tenure", "hours", "ot_hours", "monthly", "scheduled", "bonus", "workers"]
SIZES = ["計", "1000+", "100-999", "10-99"]
AGES = ["~19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
        "50-54", "55-59", "60-64", "65-69", "70~"]
AGE_MID = [18.5, 22, 27, 32, 37, 42, 47, 52, 57, 62, 67, 72]
SEXES = ["計", "男", "女"]


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return np.nan


def norm_pref(s):
    s = re.sub(r"[\s　０-９0-9]", "", str(s))
    return s


def load_age(industry="産業計"):
    """第1表: 都道府県×規模×性×年齢階級。long形式。annual=きまって支給×12+賞与（千円）"""
    rows = []
    for f in sorted(glob.glob(str(RAW / "(1-10-1-*)*.xlsx"))):
        x = pd.ExcelFile(f)
        for sh in x.sheet_names:
            m = re.match(r"\((.+?)\)(.+)", sh)
            if not m or m.group(2) != industry:
                continue
            pref = m.group(1)
            d = x.parse(sh, header=None)
            for si, size in enumerate(SIZES):
                c0 = 3 + 8 * si
                for xi, sex in enumerate(SEXES):
                    r0 = 11 + 13 * xi
                    for ai in range(13):
                        vals = [_num(v) for v in d.iloc[r0 + ai, c0:c0 + 8]]
                        rows.append(dict(pref=pref, size=size, sex=sex,
                                         ageg="all" if ai == 0 else AGES[ai - 1],
                                         **dict(zip(COLS, vals))))
    df = pd.DataFrame(rows)
    df["annual"] = df.monthly * 12 + df.bonus
    df["workers"] = df.workers * 10
    return df


OCCS = ["管理的職業従事者", "専門的・技術的職業従事者", "事務従事者", "販売従事者",
        "サービス職業従事者", "保安職業従事者", "農林漁業従事者", "生産工程従事者",
        "輸送・機械運転従事者", "建設・採掘従事者", "運搬・清掃・包装等従事者"]


def load_occ():
    """第2表: 都道府県×性×職種大分類。不詳は除外。"""
    rows = []
    for f in sorted(glob.glob(str(RAW / "(1-10-2-*)*.xlsx"))):
        d = pd.read_excel(f, sheet_name=0, header=None)
        for c0 in range(3, d.shape[1] - 7, 8):
            pref = norm_pref(d.iloc[5, c0])
            if not pref or pref == "nan":
                continue
            for xi, sex in enumerate(SEXES):
                for oi, occ in enumerate(OCCS):
                    vals = [_num(v) for v in d.iloc[9 + 12 * xi + oi, c0:c0 + 8]]
                    rows.append(dict(pref=pref, sex=sex, occ=occ, **dict(zip(COLS, vals))))
    df = pd.DataFrame(rows)
    df["annual"] = df.monthly * 12 + df.bonus
    df["workers"] = df.workers * 10
    return df


PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
