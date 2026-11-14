"""695 1人あたりの処理件数を、出勤した人数で割るか働いた時間で割るかで、担当者の順位はどれだけ入れ替わるのか

架空の窓口の担当者40人の3か月分（60営業日）の日ごとの処理件数と勤務時間。
  勤務時間：8時間の人（28人、残業で日によって8〜10時間）と短時間の人（12人、4〜6時間）
  案件の難しさ：担当によって難しい案件（重み2）の割合が違う（5〜40%）
  1時間あたりの実力（難しさで重みを付けた件数）は人ごとに置く（平均3.0、標準偏差0.4）
「1人あたり」を3通りで出して順位を比べる：
  出勤日あたり（件数 ÷ 出勤日数）／時間あたり（件数 ÷ 勤務時間）／難しさで重みを付けた時間あたり
3つ目が、置いた実力とほぼ同じ順位になることを確かめる。DuckDB の SQL でも同じ値を出して一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の担当者の勤務と処理件数（作成者が乱数で作成、seed 695）"
rng = np.random.default_rng(695)
DATA.mkdir(exist_ok=True)
NS, ND = 40, 60
short = np.r_[np.zeros(28, bool), np.ones(12, bool)]; rng.shuffle(short)
skill = rng.normal(3.0, 0.4, NS)                      # 難しさで重みを付けた1時間あたりの件数
hard = rng.uniform(0.05, 0.40, NS)                    # 難しい案件の割合
dates = pd.bdate_range("2026-07-01", periods=ND)
rows = []
for i in range(NS):
    for d in dates:
        if rng.uniform() < 0.05:                      # 休み
            continue
        h = rng.uniform(4, 6) if short[i] else 8 + rng.choice([0, 0, 0, 1, 2])
        h = round(h * 4) / 4
        load = skill[i] * h                            # 重み付きでこなせる量
        avg_w = 1 * (1 - hard[i]) + 2 * hard[i]
        n = rng.poisson(load / avg_w)
        nh = rng.binomial(n, hard[i])
        rows.append((f"S{i+1:02d}", d.date(), h, n - nh, 1.0)); rows.append((f"S{i+1:02d}", d.date(), 0.0, nh, 2.0))
W = pd.DataFrame(rows, columns=["staff_id", "work_date", "hours", "cases", "difficulty"])
W.to_csv(DATA / "daily_work.csv", index=False)

g = W.groupby("staff_id")
S = pd.DataFrame({"days": g.work_date.nunique(), "hours": g.hours.sum(), "cases": g.cases.sum(),
                  "wcases": (W.cases * W.difficulty).groupby(W.staff_id).sum()})
S["cases_per_day"] = S.cases / S.days; S["cases_per_hour"] = S.cases / S.hours; S["weighted_per_hour"] = S.wcases / S.hours
S["short"] = short; S["hard_share"] = hard; S["skill"] = skill
for c, r in [("cases_per_day", "rank_day"), ("cases_per_hour", "rank_hour"), ("weighted_per_hour", "rank_weighted"), ("skill", "rank_skill")]:
    S[r] = S[c].rank(ascending=False, method="min").astype(int)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("w", W); con.execute("CREATE TABLE daily_work AS SELECT * FROM w")
dq = con.execute((SQL / "02_productivity_duckdb.sql").read_text(encoding="utf-8")).df().set_index("staff_id")
for c in ["cases_per_day", "cases_per_hour", "weighted_per_hour", "rank_day", "rank_hour", "rank_weighted"]:
    assert np.allclose(dq[c].values, S.loc[dq.index, c].values), c
S.round(4).to_csv(RES / "by_staff.csv")

sp = lambda a, b: round(float(stats.spearmanr(S[a], S[b]).statistic), 3)
mv = lambda a, b: int((abs(S[a] - S[b]) >= 10).sum())
out = {"staff": NS, "days": ND, "short_staff": int(short.sum()),
       "spearman": {"day_vs_weighted": sp("rank_day", "rank_weighted"), "hour_vs_weighted": sp("rank_hour", "rank_weighted"),
                    "weighted_vs_skill": sp("rank_weighted", "rank_skill"), "day_vs_skill": sp("rank_day", "rank_skill")},
       "moved_10_or_more": {"day_vs_weighted": mv("rank_day", "rank_weighted"), "hour_vs_weighted": mv("rank_hour", "rank_weighted")},
       "short_staff_mean_rank": {k: round(float(S[S.short][k].mean()), 1) for k in ["rank_day", "rank_hour", "rank_weighted"]},
       "short_staff_in_bottom10_by_day": int((S[S.short].rank_day > 30).sum()),
       "short_staff_in_bottom10_by_weighted": int((S[S.short].rank_weighted > 30).sum()),
       "max_move_day_vs_weighted": int((S.rank_day - S.rank_weighted).abs().max()),
       "sql_matches_python": True}
json.dump(out, open(RES / "a695_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：出勤日あたり vs 重み付き時間あたりの順位
fig, ax = plt.subplots(figsize=(6.5, 6))
ax.scatter(S.rank_weighted, S.rank_day, c=np.where(S.short, ORANGE, BLUE), s=40, zorder=3)
ax.plot([1, 40], [1, 40], color=GRAY, ls="--", lw=0.8)
ax.scatter([], [], color=BLUE, label="8時間勤務"); ax.scatter([], [], color=ORANGE, label="短時間勤務")
ax.set_xlabel("難しさで重みを付けた時間あたりの順位"); ax.set_ylabel("出勤日あたりの件数の順位"); ax.invert_xaxis(); ax.invert_yaxis()
ax.legend(frameon=False, loc="lower right"); ax.set_title("出勤日あたりで並べると、短時間勤務の人が下に固まる")
save(fig, "a695_day_vs_weighted.png", SRC)

# 図2：時間あたり vs 重み付き時間あたり（難しい案件の割合で色）
fig, ax = plt.subplots(figsize=(7, 5.6))
sc = ax.scatter(S.rank_weighted, S.rank_hour, c=S.hard_share * 100, cmap="Oranges", s=45, edgecolor=INK, lw=0.4, zorder=3)
ax.plot([1, 40], [1, 40], color=GRAY, ls="--", lw=0.8); ax.invert_xaxis(); ax.invert_yaxis()
cb = fig.colorbar(sc, ax=ax); cb.set_label("難しい案件の割合（%）")
ax.set_xlabel("難しさで重みを付けた時間あたりの順位"); ax.set_ylabel("時間あたりの件数の順位")
ax.set_title("時間で割っても、難しい案件の多い人は下に見える")
save(fig, "a695_hour_vs_weighted.png", SRC)

# 図3：順位の一致（スピアマン）
fig, ax = plt.subplots(figsize=(8, 3.4))
items = [("出勤日あたり", out["spearman"]["day_vs_skill"]), ("時間あたり", sp("rank_hour", "rank_skill")), ("重み付きの時間あたり", out["spearman"]["weighted_vs_skill"])]
ax.barh(range(3), [v for _, v in items], color=[ORANGE, LIGHT, BLUE])
for i, (_, v) in enumerate(items):
    ax.text(v, i, f" {v:.2f}", va="center")
ax.set_yticks(range(3)); ax.set_yticklabels([n for n, _ in items]); ax.invert_yaxis(); ax.set_xlim(0, 1.1)
ax.set_xlabel("置いた実力の順位との順位相関"); ax.set_title("割り方を変えるほど、置いた実力の順位に近づく")
save(fig, "a695_agreement.png", SRC)
out["spearman"]["hour_vs_skill"] = sp("rank_hour", "rank_skill")
json.dump(out, open(RES / "a695_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
