"""共通：環境省・経済産業省 PRTR 個別事業所データ（ファイル記録事項）FY2001〜FY2024 を読む"""
from pathlib import Path
import io, re, zipfile, logging, warnings, unicodedata
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
SOURCE = "出典：環境省「PRTRインフォメーション広場」個別事業所のPRTRデータ（https://www.env.go.jp/chemi/prtr/kaiji/index.html）をもとに作成者が加工して作成"
CODES = [f"H{y:02d}" for y in range(13, 31)] + [f"R{y:02d}" for y in range(1, 7)]
FY = {c: (1988 + int(c[1:]) if c[0] == "H" else 2018 + int(c[1:])) for c in CODES}


def _name(i):
    try: return i.filename.encode("cp437").decode("cp932")
    except Exception: return i.filename


def _read(z, key):
    for i in z.infolist():
        n = _name(i)
        base = n.split("/")[-1]
        if base.startswith(key) and base.endswith(".txt") and "TITLE" not in base and "タイトル" not in base:
            return pd.read_csv(io.BytesIO(z.read(i)), header=None, dtype=str, encoding="cp932", encoding_errors="replace", keep_default_na=False)
    raise KeyError(key)


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"[\s\-‐－―ー−・,，.。()（）「」株式会社有限会社]", "", s)


def addr(s):
    s = unicodedata.normalize("NFKC", str(s)).replace(" ", "")
    s = re.sub(r"(丁目|番地の|番地|番の|番|号|の)", "-", s)
    s = re.sub(r"[ー‐－―−]", "-", s); s = re.sub(r"-+", "-", s).strip("-")
    return re.sub(r"^字", "", s)


def link(F):
    """整理番号は毎年振り直されるので、隣り合う年度の事業所を「所在地」または「事業所名＋市区町村」が同じなら同じ事業所とみなしてつなぎ、通しの番号 fid を振る（union-find）"""
    city = F.city.map(lambda s: unicodedata.normalize("NFKC", s).replace(" ", ""))
    F = F.assign(akey=F.pref + "|" + city + "|" + F.town.map(addr), skey=F.pref + "|" + city + "|" + F.site.map(norm))
    F["node"] = np.arange(len(F)); par = np.arange(len(F))
    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: par[rb] = ra
    yrs = sorted(F.fy.unique())
    for a, b in zip(yrs[:-1], yrs[1:]):
        A, B = F[F.fy == a], F[F.fy == b]
        for k in ["akey", "skey"]:
            m = A[[k, "node"]].merge(B[[k, "node"]], on=k)
            for x, y in zip(m.node_x.values, m.node_y.values): union(x, y)
        for k in ["akey", "skey"]:  # 同じ年度で所在地が同じ事業所もまとめる
            for g in (A, B):
                d = g[g.duplicated(k, keep=False)]
                for _, grp in d.groupby(k): [union(grp.node.iloc[0], n) for n in grp.node.iloc[1:]]
    F["fid"] = [find(i) for i in F.node]
    return F.drop(columns="node")


def load(cache=True):
    """事業所表 F（年×事業所）と物質表 S（年×事業所×物質、kg）を返す。ダイオキシン類（mg-TEQ）は除く"""
    pf, ps = ROOT / "data" / "fac.pkl", ROOT / "data" / "sub.pkl"
    if cache and pf.exists(): return pd.read_pickle(pf), pd.read_pickle(ps)
    Fs, Ss = [], []
    for c in CODES:
        z = zipfile.ZipFile(RAW / f"{c}PRTRdata.zip")
        h = _read(z, "本紙"); b = _read(z, "別紙")
        off = 1 if h.shape[1] >= 23 else 0
        F = pd.DataFrame({"fy": FY[c], "rid": h[0], "firm": h[10], "site": h[12 + off], "pref": h[15 + off], "city": h[16 + off],
                          "town": h[17 + off], "emp": pd.to_numeric(h[18 + off], errors="coerce"), "ind": h[19 + off], "indcode": h[20 + off]})
        F["key"] = (F.firm.map(norm) + "|" + F.site.map(norm) + "|" + F.pref + F.city.map(norm) + F.town.map(norm))
        num = lambda k: pd.to_numeric(b[k].str.replace(",", ""), errors="coerce").fillna(0)
        offsite = 15 if b.shape[1] > 16 else 14
        S = pd.DataFrame({"fy": FY[c], "rid": b[0], "sub": b[2].map(lambda s: unicodedata.normalize("NFKC", s)), "unit": b[4],
                          "air": num(5), "water": num(6), "soil": num(8), "landfill": num(9), "sewer": num(13), "offsite": num(offsite)})
        S = S[S.unit == "1"].drop(columns="unit")
        S["release"] = S[["air", "water", "soil", "landfill"]].sum(axis=1); S["transfer"] = S.sewer + S.offsite
        Fs.append(F); Ss.append(S)
        print(c, FY[c], len(F), len(S), round(S.release.sum() / 1e6, 1), "千t")
    F = link(pd.concat(Fs, ignore_index=True)); S = pd.concat(Ss, ignore_index=True)
    F.to_pickle(pf); S.to_pickle(ps)
    return F, S


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
