"""533 残業時間を15分単位で切り捨てて集計すると、1か月の時間は何%少なく出るのか（実務の型）

架空の出退勤の記録（分単位、120人×2025年10月の平日）を作り、日ごとの残業（定時18:00より後の分）を
1分単位・15分切り捨て・30分切り捨て・15分単位の四捨五入（7分以下は切り捨て、8分以上は切り上げ）の4通りで丸めてから月に合計し、
1分単位の合計との差を見る。数えるのは算数の差だけで、どの扱いが認められるかには触れない。
人ごとの月の合計は SQL（DuckDB）でも出し、Python と一致するか確かめる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 533
SRC = "架空の出退勤の記録（作成者が乱数で作成、seed 533）"
END = 18 * 60          # 定時 18:00
METHODS = {"m1": "1分単位", "t15": "15分切り捨て", "t30": "30分切り捨て", "r15": "15分の四捨五入"}


def make(n=120, seed=SEED):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2025-10-01", "2025-10-31")
    days = days[days != pd.Timestamp("2025-10-13")]          # スポーツの日
    # 人ごとの残業の多さ：残業する日の割合と、残業の長さ（中央値）が人によって違う
    p_ot = rng.beta(2, 2.5, n)
    med = rng.lognormal(np.log(55), 0.5, n)
    recs = []
    for i in range(n):
        for d in days:
            if rng.random() < p_ot[i]:
                ot = int(round(rng.lognormal(np.log(med[i]), 0.7)))
            else:
                ot = int(rng.integers(-5, 12))                  # 定時の前後に退勤（少し過ぎることもある）
            clock_out = END + ot
            clock_in = int(8 * 60 + 50 + rng.integers(-15, 10))
            recs.append((f"E{i + 1:03d}", d.date(), f"{clock_in // 60:02d}:{clock_in % 60:02d}", f"{clock_out // 60:02d}:{clock_out % 60:02d}"))
    return pd.DataFrame(recs, columns=["emp", "work_date", "clock_in", "clock_out"])


def daily(df):
    t = df.clock_out.str.split(":", expand=True).astype(int)
    ot = np.maximum(t[0] * 60 + t[1] - END, 0)
    out = df[["emp", "work_date"]].copy()
    out["m1"] = ot
    out["t15"] = ot // 15 * 15
    out["t30"] = ot // 30 * 30
    out["r15"] = (ot + 7) // 15 * 15
    return out


def main():
    df = make()
    df.to_csv(DATA / "fictional_attendance_2025_10.csv", index=False)
    d = daily(df)
    per = d.groupby("emp")[list(METHODS)].sum()
    per["ot_days"] = d.assign(x=d.m1 > 0).groupby("emp").x.sum()
    # SQL（DuckDB）
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("att", df)
    s = con.execute(open(SQL / "02_monthly_overtime_duckdb.sql", encoding="utf-8").read()).df().set_index("emp").sort_index()
    sql_ok = bool((s[list(METHODS)].astype(int).to_numpy() == per.sort_index()[list(METHODS)].to_numpy()).all())

    tot = per[list(METHODS)].sum()
    rows = []
    for k, lab in METHODS.items():
        rows.append({"丸め方": lab, "月の合計(時間)": round(tot[k] / 60, 1), "1分単位との差(時間)": round((tot[k] - tot.m1) / 60, 1),
                     "1分単位との差(%)": round((tot[k] / tot.m1 - 1) * 100, 2), "1人あたりの差(時間/月)": round((tot[k] - tot.m1) / 60 / len(per), 2)})
    pd.DataFrame(rows).to_csv(RES / "monthly_total_by_method.csv", index=False)
    pp = pd.DataFrame({"emp": per.index, "ot_days": per.ot_days, "m1_h": (per.m1 / 60).round(2)})
    for k in ["t15", "t30", "r15"]:
        pp[f"{k}_diff_h"] = ((per[k] - per.m1) / 60).round(2)
        pp[f"{k}_diff_pct"] = np.where(per.m1 > 0, ((per[k] / per.m1.replace(0, np.nan) - 1) * 100).round(2), np.nan)
    pp.to_csv(RES / "per_person_diff.csv", index=False)
    q = lambda k, f: round(float(np.nanquantile(pp[k], f)), 2)
    days_ot = d[d.m1 > 0]
    res = {"n_people": len(per), "n_days": int(d.work_date.nunique()), "n_records": len(d), "sql_matches_python": sql_ok,
           "share_days_with_ot_pct": round((d.m1 > 0).mean() * 100, 1), "median_ot_min_on_ot_days": float(days_ot.m1.median()),
           "totals": rows,
           "per_person_diff_h": {k: {"min": q(f"{k}_diff_h", 0), "p10": q(f"{k}_diff_h", .1), "median": q(f"{k}_diff_h", .5), "p90": q(f"{k}_diff_h", .9), "max": q(f"{k}_diff_h", 1)} for k in ["t15", "t30", "r15"]},
           "per_person_diff_pct_t15": {"p10": q("t15_diff_pct", .1), "median": q("t15_diff_pct", .5), "p90": q("t15_diff_pct", .9)},
           "avg_cut_min_per_ot_day": {"t15": round(float((days_ot.m1 - days_ot.t15).mean()), 2), "t30": round(float((days_ot.m1 - days_ot.t30).mean()), 2)}}
    # 残業のある日1日あたりの切り捨て分と、日数の関係（回帰の傾き）
    for k in ["t15", "t30"]:
        res[f"slope_{k}_min_per_ot_day"] = round(float(np.polyfit(pp.ot_days, -pp[f"{k}_diff_h"] * 60, 1)[0]), 2)
    json.dump(res, open(RES / "a533_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：月の合計（全員）
    fig, ax = plt.subplots(figsize=(7, 3.6))
    lab = list(METHODS.values()); v = [r["1分単位との差(%)"] for r in rows]
    cols = [GRAY, ORANGE, ORANGE, BLUE]
    ax.barh(lab[::-1], v[::-1], color=cols[::-1])
    for i, (x, r) in enumerate(zip(v[::-1], rows[::-1])):
        ax.text(x - 0.3 if x < 0 else x + 0.3, i, f"{x:+.1f}%（{r['1分単位との差(時間)']:+,.0f}時間）", va="center", ha="right" if x < 0 else "left", fontsize=9, color=INK)
    ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(min(v) * 1.9, 8)
    ax.set_xlabel("1分単位の月の合計との差（%）"); ax.set_title(f"120人・1か月の残業の合計（1分単位 {rows[0]['月の合計(時間)']:,.0f}時間）との差")
    save(fig, "a533_total_by_method.png", SRC)
    # 図2：人ごとの差の分布
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    data = [-pp[f"{k}_diff_h"] for k in ["t15", "t30", "r15"]]
    ax.boxplot(data, vert=False, widths=0.5, patch_artist=True, boxprops=dict(facecolor=LIGHT, color=INK), medianprops=dict(color=ORANGE, lw=2))
    ax.set_yticks([1, 2, 3], ["15分切り捨て", "30分切り捨て", "15分の四捨五入"]); ax.axvline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("1分単位より少なく出た時間（時間/月、1人ごと。負は多く出た）"); ax.set_title("人によって、少なく出る時間の幅がある")
    save(fig, "a533_per_person.png", SRC)
    # 図3：残業のある日数と、少なく出た時間
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for k, c, l in [("t15", ORANGE, "15分切り捨て"), ("t30", BLUE, "30分切り捨て")]:
        ax.scatter(pp.ot_days, -pp[f"{k}_diff_h"], s=14, color=c, alpha=0.7, label=l)
    ax.set_xlabel("その月に残業のあった日数"); ax.set_ylabel("少なく出た時間（時間/月）"); ax.legend(frameon=False)
    ax.set_title("残業のある日が多い人ほど、少なく出る時間も多い")
    save(fig, "a533_vs_ot_days.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
