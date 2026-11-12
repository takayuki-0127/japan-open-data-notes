"""411 「保険年齢」と「満年齢」では、同じ契約者の年齢区分はどれだけ変わるのか
架空の契約者10万人（生年月日と契約日）で、年齢の数え方を比べる。乱数の種は411。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(411)
N = 100_000
DIM = np.array([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def leap(y):
    y = np.asarray(y)
    return ((y % 4 == 0) & (y % 100 != 0)) | (y % 400 == 0)


def dim(y, m):
    return DIM[m] + ((m == 2) & leap(y))


def bday(y, bm, bd, rule):
    """生まれた月日 (bm, bd) の、y 年の誕生日。2/29生まれは、うるう年でない年に 2/28（rule=A）か 3/1（rule=B）"""
    m, d = bm.copy(), bd.copy()
    x = (bm == 2) & (bd == 29) & ~leap(y)
    if rule == "A":
        d[x] = 28
    else:
        m[x] = 3; d[x] = 1
    return m, d


def add6(y, m, d):
    """6か月後の同じ日。その日がない月は、月末に切り詰める（SQL の DATEADD(month, 6, …) と同じ）"""
    m2 = m + 6; y2 = y + (m2 > 12); m2 = np.where(m2 > 12, m2 - 12, m2)
    return y2, m2, np.minimum(d, dim(y2, m2))


def key(y, m, d):
    return y * 10000 + m * 100 + d


def ages(by, bm, bd, cy, cm, cd, rule="A", half_incl=False):
    """満年齢、保険年齢（誕生日から6か月を超えたら切り上げ）、DATEDIFF(year) を返す"""
    m, d = bday(cy, bm, bd, rule)
    reached = key(cy, cm, cd) >= key(cy, m, d)                # 今年の誕生日を迎えたか
    full = cy - by - (~reached)
    ly = np.where(reached, cy, cy - 1)                        # 直近の誕生日の年
    lm, ld = bday(ly, bm, bd, rule)
    hy, hm, hd = add6(ly, lm, ld)
    c, h = key(cy, cm, cd), key(hy, hm, hd)
    up = (c >= h) if half_incl else (c > h)                   # half_incl：6か月ちょうどで切り上げる取り違え
    return full, full + up, cy - by


# ---------------- 架空の契約者 ----------------
age_t = rng.normal(44, 13, N)                                 # 契約時のおよその年齢（20〜75歳未満。外れた分は引き直す）
while ((age_t < 20) | (age_t >= 75)).any():
    bad = (age_t < 20) | (age_t >= 75)
    age_t[bad] = rng.normal(44, 13, bad.sum())
con = pd.Timestamp("2025-04-01") + pd.to_timedelta(rng.integers(0, 365, N), unit="D")   # 2025年度の契約日
first = rng.random(N) < 0.30                                  # 3割は月の初日に契約
con = pd.DatetimeIndex(np.where(first, con.to_period("M").to_timestamp(), con))
birth = con - pd.to_timedelta((age_t * 365.2425).astype(int), unit="D")
df = pd.DataFrame({"契約者ID": np.arange(1, N + 1), "生年月日": birth.date, "契約日": con.date})
df.to_csv(DATA / "policyholders.csv", index=False)
by, bm, bd = birth.year.values, birth.month.values, birth.day.values
cy, cm, cd = con.year.values, con.month.values, con.day.values

full, ins, dd = ages(by, bm, bd, cy, cm, cd)
fy_end_y = np.where(cm >= 4, cy + 1, cy)                      # 契約日を含む年度の末日（3/31）
fye, _, _ = ages(by, bm, bd, fy_end_y, np.full(N, 3), np.full(N, 31))
approx = np.round((con - birth).days.values / 365.25).astype(int)   # 日数÷365.25 を四捨五入する近似

band = lambda a: (a // 5) * 5
defs = {"保険年齢": ins, "年度末の満年齢": fye, "DATEDIFF(year)": dd, "日数÷365.25を四捨五入": approx}
rows = []
for k, a in defs.items():
    base = full if k != "日数÷365.25を四捨五入" else ins         # 近似は、保険年齢と比べる
    rows.append({"数え方": k, "比べる相手": "満年齢" if base is full else "保険年齢",
                 "年齢が違う人の割合%": round(100 * np.mean(a != base), 2),
                 "5歳刻みの区分が違う人の割合%": round(100 * np.mean(band(a) != band(base)), 2),
                 "平均の差（歳）": round(float(np.mean(a - base)), 3)})
T = pd.DataFrame(rows); T.to_csv(RES / "definitions_vs_full_age.csv", index=False)
same3 = float(np.mean((ins == full) & (fye == full)))

# 加入の条件「65歳以下」に当てはまる人数
elig = {k: int((a <= 65).sum()) for k, a in {"満年齢": full, **{k: defs[k] for k in ["保険年齢", "年度末の満年齢", "DATEDIFF(year)"]}}.items()}
# 5歳刻みの区分ごとの人数
bt = pd.DataFrame({"区分": band(full)}).assign(満年齢=1).groupby("区分").size().rename("満年齢").to_frame()
for k in ["保険年齢", "年度末の満年齢", "DATEDIFF(year)"]:
    bt[k] = pd.Series(band(defs[k])).value_counts().reindex(bt.index, fill_value=0).values
extra = sorted(set(np.unique(band(ins))) - set(bt.index))
bt.to_csv(RES / "band_counts.csv")

# 誕生日からの経過月数ごとの人数（保険年齢で切り上がる人）
m_, d_ = bday(cy, bm, bd, "A")
reached = key(cy, cm, cd) >= key(cy, m_, d_)
mon = (cm - bm) % 12 - ((cd < np.minimum(bd, dim(cy, cm))) & True)
mon = np.where(mon < 0, mon + 12, mon)
mm = pd.DataFrame({"経過月数": mon, "切り上げ": ins > full}).groupby("経過月数")["切り上げ"].agg(["size", "sum"])
mm.columns = ["人数", "保険年齢で1歳上がる人数"]; mm.to_csv(RES / "months_since_birthday.csv")

# 6か月ちょうどの日に契約した人（「超えたら」と「以上」の取り違えで変わる）
_, ins_incl, _ = ages(by, bm, bd, cy, cm, cd, half_incl=True)
n_half = int((ins_incl != ins).sum())
# 誕生日の前の日に契約した人（「誕生日の前の日に年を取る」数え方で変わる）
con1 = con + pd.Timedelta(days=1)
full_prev, ins_prev, _ = ages(by, bm, bd, con1.year.values, con1.month.values, con1.day.values)
n_prev_full, n_prev_ins = int((full_prev != full).sum()), int((ins_prev != ins).sum())
# 2/29生まれ：うるう年でない年の誕生日を 2/28 とするか 3/1 とするか
lb = (bm == 2) & (bd == 29)
fB, iB, _ = ages(by, bm, bd, cy, cm, cd, rule="B")
n_leap, n_leap_full, n_leap_ins = int(lb.sum()), int((fB != full).sum()), int((iB != ins).sum())
# 2/29生まれの1人について、契約日を4年分（2024/3/1〜2028/2/29）すべて動かす
days = pd.date_range("2024-03-01", "2028-02-29")
o = np.ones(len(days), int)
fa, ia, _ = ages(2000 * o, 2 * o, 29 * o, days.year.values, days.month.values, days.day.values, "A")
fb, ib, _ = ages(2000 * o, 2 * o, 29 * o, days.year.values, days.month.values, days.day.values, "B")
leap_days = {"4年の日数": len(days), "満年齢が違う日数": int((fa != fb).sum()), "保険年齢が違う日数": int((ia != ib).sum()),
             "満年齢が違う日": [str(x.date()) for x in days[fa != fb]], "保険年齢が違う日": [str(x.date()) for x in days[ia != ib]]}
# 月末の切り詰め：誕生日の6か月後が「同じ日のない月」に当たる人
ly = np.where(reached, cy, cy - 1); lm, ld = bday(ly, bm, bd, "A"); hy, hm, hd = add6(ly, lm, ld)
n_clamp = int((hd != ld).sum())

# ---------------- SQL（DuckDB）で同じ年齢を出して、Python と比べる ----------------
con_db = duckdb.connect(); con_db.execute("SET threads=1")
con_db.register("p", pd.DataFrame({"id": df["契約者ID"], "b": pd.to_datetime(df["生年月日"]), "c": pd.to_datetime(df["契約日"])}))
q = con_db.execute("""
WITH a AS (
  SELECT id, b, c,
         year(c) - year(b) AS dd,                                                   -- DATEDIFF(year, b, c) と同じ：年だけの差
         year(c) - year(b) - CASE WHEN (b + to_years(year(c) - year(b))) > c THEN 1 ELSE 0 END AS full_age
  FROM p)
SELECT id, dd, full_age,
       full_age + CASE WHEN c > (b + to_years(full_age)) + INTERVAL 6 MONTH THEN 1 ELSE 0 END AS ins_age
FROM a ORDER BY id""").df()
sql_ok = {"満年齢": bool((q.full_age.values == full).all()), "保険年齢": bool((q.ins_age.values == ins).all()),
          "DATEDIFF": bool((q.dd.values == dd).all())}
assert all(sql_ok.values()), sql_ok
pd.DataFrame([sql_ok]).to_csv(RES / "sql_check_duckdb.csv", index=False)

main = {"人数": N, "満年齢の平均": round(float(full.mean()), 2), "保険年齢の平均": round(float(ins.mean()), 2),
        "数え方ごとの差": T.to_dict("records"), "満年齢・保険年齢・年度末の満年齢が3つとも同じ人の割合%": round(100 * same3, 2),
        "65歳以下の人数": elig, "保険年齢だけにある区分": [int(x) for x in extra],
        "6か月ちょうどの日に契約した人": n_half, "誕生日の前の日に契約した人（満年齢が変わる）": n_prev_full,
        "誕生日の前の日の数え方で保険年齢が変わる人": n_prev_ins,
        "2/29生まれの人数": n_leap, "2/29の扱いで満年齢が変わる人": n_leap_full, "2/29の扱いで保険年齢が変わる人": n_leap_ins,
        "2/29生まれの1人を4年分動かす": leap_days, "6か月後が月末に切り詰められる人": n_clamp,
        "月の初日に契約した人の割合%": round(100 * float(first.mean()), 1), "SQLとPythonの一致": sql_ok}
json.dump(main, open(RES / "a411_main.json", "w"), ensure_ascii=False, indent=1)

# ---------------- 図 ----------------
SRC = "架空の契約者10万人（作成者が乱数で作成、seed 411）"
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
names = ["保険年齢", "年度末の満年齢", "DATEDIFF(year)"]
v1 = [T.set_index("数え方").loc[k, "年齢が違う人の割合%"] for k in names]
v2 = [T.set_index("数え方").loc[k, "5歳刻みの区分が違う人の割合%"] for k in names]
for a, v, t in ((ax[0], v1, "満年齢と1歳違う人の割合"), (ax[1], v2, "5歳刻みの区分が満年齢と違う人の割合")):
    b = a.bar(names, v, color=[BLUE, ORANGE, GRAY]); a.set_title(t); a.set_ylabel("%"); a.set_ylim(0, max(v) * 1.25)
    for r, x in zip(b, v): a.text(r.get_x() + r.get_width() / 2, x, f"{x:.1f}%", ha="center", va="bottom")
save(fig, "a411_diff_share.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(mm.index, mm["人数"], color=LIGHT, label="満年齢のまま")
ax.bar(mm.index, mm["保険年齢で1歳上がる人数"], color=BLUE, label="保険年齢で1歳上がる")
ax.set_xticks(range(12)); ax.set_xlabel("直近の誕生日から契約日までの月数（満の月数）"); ax.set_ylabel("人数")
ax.set_title("誕生日から6か月を超えた人が、保険年齢で1歳上がる"); ax.set_ylim(0, mm["人数"].max() * 1.22); ax.legend(frameon=False, ncol=2, loc="upper left")
save(fig, "a411_months_since_birthday.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.2))
x = np.arange(len(bt)); w = 0.27
for i, (k, c) in enumerate((("満年齢", GRAY), ("保険年齢", BLUE), ("年度末の満年齢", ORANGE))):
    ax.bar(x + (i - 1) * w, bt[k], w, color=c, label=k)
ax.set_xticks(x); ax.set_xticklabels([f"{int(a)}〜{int(a) + 4}歳" for a in bt.index], rotation=45, ha="right")
ax.set_ylabel("人数"); ax.set_title("5歳刻みの区分ごとの人数は、数え方で動く"); ax.legend(frameon=False)
save(fig, "a411_band_counts.png", SRC, y=-0.12)
print(json.dumps(main, ensure_ascii=False)[:1800])
