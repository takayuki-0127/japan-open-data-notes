"""共通：農林水産省「海面漁業生産統計調査」（漁業・養殖業生産統計）の魚種別漁獲量を読む"""
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
DATA = ROOT / "data"
RAW, FIG, RES = DATA / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：農林水産省「海面漁業生産統計調査」（e-Stat）を加工して作成"

# 海に面した39都道府県（累年統計ファイル gyo_43〜gyo_81 の順）と県庁所在地の緯度
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "千葉", "東京", "神奈川", "新潟", "富山", "石川",
         "福井", "静岡", "愛知", "三重", "京都", "大阪", "兵庫", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島",
         "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
LAT = dict(zip(PREFS, [43.06, 40.82, 39.70, 38.27, 39.72, 38.24, 37.75, 36.34, 35.61, 35.69, 35.45, 37.90, 36.70, 36.59,
                       36.07, 34.98, 35.18, 34.73, 35.02, 34.69, 34.69, 34.23, 35.50, 35.47, 34.66, 34.40, 34.19, 34.07,
                       34.34, 33.84, 33.56, 33.61, 33.25, 32.74, 32.79, 33.24, 31.91, 31.56, 26.21]))
REGION = {"北海道": "北海道"}
REGION.update({p: "東北" for p in ["青森", "岩手", "宮城", "秋田", "山形", "福島"]})
REGION.update({p: "関東・東海" for p in ["茨城", "千葉", "東京", "神奈川", "静岡", "愛知", "三重"]})
REGION.update({p: "北陸" for p in ["新潟", "富山", "石川", "福井"]})
REGION.update({p: "近畿・中国・四国" for p in ["京都", "大阪", "兵庫", "和歌山", "鳥取", "島根", "岡山", "広島", "山口",
                                         "徳島", "香川", "愛媛", "高知"]})
REGION.update({p: "九州・沖縄" for p in ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]})
REGIONS = ["北海道", "東北", "北陸", "関東・東海", "近畿・中国・四国", "九州・沖縄"]
# 年別の都道府県表（2003年以降）から取り出す魚種
PREF_SPECIES = {"ぶり類": "ぶり", "さんま": "さんま", "さけ類": "さけ類", "するめいか": "するめいか", "まいわし": "まいわし"}

N = lambda v: re.sub(r"[\s　]", "", str(v)) if pd.notna(v) else ""


def _num(v):
    s = N(v).replace(",", "")
    if s in ("-", "－", "―", "0"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return np.nan  # …（調査なし）、x（秘匿）など


def _year(v):
    m = re.search(r"\((\d{4})\)", N(v))
    return int(m.group(1)) if m else None


def _cumulative(path):
    """累年統計（全国・都道府県）：年×魚種の表"""
    df = pd.read_excel(path, header=None)
    labs = [re.sub(r"t$", "", "".join(N(df.iat[r, c]) for r in range(4, 8))) for c in range(df.shape[1])]
    rows = []
    for r in range(8, df.shape[0]):
        y = _year(df.iat[r, 0])
        if y:
            rows.append([y] + [_num(df.iat[r, c]) for c in range(1, df.shape[1])])
    d = pd.DataFrame(rows, columns=["year"] + labs[1:]).set_index("year")
    return d.loc[:, ~d.columns.duplicated()]


def _annual_pref(path):
    """年別「大海区都道府県振興局別 魚種別漁獲量」：都道府県×魚種"""
    df = pd.read_excel(path, header=None)
    lc = 0 if any(N(v) == "全国" for v in df.iloc[:30, 0]) else 1
    col = [N(v) for v in df.iloc[:, lc]]
    start = col.index("全国")
    labs = ["".join(N(df.iat[r, c]) for r in range(start)) for c in range(df.shape[1])]
    out = {}
    for name, key in [("漁獲量計", "合計")] + list(PREF_SPECIES.items()):
        c = [i for i, l in enumerate(labs) if key in l]
        if key == "さけ類":
            c = [i for i in c if "ます" not in labs[i]]
        out[name] = c[0]
    rows = []
    for p in ["全国"] + PREFS:
        r = col.index(p, start)
        rows.append({"pref": p, **{k: _num(df.iat[r, c]) for k, c in out.items()}})
    return pd.DataFrame(rows)


def build():
    """data/ の整形済みCSVを作る（無ければ data/raw/ の Excel から）"""
    f1, f2, f3 = DATA / "national_species.csv", DATA / "pref_species.csv", DATA / "sst_japan.csv"
    if f1.exists() and f2.exists() and f3.exists():
        return
    nat = _cumulative(RAW / "gyo_02.xlsx")
    nat.reset_index().melt(id_vars="year", var_name="species", value_name="t").dropna().to_csv(f1, index=False)
    # 都道府県：1956〜2015年は累年統計、2003〜2024年は年別の表
    rows = []
    for i, p in enumerate(PREFS):
        d = _cumulative(RAW / f"gyo_{43 + i}.xls")
        for y, r in d.iterrows():
            rows.append({"year": y, "pref": p, "src": "累年", "漁獲量計": r["漁獲量計"],
                         **{k: r.get(k, np.nan) for k in PREF_SPECIES}})
    for f in sorted(glob.glob(str(RAW / "gyopref_*"))):
        y = int(re.search(r"(\d{4})", Path(f).name).group(1))
        a = _annual_pref(f)
        a = a[a.pref != "全国"]
        for _, r in a.iterrows():
            rows.append({"year": y, "src": "年別", **r.to_dict()})
    pd.DataFrame(rows).to_csv(f2, index=False)
    # 海面水温（気象庁、日本近海13海域平均と3海域の年平均の平年差）
    ss = []
    for a, name in [("all", "日本近海平均"), ("F", "日本海中部"), ("G", "日本海北東部"), ("K", "三陸沖")]:
        lines = open(RAW / f"sst_area{a}.txt").read().splitlines()
        i = [k for k, ln in enumerate(lines) if ln.startswith("Year")][0]
        for ln in lines[i + 1:]:
            p = [x.strip() for x in ln.split(",")]
            if len(p) > 1 and p[0].isdigit() and p[1] not in ("NoData", ""):
                ss.append({"year": int(p[0]), "area": name, "sst_anom": float(p[1])})
    pd.DataFrame(ss).to_csv(f3, index=False)


def national():
    build()
    return pd.read_csv(DATA / "national_species.csv").pivot(index="year", columns="species", values="t")


def pref(prefer="年別"):
    """都道府県×年。重なる2003〜2015年は prefer 側を使う"""
    build()
    d = pd.read_csv(DATA / "pref_species.csv")
    other = "累年" if prefer == "年別" else "年別"
    a = d[d.src == prefer]
    b = d[(d.src == other) & ~d.year.isin(a.year.unique())]
    return pd.concat([b, a]).sort_values(["year", "pref"]).reset_index(drop=True)


def sst():
    build()
    return pd.read_csv(DATA / "sst_japan.csv").pivot(index="year", columns="area", values="sst_anom")


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=8, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
