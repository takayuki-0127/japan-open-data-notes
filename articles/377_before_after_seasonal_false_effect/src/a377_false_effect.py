"""A377 季節のあるデータで「施策の前後」を比べると、効果0でもどれだけ差が出るのか
商業動態統計の業態別販売額（月次）に、効果0の「施策の月」を置き、4つの比べ方で「差あり」と出る割合を数える。
あわせて、季節とずれの続き方を決めた架空の月次系列でも同じことを数える。乱数の種は377。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 377
SRC = "経済産業省「商業動態統計」業態別販売額（月次）をもとに作成"
PRE, POST = 24, 6          # 中断時系列：前24か月・後6か月
K = 3                      # 前後の比べ：前3か月と後3か月


def ols(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b; n, k = X.shape
    s2 = e @ e / (n - k); cov = s2 * np.linalg.inv(X.T @ X)
    return b, np.sqrt(np.diag(cov)), n - k


def tests(ly, months, t):
    """ly：対数の月次系列、months：月（1〜12）、t：「施策」を始めた月の位置。4つの比べ方の（差、p値）を返す"""
    out = {}
    # ① 前後の比べ：前3か月と後3か月（ウェルチの t 検定）
    a, b = ly[t - K:t], ly[t:t + K]
    out["before_after"] = (b.mean() - a.mean(), stats.ttest_ind(b, a, equal_var=False).pvalue)
    # ② 前年同月の比べ：後3か月と、1年前の同じ3か月（対応のある t 検定）
    c = ly[t - 12:t - 12 + K]
    out["same_month_last_year"] = (b.mean() - c.mean(), stats.ttest_rel(b, c).pvalue)
    # ③ 中断時系列（季節なし）：直線の流れ＋施策後の段差
    idx = np.arange(t - PRE, t + POST); y = ly[idx]
    tt = (idx - t).astype(float); post = (idx >= t).astype(float)
    X = np.column_stack([np.ones(len(idx)), tt, post])
    bb, se, df = ols(y, X); out["its_no_season"] = (bb[2], 2 * stats.t.sf(abs(bb[2] / se[2]), df))
    # ④ 中断時系列（季節あり）：月ごとのダミーを足す
    Dm = np.zeros((len(idx), 11))
    for j, m in enumerate(months[idx]):
        if m > 1: Dm[j, m - 2] = 1
    X2 = np.column_stack([X, Dm])
    bb, se, df = ols(y, X2); out["its_season"] = (bb[2], 2 * stats.t.sf(abs(bb[2] / se[2]), df))
    # ⑤ ④と同じ式で、ずれが翌月に続くことを見込んだ標準誤差（ニューウィー・ウェスト、3か月）
    e = y - X2 @ bb; n = len(y); XtXi = np.linalg.inv(X2.T @ X2); Xe = X2 * e[:, None]
    S = Xe.T @ Xe
    for L in range(1, 4):
        G = Xe[L:].T @ Xe[:-L]; S += (1 - L / 4) * (G + G.T)
    se_nw = np.sqrt(np.diag(XtXi @ S @ XtXi) * n / df)
    out["its_season_hac"] = (bb[2], 2 * stats.t.sf(abs(bb[2] / se_nw[2]), df))
    # ⑥ 前年同月比の変化：後3か月の前年同月比と、前3か月の前年同月比を比べる
    ya = ly[t:t + K] - ly[t - 12:t - 12 + K]; yb = ly[t - K:t] - ly[t - 12 - K:t - 12]
    out["yoy_change"] = (ya.mean() - yb.mean(), stats.ttest_ind(ya, yb, equal_var=False).pvalue)
    return out


def run_series(ly, months, ts, label, extra=None):
    rows = []
    for t in ts:
        r = tests(ly, months, t)
        for k, (d, p) in r.items():
            row = dict(series=label, t=int(t), start_month=int(months[t]), method=k, diff_pct=(np.exp(d) - 1) * 100, p=p)
            if extra: row.update(extra)
            rows.append(row)
    return rows


NAMES = {"before_after": "①前3か月と後3か月", "same_month_last_year": "②前年の同じ月と比べる", "its_no_season": "③中断時系列（季節なし）", "its_season": "④中断時系列（季節あり）",
         "its_season_hac": "⑤④に、ずれの続きを見込んだ幅", "yoy_change": "⑥前年同月比の変化を比べる"}


def summarize(df):
    g = df.groupby("method", sort=False)
    return pd.DataFrame({"差ありと出た割合(%)": g.apply(lambda x: (x.p < 0.05).mean() * 100).round(1),
                         "見かけの差の大きさ_中央値(%)": g.apply(lambda x: x.diff_pct.abs().median()).round(2),
                         "見かけの差の大きさ_90%点(%)": g.apply(lambda x: x.diff_pct.abs().quantile(0.9)).round(2),
                         "見かけの差が3%以上の割合(%)": g.apply(lambda x: (x.diff_pct.abs() >= 3).mean() * 100).round(1),
                         "回数": g.size()}).rename(index=NAMES)


def main():
    d = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"]).sort_values(["gyotai", "ym"])
    rows = []
    shock = pd.Timestamp("2019-07-01"), pd.Timestamp("2021-12-01")   # 消費税率の引き上げとコロナの時期
    for gname, g in d.groupby("gyotai", sort=False):
        ly = np.log(g.sales.values.astype(float)); months = g.ym.dt.month.values; ym = g.ym.values
        ts = np.arange(PRE, len(ly) - POST + 1)
        for r in run_series(ly, months, ts, gname):
            t = r["t"]; lo, hi = pd.Timestamp(ym[t - PRE]), pd.Timestamp(ym[t + POST - 1])
            r["ym"] = str(pd.Timestamp(ym[t]).date())[:7]; r["overlaps_shock"] = bool(lo <= shock[1] and hi >= shock[0])
            rows.append(r)
    real = pd.DataFrame(rows); real.to_csv(RES / "placebo_real.csv", index=False)
    s_all = summarize(real); s_calm = summarize(real[~real.overlaps_shock])
    s_all.to_csv(RES / "real_all_months.csv"); s_calm.to_csv(RES / "real_calm_months.csv")
    by_g = real.groupby(["series", "method"], sort=False).apply(lambda x: (x.p < 0.05).mean() * 100).unstack().rename(columns=NAMES).round(1)
    by_g.to_csv(RES / "real_by_gyotai.csv")
    # 始めた月ごと：①の見かけの差（6業態の平均）
    by_m = real[real.method == "before_after"].groupby("start_month").agg(mean_diff=("diff_pct", "mean"), sig=("p", lambda x: (x < 0.05).mean() * 100)).round(2)
    by_m.to_csv(RES / "real_before_after_by_start_month.csv")

    # ---------- 架空の月次系列（効果0と分かっている） ----------
    rng = np.random.default_rng(SEED)
    REPS, T = 2000, 60
    season = np.array([-0.04, -0.10, 0.03, -0.01, 0.00, -0.02, 0.04, 0.02, -0.04, 0.00, 0.01, 0.11])   # 12月が高い型
    season = season - season.mean()
    months = (np.arange(T) % 12) + 1
    sim_rows = []
    def gen(rho, amp, effect=0.0, t0=None):
        e = np.zeros(T); sd = 0.02
        e[0] = rng.normal(0, sd)
        for i in range(1, T): e[i] = rho * e[i - 1] + rng.normal(0, sd * np.sqrt(1 - rho ** 2))
        y = 0.002 * np.arange(T) + amp * season[months - 1] + e
        if t0 is not None: y[t0:] += effect
        return y
    for rho in (0.0, 0.5):
        for amp in (0.0, 0.5, 1.0, 2.0):
            for rep in range(REPS):
                t0 = int(rng.integers(PRE, T - POST + 1))
                ly = gen(rho, amp)
                sim_rows += run_series(ly, months, [t0], "sim", dict(rho=rho, amp=amp, effect=0.0))
    # 本当に +3% の効果があるとき、見つけられる割合
    for rep in range(REPS):
        t0 = int(rng.integers(PRE, T - POST + 1))
        ly = gen(0.0, 1.0, np.log(1.03), t0)
        sim_rows += run_series(ly, months, [t0], "sim", dict(rho=0.0, amp=1.0, effect=3.0))
    sim = pd.DataFrame(sim_rows)
    st = sim.groupby(["effect", "rho", "amp", "method"], sort=False).agg(sig=("p", lambda x: (x < 0.05).mean() * 100), abs_med=("diff_pct", lambda x: x.abs().median()), mean_diff=("diff_pct", "mean"), ge3=("diff_pct", lambda x: (x.abs() >= 3).mean() * 100)).round(2).reset_index()
    st["method"] = st.method.map(NAMES); st.to_csv(RES / "simulation.csv", index=False)

    out = {"n_placebo_real": int(real.t.count() // 6), "n_calm": int((~real.overlaps_shock).sum() // 6),
           "real_all": s_all.reset_index().to_dict("records"), "real_calm": s_calm.reset_index().to_dict("records"),
           "before_after_by_start_month": by_m.reset_index().to_dict("records"),
           "sim_reps": REPS}
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(s_all.to_string()); print(s_calm.to_string()); print(by_g.to_string()); print(by_m.to_string())
    print(st.pivot_table(index=["effect", "rho", "amp"], columns="method", values="sig").to_string())
    print(st.pivot_table(index=["effect", "rho", "amp"], columns="method", values="ge3").to_string())

    # ---------- 図 ----------
    # 図1：例（スーパー、12月に「施策」を始めたことにする）
    g = d[d.gyotai == "スーパー"].reset_index(drop=True)
    t = g.index[g.ym == pd.Timestamp("2023-12-01")][0]
    seg = g.iloc[t - 9:t + 6]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(seg.ym, seg.sales / 1e6, color=GRAY, lw=1.5, marker="o", ms=4)
    a = g.sales.iloc[t - K:t].mean() / 1e6; b = g.sales.iloc[t:t + K].mean() / 1e6
    ax.hlines(a, g.ym.iloc[t - K], g.ym.iloc[t - 1], color=BLUE, lw=3); ax.hlines(b, g.ym.iloc[t], g.ym.iloc[t + K - 1], color=ORANGE, lw=3)
    ax.axvline(g.ym.iloc[t] - pd.Timedelta(days=15), color=INK, lw=0.8, ls="--")
    ax.text(g.ym.iloc[t - 2], a * 0.985, f"前3か月の平均\n{a:.2f}兆円", color=BLUE, fontsize=9, ha="center", va="top")
    ax.text(g.ym.iloc[t + 1], b * 1.012, f"後3か月の平均\n{b:.2f}兆円（{(b / a - 1) * 100:+.1f}%）", color=ORANGE, fontsize=9, ha="center")
    ax.set_ylabel("スーパーの販売額（兆円）"); ax.set_title("何もしていない12月を「施策の開始」にすると、前後で差が出る")
    ax.margins(y=0.12)
    save(fig, "a377_example.png", SRC)

    # 図2：「差あり」と出た割合（実データ：全部の月／落ち着いた時期、架空）
    fig, ax = plt.subplots(figsize=(11, 4.4))
    labs = list(NAMES.values()); x = np.arange(len(labs))
    v1 = s_all["差ありと出た割合(%)"].reindex(labs).values; v2 = s_calm["差ありと出た割合(%)"].reindex(labs).values
    v3 = st[(st.effect == 0) & (st.rho == 0) & (st.amp == 1.0)].set_index("method").sig.reindex(labs).values
    for off, v, c, l in ((-0.27, v1, GRAY, "商業動態統計（全部の月）"), (0, v2, BLUE, "商業動態統計（消費税・コロナの時期を除く）"), (0.27, v3, ORANGE, "架空の系列（効果0と分かっている）")):
        ax.bar(x + off, v, 0.26, color=c, label=l)
        for xi, vi in zip(x + off, v): ax.text(xi, vi + 1, f"{vi:.0f}%", ha="center", fontsize=8)
    ax.axhline(5, color=INK, lw=0.8, ls="--"); ax.text(5.45, 6.5, "本来は5%", fontsize=8, ha="right")
    ax.set_xticks(x); ax.set_xticklabels([l.replace("（", "\n（").replace("、", "、\n") for l in labs], fontsize=8)
    ax.set_ylabel("効果0なのに「差あり」と出た割合（%）"); ax.legend(fontsize=8, frameon=False)
    ax.set_title("「差あり」と出る割合が高いのは、前年の同じ月との比べと、中断時系列だった")
    save(fig, "a377_false_positive.png", SRC + "。架空の系列は作成者が乱数で作成（seed 377）")

    # 図3：始めた月ごとの見かけの差（①）
    fig, ax = plt.subplots(figsize=(9, 4.0))
    cols = [ORANGE if v > 0 else BLUE for v in by_m.mean_diff]
    ax.bar(by_m.index, by_m.mean_diff, color=cols)
    for m, v in zip(by_m.index, by_m.mean_diff): ax.text(m, v + (0.3 if v > 0 else -0.3), f"{v:+.1f}", ha="center", va="bottom" if v > 0 else "top", fontsize=8)
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
    ax.set_ylabel("後3か月 ÷ 前3か月 の差（%、6業態の平均）"); ax.set_xlabel("「施策」を始めたことにした月")
    ax.margins(y=0.12); ax.set_title("前後の比べの見かけの差は、始めた月で決まる")
    save(fig, "a377_by_start_month.png", SRC)


if __name__ == "__main__":
    main()
