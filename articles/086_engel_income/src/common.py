"""共通：総務省「家計調査」第4-3表（年間収入五分位階級別 品目別支出金額・購入数量・平均価格、二人以上の世帯）を読む"""
from pathlib import Path
import logging, warnings
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
SOURCE = "出典：総務省「家計調査」（e-Stat）を加工して作成"


def load_avg():
    return pd.read_csv(ROOT / "data" / "items_avg.csv", dtype={"code": str}, keep_default_na=False, na_values=[""])


def load_quintile():
    return pd.read_csv(ROOT / "data" / "items_quintile.csv", dtype={"code": str}, keep_default_na=False, na_values=[""])


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")


BIG = {"1": "食料", "2": "住居", "3": "光熱・水道", "4": "家具・家事用品", "5": "被服及び履物", "6": "保健医療",
       "7": "交通・通信", "8": "教育", "9": "教養娯楽", "10": "その他の消費支出"}


def tag(df):
    """各行に大分類（big）・中分類（mid、例：1.1 穀類）と「品目（末端）かどうか」（leaf）を付ける。
    表の後半にある「財・サービス区分」の部分は落とす"""
    out = []
    for y, g in df.groupby("year"):
        g = g.sort_values("seq").copy()
        cut = g.loc[g.name == "財・サービス支出計", "seq"]
        if len(cut): g = g[g.seq < cut.iloc[0]]
        big = mid = None; bigs, mids = [], []
        for c, n in zip(g.code.fillna(""), g.name):
            c = str(c)
            if c in BIG: big, mid = BIG[c], None
            elif c.count(".") == 1: mid = n
            bigs.append(big); mids.append(mid)
        g["big"], g["mid"] = bigs, mids
        codes = g.code.fillna("").astype(str).tolist()
        leaf = []
        for i, c in enumerate(codes):
            nxt = codes[i + 1] if i + 1 < len(codes) else ""
            agg = ("-" in c or "," in c) or ("." in c and (("-" in nxt or "," in nxt) or (len(nxt) == 3 and "." not in nxt)))
            leaf.append(not agg)
        g["leaf"] = leaf
        # 電気代：2019年までは「深夜電力」「他の電気代」に分かれていたので、続けて見られる「電気代」の合計を使う
        g.loc[g.code == "3.1", "leaf"] = True
        g.loc[g.code.isin(["43X", "430"]), "leaf"] = False
        out.append(g)
    return pd.concat(out, ignore_index=True)


def item_panel():
    """購入数量がある末端の品目（2007〜2025年、二人以上の世帯の平均）"""
    a = tag(load_avg())
    return a[a.leaf & a.Q.notna() & (a.Q > 0) & (a.E > 0)].copy()


ENERGY = ["電気代", "プロパンガス", "灯油", "ガソリン"]


def merged_panel():
    """末端の品目 × 年：平均（E・Q・P）と五分位別（E1〜E5、Q1〜Q5）"""
    p = item_panel()
    q = load_quintile()
    qq = pd.read_csv(ROOT / "data" / "items_quintile_qty.csv", dtype={"code": str})
    m = p[["year", "code", "name", "big", "mid", "E", "Q", "P"]]
    m = m.merge(q[["year", "code"] + [f"E{j}" for j in range(1, 6)]], on=["year", "code"])
    m = m.merge(qq[["year", "code"] + [f"Q{j}" for j in range(1, 6)]], on=["year", "code"])
    return m


def totals():
    """年 × 五分位（0＝平均）の消費支出と食料の支出（年間、円）"""
    a, q = load_avg(), load_quintile()
    out = []
    for y in range(2007, 2026):
        A = a[(a.year == y) & (a.seq < 5)].set_index("name").E
        Q = q[(q.year == y) & (q.seq < 5)].set_index("name")
        out.append({"year": y, "quintile": 0, "cons": A["消費支出"], "food": A["食料"]})
        for j in range(1, 6):
            out.append({"year": y, "quintile": j, "cons": Q.loc["消費支出", f"E{j}"], "food": Q.loc["食料", f"E{j}"]})
    return pd.DataFrame(out)
