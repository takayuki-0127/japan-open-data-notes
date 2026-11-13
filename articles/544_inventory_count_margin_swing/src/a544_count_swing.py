"""544 棚卸の差異を月末にまとめて計上すると、月の粗利はどれだけ振れるのか

架空の小売店（2023〜2025年の36か月）で、毎日少しずつ在庫が目減りする（帳簿に出ない減り）と置く。
目減りは実地棚卸をした月にまとめて原価に入ると置き、棚卸の回数で月の粗利率がどう振れるかを数える。
  S1 年1回（12月）  S2 四半期（3・6・9・12月）  S3 毎月
  S4 年1回＋前の年の目減りの率で毎月見込みを入れ、12月に残りを入れる
  参考：本当の目減り（その月に起きた分）を入れた粗利率
会計処理の良し悪しや、どの方法を使うべきかを扱うものではない。数え方で数字がどう動くかを測るだけ。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の小売店の売上と在庫（作成者が乱数で作成、seed 544）"
COST_RATE = 0.70          # 売上原価率（帳簿上、目減りを除く）
SHRINK = 0.012            # 目減りの平均：原価の1.2%（仮定）
SEASON = np.array([0.85, 0.80, 0.95, 0.95, 1.00, 0.95, 1.05, 1.05, 0.95, 1.00, 1.05, 1.40])


def make(seed, shrink=SHRINK, years=4):
    rng = np.random.default_rng(seed)
    rows = []
    for y in range(2022, 2022 + years):  # 2022年は S4 の見込みの率を作るためだけに使う
        for m in range(1, 13):
            days = pd.Period(f"{y}-{m:02d}").days_in_month
            sales_d = 10_000_000 / 30 * SEASON[m - 1] * rng.lognormal(0, 0.15, days)
            cogs = sales_d.sum() * COST_RATE
            # 目減り：毎日の小さな減り＋まれな大きな減り（年に数回、仮定）
            daily = (sales_d * COST_RATE * shrink * 0.75 * rng.gamma(4, 0.25, days)).sum()
            big = (rng.random(days) < 3 / 365).sum() * rng.lognormal(np.log(10_000_000 * COST_RATE * shrink * 1.0), 0.4)
            rows.append({"year": y, "month": m, "sales": sales_d.sum(), "cogs": cogs, "shrink": daily + big})
    d = pd.DataFrame(rows)
    d.attrs["shrink"] = shrink
    return d


def schedule(df, kind):
    """各月に原価へ入れる目減りの額"""
    out = np.zeros(len(df))
    acc = 0.0
    for i, r in df.iterrows():
        acc += r.shrink
        count = {"S1": r.month == 12, "S2": r.month in (3, 6, 9, 12), "S3": True}.get(kind)
        if kind == "S4":
            prev = df[(df.year == r.year - 1)]
            rate = (prev.shrink.sum() / prev.cogs.sum()) if len(prev) else df.attrs["shrink"]  # 前の年の率（初年は置いた平均の率）
            est = r.cogs * rate
            out[i] = est
            if r.month == 12:  # 12月に実地棚卸をして、見込みとの差を入れる
                yr = df[(df.year == r.year)]
                booked = out[yr.index[:-1]].sum() + est
                out[i] += yr.shrink.sum() - booked
            continue
        if count:
            out[i] = acc; acc = 0.0
    return out


def margins(df):
    m = pd.DataFrame({"year": df.year, "month": df.month})
    m["本当の目減り"] = (df.sales - df.cogs - df.shrink) / df.sales * 100
    for k in ["S1", "S2", "S3", "S4"]:
        m[k] = (df.sales - df.cogs - schedule(df, k)) / df.sales * 100
    return m[m.year >= 2023].reset_index(drop=True)


df = make(544)
mg = margins(df)
df = df[df.year >= 2023].reset_index(drop=True)
df.round(0).to_csv(RES / "monthly_store.csv", index=False)
mg.round(3).to_csv(RES / "monthly_margin.csv", index=False)
NAMES = {"S1": "S1 年1回（12月）", "S2": "S2 四半期", "S3": "S3 毎月（本当と同じ）", "S4": "S4 年1回＋見込み", "本当の目減り": "本当の目減り（参考）"}
summ = []
for k in ["本当の目減り", "S3", "S2", "S4", "S1"]:
    v = mg[k]
    summ.append({"方法": NAMES[k], "平均": v.mean(), "標準偏差": v.std(ddof=0), "最小": v.min(), "最大": v.max(),
                 "最大−最小": v.max() - v.min(), "12月の平均": v[mg.month == 12].mean(),
                 "12月以外の平均": v[mg.month != 12].mean(),
                 "本当との差の平均（絶対値）": (v - mg["本当の目減り"]).abs().mean(),
                 "本当との差の最大（絶対値）": (v - mg["本当の目減り"]).abs().max()})
sm = pd.DataFrame(summ)
sm["12月の落ち込み"] = sm["12月以外の平均"] - sm["12月の平均"]
sm.round(3).to_csv(RES / "summary.csv", index=False)

# 目減りの大きさを変えたとき（各 200 本の店、3年）
rows = []
for s in [0.005, 0.01, 0.015, 0.02, 0.03]:
    acc = {k: ([], []) for k in ["S1", "S2", "S3", "S4"]}
    for b in range(200):
        mm = margins(make(10_000 + b, shrink=s))
        for k in acc:
            acc[k][0].append(mm[k].std(ddof=0))
            acc[k][1].append(mm[k][mm.month != 12].mean() - mm[k][mm.month == 12].mean())
    for k, (sd, dip) in acc.items():
        rows.append({"shrink": s, "method": k, "sd": np.mean(sd), "dec_dip": np.mean(dip)})
sens = pd.DataFrame(rows)
sens.round(4).to_csv(RES / "by_shrink_rate.csv", index=False)

out = {"assume": {"cost_rate": COST_RATE, "shrink": SHRINK, "season": SEASON.tolist(), "big_events_per_year": 3},
       "store": {"sales_3y": float(df.sales.sum()), "shrink_rate_actual": float(df.shrink.sum() / df.cogs.sum()),
                 "shrink_by_year": (df.groupby("year").shrink.sum() / df.groupby("year").cogs.sum()).round(5).to_dict()},
       "summary": sm.round(3).to_dict(orient="records"),
       "sens": sens.round(4).to_dict(orient="records")}
(RES / "a544_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))

COL = {"本当の目減り": INK, "S1": ORANGE, "S2": BLUE, "S3": GREEN, "S4": GRAY}
# 図1 36か月の粗利率
fig, ax = plt.subplots(figsize=(9.0, 4.4))
x = np.arange(len(mg))
for k in ["S1", "S2", "S4", "S3", "本当の目減り"]:
    ax.plot(x, mg[k], "-" if k != "本当の目減り" else "--", color=COL[k], lw=1.6 if k != "本当の目減り" else 1.2, label=NAMES[k],
            marker="o" if k == "S1" else None, ms=3)
ax.set_xticks(x[::3], [f"{y % 100}年{m}月" for y, m in zip(mg.year[::3], mg.month[::3])], fontsize=9)
ax.set_ylabel("月の粗利率（%）"); ax.legend(frameon=False, fontsize=9, ncol=3, loc="lower left")
ax.set_title("棚卸が年1回だと、12月だけ粗利率が大きく落ちる（2023〜2025年）")
save(fig, "a544_monthly_margin.png", SRC)

# 図2 ばらつきと12月の落ち込み
fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
order = ["本当の目減り", "S3", "S2", "S4", "S1"]
lab = [NAMES[k].replace("（参考）", "\n（参考）") for k in order]
smi = sm.set_index("方法")
for ax, col, ttl in [(axes[0], "標準偏差", "月の粗利率の標準偏差（ポイント）"), (axes[1], "12月の落ち込み", "12月とそれ以外の月の差（ポイント）")]:
    v = [smi.loc[NAMES[k], col] for k in order]
    ax.barh(range(5), v, color=[COL[k] for k in order])
    for i, vv in enumerate(v):
        ax.text(max(vv, 0) + 0.02 * max(v), i, f"{vv:.2f}", va="center", fontsize=10)
    ax.set_yticks(range(5), lab if ax is axes[0] else [""] * 5); ax.invert_yaxis(); ax.set_title(ttl, fontsize=11)
    ax.set_xlim(min(0, min(v)) - 0.1 * max(v), max(v) * 1.25)
    ax.axvline(0, color=INK, lw=0.8)
fig.suptitle("棚卸の回数と、月の粗利率の振れ（36か月）", y=1.02)
save(fig, "a544_swing.png", SRC)

# 図3 目減りの大きさと12月の落ち込み
fig, ax = plt.subplots(figsize=(8.0, 4.0))
for k in ["S1", "S2", "S4", "S3"]:
    s = sens[sens.method == k]
    ax.plot(s.shrink * 100, s.dec_dip, "o-", color=COL[k], label=NAMES[k])
    ax.text(s.shrink.iloc[-1] * 100 + 0.05, s.dec_dip.iloc[-1], f"{s.dec_dip.iloc[-1]:.1f}", va="center", fontsize=9, color=COL[k])
ax.set_xlabel("目減りの平均（原価に対する%）"); ax.set_ylabel("12月の落ち込み（ポイント）")
ax.legend(frameon=False, fontsize=9); ax.set_xlim(0.3, 3.4)
ax.set_title("目減りが大きいほど、年1回の棚卸の月の落ち込みは大きい（200店×3年の平均）")
save(fig, "a544_dip_by_shrink.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:3000]); print(sm.round(2).to_string())
