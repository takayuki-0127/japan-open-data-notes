"""F36 共通：パス・図の体裁・階層（全国→10地方→47都道府県）・予測と整合の関数"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#8a5cc2"
SOURCE = "出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工して作成"
SEED = 20260427

# 地方：観光庁の地方運輸局の区分にそろえた10地方（福井は中部運輸局の管内）
REGIONS = {
    "北海道": ["北海道"],
    "東北": ["青森", "岩手", "宮城", "秋田", "山形", "福島"],
    "関東": ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "山梨"],
    "北陸信越": ["新潟", "富山", "石川", "長野"],
    "中部": ["福井", "岐阜", "静岡", "愛知", "三重"],
    "近畿": ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"],
    "中国": ["鳥取", "島根", "岡山", "広島", "山口"],
    "四国": ["徳島", "香川", "愛媛", "高知"],
    "九州": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島"],
    "沖縄": ["沖縄"],
}
PREFS = [p for r in REGIONS.values() for p in r]


def short(p):
    p = p[2:] if p[:2].isdigit() else p
    return p if p == "北海道" else p[:-1]


def load(col="total"):
    """都道府県×月の表（列：47都道府県、行：月）"""
    d = pd.read_csv(RAW / "lodging_pref_monthly_2011_2025.csv")
    d = d[d.pref != "全国"].copy()
    d["p"] = d.pref.map(short)
    d["date"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1))
    w = d.pivot(index="date", columns="p", values=col)[PREFS].astype(float)
    w.index.freq = "MS"
    return w


def summing_matrix():
    """S（58×47）：全国1・地方10・都道府県47"""
    rows, names, level = [np.ones(len(PREFS))], ["全国"], ["全国"]
    for r, ps in REGIONS.items():
        rows.append(np.array([1.0 if p in ps else 0.0 for p in PREFS])); names.append(r + "地方" if r in ("北海道", "沖縄") else r); level.append("地方")
    for p in PREFS:
        rows.append(np.array([1.0 if q == p else 0.0 for q in PREFS])); names.append(p); level.append("都道府県")
    return np.vstack(rows), names, level


def all_series(bottom):
    S, names, level = summing_matrix()
    Y = bottom.values @ S.T
    return pd.DataFrame(Y, index=bottom.index, columns=names), S, names, level


# ---------- 予測のモデル（対数で当てはめて戻す） ----------
def fit_forecast(y, h, model="ets"):
    """y：月次の水準（pd.Series）。返り値：(予測 h 本, 当てはめ値（学習期間）)"""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    ly = np.log(y.clip(lower=1.0))
    if model == "ets":
        m = ExponentialSmoothing(ly, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
                                 initialization_method="estimated").fit(optimized=True)
        f, fit = m.forecast(h), m.fittedvalues
    elif model == "arima":
        m = SARIMAX(ly, order=(1, 0, 1), seasonal_order=(0, 1, 1, 12), trend="c").fit(disp=False)
        f, fit = m.forecast(h), m.fittedvalues
        fit.iloc[:13] = ly.iloc[:13]          # 季節差分の最初の1年は当てはめ値が使えない
    elif model == "snaive":
        f = pd.Series(np.tile(ly.values[-12:], int(np.ceil(h / 12)))[:h])
        fit = ly.shift(12).fillna(ly)
    else:
        raise ValueError(model)
    return np.exp(np.asarray(f)), np.exp(np.asarray(fit))


# ---------- 整合（reconciliation） ----------
def shrink_cov(E):
    """Schäfer–Strimmer 型の縮小推定（対角への縮小）。E：T×n の残差"""
    E = E - E.mean(0)
    T = E.shape[0]
    W = E.T @ E / T
    d = np.sqrt(np.diag(W)); d[d == 0] = 1e-12
    R = W / np.outer(d, d)
    Es = E / d
    v = np.zeros_like(R)
    for i in range(E.shape[1]):
        v[i] = ((Es[:, [i]] * Es) ** 2).mean(0) - R[i] ** 2
    v = v * T / (T - 1) ** 2 if T > 1 else v
    off = ~np.eye(len(R), dtype=bool)
    lam = np.clip(v[off].sum() / max((R[off] ** 2).sum(), 1e-12), 0, 1)
    Rs = (1 - lam) * R; np.fill_diagonal(Rs, 1.0)
    return Rs * np.outer(d, d), lam


def G_matrix(S, method, resid=None, props=None):
    n, m = S.shape
    if method == "bu":
        G = np.hstack([np.zeros((m, n - m)), np.eye(m)])
    elif method == "td":
        G = np.zeros((m, n)); G[:, 0] = props
    else:
        if method == "ols":
            Winv = np.eye(n)
        elif method == "wls":                      # 構造による重み（下の系列の数）
            Winv = np.diag(1.0 / S.sum(1))
        elif method == "wlsv":                     # 残差の分散による重み
            Winv = np.diag(1.0 / np.var(resid, axis=0))
        elif method == "mint":
            W, _ = shrink_cov(resid)
            Winv = np.linalg.pinv(W)
        else:
            raise ValueError(method)
        G = np.linalg.solve(S.T @ Winv @ S, S.T @ Winv)
    return G


METHODS = {"base": "整合なし", "bu": "ボトムアップ", "td": "トップダウン", "ols": "OLS",
           "wlsv": "WLS（分散）", "mint": "MinT"}


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
