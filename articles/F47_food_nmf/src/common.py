"""共通の設定（パス・フォント・乱数の種・地方の並び）"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# 小計・合計の行（下位の品目の合計なので、分析からは外す）
AGG = {"穀類", "パン", "麺類", "他の穀類", "魚介類", "生鮮魚介", "鮮魚", "貝類", "塩干魚介", "魚肉練製品",
       "他の魚介加工品", "肉類", "生鮮肉", "加工肉", "乳卵類", "乳製品", "野菜・海藻", "生鮮野菜", "葉茎菜",
       "根菜", "他の野菜", "乾物・海藻", "大豆加工品", "他の野菜・海藻加工品", "果物", "生鮮果物",
       "油脂・調味料", "油脂", "調味料", "菓子類", "調理食品", "主食的調理食品", "他の調理食品", "飲料",
       "茶類", "コーヒー・コーヒー飲料", "コーヒー・ココア", "他の飲料", "酒類", "外食", "一般外食", "食事代"}
# 好みではなく制度で決まる品目
EXCLUDE = {"学校給食"}

# 都市の並び（北から）と地方
REGION = [
    ("北海道・東北", ["札幌市", "青森市", "盛岡市", "仙台市", "秋田市", "山形市", "福島市"]),
    ("関東", ["水戸市", "宇都宮市", "前橋市", "さいたま市", "千葉市", "東京都区部", "横浜市", "川崎市", "相模原市"]),
    ("北陸・甲信", ["新潟市", "富山市", "金沢市", "福井市", "甲府市", "長野市"]),
    ("東海", ["岐阜市", "静岡市", "浜松市", "名古屋市", "津市"]),
    ("近畿", ["大津市", "京都市", "大阪市", "堺市", "神戸市", "奈良市", "和歌山市"]),
    ("中国・四国", ["鳥取市", "松江市", "岡山市", "広島市", "山口市", "徳島市", "高松市", "松山市", "高知市"]),
    ("九州・沖縄", ["北九州市", "福岡市", "佐賀市", "長崎市", "熊本市", "大分市", "宮崎市", "鹿児島市", "那覇市"]),
]
CITIES = [c for _, cs in REGION for c in cs]
CITY_REGION = {c: r for r, cs in REGION for c in cs}
