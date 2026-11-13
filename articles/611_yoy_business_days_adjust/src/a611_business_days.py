"""611 営業日の数が違う月を前年同月と比べると、前年比は何ポイント動くのか

架空の2つの業態の日次売上（2024〜2025年）を作り、2025年の月次の前年比を3通りで出す。本当の伸びは毎日 +2%。
  業態W：平日に売れる（土日祝と年末年始12/29〜1/3はほぼ0。法人向けの卸を想定）
  業態R：土日祝に多く売れる（小売を想定、年末年始も営業）
  M1 月の合計をそのまま比べる
  M2 営業日（業態Wは平日、業態Rは全日）1日あたりで比べる
  M3 曜日の構成をそろえる：前年の「日の種類（平日・土・日祝）ごとの1日平均」に今年の日数を掛けた見込みと比べる
本当の +2% からのずれ・符号が変わる月の数を数える。祝日は2024・2025年の国民の祝日と振替休日。seed 611。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空の2業態の日次売上（作成者が乱数で作成、seed 611）。祝日は2024・2025年の国民の祝日と振替休日"
rng = np.random.default_rng(611)
HOL = pd.to_datetime([
    "2024-01-01", "2024-01-08", "2024-02-11", "2024-02-12", "2024-02-23", "2024-03-20", "2024-04-29", "2024-05-03", "2024-05-04",
    "2024-05-05", "2024-05-06", "2024-07-15", "2024-08-11", "2024-08-12", "2024-09-16", "2024-09-22", "2024-09-23", "2024-10-14",
    "2024-11-03", "2024-11-04", "2024-11-23",
    "2025-01-01", "2025-01-13", "2025-02-11", "2025-02-23", "2025-02-24", "2025-03-20", "2025-04-29", "2025-05-03", "2025-05-04",
    "2025-05-05", "2025-05-06", "2025-07-21", "2025-08-11", "2025-09-15", "2025-09-23", "2025-10-13", "2025-11-03", "2025-11-23",
    "2025-11-24"])
days = pd.date_range("2024-01-01", "2025-12-31")
df = pd.DataFrame({"date": days})
df["hol"] = df.date.isin(HOL)
df["yearend"] = ((df.date.dt.month == 12) & (df.date.dt.day >= 29)) | ((df.date.dt.month == 1) & (df.date.dt.day <= 3))
dow = df.date.dt.dayofweek
df["kind"] = np.where(df.hol | (dow == 6), "日祝", np.where(dow == 5, "土", "平日"))
g = np.where(df.date.dt.year == 2025, 1.02, 1.0)
season = 1 + 0.05 * np.sin(2 * np.pi * (df.date.dt.dayofyear - 60) / 365)
noise_w = rng.lognormal(0, 0.03, len(df)); noise_r = rng.lognormal(0, 0.03, len(df))
w_level = np.where(df.kind == "平日", 1.0, 0.02); w_level = np.where(df.yearend, 0.02, w_level)
r_level = np.select([df.kind == "平日", df.kind == "土"], [1.0, 1.6], 1.5)
df["W"] = np.round(500000 * w_level * season * g * noise_w, -2)
df["R"] = np.round(300000 * r_level * season * g * noise_r, -2)
df.to_csv(RES / "daily_sales.csv", index=False)
df["y"] = df.date.dt.year; df["m"] = df.date.dt.month
df["open_W"] = (df.kind == "平日") & ~df.yearend
rows = []
for biz in ["W", "R"]:
    for m in range(1, 13):
        c = df[(df.y == 2025) & (df.m == m)]; p = df[(df.y == 2024) & (df.m == m)]
        m1 = c[biz].sum() / p[biz].sum() - 1
        if biz == "W":
            m2 = (c[biz].sum() / c.open_W.sum()) / (p[biz].sum() / p.open_W.sum()) - 1
            kc = c.assign(k=np.where(c.open_W, "営業", "休み")); kp = p.assign(k=np.where(p.open_W, "営業", "休み"))
        else:
            m2 = (c[biz].sum() / len(c)) / (p[biz].sum() / len(p)) - 1
            kc = c.assign(k=c.kind); kp = p.assign(k=p.kind)
        avg_p = kp.groupby("k")[biz].mean()
        expect = sum(avg_p.get(k, 0) * n for k, n in kc.k.value_counts().items())
        m3 = c[biz].sum() / expect - 1
        rows.append({"biz": biz, "month": m, "M1": round(100 * m1, 2), "M2": round(100 * m2, 2), "M3": round(100 * m3, 2),
                     "open_days_2025": int(c.open_W.sum()) if biz == "W" else len(c), "open_days_2024": int(p.open_W.sum()) if biz == "W" else len(p),
                     "weekend_hol_2025": int((c.kind != "平日").sum()), "weekend_hol_2024": int((p.kind != "平日").sum())})
res = pd.DataFrame(rows); res.to_csv(RES / "monthly_yoy.csv", index=False)
out = {"true_growth_pct": 2.0}
for biz in ["W", "R"]:
    s = res[res.biz == biz]
    out[biz] = {k: {"mean_abs_dev": round(float((s[k] - 2).abs().mean()), 2), "max_abs_dev": round(float((s[k] - 2).abs().max()), 2),
                    "range": [float(s[k].min()), float(s[k].max())], "minus_months": int((s[k] < 0).sum())} for k in ["M1", "M2", "M3"]}
    out[biz]["months"] = s[["month", "M1", "M2", "M3", "open_days_2025", "open_days_2024"]].to_dict(orient="records")
json.dump(out, open(RES / "a611_main.json", "w"), ensure_ascii=False, indent=1)

x = np.arange(1, 13)
lab = {"M1": "月の合計をそのまま", "M2": "営業日1日あたり", "M3": "日の種類の構成をそろえる"}
col = {"M1": ORANGE, "M2": BLUE, "M3": GREEN}
for biz, fn, ttl in [("W", "a611_wholesale_yoy.png", "平日に売れる業態（卸を想定）：2025年の月次の前年比"),
                     ("R", "a611_retail_yoy.png", "土日祝に多く売れる業態（小売を想定）：2025年の月次の前年比")]:
    s = res[res.biz == biz]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    for k, mk in [("M1", "o"), ("M2", "s"), ("M3", "^")]:
        ax.plot(x, s[k], marker=mk, color=col[k], label=lab[k])
    ax.axhline(2, color=GRAY, ls=":", lw=1); ax.axhline(0, color=GRAY, lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels([f"{i}月" for i in x]); ax.set_ylabel("前年比（%）。点線が本当の +2%")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13)); ax.set_title(ttl, pad=28)
    save(fig, fn, SRC, y=-0.04)
# 図3：営業日（業態W）の数の差
s = res[res.biz == "W"]
fig, ax = plt.subplots(figsize=(8.5, 3.4))
dd = s.open_days_2025.values - s.open_days_2024.values
ax.bar(x, dd, color=[BLUE if v >= 0 else ORANGE for v in dd])
for xx, v, a, b in zip(x, dd, s.open_days_2025, s.open_days_2024):
    ax.text(xx, v, f"{b}→{a}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"{i}月" for i in x])
ax.set_ylabel("2025年−2024年（日）"); ax.set_ylim(min(dd) - 1.2, max(dd) + 1.2)
ax.set_title("平日（営業日）の数の前年との差（数字は2024年→2025年）")
save(fig, "a611_business_days_diff.png", SRC)
print(json.dumps({k: v for k, v in out.items()}, ensure_ascii=False, indent=1))
