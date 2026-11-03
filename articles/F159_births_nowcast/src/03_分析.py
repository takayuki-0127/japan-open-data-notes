"""F159 03_分析：出生数（確定数・年間）のナウキャストを、公表のタイミングどおりに再現して比べる。

対象：Y = 2012〜2025年の年間出生数（確定数）。見る時点 t は Y年1月1日〜Y+1年10月1日の各月1日（22時点）。
各時点で「その日までに公表されていたものだけ」を使う。
  - 速報（外国人を含む・2か月後に公表）、概数（日本人・約5か月後、12か月合計で読む）、確定数（翌年9月30日）
方法：
  A 年初の予測（F55型）：Y-1年までの確定数で構造時系列（UC：局所線形トレンド＋季節）を当て、Y年の12か月を予測（時点によらず一定）
  B 速報×前年の換算比：速報の年初からの累計の前年比 × 前年の速報年計 × 換算比（確定÷速報、最新の確定年）
  C 概数だけ：概数の12か月合計から年初からの累計を出し、前年同期比で年末まで延ばす
  D 速報×その年の換算比：B の換算比を、同じ年の概数と速報が重なる月から求め直す（概数がまだなければ前年の比）
  E 速報＋モデル：D の換算比で直した速報を足した月次系列に UC を当て直し、残りの月を予測
2026年：2026年11月3日時点（速報8月分・概数5月分まで）で同じ計算をし、F55 の予測（66.30万人）と並べる。
"""
from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.structural import UnobservedComponents

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

P = pd.read_csv(ROOT / "data" / "monthly_panel.csv")
for c in ["gaisu_pub", "sokuhou_pub", "kakutei_pub"]:
    P[c] = pd.to_datetime(P[c])
P = P.set_index(["year", "month"]).sort_index()
DAYS = {(y, m): pd.Period(f"{y}-{m:02d}").days_in_month for y in range(1995, 2030) for m in range(1, 13)}
ANN_K = P.kakutei.groupby(level=0).sum(min_count=12)
ANN_S = P.sokuhou.groupby(level=0).sum(min_count=12)


# ---------------------------------------------------------------- 情報集合
def info(t, c_rule="prev"):
    """時点 t に見えていた月次データ。kakutei_ok: 確定が公表済みの年、S: 速報（公表済み）、R: 概数の12か月合計（公表済み）"""
    kak_years = sorted({y for (y, m), v in P.kakutei.items() if pd.notna(v) and P.kakutei_pub[(y, m)] <= t})
    S = P.sokuhou[(P.sokuhou_pub <= t) & P.sokuhou.notna()]
    R = P.gaisu_r12[(P.gaisu_pub <= t) & P.gaisu_r12.notna()]
    return kak_years, S, R


def conv_ratio(kak_years, rule="prev"):
    """換算比（確定÷速報）。prev：最新の確定年、avg3：直近3年の平均、trend5：直近5年の直線を1年先へ"""
    ys = [y for y in kak_years if y >= 2005]
    r = (ANN_K / ANN_S).loc[ys]
    if rule == "prev":
        return float(r.iloc[-1])
    if rule == "avg3":
        return float(r.iloc[-3:].mean())
    if rule == "trend5":
        x = np.array(r.index[-5:], float)
        b = np.polyfit(x, r.iloc[-5:].values, 1)
        return float(np.polyval(b, x[-1] + 1)) if rule == "trend5" else None
    raise ValueError(rule)


def history(t, c, kak_years, S):
    """確定数ベースの月次系列（確定が出ている年は確定、それ以降は速報×換算比）"""
    last_k = max(kak_years)
    h = {}
    for (y, m), v in P.kakutei.items():
        if y <= last_k and pd.notna(v):
            h[(y, m)] = v
    for (y, m), v in S.items():
        if y > last_k:
            h[(y, m)] = v * c
    return pd.Series(h).sort_index()


def gaisu_ytd(Y, R, xprev):
    """概数の12か月合計から、Y年の年初からの累計と、その月数を出す。xprev：Y-1年の月次（確定ベース）"""
    ms = [m for (y, m) in R.index if y == Y]
    if not ms:
        return None, 0
    mg = max(ms)
    rest = sum(xprev[(Y - 1, k)] for k in range(mg + 1, 13))
    return R[(Y, mg)] - rest, mg


def uc_forecast(series, Y, last_known, window=120):
    """log（1日あたり）に UC（局所線形トレンド＋確定的な季節12）を当て、Y年の未知の月を予測（中央値ベースの合計を返す）"""
    s = series.iloc[-window:]
    idx = pd.PeriodIndex([pd.Period(f"{y}-{m:02d}") for y, m in s.index], freq="M")
    y = np.log(s.values / np.array([DAYS[k] for k in s.index]))
    mod = UnobservedComponents(pd.Series(y, index=idx), level="lltrend", freq_seasonal=[{"period": 12, "harmonics": 6}],
                               stochastic_freq_seasonal=[False])
    fit = mod.fit(disp=False, maxiter=200)
    ylast, mlast = int(last_known[0]), int(last_known[1])
    steps = int((Y - ylast) * 12 + (12 - mlast))
    if steps <= 0:
        return {}, fit
    fc = fit.get_forecast(steps)
    mean, var = fc.predicted_mean.values, fc.var_pred_mean.values
    out = {}
    yy, mm = ylast, mlast
    for i in range(steps):
        mm += 1
        if mm == 13:
            yy, mm = yy + 1, 1
        if yy == Y:
            out[mm] = float(np.exp(mean[i] + var[i] / 2) * DAYS[(yy, mm)])
    return out, fit


_UC_CACHE = {}


def method_A(Y):
    if Y in _UC_CACHE:
        return _UC_CACHE[Y]
    h = pd.Series({k: v for k, v in P.kakutei.items() if k[0] <= Y - 1 and pd.notna(v)}).sort_index()
    fc, _ = uc_forecast(h, Y, (Y - 1, 12))
    _UC_CACHE[Y] = sum(fc.values())
    return _UC_CACHE[Y]


def prev_best(Y, t, kak_years, R, c0):
    """Y-1年の年間（確定ベース）の、その時点で一番よい値：確定 → 概数の年計 → 速報×換算比"""
    if Y - 1 in kak_years:
        return float(ANN_K[Y - 1]), "確定"
    if (Y - 1, 12) in R.index:
        return float(R[(Y - 1, 12)]), "年計概数"
    return float(c0 * ANN_S[Y - 1]), "速報×換算比"


def nowcast(Y, t, c_rule="prev", extend="ytd", use_E=False, use_gap=True):
    """時点 t における Y年の年間出生数（確定数ベース）の推計。
    B：速報だけ（前年の速報年計×換算比×速報の前年同期比）
    C：概数だけ（前年の年間×(1＋概数の12か月合計の増減÷前年同期の出生数)）
    D：速報＋概数（前年の年間×（速報の前年同期比＋「概数と速報の前年同期比の差」））
    E：D の補正を入れた月次系列に UC を当て直し、残りの月を予測
    """
    kak_years, S, R = info(t)
    if Y in kak_years:
        v = ANN_K[Y]
        return dict(B=v, C=v, D=v, E=v, ks=12, kg=12, c_prev=np.nan, gap=np.nan, prev_src="確定", final=True)
    c0 = conv_ratio(kak_years, c_rule)
    H = history(t, c0, kak_years, S)
    Aprev, src = prev_best(Y, t, kak_years, R, c0)
    xprev = {k: H[k] for k in H.index if k[0] == Y - 1}
    if len(xprev) < 12:
        fc, _ = uc_forecast(H, Y - 1, H.index[-1])
        for m, v in fc.items():
            xprev[(Y - 1, m)] = v
    sY = {int(m): S[(Y, m)] for (y, m) in S.index if y == Y}
    ks = max(sY) if sY else 0
    sprev = {m: P.sokuhou[(Y - 1, m)] for m in range(1, 13)}

    def g_s(k):
        return sum(sY[m] for m in range(1, k + 1)) / sum(sprev[m] for m in range(1, k + 1))

    gm = [int(m) for (y, m) in R.index if y == Y]
    kg = max(gm) if gm else 0
    if kg > 0:
        delta = R[(Y, kg)] - R[(Y - 1, 12)]            # 概数どうしの前年同期差（12か月合計の動き）
        base = sum(xprev[(Y - 1, k)] for k in range(1, kg + 1))
        g_g = 1 + delta / base
        C = Aprev * g_g
        gap = (g_g - g_s(kg)) if (use_gap and kg <= ks) else 0.0
    else:
        C, gap = np.nan, 0.0
    if ks > 0:
        gs = g_s(ks)
        if extend == "last3" and ks >= 3:
            g3 = sum(sY[m] for m in range(ks - 2, ks + 1)) / sum(sprev[m] for m in range(ks - 2, ks + 1))
            sp = sum(sprev.values())
            gs = (sum(sY[m] for m in range(1, ks + 1)) + g3 * sum(sprev[m] for m in range(ks + 1, 13))) / sp
        B = c0 * ANN_S[Y - 1] * gs
        D = Aprev * (gs + gap)
    else:
        B = D = np.nan
    E = np.nan
    if use_E and ks > 0:
        if ks == 12:
            E = D
        else:
            # 速報を「確定ベースの前年同月 × (速報の前年同月比 ＋ 差)」に直して系列をつくり、UC で残りを予測
            Hx = pd.Series({**{k: v for k, v in H.items() if k[0] < Y}, **{(Y, m): xprev[(Y - 1, m)] * (sY[m] / sprev[m] + gap) for m in range(1, ks + 1)}}).sort_index()
            # Y-1年は確定ベースの値に置き換える（年計に合わせて比例調整）
            sc = Aprev / sum(xprev.values())
            for m in range(1, 13):
                Hx[(Y - 1, m)] = xprev[(Y - 1, m)] * sc
            for m in range(1, ks + 1):
                Hx[(Y, m)] = Hx[(Y - 1, m)] * (sY[m] / sprev[m] + gap)
            Hx = Hx.sort_index()
            fc, _ = uc_forecast(Hx, Y, (Y, ks))
            E = sum(Hx[(Y, m)] for m in range(1, ks + 1)) + sum(fc.values())
    return dict(B=B, C=C, D=D, E=E, ks=ks, kg=kg, c_prev=c0, gap=gap, prev_src=src, final=False)


def asof_dates(Y):
    return [pd.Timestamp(Y + (i // 12), i % 12 + 1, 1) for i in range(0, 22)]


def run_backtest(years, c_rule="prev", extend="ytd", use_E=True, use_gap=True):
    rows = []
    for Y in years:
        A = method_A(Y)
        for h, t in enumerate(asof_dates(Y)):
            r = nowcast(Y, t, c_rule=c_rule, extend=extend, use_E=use_E, use_gap=use_gap)
            # 情報がない時点（速報なし）は A を使う
            B = r["B"] if np.isfinite(r["B"]) else A
            D = r["D"] if np.isfinite(r["D"]) else A
            C = r["C"] if np.isfinite(r["C"]) else A
            E = r["E"] if np.isfinite(r["E"]) else A
            rows.append(dict(year=Y, h=h, asof=t.date(), ks=r["ks"], kg=r["kg"], c_prev=r["c_prev"], gap=r["gap"],
                             prev_src=r["prev_src"], final=r["final"], actual=ANN_K[Y], A=A, B=B, C=C, D=D, E=E))
    df = pd.DataFrame(rows)
    for m in "ABCDE":
        df[f"err_{m}"] = (df[m] / df.actual - 1) * 100
    return df


YEARS = list(range(2012, 2026))

if __name__ == "__main__":
    bt = run_backtest(YEARS)
    bt.to_csv(RES / "backtest_main.csv", index=False)
    summ = bt.groupby("h").agg(asof_month=("asof", lambda s: f"{pd.Timestamp(s.iloc[0]).month}月1日"),
                               ks=("ks", "median"), kg=("kg", "median"),
                               **{f"MAE_{m}": (f"err_{m}", lambda e: e.abs().mean()) for m in "ABCDE"},
                               **{f"bias_{m}": (f"err_{m}", "mean") for m in "ABCDE"})
    summ.to_csv(RES / "mae_by_horizon.csv")
    print(summ.round(2).to_string())

    # 期間別
    per = []
    for name, ys in [("2012〜19年", range(2012, 2020)), ("2020〜25年", range(2020, 2026)), ("2020・21年を除く", [y for y in YEARS if y not in (2020, 2021)])]:
        sub = bt[bt.year.isin(list(ys))]
        g = sub.groupby("h")[[f"err_{m}" for m in "ABCDE"]].apply(lambda d: d.abs().mean())
        for h in [2, 5, 8, 11, 14]:
            per.append(dict(period=name, h=h, **{m: g.loc[h, f"err_{m}"] for m in "ABCDE"}))
    pd.DataFrame(per).to_csv(RES / "mae_by_period.csv", index=False)

    # 換算比のルール
    rob = []
    for rule in ["prev", "avg3", "trend5"]:
        b2 = run_backtest(YEARS, c_rule=rule, use_E=False)
        for h in [2, 5, 8, 11, 14]:
            sub = b2[b2.h == h]
            rob.append(dict(check=f"換算比={rule}", h=h, MAE_B=sub.err_B.abs().mean(), MAE_D=sub.err_D.abs().mean(),
                            bias_B=sub.err_B.mean(), bias_D=sub.err_D.mean()))
    b4 = run_backtest(YEARS, use_E=False, use_gap=False)
    for h in [2, 5, 8, 11, 14]:
        sub = b4[b4.h == h]
        rob.append(dict(check="概数との差の補正なし", h=h, MAE_B=np.nan, MAE_D=sub.err_D.abs().mean(), bias_B=np.nan,
                        bias_D=sub.err_D.mean()))
    b3 = run_backtest(YEARS, extend="last3", use_E=False)
    for h in [2, 5, 8, 11, 14]:
        sub = b3[b3.h == h]
        rob.append(dict(check="延ばし方=直近3か月の前年比", h=h, MAE_B=np.nan, MAE_D=sub.err_D.abs().mean(), bias_B=np.nan,
                        bias_D=sub.err_D.mean()))
    # 公表を1か月遅く使う（速報・概数とも、t を1か月前にずらして同じ Y を見る）
    rows = []
    for Y in YEARS:
        for h, t in enumerate(asof_dates(Y)):
            if h == 0:
                continue
            r = nowcast(Y, t - pd.DateOffset(months=1), use_E=False)
            D = r["D"] if np.isfinite(r["D"]) else method_A(Y)
            rows.append(dict(year=Y, h=h, err=(D / ANN_K[Y] - 1) * 100))
    lag = pd.DataFrame(rows)
    for h in [2, 5, 8, 11, 14]:
        sub = lag[lag.h == h]
        rob.append(dict(check="公表を1か月遅く使う", h=h, MAE_B=np.nan, MAE_D=sub.err.abs().mean(), bias_B=np.nan, bias_D=sub.err.mean()))
    pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)

    # 区間（D）：Y より前の年の同じ時点の誤差（RMSE）で80%・95%の幅をつくり、入った割合を見る
    cov = []
    for Y in range(2016, 2026):
        for h in range(0, 22):
            past = bt[(bt.year < Y) & (bt.h == h)].err_D
            if len(past) < 4:
                continue
            rm = np.sqrt((past ** 2).mean())
            e = bt[(bt.year == Y) & (bt.h == h)].err_D.iloc[0]
            pastE = bt[(bt.year < Y) & (bt.h == h)].err_E
            rmE_ = np.sqrt((pastE ** 2).mean())
            eE = bt[(bt.year == Y) & (bt.h == h)].err_E.iloc[0]
            cov.append(dict(year=Y, h=h, rmse_past=rm, err=e, in80=abs(e) <= 1.2816 * rm, in95=abs(e) <= 1.96 * rm,
                            rmse_past_E=rmE_, err_E=eE, in80_E=abs(eE) <= 1.2816 * rmE_, in95_E=abs(eE) <= 1.96 * rmE_))
    cov = pd.DataFrame(cov)
    cov.to_csv(RES / "interval_coverage.csv", index=False)
    print("coverage", cov[(cov.h >= 3) & (cov.h < 14)][["in80", "in95", "in80_E", "in95_E"]].mean().round(3).to_dict(), "n", ((cov.h >= 3) & (cov.h < 14)).sum())

    # 2026年：毎月1日時点＋11月3日時点
    path = []
    A26 = method_A(2026)
    for t in [pd.Timestamp(2026, m, 1) for m in range(1, 12)] + [pd.Timestamp(2026, 11, 3)]:
        r = nowcast(2026, t, use_E=True)
        path.append(dict(asof=t.date(), ks=r["ks"], kg=r["kg"], c_prev=r["c_prev"], gap=r["gap"], prev_src=r["prev_src"], A=A26,
                         B=r["B"], C=r["C"], D=r["D"], E=r["E"]))
    path = pd.DataFrame(path)
    # 区間：2012〜25年の同じ時点（h=10）の D の誤差
    h_now = 10
    rm = np.sqrt((bt[bt.h == h_now].err_D ** 2).mean())
    rmE = np.sqrt((bt[bt.h == h_now].err_E ** 2).mean())
    last = path.iloc[-1]
    out = dict(asof="2026-11-03", sokuhou_months=int(last.ks), gaisu_months=int(last.kg), c_prev=last.c_prev,
               gap_2026=last.gap, A=A26, B=last.B, C=last.C, D=last.D, E=last.E,
               D_lo95=last.D * (1 - 1.96 * rm / 100), D_hi95=last.D * (1 + 1.96 * rm / 100), rmse_h10_D=rm,
               rmse_h10_E=rmE, E_lo95=last.E * (1 - 1.96 * rmE / 100), E_hi95=last.E * (1 + 1.96 * rmE / 100),
               E_lo80=last.E * (1 - 1.2816 * rmE / 100), E_hi80=last.E * (1 + 1.2816 * rmE / 100),
               p_E_below_2025=float(0.5 * (1 + __import__("math").erf(((ANN_K[2025] / last.E - 1) * 100) / rmE / 2 ** 0.5))),
               F55_median=663045.2, F55_lo95=622891.4, F55_hi95=713570.0,
               sokuhou_ytd_growth=float(P.sokuhou.loc[2026].iloc[:8].sum() / P.sokuhou.loc[2025].iloc[:8].sum() - 1),
               actual_2025=float(ANN_K[2025]))
    path.to_csv(RES / "nowcast_2026_path.csv", index=False)
    json.dump(out, open(RES / "nowcast_2026.json", "w"), ensure_ascii=False, indent=1)
    print(path.round(0).to_string())
    print(json.dumps(out, ensure_ascii=False, indent=1))

    # 換算比の推移
    rr = pd.DataFrame({"kakutei": ANN_K, "sokuhou": ANN_S}).loc[2005:2025]
    rr["ratio"] = rr.kakutei / rr.sokuhou
    rr["ratio_prev_err_%"] = (rr.ratio.shift(1) / rr.ratio - 1) * 100
    rr.to_csv(RES / "conversion_ratio.csv")
    print(rr.round(4).to_string())
