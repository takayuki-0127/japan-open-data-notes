"""共通：出入国在留管理庁「出入国管理統計」月報の表「港別 入国外国人の国籍・地域」を読む"""
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6", "#c8423b"
SOURCE = "出典：出入国在留管理庁「出入国管理統計」（e-Stat）を加工して作成"

# 港の名前のゆれ（表の様式が変わった年に名前が変わったもの）
PORT_FIX = {"富士山静岡(空港)": "静岡(空港)", "大阪（阪神）": "大阪", "神戸（阪神）": "神戸",
            "尼崎西宮芦屋（阪神）": "尼崎西宮芦屋", "福井（新）": "福井新"}
NAT_FIX = {"中国〔香港〕": "中国（香港）", "中国〔その他〕": "中国（その他）", "英国〔香港〕": "英国（香港）",
           "(朝鮮)": "朝鮮", "（朝鮮）": "朝鮮", "セントクリストファー・ネーヴィス": "セントクリストファー・ネービス",
           "スワジランド": "エスワティニ", "マケドニア": "北マケドニア", "グルジア": "ジョージア"}
REGIONS = {"総数", "アジア", "ヨーロッパ", "アフリカ", "北アメリカ", "南アメリカ", "オセアニア", "無国籍"}


def _norm(s):
    return re.sub(r"\s", "", str(s)).replace("（空港）", "(空港)")


def _read_month(fn):
    v = pd.read_excel(fn, header=None)
    pos = next((r, c) for r in range(10) for c in range(4) if _norm(v.iat[r, c]) == "国籍・地域")
    r, c = pos
    hdr = [PORT_FIX.get(_norm(x), _norm(x)) for x in v.iloc[r, c + 1:].tolist()]
    out = []
    for _, row in v.iloc[r + 1:].iterrows():
        nat = row.iloc[c]
        if pd.isna(nat): continue
        nat = _norm(nat); nat = NAT_FIX.get(nat, nat)
        if re.search(r"\d", nat): continue
        for p, val in zip(hdr, row.iloc[c + 1:].tolist()):
            if p in ("nan", ""): continue
            try: val = float(val)
            except (TypeError, ValueError): continue
            if val > 0: out.append((nat, p, val))
    return out


def _build():
    rows = []
    for fn in sorted(glob.glob(str(RAW / "nyu_*"))):
        y, m = map(int, re.findall(r"nyu_(\d{4})_(\d{2})", fn)[0])
        rows += [(y, m) + t for t in _read_month(fn)]
    df = pd.DataFrame(rows, columns=["year", "month", "nat", "port", "n"])
    df = df.groupby(["year", "month", "nat", "port"], as_index=False).n.sum()
    df["n"] = df.n.astype(int)
    return df


MAIN = ["成田(空港)", "羽田(空港)", "関西(空港)", "中部(空港)", "福岡(空港)", "新千歳(空港)", "那覇(空港)"]


def load_port_nat(cache=True):
    """主な7空港と「その他の空港」「海港」×国籍×年"""
    p = ROOT / "data" / "port_nat_year.csv"
    if cache and p.exists(): return pd.read_csv(p)
    df = _build()
    df["group"] = np.where(df.port.isin(MAIN), df.port, np.where(df.port.str.endswith("(空港)"), "その他の空港", "海港"))
    df = df[(df.port != "総数")]
    x = df.groupby(["year", "group", "nat"], as_index=False).n.sum()
    x.to_csv(p, index=False, encoding="utf-8-sig")
    return x


def load(cache=True):
    """port_month（港×月の外国人入国者数）と nat_month（国籍×月）を返す"""
    pp, pn = ROOT / "data" / "port_month.csv", ROOT / "data" / "nat_month.csv"
    if cache and pp.exists() and pn.exists():
        return pd.read_csv(pp), pd.read_csv(pn)
    df = _build()
    port = df[df.nat == "総数"].drop(columns="nat").sort_values(["year", "month", "port"])
    nat = df[df.port == "総数"].drop(columns="port").sort_values(["year", "month", "nat"])
    port.to_csv(pp, index=False, encoding="utf-8-sig"); nat.to_csv(pn, index=False, encoding="utf-8-sig")
    return port, nat


def is_air(p):
    return p.endswith("(空港)")


def spread(vals, gap):
    """ラベルが重ならないよう、y の位置を少しずらす"""
    order = sorted(range(len(vals)), key=lambda i: vals[i]); out = list(vals)
    for k in range(1, len(order)):
        a, b = order[k - 1], order[k]
        if out[b] - out[a] < gap: out[b] = out[a] + gap
    return out


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
