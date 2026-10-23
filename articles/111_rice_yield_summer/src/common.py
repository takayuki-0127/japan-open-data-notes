"""共通：農林水産省「作物統計調査」収穫量累年統計（水稲）と、気象庁「日本の季節平均気温」を読む"""
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
# 57本の Excel は GitHub では data/suito_raw.zip にまとめて置いている。初回に展開する
if not any(RAW.glob("suito_*.xls")) and (ROOT / "data" / "suito_raw.zip").exists():
    import zipfile
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(ROOT / "data" / "suito_raw.zip").extractall(RAW)
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：農林水産省「作物統計調査」（e-Stat）、気象庁「日本の季節平均気温」をもとに作成者が加工して作成"
PANEL = ROOT / "data" / "rice_panel.csv"
TEMP = ROOT / "data" / "ssn_jpn.csv"

# ファイル番号 → (区分, 名前)。000〜011は全国・地域、012〜056は青森〜鹿児島。北海道と沖縄は地域のファイル（001・011）だけにある
REGIONS = ["全国", "北海道", "都府県", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
# 農林水産省の地域区分（関東・東山は長野・山梨を含む）
BLOCK = {"北海道": "北海道", **{p: "東北" for p in ["青森", "岩手", "宮城", "秋田", "山形", "福島"]},
         **{p: "北陸" for p in ["新潟", "富山", "石川", "福井"]},
         **{p: "関東・東山" for p in ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "山梨", "長野"]},
         **{p: "東海" for p in ["岐阜", "静岡", "愛知", "三重"]},
         **{p: "近畿" for p in ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"]},
         **{p: "中国" for p in ["鳥取", "島根", "岡山", "広島", "山口"]},
         **{p: "四国" for p in ["徳島", "香川", "愛媛", "高知"]},
         **{p: "九州" for p in ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島"]}, "沖縄": "沖縄"}
COLS = {1: "area_ha", 3: "normal_yield_kg", 26: "yield_kg", 27: "harvest_t", 31: "avg_yield_kg", 32: "sakkyo", 33: "sakkyo_tanshu"}


def _num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def _read(path):
    import xlrd
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    rows = []
    for i in range(sh.nrows):
        r = sh.row_values(i)
        m = re.search(r"\((\d{4})\)", str(r[0]))
        if not m:
            continue
        rows.append({"year": int(m.group(1)), **{k: _num(r[c]) if c < len(r) else np.nan for c, k in COLS.items()}})
    return pd.DataFrame(rows)


def build_panel():
    out = []
    for i in range(57):
        f = RAW / f"suito_{i:03d}.xls"
        level, name = ("region", REGIONS[i]) if i < 12 else ("pref", PREFS[i - 11])
        d = _read(f)
        d.insert(0, "name", name); d.insert(0, "level", level)
        out.append(d)
    p = pd.concat(out, ignore_index=True)
    # 北海道と沖縄は地域の行を都道府県としても使う
    hk = p[(p.level == "region") & p.name.isin(["北海道", "沖縄"])].copy(); hk["level"] = "pref"
    p = pd.concat([p, hk], ignore_index=True)
    # 2020年以降は作況指数の代わりに作況単収指数（生産者のふるい目）を使う系列
    p["sakkyo_any"] = p["sakkyo"].where(p.year < 2020, p["sakkyo_tanshu"]).fillna(p["sakkyo"])
    p.to_csv(PANEL, index=False, encoding="utf-8")
    return p


def panel():
    if PANEL.exists():
        return pd.read_csv(PANEL)
    return build_panel()


def summer_temp():
    t = pd.read_csv(TEMP, encoding="cp932")
    t = t.rename(columns={t.columns[0]: "year", t.columns[3]: "jja"})[["year", "jja"]]
    t["jja"] = pd.to_numeric(t["jja"].astype(str).str.replace("+", "", regex=False), errors="coerce")
    return t.dropna()


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
