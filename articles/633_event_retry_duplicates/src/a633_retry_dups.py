"""633 送り直しで二重に届いたイベントを除かずに数えると、申込みの数は何%多くなるのか

架空のサービスの申込みイベント30日分（1日 約2,000件、時間帯で多さが変わる）。
送る側は、返事が来ないと同じイベント（同じ event_id・同じ端末の時刻）を送り直す（試行回数 attempt が1つ増え、受け取り時刻が変わる）。
返事が来ない確率は、その時間の混み具合に比例する（平均 p、p = 1%・3%・6%）。送り直しは最大3回。
別に、利用者が本当に2回申し込んだもの（別の event_id）も 0.5% 混ぜる（これは数えるべきもの）。
数え方：D0 そのまま、D1 全部の列が同じ行を除く、D2 受け取り時刻と試行回数を除いた列で同じ行を除く、D3 event_id で1行にする、
D4 同じ利用者の10分以内の申込みを1件にまとめる。本当の数（event_id の数）と比べる。
平均 3% の場面は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。数字は置いた送り直しの多さで決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の申込みイベント（作成者が乱数で作成、seed 633）"
rng = np.random.default_rng(633)
DAYS = 30
hw = 0.2 + np.exp(-((np.arange(24) - 21) ** 2) / 8) + 0.6 * np.exp(-((np.arange(24) - 12) ** 2) / 6)


def make(p_mean, rng):
    rows = []
    eid = 0
    for d in range(DAYS):
        lam = hw / hw.sum() * 2000 * (1.3 if d % 7 in (5, 6) else 1.0)
        for h in range(24):
            k = rng.poisson(lam[h]); load = lam[h] / lam.mean()
            ts = d * 86400 + h * 3600 + rng.uniform(0, 3600, k)
            users = rng.integers(1, 40001, k)
            p = min(p_mean * load, 0.5)
            for t, u in zip(ts, users):
                eid += 1
                rows.append((eid, u, t, t + rng.uniform(0.05, 0.5), 1, True))
                a, tt = 1, t
                while a < 4 and rng.random() < p:           # 返事が来ず、送り直す
                    a += 1; tt = tt + rng.uniform(5, 30)
                    rows.append((eid, u, t, tt + rng.uniform(0.05, 0.5), a, False))
                if rng.random() < 0.005:                    # 本当にもう1回申し込む
                    eid += 1; t2 = t + rng.uniform(30, 300)
                    rows.append((eid, u, t2, t2 + rng.uniform(0.05, 0.5), 1, True))
    E = pd.DataFrame(rows, columns=["event_id", "user_id", "client_ts", "received_at", "attempt", "first"])
    E["event_type"] = "apply"
    return E


def count(E):
    true = E.event_id.nunique()
    d0 = len(E)
    d1 = len(E.drop(columns=["first"]).drop_duplicates())
    d2 = len(E[["event_id", "user_id", "event_type", "client_ts"]].drop_duplicates())
    d3 = E.event_id.nunique()
    f = E.sort_values(["user_id", "client_ts"]).drop_duplicates("event_id")
    gap = f.groupby("user_id").client_ts.diff()
    d4 = int((gap.isna() | (gap > 600)).sum())
    return {"true": true, "D0": d0, "D1": d1, "D2": d2, "D3": d3, "D4": d4}


rows, keep = [], {}
for p in [0.01, 0.03, 0.06]:
    E = make(p, rng)
    c = count(E); c["p_mean"] = p
    E["day"] = (E.client_ts // 86400).astype(int)
    daily = E.groupby("day").agg(rows=("event_id", "size"), true=("event_id", "nunique"))
    c["daily_over_pct_min"] = float(100 * (daily.rows / daily.true - 1).min()); c["daily_over_pct_max"] = float(100 * (daily.rows / daily.true - 1).max())
    E["hour"] = ((E.client_ts % 86400) // 3600).astype(int)
    hourly = E.groupby("hour").agg(rows=("event_id", "size"), true=("event_id", "nunique"))
    keep[p] = (E, hourly)
    rows.append(c)
S = pd.DataFrame(rows)
for k in ["D0", "D1", "D2", "D3", "D4"]:
    S[f"{k}_over_pct"] = 100 * (S[k] / S["true"] - 1)
S.round(3).to_csv(RES / "summary.csv", index=False)
h3 = keep[0.03][1]; h3["over_pct"] = 100 * (h3.rows / h3["true"] - 1); h3.round(3).to_csv(RES / "hourly_p3.csv")

# SQL
E3 = keep[0.03][0].drop(columns=["first", "day", "hour"])
con = duckdb.connect(); con.execute("SET threads=1"); con.register("events", E3)
qs = [q.strip() for q in (SQL / "02_dedup_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
sv = [con.execute(q[q.index("SELECT"):]).fetchone()[0] for q in qs]
c3 = S[S.p_mean == 0.03].iloc[0]
assert sv == [c3.D0, c3.D1, c3.D2, c3.D3], (sv, c3)
pd.DataFrame({"method": ["D0", "D1", "D2", "D3"], "duckdb": sv}).to_csv(RES / "sql_p3.csv", index=False)
out = {"days": DAYS, "summary": S.round(3).to_dict(orient="records"), "hourly_p3_over_pct": {int(k): round(float(v), 2) for k, v in h3.over_pct.items()}}
json.dump(out, open(RES / "a633_main.json", "w"), ensure_ascii=False, indent=1)

LAB = {"D0": "そのまま数える", "D1": "全部の列が同じ行を除く", "D2": "時刻・試行回数以外が同じ行を除く", "D3": "event_id で1行に", "D4": "同じ人の10分以内を1件に"}
COL = {"D0": ORANGE, "D1": LIGHT, "D2": GREEN, "D3": BLUE, "D4": GRAY}
# 図1
fig, ax = plt.subplots(figsize=(8.8, 4.2))
xs = np.arange(3); w = 0.16
for j, k in enumerate(["D0", "D1", "D2", "D3", "D4"]):
    v = S[f"{k}_over_pct"]
    ax.bar(xs + (j - 2) * w, v, w, color=COL[k], label=LAB[k])
    for x, vv in zip(xs + (j - 2) * w, v):
        ax.text(x, vv + (0.15 if vv >= 0 else -0.15), f"{vv:+.1f}", ha="center", fontsize=7.5, va="bottom" if vv >= 0 else "top")
ax.axhline(0, color=INK, lw=0.6); ax.set_xticks(xs); ax.set_xticklabels([f"返事が来ない確率 平均{int(p*100)}%" for p in S.p_mean])
ax.set_ylabel("本当の申込み数との差（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
ax.set_title("数え方ごとの、本当の申込み数（event_id の数）との差")
save(fig, "a633_methods.png", SRC)

# 図2：時間帯
fig, ax = plt.subplots(figsize=(8.5, 4))
ax2 = ax.twinx()
ax.bar(h3.index, h3["true"] / DAYS, color=LIGHT, label="1時間あたりの申込み（左）")
ax2.plot(h3.index, h3.over_pct, marker="o", color=ORANGE, label="そのまま数えたときの多さ（右、%）")
ax.set_xlabel("時刻"); ax.set_ylabel("申込み（件）"); ax2.set_ylabel("多く数えた割合（%）")
ax.set_title("返事が来ない確率 平均3%：混む時間ほど二重が多い")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper left")
ax2.spines["right"].set_visible(True)
save(fig, "a633_hourly.png", SRC)

# 図3：日ごと
fig, ax = plt.subplots(figsize=(8.5, 4))
for p, c in zip([0.01, 0.03, 0.06], [LIGHT, BLUE, ORANGE]):
    E = keep[p][0]
    dd = E.groupby("day").agg(rows=("event_id", "size"), true=("event_id", "nunique"))
    ax.plot(dd.index + 1, 100 * (dd.rows / dd["true"] - 1), marker="o", ms=3, color=c, label=f"平均{int(p*100)}%")
ax.set_xlabel("日"); ax.set_ylabel("そのまま数えたときの多さ（%）"); ax.legend(frameon=False, fontsize=9, title="返事が来ない確率", title_fontsize=9)
ax.set_title("日ごとの、そのまま数えたときの多さ")
save(fig, "a633_daily.png", SRC)
print(S.round(2).to_string()); print(h3.round(2))
