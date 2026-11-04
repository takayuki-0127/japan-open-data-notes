"""共通の設定"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42

# 一致系列（内閣府 景気動向指数 *ci2.xlsx）
COIN_NAMES = {
    "C1": "生産指数（鉱工業）",
    "C2": "鉱工業用生産財出荷指数",
    "C3": "耐久消費財出荷指数",
    "C4": "労働投入量指数（調査産業計）",
    "C5": "投資財出荷指数（除輸送機械）",
    "C6": "商業販売額（小売業、前年同月比）",
    "C7": "商業販売額（卸売業、前年同月比）",
    "C8": "営業利益（全産業、四半期）",
    "C9": "有効求人倍率（除学卒）",
    "C10": "輸出数量指数",
}
# 本体で使う一致系列（指数・倍率の7系列。前年同月比の C6・C7 と四半期の C8 は頑健性で扱う）
MAIN = ["C1", "C2", "C3", "C4", "C5", "C9", "C10"]
# 先行系列（*ci1.xlsx）のうち、水準の指数・数量の系列
LEAD_NAMES = {
    "L1": "最終需要財在庫率指数（逆）",
    "L2": "鉱工業用生産財在庫率指数（逆）",
    "L3": "新規求人数（除学卒）",
    "L4": "実質機械受注（製造業）",
    "L5": "新設住宅着工床面積",
    "L6": "消費者態度指数",
    "L9": "東証株価指数",
}
