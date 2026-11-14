"""785 「1時間30分」を「1.30」と書いて合計すると、月の作業時間はどれだけ少なく出るのか

架空の作業記録。40人×22日、1日の作業時間は15分きざみ（0.5〜8時間）。
40人のうち半分は「時.分」（1.30＝1時間30分）で、残りは時間の小数（1.5＝1.5時間）で書く。
書き方を見ずに数として足すと、月の合計はどれだけ少なく出るかを数える。
DuckDB（1スレッド）で分に直した合計と、Python の本当の合計の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の作業記録（作成者が乱数で作成、seed 785）"
rng = np.random.default_rng(785)
NS, ND = 40, 22
staff = pd.DataFrame({"staff_id": [f"S{i:02d}" for i in range(1, NS + 1)],
                      "style": ["hmm" if i % 2 else "dec" for i in range(1, NS + 1)]})
rows = []
for sid, sty in zip(staff.staff_id, staff["style"]):
    base = rng.uniform(2, 6)
    for d in range(1, ND + 1):
        q = int(np.clip(np.round(rng.normal(base, 1.5) * 4), 2, 32))   # 15分きざみの回数
        m = q * 15
        h, mm = divmod(m, 60)
        txt = f"{h}.{mm:02d}" if sty == "hmm" else (f"{m / 60:g}")
        rows.append((sid, f"2025-06-{d:02d}", txt, m))
W = pd.DataFrame(rows, columns=["staff_id", "work_date", "hours_text", "minutes"])
DATA.mkdir(exist_ok=True)
staff.to_csv(DATA / "staff.csv", index=False)
W[["staff_id", "work_date", "hours_text"]].to_csv(DATA / "work_log.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("work_log", W[["staff_id", "work_date", "hours_text"]]); con.register("staff", staff)
q = "\n".join(l for l in (SQL / "02_hours_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
truth = W.groupby("staff_id").minutes.sum().reindex(Q.staff_id).to_numpy() / 60
naive = W.assign(v=W.hours_text.astype(float)).groupby("staff_id").v.sum().reindex(Q.staff_id).to_numpy()
assert np.allclose(Q.true_hours, truth) and np.allclose(Q.naive_hours, naive)
Q = Q.merge(staff, on="staff_id")
Q["gap"] = Q.naive_hours - Q.true_hours; Q["gap_pct"] = Q.gap / Q.true_hours
Q.to_csv(RES / "by_staff.csv", index=False)

# 分の部分ごとの読み違い（時.分の人だけ）
part = pd.DataFrame({"minute": [0, 15, 30, 45]})
part["read_as"] = part.minute / 100; part["true"] = part.minute / 60; part["gap_min"] = (part.read_as - part["true"]) * 60
H = W[W.staff_id.isin(staff[staff["style"] == "hmm"].staff_id)].copy(); H["mm"] = H.minutes % 60
part["rows"] = [int((H.mm == v).sum()) for v in part.minute]
part.to_csv(RES / "by_minute_part.csv", index=False)
# 小数部分が .60 以上の値の割合（見分けの手がかり）
W2 = W.merge(staff, on="staff_id"); W2["frac"] = W2.hours_text.astype(float) % 1
frac_hi = W2.groupby("style").frac.apply(lambda s: float((s.round(4) >= .6).mean()))

hmm = Q[Q["style"] == "hmm"]
out = {"staff": NS, "days": ND, "rows": len(W),
       "true_total": float(Q.true_hours.sum()), "naive_total": float(Q.naive_hours.sum()),
       "total_gap": float(Q.gap.sum()), "total_gap_pct": float(Q.gap.sum() / Q.true_hours.sum()),
       "hmm_true": float(hmm.true_hours.sum()), "hmm_naive": float(hmm.naive_hours.sum()),
       "hmm_gap_pct": float(hmm.gap.sum() / hmm.true_hours.sum()),
       "hmm_gap_per_staff_mean": float(hmm.gap.mean()), "hmm_gap_per_staff_min": float(hmm.gap.min()),
       "hmm_gap_pct_range": [float(hmm.gap_pct.min()), float(hmm.gap_pct.max())],
       "dec_gap_total": float(Q[Q["style"] == "dec"].gap.sum()),
       "gap_min_45": float(part.gap_min.iloc[3]), "gap_min_30": float(part.gap_min.iloc[2]), "gap_min_15": float(part.gap_min.iloc[1]),
       "frac_ge_060_share": {k: float(v) for k, v in frac_hi.items()},
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a785_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：分の部分ごとの読み違い
fig, ax = plt.subplots(figsize=(8.5, 4.4))
lab = ["○.00\n（0分）", "○.15\n（15分）", "○.30\n（30分）", "○.45\n（45分）"]
ax.bar(range(4), part.gap_min, color=ORANGE)
for i, v in enumerate(part.gap_min):
    ax.text(i, v - 0.6, f"{v:+.0f}分", ha="center", va="top", fontsize=11)
ax.axhline(0, color=GRAY, lw=.8)
ax.set_xticks(range(4)); ax.set_xticklabels(lab); ax.set_ylabel("数として読んだときのずれ（分）")
ax.set_ylim(-20, 2); ax.set_title("「1.45」を1.45時間と読むと、本当の1時間45分より18分少ない")
save(fig, "a785_minute_part.png", SRC)

# 図2：人ごとの月の合計
fig, ax = plt.subplots(figsize=(8.5, 5))
for sty, c, l in [("dec", BLUE, "時間の小数で書く人（1.5）"), ("hmm", ORANGE, "時.分で書く人（1.30）")]:
    s = Q[Q["style"] == sty]; ax.scatter(s.true_hours, s.naive_hours, color=c, s=30, label=l)
lim = [Q.true_hours.min() * .9, Q.true_hours.max() * 1.05]
ax.plot(lim, lim, color=GRAY, lw=.8, ls="--"); ax.text(lim[1], lim[1], "ずれなし", ha="right", va="bottom", fontsize=9, color=GRAY)
ax.set_xlabel("本当の月の作業時間（時間）"); ax.set_ylabel("数として足した合計（時間）"); ax.legend(frameon=False)
ax.set_title(f"時.分で書く人は、どの人も月の合計が{-out['hmm_gap_pct_range'][1]:.0%}〜{-out['hmm_gap_pct_range'][0]:.0%}少なく出た")
save(fig, "a785_by_staff.png", SRC)

# 図3：小数部分の分布（見分けの手がかり）
fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, sty, c, t in [(axs[0], "dec", BLUE, "時間の小数で書く人"), (axs[1], "hmm", ORANGE, "時.分で書く人")]:
    v = W2[W2["style"] == sty].frac.round(2).value_counts().sort_index()
    ax.bar([f".{int(round(k*100)):02d}" for k in v.index], v.values, color=c)
    ax.set_title(f"{t}：小数が.60以上は{frac_hi[sty]:.0%}"); ax.set_xlabel("小数の部分")
axs[0].set_ylabel("行の数")
fig.suptitle("時.分では小数が .00・.15・.30・.45 だけ。.50 や .75 があれば時間の小数と見分けられる", y=1.03)
save(fig, "a785_fraction.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
