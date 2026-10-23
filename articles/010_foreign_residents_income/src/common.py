"""共通：データの読み込み・変数・図の設定（e-Stat の市区町村データを加工）"""
from pathlib import Path
import logging
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import statsmodels.formula.api as smf

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
SOURCE = "出典：e-Stat「社会・人口統計体系 市区町村データ」「統計でみる市区町村のすがた2026」を加工して作成"
BLUE, ORANGE, GRAY, INK, LIGHT = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef"

LABEL = {"log_inc": "納税者1人あたり所得（対数）", "old": "65歳以上の割合", "univ": "大学・大学院卒の割合",
         "log_density": "人口密度（可住地、対数）", "mfg": "第2次産業で働く人の割合", "primary": "第1次産業で働く人の割合",
         "single": "単独世帯の割合"}
CONTROLS = ["log_inc", "old", "univ", "log_density", "mfg", "primary", "single"]


def load():
    d = pd.read_csv(ROOT / "data" / "municipal_base.csv")
    d = d[(d["A1101"] > 0) & (d["C120120"] > 0) & (d["A2301"] > 0)].copy()
    d["inc"] = d["C120110"] / d["C120120"] * 100                 # 万円（2024年度＝2023年の所得）
    d["log_inc"] = np.log(d["inc"])
    d["old"] = d["A1303"] / d["A1101"]
    d["univ"] = d["E9106"] / d["E9101"]
    d["mfg"] = d["F2211"] / d["F1102"]
    d["primary"] = d["F2201"] / d["F1102"]
    d["single"] = d["A810105"] / d["A710101"]
    d["ward23"] = d["code"].between(13101, 13123)
    for c in CONTROLS:
        d["z_" + c] = (d[c] - d[c].mean()) / d[c].std()
    return d


def steps(d, y, key, label_key, extra=None):
    """key の係数が、条件を足すとどう変わるか（標準化した1標準偏差あたり）"""
    others = [c for c in CONTROLS if c != key]
    specs = [("そのまま（何もそろえない）", f"{y} ~ z_{key}"),
             ("＋都道府県", f"{y} ~ z_{key} + C(pref_code)"),
             ("＋年齢構成", f"{y} ~ z_{key} + z_old + C(pref_code)" if key != "old" else f"{y} ~ z_{key} + C(pref_code)"),
             ("＋ほかの条件すべて", f"{y} ~ z_{key} + " + " + ".join("z_" + c for c in others) + " + C(pref_code)")]
    rows = []
    for name, f in specs:
        r = smf.ols(f, d).fit(cov_type="HC3")
        k = "z_" + key
        rows.append({"model": name, "coef": r.params[k], "lo": r.conf_int().loc[k, 0], "hi": r.conf_int().loc[k, 1],
                     "p": r.pvalues[k], "r2": r.rsquared, "n": int(r.nobs)})
    return pd.DataFrame(rows)


def plot_steps(t, title, xlabel, path, color=BLUE):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = np.arange(len(t))[::-1]
    for yi, (_, r) in zip(y, t.iterrows()):
        c = color if r.p < 0.05 else GRAY
        ax.hlines(yi, r.lo, r.hi, color=c, lw=2.5); ax.scatter(r.coef, yi, color=c, zorder=3, s=40)
        ax.text(max(r.hi, r.coef) + (t.hi.max() - t.lo.min()) * 0.03, yi, f"{r.coef:+.2f}" + ("" if r.p < 0.05 else "（はっきりしない）"), va="center", fontsize=9)
    ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y, t.model); ax.set_xlabel(xlabel)
    ax.set_xlim(min(t.lo.min(), 0) - (t.hi.max() - t.lo.min()) * 0.1, t.hi.max() + (t.hi.max() - t.lo.min()) * 0.45)
    ax.set_title(title, loc="left")
    fig.text(0.01, -0.06, SOURCE + "／重回帰・HC3 頑健標準誤差。灰色は95%区間が0をまたぐ", fontsize=8, color="#8a8984")
    fig.savefig(path); plt.close(fig)


def full_model(d, y):
    f = f"{y} ~ " + " + ".join("z_" + c for c in CONTROLS) + " + C(pref_code)"
    r = smf.ols(f, d).fit(cov_type="HC3")
    out = pd.DataFrame({"var": [LABEL[c] for c in CONTROLS], "coef": [r.params["z_" + c] for c in CONTROLS],
                        "lo": [r.conf_int().loc["z_" + c, 0] for c in CONTROLS], "hi": [r.conf_int().loc["z_" + c, 1] for c in CONTROLS],
                        "p": [r.pvalues["z_" + c] for c in CONTROLS]})
    out["r2"], out["n"] = r.rsquared, int(r.nobs)
    return out


def plot_coefs(t, title, xlabel, path):
    t = t.sort_values("coef")
    fig, ax = plt.subplots(figsize=(8, 4.2)); y = np.arange(len(t))
    col = [(BLUE if v > 0 else ORANGE) if p < 0.05 else GRAY for v, p in zip(t.coef, t.p)]
    ax.hlines(y, t.lo, t.hi, color=col, lw=2.2); ax.scatter(t.coef, y, color=col, zorder=3)
    ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y, t["var"]); ax.set_xlabel(xlabel); ax.set_title(title, loc="left")
    fig.text(0.01, -0.05, SOURCE + "／都道府県固定効果・HC3。灰色は95%区間が0をまたぐ", fontsize=8, color="#8a8984")
    fig.savefig(path); plt.close(fig)


def load_extra():
    """load() に追加データ（ふるさと納税・財政・住宅・医療）をつなぐ"""
    d = load()
    x = pd.read_csv(ROOT / "data" / "municipal_extra.csv")
    return d.merge(x, on="code", how="left")
