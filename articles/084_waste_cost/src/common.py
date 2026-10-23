"""共通：環境省「一般廃棄物処理実態調査結果」（市区町村のごみ処理状況、都道府県の経費）を読む"""
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
SOURCE = "出典：環境省「一般廃棄物処理実態調査結果」（https://www.env.go.jp/recycle/waste_tech/ippan/stats.html）をもとに作成者が加工して作成"
# 年度フォルダ（＝実績の年度）と、市区町村別「ごみ処理概要」が入っているファイル番号
YEARS = {"h19": 2007, "h20": 2008, "h21": 2009, "h22": 2010, "h23": 2011, "h24": 2012, "h25": 2013, "h26": 2014,
         "h27": 2015, "h28": 2016, "h29": 2017, "h30": 2018, "r1": 2019, "r2": 2020, "r3": 2021, "r4": 2022, "r5": 2023, "r6": 2024}
MUNI_FILE = {y: ("02" if y in ("h19", "h20", "h21", "h22", "h23") else "01") for y in YEARS}


def _sheet(path, name):
    if str(path).endswith(".xls"):
        import xlrd
        s = xlrd.open_workbook(path, on_demand=True).sheet_by_name(name)
        return [s.row_values(i) for i in range(s.nrows)]
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)[name]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _find(path_glob):
    fs = glob.glob(str(path_glob))
    return fs[0] if fs else None


def _labels(rows):
    """見出し3行（1〜3行目）を前方埋めしてつなぐ"""
    n = max(len(r) for r in rows[1:4])
    out = []
    last1 = ""
    for j in range(n):
        a = rows[1][j] if j < len(rows[1]) else None
        b = rows[2][j] if j < len(rows[2]) else None
        c = rows[3][j] if j < len(rows[3]) else None
        a = str(a).strip() if a not in (None, "", "None") else ""
        if a: last1 = a
        out.append("|".join([last1, str(b or "").strip(), str(c or "").strip()]).replace("None", ""))
    return out


def _col(lab, k1, k2=None, start=0):
    """1段目に k1 を含み、2・3段目（k2 があれば）が k2 で始まる最初の列"""
    for lev in (1, 2):
        for j in range(start, len(lab)):
            parts = (lab[j].split("|") + ["", ""])[:3]
            if not parts[0].startswith(k1): continue
            if k2 is None or parts[lev].startswith(k2): return j
    return None


def num(x):
    try:
        if x in (None, "", "-", "None"): return np.nan
        return float(x)
    except Exception: return np.nan


def load_muni(cache=True):
    p = ROOT / "data" / "muni_panel.csv"
    if cache and p.exists(): return pd.read_csv(p, dtype={"code": str})
    out = []
    for y, fy in YEARS.items():
        f = _find(RAW / f"{y}_total_{MUNI_FILE[y]}.xls*")
        rows = _sheet(f, "ごみ処理概要")
        lab = _labels(rows)
        c = dict(pop=3, total_t=_col(lab, "ごみ総排出量", "合計"), group_t=_col(lab, "ごみ総排出量", "集団回収量"),
                 gpd=_col(lab, "１人１日当たり", "合計"), gpd_life=_col(lab, "１人１日当たり", "生活系"),
                 gpd_home=_col(lab, "１人１日当たり", "家庭系"), gpd_biz=_col(lab, "１人１日当たり", "事業系"),
                 proc_t=_col(lab, "ごみ処理量", "合計"), inc_t=_col(lab, "ごみ処理量", "直接焼却量"),
                 land_t=_col(lab, "ごみ処理量", "直接最終"), mid_t=_col(lab, "ごみ処理量", "焼却以外の中間処理量"),
                 dres_t=_col(lab, "ごみ処理量", "直接\n資源化量"), reuse_t=_col(lab, "中間処理後再生利用量", "合計"),
                 recy=_col(lab, "リサイクル率 Ｒ\n"), final_t=_col(lab, "最終処分量", "合計"))
        for r in rows[4:]:
            code = str(r[1]).split(".")[0].strip() if len(r) > 1 and r[1] is not None else ""
            if not re.fullmatch(r"\d{5}", code) or code.endswith("000") or code.startswith("48"): continue
            d = {"fy": fy, "pref": r[0], "code": code, "name": r[2]}
            for k, j in c.items(): d[k] = num(r[j]) if j is not None and j < len(r) else np.nan
            out.append(d)
    x = pd.DataFrame(out)
    # 東京23区：ごみの量は「23区」の行（13100）にまとめて入り、人口は区ごとの行に入っている年がある。
    # 23区は1つの単位（13100）として、人口は区の合計、ごみの量は13100の行を使う
    wards = x.code.str.match(r"131(0[1-9]|1\d|2[0-3])$")
    wpop = x[wards].groupby("fy")["pop"].sum()
    m = x.code == "13100"
    for i in x.index[m]:
        fy = x.at[i, "fy"]
        if not (x.at[i, "pop"] > 0):
            x.at[i, "pop"] = wpop.get(fy, np.nan)
            x.at[i, "gpd"] = x.at[i, "total_t"] * 1e6 / x.at[i, "pop"] / 365
            for k in ("gpd_life", "gpd_home", "gpd_biz"): x.at[i, k] = np.nan
    x = x[~wards].copy()
    x.loc[x.code == "13100", "name"] = "東京都23区"
    x = x.sort_values(["fy", "code"]).reset_index(drop=True)
    x.to_csv(p, index=False, encoding="utf-8-sig")
    return x


def load_pref_cost(cache=True):
    """都道府県別（市区町村＋一部事務組合）のごみの経費（建設改良費＋処理及び維持管理費）"""
    p = ROOT / "data" / "pref_cost.csv"
    if cache and p.exists(): return pd.read_csv(p, dtype={"code": str})
    out = []
    for y, fy in YEARS.items():
        f = _find(RAW / f"{y}_total_05.xls*")
        rows = _sheet(f, "廃棄物事業経費（歳出）")
        jt, jm, jall = 3, 11, 30  # 列の位置は全年度で同じ（建設改良費計・処理及び維持管理費計・ごみ合計）
        for r in rows[4:]:
            code = str(r[1]).split(".")[0].strip() if len(r) > 1 and r[1] is not None else ""
            if not re.fullmatch(r"\d{2}000", code) or code in ("48000", "00000") or r[0] == "全国": continue
            out.append({"fy": fy, "pref": r[0], "code": code, "build": num(r[jt]), "opex": num(r[jm]),
                        "total": num(r[jall]) if jall is not None else np.nan})
    x = pd.DataFrame(out)
    x.to_csv(p, index=False, encoding="utf-8-sig")
    return x


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
