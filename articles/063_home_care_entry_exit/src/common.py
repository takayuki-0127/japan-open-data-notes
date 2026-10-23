"""共通：厚生労働省「介護サービス情報公表システム」オープンデータ（訪問介護・通所介護、2020年12月末〜2026年6月末の12時点）を読む"""
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
SOURCE = "出典：厚生労働省「介護サービス情報公表システム」オープンデータ（https://www.mhlw.go.jp/stf/kaigo-kouhyou_opendata.html）をもとに作成者が加工して作成"
SNAPS = ["2020-12", "2021-06", "2021-12", "2022-06", "2022-12", "2023-06", "2023-12", "2024-06", "2024-12", "2025-06", "2025-12", "2026-06"]
SVC = {"110": "訪問介護", "150": "通所介護"}
SCOL = {"訪問介護": BLUE, "通所介護": ORANGE}


def corp_type(name):
    n = str(name)
    if re.search(r"株式会社|有限会社|合同会社|合資会社|合名会社|\(株\)|（株）|\(有\)|（有）", n): return "営利法人"
    if "社会福祉" in n: return "社会福祉法人"
    if "医療法人" in n or "医療" in n and "法人" in n: return "医療法人"
    if "特定非営利" in n or "ＮＰＯ" in n or "NPO" in n: return "NPO法人"
    if "協同組合" in n: return "協同組合"
    if re.search(r"社団|財団", n): return "社団・財団"
    if re.search(r"[都道府県市町村]$|広域連合|組合$", n): return "自治体等"
    return "その他"


def muni_type(city):
    c = str(city)
    if c.endswith("区"): return "特別区・政令市"
    if c.endswith("市"): return "市"
    return "町村"


def norm(s):
    return str(s).replace(" ", "").replace("　", "").replace("（", "(").replace("）", ")")


def load(cache=True):
    p = ROOT / "data" / "panel.pkl"
    if cache and p.exists(): return pd.read_pickle(p)
    out = []
    for s in SNAPS:
        for code, svc in SVC.items():
            d = pd.read_csv(RAW / f"{s}_{code}.csv", dtype=str, encoding="utf-8-sig")
            x = pd.DataFrame({"snap": s, "svc": svc, "id": d["事業所番号"].str.zfill(10),
                              "muni": d["都道府県コード又は市町村コード"].str.zfill(6).str[:5], "pref": d["都道府県名"], "city": d["市区町村名"],
                              "lat": pd.to_numeric(d["緯度"], errors="coerce"), "lon": pd.to_numeric(d["経度"], errors="coerce"),
                              "corp": d["法人の名称"].map(norm), "days": d["利用可能曜日"].fillna("")})
            out.append(x.drop_duplicates("id"))
    x = pd.concat(out, ignore_index=True)
    x["k"] = x.snap.map({s: i for i, s in enumerate(SNAPS)})
    x["ctype"] = x.corp.map(corp_type)
    x["mtype"] = x.city.map(muni_type)
    # 同じ時点・同じサービスで同じ法人名がいくつ事業所を持つか
    x["csize"] = x.groupby(["snap", "svc", "corp"]).id.transform("size")
    x["csize_c"] = pd.cut(x.csize, [0, 1, 4, 19, 1e9], labels=["1か所", "2〜4か所", "5〜19か所", "20か所以上"]).astype(str)
    x["sat"] = x.days.str.contains("土曜").astype(int); x["sun"] = x.days.str.contains("日曜").astype(int)
    x.to_pickle(p)
    return x


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
