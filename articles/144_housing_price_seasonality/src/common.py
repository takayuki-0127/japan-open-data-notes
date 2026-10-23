"""不動産価格指数（住宅）・取引件数の読み込み"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
for d in (FIG, RES):
    os.makedirs(d, exist_ok=True)
for f in ["Noto Sans CJK JP", "IPAexGothic", "IPAGothic", "TakaoGothic", "Hiragino Sans", "Yu Gothic", "Meiryo"]:
    if any(f == x.name for x in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "axes.titleweight": "bold"})
C = ["#2f6db3", "#d1495b", "#edae49", "#66a182", "#7b5ea7", "#8c8c8c"]

CATS = ["住宅総合", "住宅地", "戸建住宅", "マンション（区分所有）"]
AREAS = {"全国Japan": "全国", "南関東圏Tokyo including": "南関東圏", "名古屋圏Nagoya including": "名古屋圏",
         "京阪神圏Osaka including": "京阪神圏", "東京都Tokyo": "東京都"}
TX = {1: "戸建住宅", 15: "マンション（区分所有）"}


def _index_sheet(xl, sheet, kind):
    df = xl.parse(sheet, header=None)
    rows = df[pd.to_datetime(df[0], errors="coerce").notna()]
    out = []
    for k, c in enumerate(CATS):
        j = 1 + 3 * k
        out.append(pd.DataFrame({"month": pd.to_datetime(rows[0]).dt.strftime("%Y-%m"), "category": c,
                                 kind: pd.to_numeric(rows[j], errors="coerce").values,
                                 "samples": pd.to_numeric(rows[j + 2], errors="coerce").values}))
    return pd.concat(out)


def build():
    p = os.path.join(RAW, "144_housing_index.xlsx")
    if not os.path.exists(p):
        raise SystemExit("data/raw に 144_housing_index.xlsx・144_torihiki_kensu.xlsx を置いてください（README 参照）")
    xl = pd.ExcelFile(p)
    frames = []
    for key, name in AREAS.items():
        raw = _index_sheet(xl, key + "原系列", "index_raw")
        sa = _index_sheet(xl, key + "季節調整", "index_sa").drop(columns="samples")
        m = raw.merge(sa, on=["month", "category"], how="left")
        m.insert(0, "area", name)
        frames.append(m)
    idx = pd.concat(frames, ignore_index=True)
    idx.to_csv(os.path.join(DATA, "price_index_monthly.csv"), index=False)
    t = pd.read_excel(os.path.join(RAW, "144_torihiki_kensu.xlsx"), sheet_name=0, header=None)
    rows = t[pd.to_datetime(t[0], errors="coerce").notna()]
    tx = pd.concat([pd.DataFrame({"month": pd.to_datetime(rows[0]).dt.strftime("%Y-%m"), "category": c,
                                  "transactions": pd.to_numeric(rows[j], errors="coerce").values})
                    for j, c in TX.items()])
    tx.to_csv(os.path.join(DATA, "transactions_monthly.csv"), index=False)
    return idx, tx


def load():
    a, b = os.path.join(DATA, "price_index_monthly.csv"), os.path.join(DATA, "transactions_monthly.csv")
    if os.path.exists(a) and os.path.exists(b):
        return pd.read_csv(a), pd.read_csv(b)
    return build()
