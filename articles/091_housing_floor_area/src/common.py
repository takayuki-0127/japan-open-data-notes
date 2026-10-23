"""共通：国土交通省「建築着工統計調査」（e-Stat）の時系列表を読み、data/ の CSV に整える"""
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
DATA, RAW, FIG, RES = ROOT / "data", ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：国土交通省「建築着工統計調査」（e-Stat）を加工して作成"

# data/raw/ に置く元ファイル（e-Stat の「時系列表」。名前は e-Stat の表題）
RAW_FILES = {
    "tenure": "住宅_利用関係別_時系列.xls",          # 【住宅】利用関係別 時系列（年）
    "pref": "住宅_都道府県別戸数_時系列.xls",        # 【住宅】都道府県別戸数 時系列（年）
    "struct": "建築物_構造別床面積_時系列.xls",      # 【建築物】構造別床面積 時系列（年）
    "struct_use": "建築物_構造別用途別都道府県別.xls",  # 【建築物】構造別 用途別 都道府県別（年度）
    "private": "建築物_民間非居住_用途別床面積.xls",  # 【建築物】民間非居住 用途別 床面積（月）
}
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def _num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def _rows(name, sheet=0):
    import xlrd
    b = xlrd.open_workbook(RAW / RAW_FILES[name])
    s = b.sheet_by_index(sheet) if isinstance(sheet, int) else b.sheet_by_name(sheet)
    return [s.row_values(i) for i in range(s.nrows)]


def _era_year(label):
    t = str(label).replace("　", "").replace(" ", "").replace("元", "1")
    t = t.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    m = re.search(r"(昭和|平成|令和)(\d+)", t)
    return ERA[m.group(1)] + int(m.group(2)) if m else None


def build_tenure():
    """利用関係別 新設住宅の戸数・床面積（暦年、1948〜）"""
    rows = _rows("tenure")
    cols = [("総計", 1), ("持家", 3), ("貸家", 5), ("給与住宅", 7), ("分譲住宅", 9), ("分譲マンション", 11), ("分譲一戸建", 13)]
    out = []
    start = next(i for i, r in enumerate(rows) if str(r[0]).startswith("昭和23"))
    i, y = start, 1948
    while i < len(rows) and str(rows[i][0]).strip() not in ("",) and not str(rows[i][0]).startswith("※"):
        for name, c in cols:
            out.append({"year": y, "tenure": name, "units": _num(rows[i][c]), "floor_m2": _num(rows[i][c + 1])})
        i += 1; y += 1
    return pd.DataFrame(out)


def build_pref():
    """都道府県別 新設住宅の戸数・床面積（暦年、1951〜）"""
    rows = [[re.sub(r"[\s\u3000]", "", v) if isinstance(v, str) else v for v in r] for r in _rows("pref")]
    out = []
    i = 0
    while i < len(rows):
        r = rows[i]
        if any("年計" in str(v) for v in r[1:]):
            years = {c: _era_year(r[c]) for c in range(1, len(r), 2) if "年計" in str(r[c])}
            j = i + 3
            while j < len(rows) and not any("年計" in str(v) for v in rows[j][1:]):
                name = str(rows[j][0]).replace("　", "").replace(" ", "")
                if name and not name.startswith("※"):
                    for c, y in years.items():
                        out.append({"year": y, "pref": "全国" if name.startswith("合") else name,
                                    "units": _num(rows[j][c]), "floor_m2": _num(rows[j][c + 1])})
                j += 1
            i = j
        else:
            i += 1
    d = pd.DataFrame(out)
    return d[d["pref"].str.len() <= 4]


def build_struct():
    """構造別 着工建築物の床面積・工事費予定額（暦年、1951〜、千㎡・億円）"""
    rows = _rows("struct")
    names = ["総計", "木造", "鉄骨鉄筋コンクリート造", "鉄筋コンクリート造", "鉄骨造", "コンクリートブロック造", "その他"]
    out = []
    start = next(i for i, r in enumerate(rows) if str(r[1]).startswith("26年"))
    for k, i in enumerate(range(start, start + 75)):
        for n, name in enumerate(names):
            out.append({"year": 1951 + k, "structure": name, "floor_1000m2": _num(rows[i][2 + 2 * n]),
                        "cost": _num(rows[i][3 + 2 * n])})
    d = pd.DataFrame(out)
    assert d.year.max() == 2025
    return d


USE_MAP = {  # 再掲の7区分（全期間で同じ）
    "事務所": "事務所", "店舗": "店舗", "工場及び作業場": "工場・作業場", "倉庫": "倉庫",
    "学校の校舎": "学校", "病院・診療所": "病院・診療所", "その他": "その他の非住宅"}
STRUCTS = ["総計", "木造", "鉄骨鉄筋コンクリート造", "鉄筋コンクリート造", "鉄骨造", "コンクリートブロック造", "その他"]


def build_struct_use():
    """構造別×用途別の床面積（年度、1988〜。都道府県の行を足して全国にする）"""
    import xlrd
    b = xlrd.open_workbook(RAW / RAW_FILES["struct_use"])
    out = []
    for sn in b.sheet_names():
        t = sn.replace(" ", "").replace("　", "")
        fy = _era_year(t.replace("年度", ""))
        s = b.sheet_by_name(sn)
        for i in range(s.nrows):
            r = s.row_values(i)
            lab = re.sub(r"[\s　]", "", str(r[0]))
            lab = re.sub(r"^[①-⑦]|^\d\.", "", lab)
            lab = lab.replace("病院・診療所", "病院・診療所")
            if lab.startswith("全国") or lab in ("住宅計", "産業用建築物計") or lab == "":
                continue
            if lab.startswith("居住専用"):
                use = "居住専用"
            elif lab.startswith("居住産業併用"):
                use = "居住産業併用"
            elif lab in USE_MAP:
                use = USE_MAP[lab]
            else:
                continue
            for n, st in enumerate(STRUCTS):
                out.append({"fy": fy, "use": use, "structure": st, "buildings": _num(r[1 + 3 * n]),
                            "floor_m2": _num(r[2 + 3 * n]), "cost_10k_yen": _num(r[3 + 3 * n])})
    d = pd.DataFrame(out)
    return d.groupby(["fy", "use", "structure"], as_index=False)[["buildings", "floor_m2", "cost_10k_yen"]].sum()


def build_private():
    """民間非居住の用途別 床面積（月、2004年11月〜、千㎡）→ 暦年に集計"""
    rows = _rows("private")
    out = []
    i = 0
    while i < len(rows):
        if any("（民間）" in str(v) for v in rows[i]):
            heads = {c: str(v).strip().replace("（民間）", "").replace(" ", "").replace("　", "")
                     for c, v in enumerate(rows[i]) if "（民間）" in str(v)}
            j, y = i + 3, None
            while j < len(rows) and not any("（民間）" in str(v) for v in rows[j]):
                a, m = str(rows[j][0]).replace("　", "").strip(), str(rows[j][1]).replace(" ", "")
                a = a.replace("元", "1")
                if a and re.search(r"[0-9０-９]", a) and "年" in a:
                    yy = int(re.sub(r"\D", "", a.translate(str.maketrans("０１２３４５６７８９", "0123456789"))))
                    y = yy + (1988 if yy >= 16 else 2018)
                if m.endswith("月") and y:
                    mm = int(re.sub(r"\D", "", m))
                    for c, h in heads.items():
                        out.append({"year": y, "month": mm, "use": h, "buildings": _num(rows[j][c]),
                                    "floor_1000m2": _num(rows[j][c + 1])})
                j += 1
            i = j
        else:
            i += 1
    return pd.DataFrame(out).dropna(subset=["floor_1000m2"])


BUILDERS = {"tenure_year.csv": build_tenure, "pref_year.csv": build_pref, "structure_year.csv": build_struct,
            "structure_use_fy.csv": build_struct_use, "private_nonres_month.csv": build_private}


def load(name):
    p = DATA / name
    if not p.exists():
        BUILDERS[name]().to_csv(p, index=False, encoding="utf-8")
    return pd.read_csv(p)


def note(fig, text=SOURCE):
    fig.text(0.01, -0.02, text, fontsize=8, color=GRAY, ha="left", va="top")
