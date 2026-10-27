import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW, DATA, RES, FIG = ROOT/"data/raw", ROOT/"data", ROOT/"results", ROOT/"figures"
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
AGES = [f"{5*i}-{5*i+4}" for i in range(18)] + ["90+"]
