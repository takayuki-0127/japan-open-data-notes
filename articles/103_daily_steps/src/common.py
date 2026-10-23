"""共通：厚生労働省「国民健康・栄養調査」（e-Stat）の歩数・睡眠・朝食欠食の表を読む"""
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
if not any(RAW.glob("eiyo_*")) and (ROOT / "data" / "eiyo_raw.zip").exists():
    import zipfile
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(ROOT / "data" / "eiyo_raw.zip").extractall(RAW)
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
AGE_COLORS = ["#a9c9ef", "#6aa4e6", "#2a78d6", "#1b4f99", "#eb6834", "#b8401a"]
SOURCE = "出典：厚生労働省「国民健康・栄養調査」（e-Stat、https://www.e-stat.go.jp/stat-search/files?toukei=00450171）を加工して作成"
AGES = ["20-29", "30-39", "40-49", "50-59", "60-69", "70+"]
Z2H = str.maketrans("０１２３４５６７８９－～", "0123456789-~")

# 年ごとのファイル（e-Stat の表番号は年で変わる）
STEP_TREND = "eiyo_2017_044"          # 第96表 歩数の平均値の年次推移 2003〜2017年
STEP_YEAR = {2018: "eiyo_2018_046", 2019: "eiyo_2019_049", 2022: "eiyo_2022_056", 2023: "eiyo_2023_061", 2024: "eiyo_2024_064"}
STEP_PREF = {2012: "eiyo_2012_006", 2016: "eiyo_2016_034", 2024: "eiyo_2024_068"}
BREAKFAST = "eiyo_2017_043"           # 第91表 朝食欠食率の年次推移 2003〜2017年
SLEEP = {2009: ("eiyo_2009_000", "第67表"), 2010: ("eiyo_2010_002", "58"), 2011: ("eiyo_2011_003", "第62表"),
         2014: ("eiyo_2014_015", 0), 2015: ("eiyo_2015_022", 0), 2017: ("eiyo_2017_041", 0), 2018: ("eiyo_2018_047", 0),
         2019: ("eiyo_2019_050", 0), 2022: ("eiyo_2022_057", 0), 2023: ("eiyo_2023_062", 0), 2024: ("eiyo_2024_065", 0)}
# 公表の年齢調整値（20歳以上、平成22年国勢調査の基準人口。2024年は令和2年基準で総数のみ）
STEP_ADJ_NOTE = {2018: (7035, 6115), 2019: (7162, 6105), 2022: (6790, 6063), 2023: (6914, 5922)}


def path(stem):
    return next(RAW.glob(stem + ".*"))


def sheet(stem, sh=0):
    return pd.read_excel(path(stem), header=None, sheet_name=sh)


def age_key(s):
    s = str(s).translate(Z2H).replace(" ", "").replace("　", "")
    if "再掲" in s:
        return None
    m = re.match(r"^(\d{2})[-~](\d{2})歳$", s)
    if m and m.group(1) in ("20", "30", "40", "50", "60"):
        return f"{m.group(1)}-{m.group(2)}"
    if s.startswith("70歳以上"):
        return "70+"
    if s in ("総数", "総　数"):
        return "total"
    return None


SEX = {"総数": "total", "男性": "male", "女性": "female"}


def _sexcol(d, row):
    v = str(d.iloc[row, 0]).replace(" ", "").replace("　", "")
    return SEX.get(v)


def load_step_trend():
    """2003〜2017年：性×年齢階級の平均歩数と年齢調整値（年次推移表）"""
    d = sheet(STEP_TREND)
    years = [int(str(v).split("\n")[-1]) if isinstance(v, str) and "\n" in v else None for v in d.iloc[6]]
    recs, sex = [], None
    for i in range(7, len(d)):
        s0 = str(d.iloc[i, 0]).strip()
        if s0 in ("男性", "女性"):
            sex = SEX[s0]
        lab = str(d.iloc[i, 1]).strip()
        age = "adj" if lab == "年齢調整値" else ("total" if lab == "総数" else age_key(lab))
        if not sex or not age:
            continue
        for j, y in enumerate(years):
            if y:
                recs.append((y, sex, age, float(d.iloc[i, j])))
    return pd.DataFrame(recs, columns=["year", "sex", "age", "steps"])


def load_step_year(year):
    """各年の表：性×年齢階級の人数・平均値・標準偏差"""
    d = sheet(STEP_YEAR[year])
    hdr = 5
    cols = {}
    for j in range(d.shape[1]):
        k = age_key(d.iloc[hdr, j]) if pd.notna(d.iloc[hdr, j]) else None
        if k and k not in cols:
            cols[k] = j
    recs = []
    for i in range(hdr + 3, len(d)):
        sex = _sexcol(d, i)
        if not sex:
            continue
        for k, j in cols.items():
            recs.append((year, sex, k, float(d.iloc[i, j]), float(d.iloc[i, j + 1]), float(d.iloc[i, j + 2])))
    return pd.DataFrame(recs, columns=["year", "sex", "age", "n", "steps", "sd"])


def load_steps():
    """2003〜2024年の性×年齢階級の平均歩数（2018年以降は各年の表）。adj＝公表の年齢調整値"""
    a = load_step_trend()
    b = pd.concat([load_step_year(y) for y in STEP_YEAR])
    adj = pd.DataFrame([(y, s, "adj", v) for y, (m, f) in STEP_ADJ_NOTE.items() for s, v in (("male", m), ("female", f))],
                       columns=["year", "sex", "age", "steps"])
    out = pd.concat([a, b[a.columns], adj], ignore_index=True)
    out = out.merge(b[["year", "sex", "age", "n", "sd"]], on=["year", "sex", "age"], how="left")
    return out.sort_values(["sex", "age", "year"]).reset_index(drop=True)


def load_step_pref():
    """都道府県別の平均歩数（20〜64歳、年齢調整）2012・2016・2024年"""
    recs = []
    for y, stem in STEP_PREF.items():
        d = sheet(stem)
        for i in range(len(d)):
            name = str(d.iloc[i, 0]).strip()
            if (re.search(r"(都|道|府|県)$", name) and name != "都道府県" or name == "全国") and isinstance(d.iloc[i, 1], (int, float)):
                for sex, j in (("male", 1), ("female", 5)):
                    recs.append((y, name, sex, float(d.iloc[i, j]), float(d.iloc[i, j + 1]),
                                 float(d.iloc[i, j + 2]), float(d.iloc[i, j + 3])))
    return pd.DataFrame(recs, columns=["year", "pref", "sex", "n", "steps", "lo", "hi"])


def load_breakfast():
    """2003〜2017年：性×年齢階級の朝食欠食率（%）"""
    d = sheet(BREAKFAST)
    years = [int(str(v).split("\n")[-1]) if isinstance(v, str) and "\n" in v else None for v in d.iloc[6]]
    recs, sex = [], None
    for i in range(7, len(d)):
        s0 = str(d.iloc[i, 0]).strip()
        if s0 in ("男性", "女性"):
            sex = SEX[s0]
        lab = str(d.iloc[i, 1]).strip()
        age = "total" if lab == "総数" else age_key(lab)
        if not sex or not age:
            continue
        for j, y in enumerate(years):
            if y:
                recs.append((y, sex, age, float(d.iloc[i, j])))
    return pd.DataFrame(recs, columns=["year", "sex", "age", "skip_pct"])


SLEEP_CAT = {"5時間未満": "lt5", "5時間以上6時間未満": "5-6", "6時間以上7時間未満": "6-7",
             "7時間以上8時間未満": "7-8", "8時間以上9時間未満": "8-9", "9時間以上": "9+", "総数": "n_total", "総　　　　　数": "n_total"}


def load_sleep_year(year):
    stem, sh = SLEEP[year]
    d = sheet(stem, sh)
    hdr = next(i for i in range(10) if any(age_key(v) == "20-29" for v in d.iloc[i] if pd.notna(v)))
    cols = {}
    for j in range(d.shape[1]):
        v = d.iloc[hdr, j]
        k = age_key(v) if pd.notna(v) else None
        if k and k not in cols:
            cols[k] = j
    recs, sex = [], None
    for i in range(hdr + 2, len(d)):
        s = _sexcol(d, i)
        if s:
            sex = s
        lab = str(d.iloc[i, 1]).translate(Z2H).replace(" ", "").replace("　", "")
        lab = re.sub(r"^\d\.", "", lab)
        cat = "n_total" if lab.startswith("総") else SLEEP_CAT.get(lab)
        if not sex or not cat:
            continue
        for k, j in cols.items():
            n, pct = d.iloc[i, j], d.iloc[i, j + 1]
            recs.append((year, sex, k, cat, float(n), float(pct)))
    return pd.DataFrame(recs, columns=["year", "sex", "age", "cat", "n", "pct"])


def load_sleep():
    """2009〜2024年（11年分）：性×年齢階級×睡眠時間の区分の人数・割合（20歳以上）"""
    return pd.concat([load_sleep_year(y) for y in SLEEP], ignore_index=True)


def note(fig, text=SOURCE, y=-0.02):
    fig.text(0.01, y, text, fontsize=7.5, color="#555555", ha="left", va="top")
