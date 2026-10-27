"""共通の設定（パス・フォント・乱数の種・辞書）"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
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
for p in (DATA, RAW, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

# 景気判断理由集（CSV）をまとめた JSON（gzip）。コメントの全文を含むので GitHub には置かない。01_取得 で作り直す
WATCHER_JSON = Path(os.environ.get("F73_WATCHER", RAW / "f73_watcher.json.gz"))
# コメントを1行ずつにした中間ファイル（GitHub には置かない）
COMMENTS = DATA / "_comments.parquet"
# 埋め込みモデル（cl-nagoya/ruri-v3-30m、Apache-2.0）。手元のフォルダを RURI_PATH で指定できる
MODEL = os.environ.get("RURI_PATH", "cl-nagoya/ruri-v3-30m")

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# 判断の記号 → 点数（DI と同じ重み）
MARK = {"◎": 1.0, "○": 0.75, "□": 0.5, "▲": 0.25, "×": 0.0}

# ---- 辞書（F53 の辞書をもとに、街角の言葉を足した）。部分一致で数える ----
POS = ["回復", "改善", "持ち直", "増加", "増えて", "増えた", "伸び", "拡大", "底堅", "堅調", "好調", "好転",
       "上向", "上回", "活発", "にぎわ", "賑わ", "盛況", "順調", "前向き", "期待"]
NEG = ["悪化", "減少", "減って", "減った", "落ち込", "低迷", "停滞", "鈍", "弱い", "弱め", "弱含", "厳し",
       "下回", "控え", "節約", "買い控", "苦戦", "低調", "不振", "減速", "不安", "懸念", "様子見"]
# 「期待」「不安」「懸念」は先行きの文に多い語。頑健性で外した辞書も試す
POS_CORE = [w for w in POS if w not in ("期待",)]
NEG_CORE = [w for w in NEG if w not in ("不安", "懸念", "様子見")]

# 埋め込みの基準文（強気5・弱気5）
ANCHOR_POS = ["来客数が増えて売上は好調だ。", "受注が増加しており、景気は良くなっている。",
              "客の購買意欲が高まり、販売量が伸びている。", "求人が増えて、人手を確保する動きが活発だ。",
              "客足が戻り、にぎわいが回復している。"]
ANCHOR_NEG = ["来客数が減って売上は厳しい。", "受注が減少しており、景気は悪くなっている。",
              "客の節約志向が強く、買い控えが続いている。", "求人が減って、雇用は弱含んでいる。",
              "客足が落ち込み、低迷が続いている。"]

# 話題の語（月ごとにコメントの何%に出てくるか）
TOPICS = {
    "物価・値上げ": ["値上げ", "物価", "価格高騰", "値上がり", "物価高"],
    "インバウンド": ["インバウンド", "訪日", "外国人観光客", "外国人客"],
    "人手不足": ["人手不足", "人材不足", "人が足りない", "採用難"],
    "コロナ": ["コロナ", "感染", "緊急事態", "まん延防止"],
    "天候": ["天候", "猛暑", "暖冬", "大雪", "台風", "長雨", "気温"],
    "消費税": ["消費税", "増税", "駆け込み"],
}
