"""共通：経済産業省「商業動態統計」の時系列データ（e-Stat）を読む

data/ の CSV があればそれを使う。無いときは data/raw/ の Excel（e-Stat「■時系列データ」）から作り直す。
"""
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6", "#c8402f"
SOURCE = "出典：経済産業省「商業動態統計」（e-Stat）を加工して作成"

# 生データ（e-Stat「■時系列データ」の Excel）→ 系列名の頭につける業態名と、読むシート
RAW_FILES = {
    "業種別": ("業種別商業販売額", {"value": "販売額（value）(月次M)", "yoy": "前年比（change）(月次M)",
                              "value_y": "販売額（value）(年CY)", "yoy_y": "前年比（change）(年CY)"}),
    "百貨店・スーパー": ("百貨店・スーパー商品別販売額", None),
    "コンビニ": ("コンビニエンスストア商品別販売額等", None),
    "家電大型専門店": ("家電大型専門店商品別販売額等", None),
    "ドラッグストア": ("ドラッグストア商品別販売額等", None),
    "ホームセンター": ("ホームセンター商品別販売額等", None),
}
UNIT_WORDS = {"百万円", "million yen", "10億円", "billion yen", "%", "店", "Establishments", "Number of establishments", "nan"}


def _num(v):
    if isinstance(v, (int, float, np.number)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return np.nan


def parse_sheet(path, sheet):
    """表頭の「時間軸コード」を目印に、期間×系列の表にする（月次なら年月、年次なら年）"""
    d = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    hit = [(r, c) for r in range(min(20, len(d))) for c in range(d.shape[1]) if str(d.iat[r, c]).strip() == "時間軸コード"]
    r0, c0 = hit[0]
    names = {}
    for c in range(c0 + 2, d.shape[1]):
        for r in range(r0 - 1, -1, -1):
            v = str(d.iat[r, c]).strip()
            if v and v not in UNIT_WORDS and not v.isascii():
                names[c] = v
                break
    rows = []
    for r in range(r0 + 1, len(d)):
        lab = str(d.iat[r, c0 + 1])
        m = re.match(r"^(\d{4})年(\d{1,2})月$", lab) or re.match(r"^(\d{4})年$", lab)
        if not m:
            continue
        key = pd.Period(year=int(m.group(1)), month=int(m.group(2)), freq="M") if m.lastindex == 2 else int(m.group(1))
        rows.append([key] + [_num(d.iat[r, c]) for c in names])
    out = pd.DataFrame(rows, columns=["t"] + list(names.values())).set_index("t")
    return out.loc[:, ~out.columns.duplicated()]


def _sheets_for(path, kind):
    """業態別ファイルのシート名（kind: value / yoy / value_y / yoy_y）"""
    xs = pd.ExcelFile(path).sheet_names
    if kind == "value":
        return [s for s in xs if re.search(r"販売額.*月次", s) and "局別" not in s]
    if kind == "value_y":
        return [s for s in xs if re.search(r"販売額.*(年\(CY\)|　年$|年CY)", s) and "局別" not in s]
    if kind == "yoy":
        return [s for s in xs if re.search(r"(前年同月比|伸び率　月次)", s) and "局別" not in s]
    return [s for s in xs if re.search(r"(前年比\(change\)\(CY\)|伸び率　年$)", s) and "局別" not in s]


def build_from_raw():
    """data/raw/shogyo_ts_00〜06.xlsx から4つの CSV を作る"""
    files = {"業種別": "shogyo_ts_00.xlsx", "百貨店・スーパー": "shogyo_ts_02.xlsx", "コンビニ": "shogyo_ts_03.xlsx",
             "家電大型専門店": "shogyo_ts_04.xlsx", "ドラッグストア": "shogyo_ts_05.xlsx", "ホームセンター": "shogyo_ts_06.xlsx"}
    out = {k: [] for k in ["value", "yoy", "value_y", "yoy_y"]}
    for gyo, fn in files.items():
        p = RAW / fn
        for kind in out:
            if gyo == "業種別":
                sheets = [RAW_FILES["業種別"][1][kind]]
            else:
                sheets = _sheets_for(p, kind)
            for s in sheets:
                t = parse_sheet(p, s)
                if gyo == "百貨店・スーパー":
                    pre = s.split("　")[0]  # 合計／百貨店／スーパー
                    pre = "百貨店・スーパー" if pre == "合計" else pre
                else:
                    pre = gyo
                t.columns = [f"{pre}|{c}" for c in t.columns]
                out[kind].append(t)
    for kind, lst in out.items():
        df = pd.concat(lst, axis=1)
        df = df.loc[:, ~df.columns.duplicated()].sort_index()
        df.index.name = "年月" if kind in ("value", "yoy") else "年"
        df.to_csv(DATA / f"{'monthly' if kind in ('value', 'yoy') else 'annual'}_{'value' if kind.startswith('value') else 'yoy'}.csv",
                  encoding="utf-8")


def load(kind="monthly_value"):
    """kind: monthly_value / monthly_yoy / annual_value / annual_yoy"""
    p = DATA / f"{kind}.csv"
    if not p.exists():
        build_from_raw()
    df = pd.read_csv(p, index_col=0)
    if kind.startswith("monthly"):
        df.index = pd.PeriodIndex(df.index, freq="M")
    return df


def growth_factor(s):
    """公表の前年同月（同年）比を倍率にする。100基準（例：103.1）と増減率（例：3.1）の両方に対応"""
    s = s.astype(float)
    med = s.dropna().median()
    return s / 100 if med > 50 else 1 + s / 100


def chain_annual(yoy, base_year):
    """前年比をつないだ指数（base_year=100）。水準の断層（調査対象の見直し）の影響を受けない"""
    f = growth_factor(yoy).dropna()
    idx = pd.Series(np.nan, index=range(int(f.index.min()) - 1, int(f.index.max()) + 1), dtype=float)
    idx[int(f.index.min()) - 1] = 1.0
    for y in range(int(f.index.min()), int(f.index.max()) + 1):
        idx[y] = idx[y - 1] * f.get(y, np.nan)
    return idx / idx[base_year] * 100


def vs_2019(yoy_m):
    """月次の前年同月比をつないで「2019年同月＝100」の値にする（2020年1月以降）"""
    f = growth_factor(yoy_m)
    out = {}
    for p in f.index:
        if p.year < 2020:
            continue
        v = 1.0
        for y in range(2020, p.year + 1):
            v *= f.get(pd.Period(year=y, month=p.month, freq="M"), np.nan)
        out[p] = v * 100
    return pd.Series(out)


def backcast_monthly(value, yoy_m):
    """最新の水準から、前年同月比で12か月ずつさかのぼった月次系列（調査対象の見直しなどによる水準の断層を除く）"""
    v = value.astype(float).copy()
    f = growth_factor(yoy_m).reindex(v.index)
    last = v.dropna().index.max()
    out = pd.Series(np.nan, index=v.index)
    out[last - 11:last] = v[last - 11:last]
    for p in sorted(v.index[v.index <= last - 12], reverse=True):
        nxt = p + 12
        if not np.isnan(out.get(nxt, np.nan)) and not np.isnan(f.get(nxt, np.nan)):
            out[p] = out[nxt] / f[nxt]
    return out


def note(ax, text=SOURCE, y=-0.16):
    ax.annotate(text, xy=(0, y), xycoords="axes fraction", fontsize=8, color=GRAY, ha="left", va="top")
