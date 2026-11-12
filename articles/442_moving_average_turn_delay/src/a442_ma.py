"""442 移動平均でならすと、向きが変わったことに気づくのは何日遅れるか（架空の日次系列500本）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED, N, DAYS = 442, 500, 420
SRC = "架空の日次系列（作成者が乱数で作成、seed 442）"
WK = np.array([1.00, 0.97, 0.98, 1.00, 1.06, 1.18, 1.12])     # 曜日の型（月〜日）


def make(n=N, slope=0.10, sd=3.0, seed=SEED, turn=True):
    """上がり続けて、ある日から下がる系列。slope は1日あたりの上がり幅（水準100に対して）"""
    r = np.random.default_rng(seed)
    T = r.integers(180, 260, n) if turn else np.full(n, 10**6)
    t = np.arange(DAYS)
    base = 100 + slope * np.minimum(t[None, :], T[:, None]) - slope * np.clip(t[None, :] - T[:, None], 0, None)
    y = base * WK[t % 7][None, :] + r.normal(0, sd, (n, DAYS))
    return y, T


def trail(y, w):
    c = np.cumsum(np.concatenate([np.zeros((y.shape[0], 1)), y], axis=1), axis=1)
    out = np.full(y.shape, np.nan); out[:, w - 1:] = (c[:, w:] - c[:, :-w]) / w
    return out


def center7_final(y):
    out = np.full(y.shape, np.nan); t7 = trail(y, 7); out[:, 3:-3] = t7[:, 6:]
    return out


def signal(s, lag=7, run=3):
    """ならした値が lag 日前より低い日が run 日続いたら「下向き」"""
    down = np.zeros(s.shape, bool); down[:, lag:] = s[:, lag:] < s[:, :-lag]
    k = np.zeros(s.shape, int)
    for j in range(1, s.shape[1]): k[:, j] = np.where(down[:, j], k[:, j - 1] + 1, 0)
    return k >= run


def score(sig, T, avail_lag=0, start=70):
    """気づくまでの日数（その値が手に入る日で数える）と、向きが変わる前の空振り"""
    n = sig.shape[0]; delay = np.full(n, np.nan); fa = np.zeros(n); days = np.zeros(n); sus = np.full(n, np.nan)
    for i in range(n):
        tt = min(T[i], DAYS); pre = sig[i, start:tt]
        fa[i] = np.sum(pre[1:] & ~pre[:-1]) + (1 if len(pre) and pre[0] else 0); days[i] = max(tt - start, 0)
        if T[i] < DAYS:
            idx = np.flatnonzero(sig[i, T[i]:])
            if len(idx): delay[i] = idx[0] + avail_lag
            x = sig[i, T[i]:]; c = np.convolve(x.astype(int), np.ones(14, int), "valid")      # 14日続けて「下向き」になる最初の日
            j = np.flatnonzero(c == 14)
            if len(j): sus[i] = j[0] + avail_lag
    score.sus = sus
    return delay, fa, days


def med(su):
    v = np.median(np.where(np.isnan(su), 9999, su)); return None if v >= 9999 else float(v)


def methods(y):
    return {"そのまま（前の週の同じ曜日と比べる）": (y, 0), "後ろ7日": (trail(y, 7), 0), "後ろ14日": (trail(y, 14), 0), "後ろ28日": (trail(y, 28), 0),
            "後ろ56日": (trail(y, 56), 0), "中心7日（3日あとに確定）": (center7_final(y), 3)}


def table(slope=0.10, sd=3.0, seed=SEED):
    y, T = make(slope=slope, sd=sd, seed=seed); y0, T0 = make(slope=slope, sd=sd, seed=seed + 1, turn=False)
    rows = []
    for name, (s, lagd) in methods(y).items():
        d, fa, days = score(signal(s), T, lagd); su = score.sus.copy()
        s0 = methods(y0)[name][0]; _, fa0, _ = score(signal(s0), T0, lagd); d0 = DAYS - 70
        rows.append(dict(method=name, slope=slope, sd=sd, median_delay=float(np.nanmedian(d)), p90_delay=float(np.nanpercentile(d, 90)), sustained_delay=med(su), sustained_share=float(np.mean(~np.isnan(su)) * 100),
                         false_per_year_before=float(fa.sum() / days.sum() * 365), false_per_year_no_turn=float(fa0.sum() / (len(fa0) * d0) * 365)))
    return pd.DataFrame(rows)


main_t = table(); main_t.round(2).to_csv(RES / "delay_main.csv", index=False)
sweep = pd.concat([table(slope=s, sd=d) for s in (0.05, 0.10, 0.20) for d in (1.5, 3.0, 6.0)]); sweep.round(2).to_csv(RES / "delay_by_slope_noise.csv", index=False)

# 窓の長さを変える（後ろN日）
y, T = make(); y0, T0 = make(seed=SEED + 1, turn=False); rows = []
for w in (3, 5, 7, 10, 14, 21, 28, 42, 56, 84):
    d, fa, days = score(signal(trail(y, w)), T); su = score.sus.copy(); _, fa0, _ = score(signal(trail(y0, w)), T0, start=max(70, w + 10))
    rows.append(dict(window=w, median_delay=float(np.nanmedian(d)), p90_delay=float(np.nanpercentile(d, 90)), sustained_delay=med(su), false_per_year_no_turn=float(fa0.sum() / (N * (DAYS - max(70, w + 10))) * 365)))
win = pd.DataFrame(rows); win.round(2).to_csv(RES / "delay_by_window.csv", index=False)

# 「続いた日数」の条件を変える（後ろ7日・28日）
rows = []
for run in (1, 2, 3, 5, 7, 10):
    for w in (7, 28):
        d, _, _ = score(signal(trail(y, w), run=run), T); _, fa0, _ = score(signal(trail(y0, w), run=run), T0)
        rows.append(dict(window=w, run=run, median_delay=float(np.nanmedian(d)), false_per_year_no_turn=float(fa0.sum() / (N * (DAYS - 70)) * 365)))
runs = pd.DataFrame(rows); runs.round(2).to_csv(RES / "delay_by_run_length.csv", index=False)

# 中心7日：最新の日の値を「手元にある日だけ」で出すと、あとでどれだけ動くか
fin = center7_final(y); rows = []
for k in (0, 1, 2):                     # k = その日より先に手に入っている日数（0〜2）。窓は 3+1+k 日
    c = np.cumsum(np.concatenate([np.zeros((N, 1)), y], axis=1), axis=1); w = 4 + k
    prov = np.full(y.shape, np.nan); prov[:, 3:DAYS - k] = (c[:, 4 + k:] - c[:, :DAYS - 3 - k]) / w      # t-3..t+k
    rev = (prov - fin) / fin * 100; v = rev[:, 60:-10].ravel(); v = v[~np.isnan(v)]
    rows.append(dict(days_ahead_known=k, window_days=w, mean_abs_revision_pct=float(np.mean(np.abs(v))), p90_abs_revision_pct=float(np.percentile(np.abs(v), 90)), max_abs_revision_pct=float(np.max(np.abs(v))),
                     sign_flip_share=float(np.nanmean(((prov[:, 61:-10] - prov[:, 60:-11]) * (fin[:, 61:-10] - fin[:, 60:-11]) < 0)) * 100)))
revt = pd.DataFrame(rows); revt.round(3).to_csv(RES / "center7_revision.csv", index=False)
# 曜日の型をならさない窓（5日・10日）の残り方
rows = []
for w in (5, 7, 10, 14):
    s = trail(make(slope=0.0, sd=0.0, turn=False)[0], w)[:, 100:200]; rows.append(dict(window=w, ripple_pct=float((np.nanmax(s, axis=1) / np.nanmin(s, axis=1) - 1).mean() * 100)))
rip = pd.DataFrame(rows); rip.round(3).to_csv(RES / "weekday_ripple_by_window.csv", index=False)

# SQL（DuckDB）と Python の一致
sub = pd.DataFrame({"series_id": np.repeat(np.arange(20), DAYS), "d": np.tile(np.arange(DAYS), 20), "value": y[:20].ravel()})
sub.to_csv(DATA / "daily_sample_20_series.csv", index=False)
pd.DataFrame({"series_id": np.arange(N), "turn_day": T}).to_csv(DATA / "turn_days.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("daily", sub)
q = open(SQL / "01_moving_average_tsql.sql", encoding="utf-8").read().split("WITH ma AS", 1)[1]
r = con.execute("WITH ma AS" + q.rstrip().rstrip(";")).df()
m7 = trail(y[:20], 7).ravel(); m28 = trail(y[:20], 28).ravel()
assert np.allclose(r["ma7"].values[~np.isnan(m7)], m7[~np.isnan(m7)]) and np.allclose(r["ma28"].values[~np.isnan(m28)], m28[~np.isnan(m28)])
d7 = np.zeros((20, DAYS), int); s7 = trail(y[:20], 7); d7[:, 13:] = s7[:, 13:] < s7[:, 6:-7]
assert (r["down7"].values.reshape(20, DAYS)[:, 13:] == d7[:, 13:]).all()
r.head(60).round(3).to_csv(RES / "sql_check_duckdb.csv", index=False)

g = lambda name, col: float(main_t[main_t.method == name][col].iloc[0])
out = dict(n=N, days=DAYS, slope=0.10, sd=3.0, main=json.loads(main_t.round(2).to_json(orient="records", force_ascii=False)), window=json.loads(win.round(2).to_json(orient="records")), run=runs.round(2).to_dict("records"),
           revision=revt.round(3).to_dict("records"), ripple=rip.round(3).to_dict("records"),
           sweep=sweep[sweep.method.isin(["後ろ7日", "後ろ28日"])].round(2).to_dict("records"))
json.dump(out, open(RES / "a442_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例の1本
i = 0; fig, ax = plt.subplots(figsize=(10, 4.2)); t = np.arange(DAYS)
ax.plot(t, y[i], color=LIGHT, lw=0.8, label="日々の値"); ax.plot(t, trail(y, 7)[i], color=BLUE, lw=1.6, label="後ろ7日の平均"); ax.plot(t, trail(y, 28)[i], color=ORANGE, lw=1.6, label="後ろ28日の平均")
ax.axvline(T[i], color=INK, lw=1, ls="--"); ax.text(T[i] + 2, ax.get_ylim()[1] * 0.99, "本当に向きが変わった日", fontsize=9, va="top")
for (w, c) in ((7, BLUE), (28, ORANGE)):
    sg = signal(trail(y, w))[i]; k = np.flatnonzero(sg[T[i]:])[0] + T[i]; ax.axvline(k, color=c, lw=1, ls=":"); ax.text(k + 2, ax.get_ylim()[0] + (2 if w == 7 else 8), f"{w}日平均で気づく（{k - T[i]}日後）", color=c, fontsize=9)
ax.set_xlim(120, 330); ax.set_xlabel("日"); ax.set_ylabel("値"); ax.set_title("上がり続けていた数字が下がりはじめる例"); ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a442_example.png", SRC)
# 図2：窓の長さと、遅れ・空振り
fig, ax = plt.subplots(figsize=(9, 4.4)); ax2 = ax.twinx()
ax.plot(win.window, win.median_delay, "-o", color=BLUE, label="最初に印が出るまでの日数（中央値）"); ax.plot(win.window, win.sustained_delay, "--o", color=INK, lw=1.2, ms=4, label="印が14日続きはじめるまでの日数（中央値）")
ax2.plot(win.window, win.false_per_year_no_turn, "-s", color=ORANGE, label="空振りの回数（1年あたり、右の軸）"); ax2.spines["right"].set_visible(True)
ax.set_xscale("log"); ax.set_xticks(win.window); ax.set_xticklabels(win.window); ax.minorticks_off(); ax2.minorticks_off(); ax.set_xlabel("後ろ何日の平均か"); ax.set_ylabel("気づくまでの日数"); ax2.set_ylabel("空振りの回数（1年あたり）")
ax.set_title("窓を長くすると、空振りは減り、気づくのは遅れる"); h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper center")
save(fig, "a442_window_tradeoff.png", SRC)
# 図3：動きの速さ・揺れの大きさ別（後ろ7日と28日）
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4), sharey=True)
for ax, name in zip(axs, ["後ろ7日", "後ろ28日"]):
    d = sweep[sweep.method == name]
    for sd, c in ((1.5, LIGHT), (3.0, BLUE), (6.0, INK)):
        dd = d[d.sd == sd]; ax.plot(dd.slope, dd.median_delay, "-o", color=c, label=f"揺れの大きさ {sd}")
    ax.set_xticks([0.05, 0.10, 0.20]); ax.set_xlabel("1日あたりの動き（水準100に対して）"); ax.set_title(f"{name}の平均")
axs[0].set_ylabel("気づくまでの日数（中央値）"); axs[0].legend(frameon=False, fontsize=9)
save(fig, "a442_slope_noise.png", SRC)
print(main_t.round(2).to_string()); print(win.round(2).to_string()); print(runs.round(2).to_string()); print(revt.round(3).to_string()); print(rip.round(3).to_string())
print(sweep[sweep.method.isin(["後ろ7日", "後ろ28日"])].round(2).to_string())
