"""共通：国立健康危機管理研究機構「感染症発生動向調査週報（IDWR）」速報データ（2023年第1週〜2026年第41週）を読む"""
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
# 週ごとの CSV（394本）は GitHub では data/idwr_raw.zip にまとめて置いている。初回に展開する
if not any(RAW.glob("*-teiten.csv")) and (ROOT / "data" / "idwr_raw.zip").exists():
    import zipfile
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(ROOT / "data" / "idwr_raw.zip").extractall(RAW)
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：国立健康危機管理研究機構「感染症発生動向調査週報（IDWR）」速報データ（https://id-info.jihs.go.jp/surveillance/idwr/）をもとに作成者が加工して作成"
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
         "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
         "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
# 県庁所在地のおおよその緯度経度
CAP = {"北海道": (43.06, 141.35), "青森県": (40.82, 140.74), "岩手県": (39.70, 141.15), "宮城県": (38.27, 140.87), "秋田県": (39.72, 140.10),
       "山形県": (38.24, 140.36), "福島県": (37.75, 140.47), "茨城県": (36.34, 140.45), "栃木県": (36.57, 139.88), "群馬県": (36.39, 139.06),
       "埼玉県": (35.86, 139.65), "千葉県": (35.61, 140.12), "東京都": (35.69, 139.69), "神奈川県": (35.45, 139.64), "新潟県": (37.90, 139.02),
       "富山県": (36.70, 137.21), "石川県": (36.59, 136.63), "福井県": (36.07, 136.22), "山梨県": (35.66, 138.57), "長野県": (36.65, 138.18),
       "岐阜県": (35.39, 136.72), "静岡県": (34.98, 138.38), "愛知県": (35.18, 136.91), "三重県": (34.73, 136.51), "滋賀県": (35.00, 135.87),
       "京都府": (35.02, 135.76), "大阪府": (34.69, 135.52), "兵庫県": (34.69, 135.18), "奈良県": (34.69, 135.83), "和歌山県": (34.23, 135.17),
       "鳥取県": (35.50, 134.24), "島根県": (35.47, 133.05), "岡山県": (34.66, 133.93), "広島県": (34.40, 132.46), "山口県": (34.19, 131.47),
       "徳島県": (34.07, 134.56), "香川県": (34.34, 134.04), "愛媛県": (33.84, 132.77), "高知県": (33.56, 133.53), "福岡県": (33.61, 130.42),
       "佐賀県": (33.25, 130.30), "長崎県": (32.74, 129.87), "熊本県": (32.79, 130.74), "大分県": (33.24, 131.61), "宮崎県": (31.91, 131.42),
       "鹿児島県": (31.56, 130.56), "沖縄県": (26.21, 127.68)}
SHORT = {"インフルエンザ": "インフルエンザ", "ＲＳウイルス感染症": "RSウイルス", "咽頭結膜熱": "咽頭結膜熱", "Ａ群溶血性レンサ球菌咽頭炎": "A群溶連菌咽頭炎",
         "感染性胃腸炎": "感染性胃腸炎", "手足口病": "手足口病", "伝染性紅斑": "伝染性紅斑", "ヘルパンギーナ": "ヘルパンギーナ",
         "マイコプラズマ肺炎": "マイコプラズマ肺炎", "COVID-19": "COVID-19", "水痘": "水痘", "突発性発しん": "突発性発しん",
         "流行性耳下腺炎": "流行性耳下腺炎", "流行性角結膜炎": "流行性角結膜炎"}


def _num(x):
    x = str(x).strip()
    return np.nan if x in ("", "-", "nan") else float(x.replace(",", ""))


def _header(path):
    t = open(path, encoding="cp932").read().split("\n")[1]
    m = re.search(r"(\d{4})年(\d+)週\((\d+)月(\d+)日～(\d+)月(\d+)日\)", t)
    y, w, m1, d1 = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    start = pd.Timestamp(year=y if not (w == 1 and m1 == 12) else y - 1, month=m1, day=d1)
    return y, w, start


def load_teiten(cache=True):
    p = ROOT / "data" / "teiten.pkl"
    if cache and p.exists(): return pd.read_pickle(p)
    out = []
    for f in sorted(glob.glob(str(RAW / "*-teiten.csv"))):
        y, w, start = _header(f)
        d = pd.read_csv(f, encoding="cp932", header=None, skiprows=2, dtype=str)
        dis = d.iloc[0].ffill().tolist(); kind = d.iloc[1].tolist()
        body = d.iloc[2:]
        for j in range(1, d.shape[1], 2):
            name = dis[j]
            if not isinstance(name, str) or kind[j] != "報告": continue
            for _, r in body.iterrows():
                pref = str(r[0]).strip()
                if pref not in PREFS and pref != "総数": continue
                out.append((y, w, start, pref, name, _num(r[j]), _num(r[j + 1])))
    x = pd.DataFrame(out, columns=["year", "week", "start", "pref", "disease", "n", "per"])
    x.to_pickle(p)
    return x


def load_zensu(cache=True):
    """全数把握疾患：各週の報告数と、年初からの累積"""
    p = ROOT / "data" / "zensu.pkl"
    if cache and p.exists(): return pd.read_pickle(p)
    out = []
    for f in sorted(glob.glob(str(RAW / "*-zensu.csv"))):
        y, w, start = _header(f)
        import csv
        rows = list(csv.reader(open(f, encoding="cp932")))[2:]
        dis = pd.Series([c if c else None for c in rows[0]]).ffill().tolist(); kind = rows[1]
        for j in range(1, len(kind) - 1):
            if kind[j] != "報告" or not isinstance(dis[j], str): continue
            for r in rows[2:]:
                if not r: continue
                pref = r[0].strip()
                if pref not in PREFS and pref != "総数": continue
                out.append((y, w, start, pref, dis[j], _num(r[j]), _num(r[j + 1]) if j + 1 < len(r) else np.nan))
    x = pd.DataFrame(out, columns=["year", "week", "start", "pref", "disease", "n", "cum"])
    x.to_pickle(p)
    return x


def population():
    d = pd.read_csv(RAW / "SSDSE-E-2026.csv", encoding="cp932", header=None, skiprows=3)
    return pd.Series(pd.to_numeric(d[2], errors="coerce").values, index=d[1].str.strip()).loc[PREFS]


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
