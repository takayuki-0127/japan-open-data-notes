"""共通：国勢調査 時系列データ（従業地・通学地）第1表 夜間人口・昼間人口（1990〜2020年）を読む"""
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
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：総務省「国勢調査」時系列データ（従業地・通学地）（e-Stat）をもとに作成者が加工して作成"
XLSX = "125_jikeiretsu_hiruma.xlsx"
# 2015・2020年は「原数値」のシートを使う（1990〜2010年と同じ作り方）
SHEETS = {1990: "平成2年", 1995: "平成7年", 2000: "平成12年", 2005: "平成17年", 2010: "平成22年",
          2015: "平成27年_原数値", 2020: "令和2年_原数値"}
# 列の位置は年で違うので、見出し行（「総数(夜間人口)」のある行）から探す


def load(cache=True):
    GR = [(1990, 1995), (2000, 2005), (2010, 2020)]
    ps = [ROOT / "data" / f"day_night_{a}_{b}.csv" for a, b in GR]
    if cache and all(p.exists() for p in ps):
        return pd.concat([pd.read_csv(p, dtype={"code": str, "pref_code": str}) for p in ps], ignore_index=True)
    import openpyxl
    wb = openpyxl.load_workbook(RAW / XLSX, read_only=True, data_only=True)
    out = []
    for y, sh in SHEETS.items():
        rows = list(wb[sh].iter_rows(values_only=True))
        h = next(r for r in rows[:20] if r and "総数(夜間人口)" in [str(v) for v in r])
        lab = [str(v or "") for v in h]
        jn, jd = lab.index("総数(夜間人口)"), lab.index("総数(昼間人口)")
        jo1 = next(j for j in range(jn, jd) if lab[j].startswith("県内他市"))
        jo2 = next(j for j in range(jn, jd) if lab[j].startswith("他県で"))
        ji1 = next(j for j in range(jd, len(lab)) if "県内他市" in lab[j])
        ji2 = next(j for j in range(jd, len(lab)) if "他県に常住" in lab[j])
        def f(v):
            if isinstance(v, (int, float)): return float(v)
            return 0.0 if v == "-" else np.nan
        for r in rows:
            if not r or not isinstance(r[0], str) or not re.match(r"\d{4}年", r[0]): continue
            if not isinstance(r[3], str) or "_" not in r[3]: continue
            code, name = r[3].split("_", 1)
            pc, pn = str(r[2]).split("_", 1)
            out.append(dict(year=y, code=code, name=name, pref_code=pc[:2], pref=pn, night=f(r[jn]),
                            out_pref=f(r[jo1]), out_other=f(r[jo2]), day=f(r[jd]), in_pref=f(r[ji1]), in_other=f(r[ji2])))
    x = pd.DataFrame(out)
    # 区分：全国・都道府県・政令市（区の合計）・区・一般の市町村
    nxt = {}
    for y, g in x.groupby("year"):
        codes = set(g.code)
        for c in g.code:
            nxt[(y, c)] = str(int(c) + 1).zfill(5) in codes
    def kind(row):
        c = row.code
        if c == "00000": return "全国"
        if c.endswith("000"): return "都道府県"
        if row["name"].endswith("区部") or (c.endswith("0") and row["name"].endswith("市") and nxt.get((row.year, c)) and
                                              (x[(x.year == row.year) & (x.code == str(int(c) + 1).zfill(5))].name.str.endswith("区").any())):
            return "政令市"
        if row["name"].endswith("区"): return "区"
        return "市町村"
    x["kind"] = x.apply(kind, axis=1)
    x["ratio"] = x.day / x.night * 100
    for (a, b), p in zip(GR, ps):
        x[(x.year >= a) & (x.year <= b)].to_csv(p, index=False, encoding="utf-8-sig")
    return x


def units(x):
    """順位づけに使う単位：区（東京23区・政令市の区）と一般の市町村"""
    return x[x.kind.isin(["区", "市町村"])].copy()


def note(ax, text=SOURCE, y=-0.14):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
