"""724 日次の売上に7日以外の幅の移動平均をかけると、曜日の波はどれだけ残るのか

架空の店の2年分（2024-01-01〜2025-12-30、730日）の日次売上（万円）。
  ふだんの水準：100万円から2年でゆるやかに+15%
  曜日の波：月 −12%・火 −15%・水 −10%・木 −8%・金 +5%・土 +25%・日 +15%（平均0）
  2025-06-01 から水準が+10%上がる（売り場の変更などの想定）
  日ごとのノイズ：標準偏差4%
その日までの k 日（k＝3・5・7・14・28）の移動平均（後ろ向き）を出し、
  残った曜日の波の大きさ（曜日の波だけに同じ移動平均をかけたときの最大−最小）
  本当の水準（曜日の波とノイズを除いたもの）との誤差（RMSE）
  2025-06-01 の水準の上がりを半分まで映すのにかかった日数
を比べる。DuckDB の SQL（ROWS BETWEEN）と Python の移動平均が一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の店の日次売上（作成者が乱数で作成、seed 724）"
rng = np.random.default_rng(724)
DATA.mkdir(exist_ok=True)
dates = pd.date_range("2024-01-01", periods=730, freq="D")
WEEK = np.array([-0.12, -0.15, -0.10, -0.08, 0.05, 0.25, 0.15])        # 月〜日
assert abs(WEEK.mean()) < 1e-12
t = np.arange(730)
step_day = int(np.where(dates == pd.Timestamp("2025-06-01"))[0][0])
level = 100 * (1 + 0.15 * t / 729) * np.where(t >= step_day, 1.10, 1.0)
wk = WEEK[dates.dayofweek]
sales = np.round(level * (1 + wk) * (1 + rng.normal(0, 0.04, 730)), 1)
D = pd.DataFrame({"sales_date": dates.date, "sales": sales})
D.to_csv(DATA / "daily_sales.csv", index=False)

KS = [3, 5, 7, 14, 28]
for k in KS: D[f"ma{k}"] = D.sales.rolling(k, min_periods=1).mean()
con = duckdb.connect(); con.execute("SET threads=1")
con.register("d0", D[["sales_date", "sales"]]); con.execute("CREATE TABLE daily_sales AS SELECT * FROM d0")
dq = con.execute((SQL / "02_moving_avg_duckdb.sql").read_text(encoding="utf-8")).df()
for k in KS: assert np.allclose(dq[f"ma{k}"].values, D[f"ma{k}"].values), k

rows = []
valid = t >= 27                                                           # 28日分そろってから
for k in KS:
    wave = pd.Series(level * wk).rolling(k).mean().values / level        # 曜日の波だけに移動平均（水準に対する割合）
    w = wave[valid & (t < step_day - 30) | valid & (t > step_day + 30)]
    amp = (np.nanmax(w) - np.nanmin(w)) * 100
    ma = D[f"ma{k}"].values
    rmse = np.sqrt(np.mean(((ma - level) / level)[valid] ** 2)) * 100
    pre = level[step_day - 1]; post = level[step_day]
    half = pre + 0.5 * (post - pre)
    # ノイズと曜日の波を除いた移動平均（水準だけ）で、半分まで映す日数
    lv = pd.Series(level).rolling(k).mean().values
    lag = int(np.argmax(lv[step_day:] >= half))
    rows.append({"window": k, "weekday_wave_amp_pct": amp, "rmse_vs_level_pct": rmse, "days_to_half_step": lag})
S = pd.DataFrame(rows); S.round(3).to_csv(RES / "summary.csv", index=False)
D.round(3).to_csv(RES / "moving_averages.csv", index=False)

out = {"days": 730, "weekday_effect_pct": dict(zip(["月", "火", "水", "木", "金", "土", "日"], (WEEK * 100).round(0).astype(int).tolist())),
       "weekday_range_pct": round(float((WEEK.max() - WEEK.min()) * 100), 0), "noise_sd_pct": 4, "step_date": "2025-06-01", "step_pct": 10,
       "by_window": {str(r.window): {"wave_amp_pct": round(r.weekday_wave_amp_pct, 2), "rmse_pct": round(r.rmse_vs_level_pct, 2),
                                     "days_to_half_step": int(r.days_to_half_step)} for r in S.itertuples()},
       "sql_matches_python": True}
json.dump(out, open(RES / "a724_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：13週間の日次と移動平均
sel = (dates >= "2025-04-07") & (dates < "2025-07-07")
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(dates[sel], D.sales[sel], color=GRAY, lw=0.8, label="日次の売上")
for k, col, lw in [(5, ORANGE, 1.6), (7, BLUE, 1.8), (28, GREEN, 1.6)]:
    ax.plot(dates[sel], D[f"ma{k}"][sel], color=col, lw=lw, label=f"{k}日の移動平均")
ax.plot(dates[sel], level[sel], color=INK, lw=0.8, ls="--", label="本当の水準")
ax.axvline(pd.Timestamp("2025-06-01"), color=GRAY, lw=0.8, ls=":")
ax.set_ylabel("売上（万円）"); ax.legend(frameon=False, fontsize=8.5, ncol=5, loc="upper left")
ax.set_ylim(D.sales[sel].min() * 0.95, D.sales[sel].max() * 1.12)
ax.set_title("5日の移動平均には曜日の波が残る。7日と28日は波が消える（6/1から水準+10%）")
save(fig, "a724_series.png", SRC)

# 図2：残った曜日の波
fig, ax = plt.subplots(figsize=(8, 3.6))
cols = [ORANGE if k % 7 else BLUE for k in KS]
ax.bar([f"{k}日" for k in KS], S.weekday_wave_amp_pct, color=cols)
for i, v in enumerate(S.weekday_wave_amp_pct): ax.text(i, v + 0.4, f"{v:.1f}%", ha="center", fontsize=9)
ax.axhline(out["weekday_range_pct"], color=GRAY, ls="--", lw=0.8); ax.text(4.4, out["weekday_range_pct"] + 0.5, f"元の波 {out['weekday_range_pct']:.0f}%", ha="right", fontsize=8.5, color=GRAY)
ax.set_ylabel("残った曜日の波（最大−最小、水準に対する%）"); ax.set_xlabel("移動平均の幅")
ax.set_ylim(0, out["weekday_range_pct"] * 1.15)
ax.set_title("7の倍数の幅なら曜日の波は0。3日・5日では大きく残る")
save(fig, "a724_wave.png", SRC)

# 図3：誤差と遅れ
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
axes[0].bar([f"{k}日" for k in KS], S.rmse_vs_level_pct, color=cols)
for i, v in enumerate(S.rmse_vs_level_pct): axes[0].text(i, v + 0.15, f"{v:.1f}%", ha="center", fontsize=9)
axes[0].set_ylabel("本当の水準との誤差（RMSE、%）"); axes[0].set_title("誤差は7日・14日が小さい")
axes[1].bar([f"{k}日" for k in KS], S.days_to_half_step, color=GRAY)
for i, v in enumerate(S.days_to_half_step): axes[1].text(i, v + 0.3, f"{v}日", ha="center", fontsize=9)
axes[1].set_ylabel("水準の上がりを半分映すまで（日）"); axes[1].set_title("幅が広いほど、変化に遅れる")
save(fig, "a724_error_lag.png", SRC)
print(json.dumps(out, ensure_ascii=False))
