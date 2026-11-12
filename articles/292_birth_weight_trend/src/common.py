"""289〜293 共通：厚生労働省「人口動態統計」確定数（令和7年＝2025年）上巻の CSV を読む"""
from pathlib import Path
import csv, json, re
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["figure.dpi"] = 110
plt.rcParams["svg.hashsalt"] = "jinkou"

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; RES = ROOT / "results"; FIG = ROOT / "figures"
for p in (RES, FIG): p.mkdir(parents=True, exist_ok=True)


def rows(name):
    """cp932 の CSV を行のリストで返す（前後の空白・全角空白は落とす）"""
    with open(DATA / name, encoding="cp932", newline="") as f:
        return [[c.strip().replace("　", "") for c in r] for r in csv.reader(f)]


def num(s):
    s = str(s).strip().replace("　", "")
    if s in ("", "-", "・", "…"): return np.nan if s != "-" else 0.0
    try: return float(s.replace(",", ""))
    except ValueError: return np.nan


def year_rows(r, start=None, stop=None):
    """先頭列が年（4桁）の行を DataFrame に（start/stop は行の範囲）"""
    out = {}
    for x in r[start:stop]:
        m = re.match(r"^(\d{4})", x[0]) if x else None
        if m: out[int(m.group(1))] = [num(v) for v in x[1:]]
    return out


def save_json(obj, name="main.json"):
    def conv(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return None if np.isnan(o) else round(float(o), 6)
        if isinstance(o, dict): return {str(k): conv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [conv(v) for v in o]
        return o
    (RES / name).write_text(json.dumps(conv(obj), ensure_ascii=False, indent=1), encoding="utf-8")


def savefig(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
