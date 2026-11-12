"""A391 週の波と年の波が重なる日次データを、4つの方法で分ける。真の波が分かっている架空のデータで、取り出した波の誤差を測る。
python a391_two_seasonalities.py            # 全部を計算し直す（約7〜9分）
"""
import json, warnings
import numpy as np, pandas as pd
from statsmodels.tsa.seasonal import STL, MSTL
from common import *
warnings.filterwarnings("ignore")
SEED = 391
SRC = "出典：架空のデータ（作成者が乱数で作成、seed 391）"
DOW = np.array([-60., -75., -70., -45., 20., 110., 120.])   # 月〜日の週の波（平均0）
LEVEL, NOISE, HOL = 1000.0, 30.0, 150.0                       # 水準、日々の揺れ、祝日の上乗せ
FIXED = [(1, 1), (1, 2), (1, 3), (2, 11), (2, 23), (4, 29), (5, 3), (5, 4), (5, 5), (8, 11), (11, 3), (11, 23)]  # 日付が決まった休み
MONDAY = [(1, 2), (7, 3), (9, 3), (10, 2)]                    # （月、第何月曜）の休み


def calendar(years):
    idx = pd.date_range("2021-01-01", periods=int(round(365.25 * years)) if years != 4 else 1461, freq="D")
    hol = np.zeros(len(idx), bool)
    for i, d in enumerate(idx):
        if (d.month, d.day) in FIXED: hol[i] = True
        if d.dayofweek == 0 and (d.month, (d.day - 1) // 7 + 1) in MONDAY: hol[i] = True
    return idx, hol


def truth(idx):
    t = np.arange(len(idx)); doy = idx.dayofyear.values + (idx.hour.values * 0)
    f = (doy - 1) / 365.25
    trend = LEVEL + 0.08 * t + 40 * np.sin(2 * np.pi * t / (365.25 * 3.3))      # ゆるい上り＋ゆっくりした波
    yearly = 90 * np.sin(2 * np.pi * (f - 0.30)) + 35 * np.cos(4 * np.pi * (f - 0.05))
    yearly = yearly + 160 * np.exp(-0.5 * ((doy - 358) / 6.0) ** 2) - 110 * np.exp(-0.5 * ((doy - 226) / 4.0) ** 2)   # 年末の山とお盆の谷（鋭い）
    weekly = DOW[idx.dayofweek.values]
    return trend, weekly, yearly - yearly.mean()


def fourier(idx, K):
    f = (idx.dayofyear.values - 1) / 365.25
    return np.column_stack([fn(2 * np.pi * k * f) for k in range(1, K + 1) for fn in (np.sin, np.cos)])


def regress(y, idx, K, hol=None):
    """曜日のダミー＋年の波（三角関数 K 組）＋3次式の傾き。hol を渡すと祝日のダミーも入れる"""
    t = np.arange(len(y)) / len(y)
    D = np.eye(7)[idx.dayofweek.values]
    if hol is not None: D = D * (~hol)[:, None]                 # 祝日は曜日の波から外す
    F = fourier(idx, K)
    X = [D[:, 1:] - D[:, [0]] if hol is None else D[:, 1:], F, np.column_stack([t, t ** 2, t ** 3]), np.ones((len(y), 1))]
    if hol is not None: X.append(hol[:, None].astype(float))
    X = np.column_stack(X); b = np.linalg.lstsq(X, y, rcond=None)[0]
    w = X[:, :6] @ b[:6]; yr = F @ b[6:6 + 2 * K]
    if hol is not None:                                           # 祝日を入れた形：曜日の波は「祝日でない日の曜日の差」
        eff = np.r_[0.0, b[:6]]; eff = eff - eff.mean(); w = eff[idx.dayofweek.values]
    return w, yr, y - w - yr                                      # 最後は「傾き＋残り」


def nrmse(est, true, mask=None):
    e = (est - est.mean()) - (true - true.mean())
    if mask is not None: e, true = e[mask], true[mask]
    return 100 * np.sqrt((e ** 2).mean()) / true.std()


def trend_err(est, true):
    return 100 * np.sqrt(((est - est.mean() - (true - true.mean())) ** 2).mean()) / LEVEL


def decompose(y, idx, hol_known=None):
    out = {}
    r = STL(y, period=7).fit(); out["STL（週だけ）"] = (r.seasonal, None, r.trend)
    r = STL(y, period=365).fit(); out["STL（年だけ）"] = (None, r.seasonal, r.trend)
    r = MSTL(y, periods=(7, 365)).fit(); out["MSTL（週と年）"] = (r.seasonal[:, 0], r.seasonal[:, 1], r.trend)
    r = MSTL(y, periods=(7, 365), windows=(101, 15)).fit(); out["MSTL（週の波の窓を101に）"] = (r.seasonal[:, 0], r.seasonal[:, 1], r.trend)
    for K in (3, 10):
        w, yr, rest = regress(y, idx, K); out[f"回帰（三角関数{K}組）"] = (w, yr, None)
    if hol_known is not None:
        w, yr, rest = regress(y, idx, 10, hol_known); out["回帰（10組＋祝日）"] = (w, yr, None)
    return out


def one(rng, years, holidays):
    idx, hol = calendar(years); tr, wk, yr = truth(idx)
    y = tr + wk + yr + rng.normal(0, NOISE, len(idx))
    if holidays: y = y + hol * (HOL - wk)                        # 祝日は曜日の波の代わりに +150
    rows = []
    for name, (w, s, t) in decompose(y, idx, hol if holidays else None).items():
        ok = ~hol if holidays else None                          # 祝日のある場面では、祝日でない日で比べる
        rows.append(dict(method=name, weekly=nrmse(w, wk, ok) if w is not None else np.nan,
                         yearly=nrmse(s, yr, ok) if s is not None else np.nan,
                         trend=trend_err(t, tr) if t is not None else np.nan))
        if holidays and name == "MSTL（週と年）":                   # 祝日の上乗せがどこへ行ったか
            extra = (HOL - wk)[hol]
            rows[-1].update(h_week=((w - w.mean() - wk)[hol] / extra).mean() * 100,
                            h_year=((s - s.mean() - yr)[hol] / extra).mean() * 100,
                            h_trend=((t - t.mean() - (tr - tr.mean()))[hol] / extra).mean() * 100)
    return rows, (idx, hol, y, tr, wk, yr)


def run():
    rng = np.random.default_rng(SEED); rec = []
    for years, reps in ((3, 20), (4, 60), (6, 20), (10, 20)):
        for holidays in (False, True):
            for i in range(reps):
                rows, _ = one(rng, years, holidays)
                for r in rows: rec.append(dict(years=years, holidays=holidays, rep=i, **r))
    df = pd.DataFrame(rec); df.to_csv(RES / "errors_by_run.csv", index=False, float_format="%.4f")
    return df


def example():
    rng = np.random.default_rng(SEED + 1)
    rows, (idx, hol, y, tr, wk, yr) = one(rng, 4, False)
    pd.DataFrame({"date": idx.strftime("%Y-%m-%d"), "y": y.round(2), "trend": tr.round(2), "weekly": wk, "yearly": yr.round(2)}).to_csv(DATA / "example_daily_4years.csv", index=False)
    return idx, y, tr, wk, yr, decompose(y, idx)


def figures(df, ex):
    idx, y, tr, wk, yr, dec = ex
    # 図1：1本の例
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1, 1.7]})
    dw = idx.dayofweek.values; lab = list("月火水木金土日")
    ax[0].bar(np.arange(7) - 0.2, DOW, 0.4, color=GRAY, label="真の波")
    m = dec["MSTL（週と年）"][0]; ax[0].bar(np.arange(7) + 0.2, [(m - m.mean())[dw == k].mean() for k in range(7)], 0.4, color=BLUE, label="MSTL")
    ax[0].set_xticks(range(7)); ax[0].set_xticklabels(lab); ax[0].axhline(0, color=INK, lw=0.6); ax[0].set_ylabel("週の波（水準1,000に対する上乗せ）"); ax[0].set_title("週の波"); ax[0].legend(frameon=False)
    sel = slice(365, 730); d = np.arange(365)
    ax[1].plot(d, yr[sel], color=INK, lw=2.2, label="真の波")
    s = dec["MSTL（週と年）"][1]; ax[1].plot(d, (s - s.mean())[sel], color=BLUE, lw=1, label="MSTL")
    s = dec["回帰（三角関数3組）"][1]; ax[1].plot(d, (s - s.mean())[sel], color=GREEN, lw=1.6, ls="--", label="回帰（三角関数3組）")
    s = dec["回帰（三角関数10組）"][1]; ax[1].plot(d, (s - s.mean())[sel], color=ORANGE, lw=1.6, label="回帰（三角関数10組）")
    ax[1].axhline(0, color=INK, lw=0.6); ax[1].set_xlabel("1月1日からの日数（2年目）"); ax[1].set_ylabel("年の波"); ax[1].set_title("年の波"); ax[1].legend(frameon=False, ncol=2, fontsize=9)
    fig.suptitle("取り出した波と真の波（4年分の日次データ、1本の例）", y=1.02)
    save(fig, "a391_example_components.png", SRC)
    # 図2：方法ごとの誤差（4年、祝日なし）
    g = df[(df.years == 4) & (~df.holidays)].groupby("method")[["weekly", "yearly"]].mean()
    order = ["STL（週だけ）", "STL（年だけ）", "MSTL（週と年）", "MSTL（週の波の窓を101に）", "回帰（三角関数3組）", "回帰（三角関数10組）"]
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.2))
    for a, col, ttl in ((ax[0], "weekly", "週の波の誤差"), (ax[1], "yearly", "年の波の誤差")):
        v = g.loc[order, col]; x = np.arange(len(order))
        a.barh(x, v.fillna(0), color=[GRAY if np.isnan(z) else BLUE for z in v])
        for i, z in enumerate(v): a.text((0 if np.isnan(z) else z) + 1, i, "分けられない" if np.isnan(z) else f"{z:.0f}%", va="center", fontsize=10)
        a.set_yticks(x); a.set_yticklabels(order if a is ax[0] else []); a.invert_yaxis(); a.set_xlim(0, max(60, v.max() * 1.25)); a.set_title(ttl); a.set_xlabel("誤差（真の波の大きさを100%とする）")
    fig.suptitle("方法ごとの誤差（4年分・祝日なし、60回の平均）", y=1.02)
    save(fig, "a391_error_by_method.png", SRC)
    # 図3：祝日が入ったとき
    order = ["MSTL（週と年）", "MSTL（週の波の窓を101に）", "回帰（三角関数10組）", "回帰（10組＋祝日）"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
    for a, col, ttl in ((ax[0], "weekly", "週の波の誤差"), (ax[1], "yearly", "年の波の誤差")):
        x = np.arange(len(order))
        v0 = [df[(df.years == 4) & (~df.holidays) & (df.method == m)][col].mean() if m != "回帰（10組＋祝日）" else np.nan for m in order]
        v1 = [df[(df.years == 4) & (df.holidays) & (df.method == m)][col].mean() for m in order]
        a.bar(x - 0.2, np.nan_to_num(v0), 0.4, color=LIGHT, label="祝日なし"); a.bar(x + 0.2, v1, 0.4, color=ORANGE, label="祝日あり（祝日でない日で比べる）")
        for i, (p, q) in enumerate(zip(v0, v1)):
            if not np.isnan(p): a.text(i - 0.2, p + 0.6, f"{p:.0f}%", ha="center", fontsize=9)
            a.text(i + 0.2, q + 0.6, f"{q:.0f}%", ha="center", fontsize=9)
        a.set_xticks(x); a.set_xticklabels([o.replace("（", "\n（") for o in order], fontsize=9); a.set_title(ttl); a.set_ylabel("誤差（真の波の大きさを100%とする）")
    ax[0].legend(frameon=False, fontsize=9)
    fig.suptitle("祝日（年16日前後）が入ると、波はどれだけ崩れるか（4年分、60回の平均）", y=1.02)
    save(fig, "a391_holiday_effect.png", SRC)


def tables(df):
    t = df.groupby(["years", "holidays", "method"])[["weekly", "yearly", "trend"]].mean().round(1).reset_index()
    t.to_csv(RES / "error_table.csv", index=False)
    h = df[df.holidays & (df.method == "MSTL（週と年）")].groupby("years")[["h_week", "h_year", "h_trend"]].mean().round(1)
    h["h_resid"] = (100 - h.sum(axis=1)).round(1); h.to_csv(RES / "holiday_effect_destination.csv")
    g = lambda y, hol, m, c: float(t[(t.years == y) & (t.holidays == hol) & (t.method == m)][c].iloc[0])
    main = {"seed": SEED, "level": LEVEL, "noise_sd": NOISE, "weekly_sd": float(DOW.std()), "holiday_extra": HOL,
            "four_years_no_holiday": {m: {"weekly": g(4, False, m, "weekly"), "yearly": g(4, False, m, "yearly"), "trend": g(4, False, m, "trend")} for m in t.method.unique() if m != "回帰（10組＋祝日）"},
            "four_years_holiday": {m: {"weekly": g(4, True, m, "weekly"), "yearly": g(4, True, m, "yearly")} for m in t.method.unique()},
            "mstl_weekly_window101": {"weekly": g(4, False, "MSTL（週の波の窓を101に）", "weekly"), "yearly": g(4, False, "MSTL（週の波の窓を101に）", "yearly")},
            "mstl_yearly_by_years": {int(y): g(y, False, "MSTL（週と年）", "yearly") for y in (3, 4, 6, 10)},
            "reg10_yearly_by_years": {int(y): g(y, False, "回帰（三角関数10組）", "yearly") for y in (3, 4, 6, 10)},
            "holiday_destination_4y": h.loc[4].to_dict()}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    return main


if __name__ == "__main__":
    ex = example(); df = run(); figures(df, ex); print(json.dumps(tables(df), ensure_ascii=False, indent=1))
