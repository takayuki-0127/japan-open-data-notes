"""法人企業統計調査（年次別調査）統計表2 の読み込み（全産業＝金融業・保険業以外）"""
import os, re, glob
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

ITEMS = {  # 出力名: 表の項目名（最初に出てくる行）
    "cash": "現金・預金", "securities_current": "有価証券", "inventory": "棚卸資産",
    "tangible": "有形固定資産", "land": "土地", "inv_securities": "投資有価証券",
    "total_assets": "資産合計", "retained": "利益剰余金", "capital": "資本金",
    "sales": "売上高", "ordinary_profit": "経常利益", "net_income": "当期純利益",
    "dividends": "配当金", "employee_pay": "従業員給与",
}
EQUITY = ("純資産", "資本")  # 2006年度は「資本」、のちに「純資産」


def _norm(s):
    return re.sub(r"[\s　]", "", str(s)) if isinstance(s, str) else ""


def _engine(path):
    return "xlrd" if open(path, "rb").read(4) == b"\xd0\xcf\x11\xe0" else "openpyxl"


def size_group(col):
    """資本金階級（百万円）→ 3区分"""
    c = _norm(col).replace(",", "")
    if c == "総額":
        return "total"
    m = re.match(r"(\d+)(?:～(\d+))?(未満|以上)", c)
    if not m:
        return None
    lo = 0 if m.group(2) is None and m.group(3) == "未満" else int(m.group(1))
    if m.group(3) == "以上":
        lo = int(m.group(1))
    if lo >= 1000:
        return "large"     # 10億円以上
    if lo >= 100:
        return "medium"    # 1億〜10億円未満
    return "small"         # 1億円未満


def read_year(path, sheet="全産業"):
    df = pd.read_excel(path, sheet_name=sheet, header=None, engine=_engine(path))
    # 見出し行（「総額」を含む行）とデータ開始列
    hr = next(i for i in range(10) if any(_norm(v) == "総額" for v in df.iloc[i]))
    c0 = next(j for j, v in enumerate(df.iloc[hr]) if _norm(v) == "総額")
    groups = {j: size_group(df.iloc[hr, j]) for j in range(c0, df.shape[1])}
    labels = df.iloc[:, :c0].apply(lambda r: "".join(_norm(v) for v in r), axis=1)
    out = {}
    for key, lab in list(ITEMS.items()) + [("equity", None)]:
        if key == "equity":
            idx = [i for i in range(hr + 1, len(df)) if labels[i] in EQUITY]
        else:
            idx = [i for i in range(hr + 1, len(df)) if labels[i] == lab]
        if not idx:
            continue
        i = idx[0]
        for j, g in groups.items():
            if g is None:
                continue
            v = pd.to_numeric(df.iloc[i, j], errors="coerce")
            if pd.isna(v):
                continue
            out[(g, key)] = out.get((g, key), 0) + float(v)
    rows = [{"size": g, "item": k, "value_million_yen": v} for (g, k), v in out.items()]
    return pd.DataFrame(rows)


def build_panel():
    files = sorted(glob.glob(os.path.join(RAW, "143_*.k0")))
    if not files:
        raise SystemExit("data/raw に e-Stat の統計表2（143_YYYY.k0）を置いてください（README 参照）")
    frames = []
    for f in files:
        fy = int(re.search(r"(\d{4})", os.path.basename(f)).group(1))
        d = read_year(f)
        d.insert(0, "fiscal_year", fy)
        frames.append(d)
    p = pd.concat(frames, ignore_index=True)
    p.to_csv(os.path.join(DATA, "bs_pl_by_size.csv"), index=False)
    return p


def load_panel():
    path = os.path.join(DATA, "bs_pl_by_size.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return build_panel()
