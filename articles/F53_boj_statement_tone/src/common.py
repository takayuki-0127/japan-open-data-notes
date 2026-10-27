"""共通の設定（パス・フォント・乱数の種・辞書）"""
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
for p in (DATA, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

# 公表文の全文（会合ごとの JSON）。氏名を含むので GitHub には置かない。01_取得 で作り直す
STATEMENTS_JSON = Path(os.environ.get("F53_STATEMENTS", RAW / "f53_boj_statements.json"))
# 埋め込みモデル（cl-nagoya/ruri-v3-30m）。ネットにつながらない環境では手元のフォルダを RURI_PATH で指定する
MODEL = os.environ.get("RURI_PATH", "cl-nagoya/ruri-v3-30m")

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# ---- 辞書（景気の判断の文に出てくる語）。表記ゆれは部分一致で拾う ----
POS = ["回復", "改善", "持ち直", "増加", "拡大", "底堅", "堅調", "しっかり", "強まっ", "強めの",
       "上向", "好転", "高水準", "緩やかに成長", "成長して"]
NEG = ["悪化", "減少", "弱い", "弱め", "弱まっ", "弱含", "低迷", "停滞", "下押し", "減速",
       "落ち込", "厳し", "下落", "足踏み", "鈍化", "調整", "下げ止", "横ばい", "慎重", "不透明",
       "大幅に", "急速に"]
# 「下げ止まり」「横ばい」は、悪い状態の説明に使われることが多いので弱気側に入れた（頑健性で外す）

# 景気の判断の文かどうか（実体経済の語を含み、金融調節や買入れの語を含まない）
ECON = ["景気", "経済", "輸出", "生産", "設備投資", "個人消費", "雇用", "所得", "住宅投資",
        "公共投資", "企業収益", "需要", "消費"]
PRICE = ["物価", "消費者物価", "予想物価", "インフレ"]
OPS = ["オペ", "買入れ", "買い入れ", "残高", "調節方針", "当座預金", "コールレート", "誘導",
       "賛成", "反対", "委員", "議案", "貸出", "担保", "決定会合", "決定した", "政府"]

# 埋め込みの基準文（強気・弱気）
ANCHOR_POS = ["わが国の景気は回復している。", "景気は緩やかに拡大している。",
              "輸出や生産は増加している。", "個人消費は底堅く推移している。",
              "雇用・所得環境は改善している。"]
ANCHOR_NEG = ["わが国の景気は悪化している。", "景気は大幅に落ち込んでいる。",
              "輸出や生産は減少している。", "個人消費は弱い動きとなっている。",
              "雇用・所得環境は厳しさを増している。"]
