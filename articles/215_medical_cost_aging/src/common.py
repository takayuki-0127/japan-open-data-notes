"""共通：厚生労働省「介護保険事業状況報告（年報）」全国計の要介護（要支援）認定者数（年度末現在）"""
from pathlib import Path
import logging, warnings
import pandas as pd
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
DATA = ROOT / "data"; FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：厚生労働省「国民医療費」第9表（e-Stat）をもとに作成者が加工して作成"
GROUPS = ["0-14", "15-44", "45-64", "65-69", "70-74", "75+"]


def load():
    """年度×年齢階級の国民医療費（億円）、人口一人当たり（千円）、人口（千人＝医療費÷一人当たりで逆算）。
    65〜69歳＝65歳以上−70歳以上、70〜74歳＝70歳以上−75歳以上"""
    raw = pd.read_csv(DATA / "nme_table9_age_1997_2023.csv", header=None, dtype=str).fillna("")
    years = list(range(1997, 2024)); c0 = 7
    lab = raw.iloc[:, 1:4].apply(lambda r: "".join(r), axis=1)
    blocks = [i for i, v in enumerate(raw.iloc[:, c0]) if v.startswith("国民医療費") or v.startswith("構成割合") or v.startswith("人口一人当たり")]
    def block(start):
        out = {}
        for i in range(start + 1, start + 11):
            out[lab[i]] = pd.to_numeric(raw.iloc[i, c0:c0 + len(years)].str.replace("…", ""), errors="coerce").values
        return pd.DataFrame(out, index=years)
    cost, pc = block(blocks[0]), block(blocks[2])
    def split(df):
        g = pd.DataFrame(index=df.index)
        g["0-14"], g["15-44"], g["45-64"] = df["0～14"], df["15～44"], df["45～64"]
        g["65-69"] = df["65歳以上"] - df["70歳以上"]; g["70-74"] = df["70歳以上"] - df["75歳以上"]; g["75+"] = df["75歳以上"]
        return g
    C = split(cost)  # 億円
    P = pd.DataFrame({k: cost[k] / pc[k] * 100 for k in ["総数", "0～14", "15～44", "45～64", "65歳以上", "70歳以上", "75歳以上"]})  # 億円/千円=1e8/1e3 → 万人... 
    # 億円÷千円＝10万人単位 → ×100で千人
    N = split(P)
    return C, N, cost["総数"]
