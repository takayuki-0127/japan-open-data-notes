"""F02 共通：パス・図の体裁・月次データの読み込み・3つのモデル（SARIMA / ETS / Prophet）"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
for name in ("matplotlib.font_manager", "prophet", "cmdstanpy"):
    logging.getLogger(name).setLevel(logging.ERROR)
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：厚生労働省「人口動態統計（確定数）」（e-Stat）をもとに作成者が加工して作成"
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
NSIM = 2000          # 予測区間・累積ギャップの区間を作るシミュレーション本数
SEED = 20201
EVAL_START, EVAL_END = "2020-01", "2025-12"


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def monthly():
    """data/monthly.csv：月ごとの出生数・婚姻件数・日数・1日あたり出生数"""
    d = pd.read_csv(DATA / "monthly.csv", parse_dates=["date"])
    return d.set_index("date").asfreq("MS")


# ---------- モデル：y は log(1日あたり出生数)。将来の経路を NSIM 本シミュレーションして返す ----------
def fit_sim_sarima(y, h, order=(1, 1, 1), sorder=(0, 1, 1, 12), exog=None, exog_f=None):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    m = SARIMAX(y, exog=exog, order=order, seasonal_order=sorder).fit(disp=False)
    sims = m.simulate(h, repetitions=NSIM, anchor="end", exog=exog_f, rng=np.random.default_rng(SEED))
    sims = np.asarray(sims).reshape(h, -1)          # (h, NSIM)
    mean = np.asarray(m.get_forecast(h, exog=exog_f).predicted_mean)
    return mean, sims, m


def fit_sim_ets(y, h):
    from statsmodels.tsa.exponential_smoothing.ets import ETSModel
    m = ETSModel(y, error="add", trend="add", damped_trend=True, seasonal="add", seasonal_periods=12).fit(disp=False)
    sims = np.asarray(m.simulate(h, repetitions=NSIM, anchor="end", rng=np.random.default_rng(SEED))).reshape(h, -1)
    mean = np.asarray(m.forecast(h))
    return mean, sims, m


def fit_sim_prophet(y, h):
    from prophet import Prophet
    df = pd.DataFrame({"ds": y.index, "y": y.values})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
                uncertainty_samples=NSIM, mcmc_samples=0)
    np.random.seed(SEED)
    m.fit(df)
    fut = pd.DataFrame({"ds": pd.date_range(y.index[-1] + pd.offsets.MonthBegin(), periods=h, freq="MS")})
    mean = m.predict(fut)["yhat"].values
    sims = m.predictive_samples(fut)["yhat"]          # (h, NSIM)
    return mean, sims, m


MODELS = {"SARIMA": fit_sim_sarima, "ETS": fit_sim_ets, "Prophet": fit_sim_prophet}


def to_counts(logpd, days):
    """log(1日あたり) → 月の出生数"""
    return np.exp(logpd) * np.asarray(days).reshape(-1, *([1] * (np.ndim(logpd) - 1)))
