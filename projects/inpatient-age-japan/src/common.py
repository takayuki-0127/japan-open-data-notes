"""共通：厚生労働省「患者調査」年次推移表（第2表 推計患者数・第4表 受療率、性・年齢階級別）を読む"""
from pathlib import Path
import re, logging, warnings, io
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
RAW, DATA, FIG, RES = ROOT / "data" / "raw", ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：厚生労働省「患者調査」年次推移表（e-Stat）をもとに作成者が加工して作成"
PAT = ["131_Z_242.csv", "131_Z_243.csv", "131_Z_244.csv", "131_Z_245.csv"]   # 第2表 推計患者数（千人）
RATE = ["131_Z_248.csv", "131_Z_249.csv", "131_Z_250.csv", "131_Z_251.csv"]  # 第4表 受療率（人口10万対）
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}
# 年齢階級の代表値（中央。上の開いた階級は仮定）
OPEN_TOP = {"75歳以上": 82.0, "80歳以上": 85.0, "85歳以上": 88.5, "90歳以上": 92.5}


def _years(cells):
    out, era = [], None
    for c in cells:
        c = c.strip()
        m = re.match(r"(昭和|平成|令和)?(\d+)年", c)
        if not m:
            out.append(None); continue
        if m.group(1): era = m.group(1)
        out.append(ERA[era] + int(m.group(2)))
    return out


def _age_range(lab):
    lab = lab.strip().replace(" ", "")
    z = str.maketrans("０１２３４５６７８９", "0123456789")
    lab = lab.translate(z)
    if lab == "0歳": return (0, 1)
    m = re.match(r"(\d+)～(\d+)$", lab)
    if m: return (int(m.group(1)), int(m.group(2)) + 1)
    m = re.match(r"(\d+)歳以上$", lab)
    if m: return (int(m.group(1)), None)
    return None


def _ensure_raw():
    """data/raw が無ければ data/raw.zip から展開する"""
    if not (RAW / PAT[0]).exists() and (DATA / "raw.zip").exists():
        import zipfile
        RAW.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(DATA / "raw.zip").extractall(RAW)


def read_table(files):
    """→ long: year, kind(総数/入院/外来), age_label, lo, hi, value"""
    recs = []
    for fn in files:
        txt = (RAW / fn).read_bytes().decode("cp932", errors="replace")
        rows = [r.split(",") for r in txt.splitlines()]
        years, kind = None, None
        for r in rows:
            if len(r) > 1 and re.search(r"(昭和|平成|令和)\d+年", ",".join(r[1:3])):
                years = _years(r[1:])
                continue
            head = r[0].replace("　", "").replace(" ", "").strip()
            if head in ("総数", "入院", "外来") and all(x.strip() == "" for x in r[1:]):
                kind = head; continue
            if years is None or kind is None: continue
            rg = _age_range(r[0])
            if rg is None: continue
            for y, v in zip(years, r[1:]):
                if y is None: continue
                v = v.strip()
                try: val = float(v)
                except ValueError: continue
                recs.append(dict(year=y, kind=kind, age=r[0].strip().translate(str.maketrans("０１２３４５６７８９", "0123456789")),
                                 lo=rg[0], hi=rg[1], value=val))
    df = pd.DataFrame(recs).drop_duplicates(["year", "kind", "age"])
    return df


def load():
    p = DATA / "patients_by_age.csv"
    if p.exists():
        return pd.read_csv(p)
    _ensure_raw()
    pat = read_table(PAT).rename(columns={"value": "patients_k"})
    rate = read_table(RATE).rename(columns={"value": "rate_per100k"})
    df = pat.merge(rate[["year", "kind", "age", "rate_per100k"]], on=["year", "kind", "age"], how="left")
    df = df.sort_values(["kind", "year", "lo"])
    df.to_csv(p, index=False)
    return df


def mid(lo, hi, lab):
    if hi is None or (isinstance(hi, float) and np.isnan(hi)):
        return OPEN_TOP.get(lab, lo + 5)
    return (lo + hi) / 2


def summarize(df, kind):
    """年ごとに平均年齢・65歳以上・75歳以上の割合（年齢不詳を除く）"""
    out = []
    for y, g in df[df.kind == kind].groupby("year"):
        g = g.copy()
        g["mid"] = [mid(a, b, l) for a, b, l in zip(g.lo, g.hi, g.age)]
        # 細かい階級だけ残す（重なりは無い前提）
        tot = g.patients_k.sum()
        if tot <= 0: continue
        mean = (g.mid * g.patients_k).sum() / tot
        s65 = g[g.lo >= 65].patients_k.sum() / tot
        s75 = g[g.lo >= 75].patients_k.sum() / tot
        # 人口（推計患者数÷受療率）から人口の平均年齢も
        gg = g.dropna(subset=["rate_per100k"])
        gg = gg[gg.rate_per100k > 0]
        if len(gg) == len(g):
            pop = gg.patients_k * 1000 / gg.rate_per100k * 1e5
            pmean = (gg.mid * pop).sum() / pop.sum()
            p65 = pop[gg.lo >= 65].sum() / pop.sum(); p75 = pop[gg.lo >= 75].sum() / pop.sum()
        else:
            pmean = p65 = p75 = np.nan
        out.append(dict(year=y, kind=kind, patients_k=round(tot, 1), mean_age=round(mean, 1), share65=round(100 * s65, 1),
                        share75=round(100 * s75, 1), pop_mean_age=round(pmean, 1) if pmean == pmean else np.nan,
                        pop_share65=round(100 * p65, 1) if p65 == p65 else np.nan,
                        pop_share75=round(100 * p75, 1) if p75 == p75 else np.nan, top_class=g.loc[g.lo.idxmax(), "age"]))
    return pd.DataFrame(out)
