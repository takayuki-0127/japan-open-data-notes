"""共通の設定"""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 146
EPS = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]   # プライバシーの強さ（小さいほど強い）
NREP = 200                                     # ノイズを入れ直す回数


def laplace(rng, scale, size):
    """ラプラス機構：平均0・尺度 scale のノイズ"""
    return rng.laplace(0.0, scale, size)


def geometric(rng, scale, size):
    """離散ラプラス（両側幾何分布）：整数のノイズ。頑健性チェック用"""
    p = 1 - np.exp(-1.0 / scale)
    return rng.geometric(p, size) - rng.geometric(p, size)
