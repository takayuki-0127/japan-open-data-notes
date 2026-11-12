"""共通：提出の記録（自分でまとめた表）の読み込みと図の設定"""
import os, json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
def load(name="submissions.csv"):
    return pd.read_csv(os.path.join(ROOT, "data", name))
def out(*p):
    return os.path.join(ROOT, *p)
def save_json(obj, name):
    json.dump(obj, open(out("results", name), "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
def table_png(rows, cols, path, widths=None, fs=10, title=None):
    fig, ax = plt.subplots(figsize=(10, 0.5 + 0.42 * (len(rows) + 1)), dpi=150)
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="left", colWidths=widths)
    t.auto_set_font_size(False); t.set_fontsize(fs); t.scale(1, 1.5)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#bbbbbb")
        if r == 0: cell.set_facecolor("#e8eef5"); cell.set_text_props(weight="bold")
    if title: ax.set_title(title, fontsize=12)
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
