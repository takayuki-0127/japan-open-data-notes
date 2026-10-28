"""共通：パス・図の設定・変数の作成（F16 の common.py をもとにした）"""
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
FIG = ROOT / "figures"
RES = ROOT / "results"
for p in (FIG, RES):
    p.mkdir(parents=True, exist_ok=True)
SEED = 20261028
UNIT = 10          # 効果は「0〜5歳100人あたりの在所児が10人多い（増えた）とき」で表す
MIN_CHILD = 100    # 0〜5歳が100人未満の町村は割合が大きく振れるので除く

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False


def wide():
    p = pd.read_csv(DATA / "panel_long.csv", dtype={"code": str})
    return {y: g.set_index("code") for y, g in p.groupby("year")}


def lfpr(g):
    """女性の労働力率（%）"""
    return 100 * g.F110102 / (g.F110102 + g.F110802)


def enroll(g):
    """保育所等に通う子ども（0〜5歳100人あたり）"""
    return 100 * g.J2506 / g.A1405


def facilities(g, kids):
    """保育所等の数（0〜5歳千人あたり）。kids は0〜5歳人口"""
    return 1000 * g.J2503 / kids


def base_covariates(w, base=2010):
    """2010年の地域の性格。出生・保育・女性の就業に直接かかわる列は含めない（設計ごとに足す）"""
    g = w[base]; g5 = w[2005]
    X = pd.DataFrame(index=g.index)
    X["log人口"] = np.log(g.A1101)
    X["log人口密度"] = np.log(g.A1101 / g.B1103)
    X["女性65歳以上の割合"] = 100 * g.A130302 / g.A110102
    X["女性15〜64歳の割合"] = 100 * g.A130202 / g.A110102
    X["核家族世帯の割合"] = 100 * g.A810102 / g.A7101
    X["単独世帯の割合"] = 100 * g.A810105 / g.A7101
    X["核家族以外の世帯の割合"] = 100 * g.A810103 / g.A7101
    X["母子世帯の割合"] = 100 * g.A8401 / g.A7101
    X["第1次産業の割合"] = 100 * g.F2201 / g.F1102
    X["第2次産業の割合"] = 100 * g.F2211 / g.F1102
    X["第3次産業の割合"] = 100 * g.F2221 / g.F1102
    X["女性の市外への通勤の割合"] = 100 * g.F270502 / g.F110202
    X["昼夜間人口比率"] = g.A6108
    X["納税者1人あたり所得"] = g.C120110 / g.C120120
    X["納税者の割合"] = 100 * g.C120120 / g.A1101
    X["財政力指数"] = g.D2201
    X["子ども1人あたり児童福祉費"] = g.D3203033 / g.A1301
    X["大卒の割合"] = 100 * g.E9106 / g.E9101
    X["短大・高専卒の割合"] = 100 * g.E9105 / g.E9101
    X["雇用者のうち正規の割合"] = 100 * g.F2409 / g.F2401
    X["雇用者のうちパートの割合"] = 100 * g.F2411 / g.F2401
    X["前の5年の人口増減率"] = 100 * (g.A1101 / g5.A1101 - 1)
    X["財政力指数が空欄"] = X["財政力指数"].isna().astype(float)
    X["財政力指数"] = X["財政力指数"].fillna(X["財政力指数"].median())
    return X


def pref_dummies(idx):
    pref = pd.Series([c[:2] for c in idx], index=idx)
    return pd.get_dummies(pref, prefix="県", drop_first=True).astype(float)
