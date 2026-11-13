"""543 予約枠の稼働率は、無断キャンセルと直前キャンセルをどう数えるかで何ポイント違うのか

架空の予約制の店（2025年、火曜定休、1日16枠）の予約記録を作り、稼働率を4通りで数える。
  D1 予約件数 ÷ 枠（直前キャンセルのあとに埋め直した枠は2件に数える）
  D2 予約が入った枠 ÷ 枠（枠ごとに1回）
  D3 直前キャンセルを除く：最後まで予約が残った枠（来店＋無断キャンセル）÷ 枠
  D4 来店ベース：実際に来店があった枠 ÷ 枠
差のポイント、曜日・月の順位の入れ替わりを数える。Python と SQL（DuckDB、1スレッド）で同じ値になるかを確かめる。
数字は、置いた予約・キャンセルの起きやすさで決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の予約記録（作成者が乱数で作成、seed 543）"
rng = np.random.default_rng(543)
WD = ["月", "火", "水", "木", "金", "土", "日"]
# 曜日ごとの仮定：前もって予約が入る確率、直前キャンセル（24時間以内）の確率、無断キャンセルの確率、当日予約で埋まる確率
BOOK = {0: 0.62, 2: 0.58, 3: 0.63, 4: 0.72, 5: 0.90, 6: 0.86}
LATE = {0: 0.07, 2: 0.06, 3: 0.06, 4: 0.09, 5: 0.12, 6: 0.15}
NOSHOW = {0: 0.04, 2: 0.03, 3: 0.04, 4: 0.06, 5: 0.07, 6: 0.09}
REFILL = {0: 0.30, 2: 0.25, 3: 0.30, 4: 0.40, 5: 0.35, 6: 0.25}  # 直前キャンセルの枠が当日予約で埋まる確率
WALK = {0: 0.10, 2: 0.08, 3: 0.10, 4: 0.12, 5: 0.15, 6: 0.12}    # はじめから空いていた枠が当日予約で埋まる確率
MONTH = np.array([0.92, 0.95, 1.02, 1.0, 1.04, 0.96, 1.0, 1.03, 0.97, 1.0, 1.01, 1.08])  # 月ごとの予約の入りやすさ（倍率）
MLATE = np.array([1.3, 1.1, 1.0, 0.9, 0.9, 1.2, 1.0, 0.9, 1.1, 0.9, 1.0, 1.4])         # 月ごとの直前キャンセルの起きやすさ（倍率）
SLOTS = 16

days = pd.date_range("2025-01-01", "2025-12-31")
days = days[days.weekday != 1]
slots, res = [], []
rid = 0
for d in days:
    w, m = d.weekday(), d.month - 1
    for k in range(SLOTS):
        sid = f"{d:%Y%m%d}-{k:02d}"
        slots.append((sid, d, k))
        if rng.random() < min(BOOK[w] * MONTH[m], 0.98):
            u = rng.random()
            if u < LATE[w] * MLATE[m]:
                rid += 1; res.append((rid, sid, "前もって", "直前キャンセル"))
                if rng.random() < REFILL[w]:
                    rid += 1; res.append((rid, sid, "当日", "来店"))
            elif u < LATE[w] * MLATE[m] + NOSHOW[w]:
                rid += 1; res.append((rid, sid, "前もって", "無断キャンセル"))
            else:
                rid += 1; res.append((rid, sid, "前もって", "来店"))
        elif rng.random() < WALK[w]:
            rid += 1; res.append((rid, sid, "当日", "来店"))
S = pd.DataFrame(slots, columns=["slot_id", "day", "slot_no"])
R = pd.DataFrame(res, columns=["res_id", "slot_id", "booked", "status"])
S.assign(day=S.day.dt.strftime("%Y-%m-%d")).to_csv(DATA / "slots.csv", index=False)
R.to_csv(DATA / "reservations.csv", index=False)


def rates(S, R, by):
    g = R.groupby("slot_id")
    per = pd.DataFrame({"n_res": g.size(),
                        "kept": g.status.agg(lambda s: s.isin(["来店", "無断キャンセル"]).any()),
                        "came": g.status.agg(lambda s: (s == "来店").any())})
    x = S.set_index("slot_id").join(per).fillna({"n_res": 0, "kept": False, "came": False})
    x["wd"] = x.day.dt.weekday.map(dict(enumerate(WD)))
    x["month"] = x.day.dt.month
    x["all"] = "全体"
    a = x.groupby(by).agg(slots=("n_res", "size"), D1=("n_res", "sum"), D2=("n_res", lambda s: (s > 0).sum()),
                          D3=("kept", "sum"), D4=("came", "sum"))
    for c in ["D1", "D2", "D3", "D4"]:
        a[c] = a[c] / a.slots * 100
    return a


tot = rates(S, R, "all")
wd = rates(S, R, "wd").reindex([w for w in WD if w != "火"])
mo = rates(S, R, "month")

# SQL（DuckDB）で同じ稼働率を出して突き合わせる
con = duckdb.connect(); con.execute("SET threads=1")
con.register("slots", S); con.register("reservations", R)
q = open(SQL / "02_utilization_duckdb.sql", encoding="utf-8").read()
sq = con.execute(q).df().set_index("wd").reindex(wd.index)
assert np.allclose(sq[["D1", "D2", "D3", "D4"]].to_numpy(), wd[["D1", "D2", "D3", "D4"]].to_numpy())


def discordant(a, b):
    n = len(a); c = 0
    for i in range(n):
        for j in range(i + 1, n):
            if (a[i] - a[j]) * (b[i] - b[j]) < 0:
                c += 1
    return c


DEF = ["D1", "D2", "D3", "D4"]
flips = []
for tab, name in [(wd, "曜日"), (mo, "月")]:
    for i in range(4):
        for j in range(i + 1, 4):
            a, b = tab[DEF[i]].to_numpy(), tab[DEF[j]].to_numpy()
            ra = pd.Series(a).rank(ascending=False).to_numpy(); rb = pd.Series(b).rank(ascending=False).to_numpy()
            flips.append({"単位": name, "定義1": DEF[i], "定義2": DEF[j], "ペア数": len(a) * (len(a) - 1) // 2,
                          "順番が逆になるペア": discordant(a, b), "順位が変わる数": int((ra != rb).sum()),
                          "1位1": str(tab.index[np.argmax(a)]), "1位2": str(tab.index[np.argmax(b)])})
fl = pd.DataFrame(flips)
fl.to_csv(RES / "rank_flips.csv", index=False)
wd.round(3).to_csv(RES / "by_weekday.csv"); mo.round(3).to_csv(RES / "by_month.csv")
counts = R.groupby(["booked", "status"]).size()
out = {"slots": int(len(S)), "reservations": int(len(R)), "counts": {f"{a}・{b}": int(v) for (a, b), v in counts.items()},
       "total": tot[DEF].round(2).iloc[0].to_dict(), "weekday": wd[DEF].round(2).to_dict(orient="index"),
       "month_range": {c: [round(mo[c].min(), 2), round(mo[c].max(), 2)] for c in DEF},
       "gap_D1_D4_weekday": (wd.D1 - wd.D4).round(2).to_dict(), "gap_D1_D4_month": [round((mo.D1 - mo.D4).min(), 2), round((mo.D1 - mo.D4).max(), 2)],
       "sql_match": True}
(RES / "a543_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))

COL = {"D1": GRAY, "D2": LIGHT, "D3": BLUE, "D4": ORANGE}
LAB = {"D1": "D1 予約件数", "D2": "D2 予約が入った枠", "D3": "D3 直前キャンセルを除く", "D4": "D4 来店ベース"}
# 図1 全体
fig, ax = plt.subplots(figsize=(8.2, 3.6))
v = tot[DEF].iloc[0]
ax.barh(range(4), v, color=[COL[c] for c in DEF])
for i, c in enumerate(DEF):
    ax.text(v[c] + 0.6, i, f"{v[c]:.1f}%", va="center", fontsize=11)
ax.set_yticks(range(4), [LAB[c] for c in DEF]); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("稼働率（%）")
ax.set_title(f"同じ1年分の予約記録（{len(S):,}枠）でも、数え方で稼働率は{v.D1 - v.D4:.1f}ポイント違う")
save(fig, "a543_total.png", SRC)

# 図2 曜日
fig, ax = plt.subplots(figsize=(8.6, 4.2))
x = np.arange(len(wd)); w = 0.2
for i, c in enumerate(DEF):
    ax.bar(x + (i - 1.5) * w, wd[c], w, color=COL[c], label=LAB[c])
ax.set_xticks(x, [f"{d}曜" for d in wd.index]); ax.set_ylabel("稼働率（%）"); ax.set_ylim(40, 105)
ax.legend(ncol=2, frameon=False, fontsize=9, loc="upper left")
for xi, d in zip(x, wd.index):
    ax.text(xi, 41.5, f"差 {wd.D1[d] - wd.D4[d]:.1f}", ha="center", fontsize=9, color=INK)
ax.set_title("曜日ごとの稼働率：土日ほど、数え方の差が大きい")
save(fig, "a543_by_weekday.png", SRC + "。「差」は D1 − D4（ポイント）")

# 図3 月の順位
fig, ax = plt.subplots(figsize=(8.6, 4.4))
for c in ["D1", "D4"]:
    r = mo[c].rank(ascending=False)
    ax.plot(mo.index, r, "o-", color=COL[c] if c != "D1" else BLUE, label=LAB[c] + " の順位")
ax.invert_yaxis(); ax.set_yticks(range(1, 13)); ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)])
ax.set_ylabel("12か月の中の順位（1が最も高い）"); ax.legend(frameon=False, fontsize=9, loc="lower center", ncol=2)
f24 = fl[(fl.単位 == "月") & (fl.定義1 == "D1") & (fl.定義2 == "D4")].iloc[0]
ax.set_title(f"月の順位：D1 と D4 で{f24['順位が変わる数']}か月の順位が変わり、{f24['順番が逆になるペア']}組の大小が入れ替わる")
save(fig, "a543_month_rank.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)); print(fl.to_string())
