"""02 整形：F247 の mart（または F246 の gen(seed) が返す表）に「架空の販促」を入れ、店×週の表にする。

架空の販促（この回で置いた設定。答えが分かるように、効果をこちらで決めて入れる）
- 名前：会員アプリの来店クーポン（2,000円以上で200円引き）。期間 2025-10-06（月）〜 2025-11-30（日）の8週。
- 対象の店の選び方：「7〜9月の既存店売上の前年比が低い6店」。現場でよくある「弱い店にてこ入れ」の選び方。
  候補は FY2023〜FY2025 にずっと営業している20店（08・16・21・24 の開店・閉店の店は除く）。残り14店が比べる相手。
- 入れた効果（答え）：期間中、対象の店のレシート枚数 ×1.04、1回の買上点数 ×1.01（売上 約 +5.0%）。
  期間の後の4週（2025-12-01〜12-28）はレシート枚数 ×1.015（効果の残り）。
- 費用：クーポンの利用はレシートの6%、1回200円（売上からは引かず、販促費として別に数える）。アプリの配信・制作の固定費 60万円。
- 粗利：増えた売上に、その店・その日の粗利率（廃棄の後）を掛ける。人件費は変えない（簡単のため）。

03_分析.py はこのファイルの関数を読み込んで使う。直接実行すると、入れた効果の答えを results/02_truth_seed0.json に書く。
"""
import importlib.util, json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
MART = ROOT / "data" / "mart"
F246 = ROOT / "data" / "f246" / "src" / "02_整形.py"

PROMO_START, PROMO_END = pd.Timestamp("2025-10-06"), pd.Timestamp("2025-11-30")
AFTER_END = pd.Timestamp("2025-12-28")
PRE_START = pd.Timestamp("2024-10-07")          # 期間の前の52週
SEL_MONTHS = ["2025-07", "2025-08", "2025-09"]  # 対象の店を選ぶのに使う月
EXCLUDE = [8, 16, 21, 24]                        # 開店・閉店のある店
N_TREAT = 6
EFF_REC, EFF_ITEMS, EFF_AFTER = 1.04, 1.01, 1.015
COUPON_RATE, COUPON_YEN, FIXED_YEN = 0.06, 200, 600_000


def load_gen_module():
    s = importlib.util.spec_from_file_location("f246gen", F246)
    g = importlib.util.module_from_spec(s); s.loader.exec_module(g)
    return g


def dims():
    st = pd.read_csv(MART / "dim_store.csv", encoding="utf-8-sig", parse_dates=["open_date", "close_date"])
    return st


COLS = ["date", "store_id", "receipts", "items", "sales", "gross_profit"]


def from_mart():
    sd = pd.read_csv(MART / "fact_store_day.csv.gz", parse_dates=["biz_date"]).rename(columns={"biz_date": "date"})
    return sd[COLS].copy()


def from_gen(g, seed):
    cal, fsd, fsdc, fmm, ec = g.gen(seed)
    d = fsd[COLS].copy(); d["date"] = pd.to_datetime(d.date)
    return d


def select_treated(sd, rule="weak", rng=None):
    """対象の店を選ぶ。weak＝7〜9月の前年比が低い6店、random＝候補20店から無作為に6店。"""
    cand = sorted(set(sd.store_id.unique()) - set(EXCLUDE))
    if rule == "random":
        return sorted(rng.choice(cand, N_TREAT, replace=False).tolist())
    d = sd[sd.store_id.isin(cand)].copy()
    d["ym"] = d.date.dt.strftime("%Y-%m")
    prev = [str(pd.Period(m, "M") - 12) for m in SEL_MONTHS]
    a = d[d.ym.isin(SEL_MONTHS)].groupby("store_id").sales.sum()
    b = d[d.ym.isin(prev)].groupby("store_id").sales.sum()
    yoy = (a / b - 1).sort_values()
    return sorted(yoy.index[:N_TREAT].tolist())


def inject(sd, treated, eff_rec=EFF_REC, eff_items=EFF_ITEMS, eff_after=EFF_AFTER):
    """販促の効果を入れる。元の売上（販促がなかった場合＝答えの反事実）も残す。"""
    d = sd.copy()
    d["sales0"], d["gp0"] = d.sales, d.gross_profit
    tr = d.store_id.isin(treated)
    inp = tr & d.date.between(PROMO_START, PROMO_END)
    aft = tr & d.date.between(PROMO_END + pd.Timedelta("1D"), AFTER_END)
    mult = np.where(inp, eff_rec * eff_items, np.where(aft, eff_after, 1.0))
    rmult = np.where(inp, eff_rec, np.where(aft, eff_after, 1.0))
    d["receipts"] = d.receipts * rmult
    d["items"] = d["items"] * mult
    d["sales"] = d.sales0 * mult
    d["gross_profit"] = d.gp0 * mult            # 粗利率はその店・その日のまま
    d["coupon_cost"] = np.where(inp, d.receipts * COUPON_RATE * COUPON_YEN, 0.0)
    d["treated"] = tr.astype(int)
    return d


def truth(d):
    """答え：販促がなかった場合（sales0）との差。"""
    t = d[d.treated == 1]
    out = {}
    for name, a, b in [("promo", PROMO_START, PROMO_END), ("after", PROMO_END + pd.Timedelta("1D"), AFTER_END)]:
        x = t[t.date.between(a, b)]
        out[name] = {"sales": float(x.sales.sum()), "sales0": float(x.sales0.sum()),
                     "lift_pct": float(x.sales.sum() / x.sales0.sum() - 1), "inc_sales": float(x.sales.sum() - x.sales0.sum()),
                     "inc_gp": float(x.gross_profit.sum() - x.gp0.sum()), "coupon": float(x.coupon_cost.sum())}
    out["fixed"] = FIXED_YEN
    out["net"] = out["promo"]["inc_gp"] + out["after"]["inc_gp"] - out["promo"]["coupon"] - FIXED_YEN
    return out


def weekly(d):
    """店×週（月曜始まり）。期間の前の52週〜期間の後の4週。"""
    x = d[d.date.between(PRE_START - pd.Timedelta("364D"), AFTER_END)].copy()
    x["week"] = x.date - pd.to_timedelta(x.date.dt.dayofweek, unit="D")
    w = x.groupby(["store_id", "week"], as_index=False)[["sales", "sales0", "receipts", "items", "gross_profit", "gp0", "coupon_cost"]].sum()
    w = w.merge(x.groupby("store_id").treated.max().rename("treated").reset_index(), on="store_id")
    w["k"] = ((w.week - PROMO_START).dt.days // 7).astype(int)   # 期間の1週目が 0
    w["phase"] = np.select([w.k < 0, w.k < 8], ["pre", "promo"], "after")
    return w


if __name__ == "__main__":
    sd = from_mart()
    tr = select_treated(sd)
    d = inject(sd, tr)
    st = dims().set_index("store_id")
    out = {"treated": tr, "treated_area": st.loc[tr, "area"].tolist(), "truth": truth(d),
           "rows": len(d), "weeks": int(weekly(d).week.nunique())}
    (ROOT / "results").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "results" / "02_truth_seed0.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
