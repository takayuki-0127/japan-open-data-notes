"""704 年齢を「年の差」だけで出すと、誕生日前の会員は何%が1歳多く数えられるのか

架空の会員2万人（1950〜2006年生まれ）。基準日 2025-10-01 で
  年の差（基準日の年−生まれた年。T-SQL の DATEDIFF(year) と同じ考え方）
  誕生日を考えた年齢（基準日の月日が誕生日の月日より前なら1を引く）
を比べる。基準日を月ごとに変えた場合と、10歳ごとの人数、20歳・65歳の線の上下の人数も見る。
DuckDB（1スレッド）と pandas で一致を確かめる。seed 704。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の会員（作成者が乱数で作成、seed 704）"
rng = np.random.default_rng(704)
N = 20000
start, end = pd.Timestamp("1950-01-01"), pd.Timestamp("2006-12-31")
nd = (end - start).days + 1
p = np.exp(-((np.arange(nd) / 365.25 - 30) / 18) ** 2)  # 1980年ごろ生まれが多い
bd = start + pd.to_timedelta(rng.choice(nd, size=N, p=p / p.sum()), unit="D")
Mb = pd.DataFrame({"member_id": np.arange(1, N + 1), "birth_date": bd})
Mb.assign(birth_date=Mb.birth_date.dt.strftime("%Y-%m-%d")).to_csv(DATA / "members.csv", index=False)
REF = pd.Timestamp("2025-10-01")


def ages(ref):
    yd = ref.year - Mb.birth_date.dt.year
    before = (ref.month * 100 + ref.day) < (Mb.birth_date.dt.month * 100 + Mb.birth_date.dt.day)
    return yd, yd - before.astype(int)


con = duckdb.connect(); con.execute("SET threads=1"); con.register("members", Mb)
q = [x for x in (SQL / "02_age_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
A = con.execute(q[0]).df()
con.register("ages", A)
band_sql = con.execute(q[1]).df().set_index("band").n_year_diff
yd, tr = ages(REF)
assert (A.age_year_diff.values == yd.values).all() and (A.age_true.values == tr.values).all()
over = (yd != tr)
bands = list(range(10, 80, 10))
b_yd = (yd // 10 * 10).value_counts().reindex(bands, fill_value=0)
b_tr = (tr // 10 * 10).value_counts().reindex(bands, fill_value=0)
assert (band_sql.reindex(bands, fill_value=0).values == b_yd.values).all()
# 基準日を毎月1日にしたとき
refs = pd.date_range("2025-01-01", "2025-12-01", freq="MS").append(pd.DatetimeIndex(["2025-12-31"]))
by_ref = []
for r in refs:
    a, b = ages(r)
    by_ref.append({"ref": r.strftime("%Y-%m-%d"), "over_pct": round(float((a != b).mean() * 100), 1)})
by_ref = pd.DataFrame(by_ref); by_ref.to_csv(RES / "by_ref_date.csv", index=False)
# 線の上下
th = {}
for t in [20, 30, 65]:
    th[str(t)] = {"year_diff": int((yd >= t).sum()), "true": int((tr >= t).sum()), "diff": int((yd >= t).sum() - (tr >= t).sum())}
pd.DataFrame({"band": bands, "year_diff": b_yd.values, "true": b_tr.values}).to_csv(RES / "age_bands.csv", index=False)
out = {"members": N, "ref_date": "2025-10-01", "over_by_one_pct": round(float(over.mean() * 100), 1), "over_by_one": int(over.sum()),
       "max_diff": int((yd - tr).max()), "over_pct_by_ref_date": dict(zip(by_ref.ref, by_ref.over_pct)),
       "bands_year_diff": {str(k): int(v) for k, v in b_yd.items()}, "bands_true": {str(k): int(v) for k, v in b_tr.items()},
       "band_change_pct": {str(k): round(float((b_yd[k] / b_tr[k] - 1) * 100), 1) for k in bands},
       "threshold_counts": th, "feb29_births": int(((Mb.birth_date.dt.month == 2) & (Mb.birth_date.dt.day == 29)).sum())}
json.dump(out, open(RES / "a704_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：基準日ごとの「1歳多い」割合
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(pd.to_datetime(by_ref.ref), by_ref.over_pct, "o-", color=ORANGE)
for _, r in by_ref.iloc[[0, 3, 6, 9, 12]].iterrows():
    ax.annotate(f"{r.over_pct:.0f}%", (pd.Timestamp(r.ref), r.over_pct), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9)
ax.set_ylim(-5, 105); ax.set_ylabel("1歳多く数えられる会員（%）"); ax.set_xlabel("基準日（2025年）")
ax.set_title("年の差だけの年齢は、基準日が年の初めに近いほど多くの人を1歳多く数える")
save(fig, "a704_by_ref_date.png", SRC)
# 図2：10歳ごとの人数
fig, ax = plt.subplots(figsize=(8, 3.6)); x = np.arange(len(bands))
ax.bar(x - 0.2, b_tr.values, 0.4, color=BLUE, label="誕生日を考えた年齢")
ax.bar(x + 0.2, b_yd.values, 0.4, color=ORANGE, label="年の差だけの年齢")
ax.set_xticks(x); ax.set_xticklabels([f"{b}代" for b in bands]); ax.set_ylabel("会員数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("基準日10月1日：年の差だけだと、各年代の一部が1つ上の年代に移る")
save(fig, "a704_bands.png", SRC)
# 図3：誕生月ごとの「1歳多い」割合
bm = Mb.birth_date.dt.month
fig, ax = plt.subplots(figsize=(8, 3.6))
v = over.groupby(bm).mean() * 100
ax.bar(v.index, v.values, color=[ORANGE if m >= 10 else LIGHT for m in v.index])
ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)]); ax.set_ylabel("1歳多く数えられる割合（%）")
ax.set_title("基準日10月1日：10月2日以降が誕生日の人は、年の差だと全員1歳多い")
save(fig, "a704_by_birth_month.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
