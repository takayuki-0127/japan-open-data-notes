"""共通：観光庁「宿泊旅行統計調査」（e-Stat）の年次ファイルを読み、都道府県×月の延べ宿泊者数（総数・外国人）と国籍別の外国人延べ宿泊者数を作る"""
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：観光庁「宿泊旅行統計調査」（e-Stat）を加工して作成"
YEARS = range(2011, 2026)   # 従業者数9人以下の施設を含む通年の値がある年（2010年4月から調査対象を拡大）
NAT_YEARS = range(2015, 2026)
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県",
         "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県",
         "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県",
         "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
# 三大都市圏（首都圏・中京圏・近畿圏）の8都府県
METRO = ["埼玉県", "千葉県", "東京都", "神奈川県", "愛知県", "京都府", "大阪府", "兵庫県"]


def raw_file(y):
    return RAW / (f"shuku_{y}.xls" if y < 2015 else f"shuku_{y}.xlsx")


def _num(v):
    return pd.to_numeric(v, errors="coerce")


def _name(v):
    return re.sub(r"[\s　\d]", "", str(v))


def _pref_rows(d):
    """北海道〜沖縄県の47行（最初に出てくるもの）の行番号"""
    names = d.iloc[:, 0].map(_name).tolist()
    i0 = names.index("北海道")
    rows = list(range(i0, i0 + 47))
    assert [names[i] for i in rows] == PREFS, names[i0:i0 + 47]
    return rows, i0


def _parse_t2(d):
    rows, i0 = _pref_rows(d)
    head = d.iloc[:i0].map(str)
    fcol = [j for j in range(d.shape[1]) if any("外国人" in v and "うち" in v for v in head.iloc[:, j])]
    assert len(fcol) == 1, fcol
    tot = _num(d.iloc[rows, 1]).values
    fo = _num(d.iloc[rows, fcol[0]]).values
    nat = _num(d.iloc[i0 - 1, [1, fcol[0]]]).values  # 全国の行
    return tot, fo, nat


def build_monthly():
    """data/pref_month.csv：年・月・都道府県ごとの延べ宿泊者数（総数・外国人・日本人＝総数−外国人、人泊）"""
    out = []
    for y in YEARS:
        x = pd.ExcelFile(raw_file(y))
        for m in range(1, 13):
            s = [n for n in x.sheet_names if re.fullmatch(rf"第2表[\(（]{m}月[\)）]", n)][0]
            tot, fo, nat = _parse_t2(pd.read_excel(x, s, header=None))
            # 都道府県の合計と全国の行が合うか（四捨五入の差のみ）
            assert abs(np.nansum(tot) - nat[0]) <= 1000 and abs(np.nansum(fo) - nat[1]) <= 1000, (y, m, nat, np.nansum(tot), np.nansum(fo))
            for p, t, f in zip(PREFS, tot, fo):
                out.append((y, m, p, t, f))
    df = pd.DataFrame(out, columns=["year", "month", "pref", "total", "foreign"])
    df["japanese"] = df["total"] - df["foreign"]
    df[["total", "foreign", "japanese"]] = df[["total", "foreign", "japanese"]].astype("int64")
    return df


def build_nationality():
    """data/pref_nationality.csv：年・都道府県・国籍（出身地）ごとの外国人延べ宿泊者数（従業者数10人以上の施設、年計）"""
    out = []
    for y in NAT_YEARS:
        d = pd.read_excel(raw_file(y), "参考第1表(年計)", header=None)
        rows, i0 = _pref_rows(d)
        hr = [i for i in range(i0) if "韓国" in [str(v).strip() for v in d.iloc[i]]][0]
        cats = [(j, str(d.iat[hr, j]).strip()) for j in range(2, d.shape[1]) if str(d.iat[hr, j]).strip() not in ("nan", "")]
        for i, p in zip(rows, PREFS):
            out.append((y, p, "計", _num(d.iat[i, 1])))
            for j, c in cats:
                out.append((y, p, c, _num(d.iat[i, j])))
    df = pd.DataFrame(out, columns=["year", "pref", "nationality", "foreign"])
    df["foreign"] = df["foreign"].fillna(0).astype("int64")
    return df


def load_monthly():
    p = DATA / "pref_month.csv"
    if not p.exists():
        build_monthly().to_csv(p, index=False)
    return pd.read_csv(p)


def load_nationality():
    p = DATA / "pref_nationality.csv"
    if not p.exists():
        build_nationality().to_csv(p, index=False)
    return pd.read_csv(p)


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def note(ax, text=SOURCE, y=-0.16):
    ax.annotate(text, xy=(0, y), xycoords="axes fraction", fontsize=8, color="#555555", ha="left", va="top")
