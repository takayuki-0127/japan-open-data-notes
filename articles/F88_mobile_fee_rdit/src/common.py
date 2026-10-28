from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; RAW = DATA / "raw"; RES = ROOT / "results"; FIG = ROOT / "figures"
for p in (DATA, RAW, RES, FIG): p.mkdir(parents=True, exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
SEED = 42
EVENT = "2021-04"   # 携帯電話通信料の大幅値下げが CPI に入った月
EVENT2 = "2021-10"  # 2回目の値下げが入った月
