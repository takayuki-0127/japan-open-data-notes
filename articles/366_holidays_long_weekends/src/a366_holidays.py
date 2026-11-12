"""366：祝日と3連休は、70年でどれだけ増えたのか。
内閣府「国民の祝日」CSV（1955年〜）と暦の計算だけで数える。
"""
import json, datetime as dt
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：内閣府「国民の祝日について」（昭和30年〜令和9年 国民の祝日・休日 CSV）をもとに作成者が加工して作成"
Y0, Y1 = 1955, 2026
raw = pd.read_csv(DATA / "raw" / "syukujitsu.csv", encoding="cp932")
raw.columns = ["date", "name"]
raw["date"] = pd.to_datetime(raw["date"]).dt.date
raw = raw[(raw.date >= dt.date(Y0, 1, 1)) & (raw.date <= dt.date(Y1, 12, 31))].reset_index(drop=True)
SPECIAL = {"結婚の儀", "大喪の礼", "即位礼正殿の儀", "休日（祝日扱い）"}
D1 = dt.timedelta(days=1)

def make_extra(named, special=()):
    """祝日（名前のある日）から、振替休日と国民の休日を決まりどおりに作る。"""
    hol = set(named) | set(special); extra = {}
    for d in sorted(named):
        if d.weekday() != 6 or d < dt.date(1973, 4, 12): continue
        n = d + D1
        if d >= dt.date(2007, 1, 1):
            while n in hol or n in extra: n += D1
            extra[n] = "振替休日"
        elif n not in hol:
            extra[n] = "振替休日"
    both = set(named) | set(special)   # 祝日扱いの日（2019年5月1日など）も、前後の日を国民の休日にする
    for d in sorted(both):
        m = d + D1
        if m >= dt.date(1985, 12, 27) and (m + D1) in both and m not in both and m not in extra:
            if m.weekday() == 6 and m < dt.date(2007, 1, 1): continue
            extra[m] = "国民の休日"
    return extra

named = {r.date: r.name for r in raw.itertuples() if r.name != "休日" and r.name not in SPECIAL}
special = {r.date: r.name for r in raw.itertuples() if r.name in SPECIAL}
csv_extra = {r.date for r in raw.itertuples() if r.name == "休日"}
extra = make_extra(named, special)
check = {"csv_kyujitsu": len(csv_extra), "rule_kyujitsu": len(extra), "only_csv": sorted(map(str, csv_extra - set(extra))),
         "only_rule": sorted(map(str, set(extra) - csv_extra))}
assert not check["only_csv"] and not check["only_rule"], check

def runs(off, ymin, ymax, minlen):
    """休みが minlen 日以上続くかたまりを、最後の日の年で数える。"""
    out = {y: [] for y in range(ymin, ymax + 1)}
    d = dt.date(ymin, 1, 1) - dt.timedelta(days=10); end = dt.date(ymax, 12, 31); cur = []
    while d <= end + dt.timedelta(days=10):
        if d in off: cur.append(d)
        else:
            if len(cur) >= minlen and ymin <= cur[-1].year <= ymax: out[cur[-1].year].append((cur[0], len(cur)))
            cur = []
        d += D1
    return out

def offset(hols, sat=True):
    off = set(hols); d = dt.date(Y0 - 1, 12, 1)
    while d <= dt.date(Y1 + 1, 1, 31):
        if d.weekday() == 6 or (sat and d.weekday() == 5): off.add(d)
        d += D1
    return off

allh = set(named) | set(special) | set(extra)
R3 = runs(offset(allh, True), Y0, Y1, 3)       # 土日を休みとして3日以上
R2 = runs(offset(allh, False), Y0, Y1, 2)      # 日曜と祝日だけで2日以上
rows = []
for y in range(Y0, Y1 + 1):
    nm = [d for d in named if d.year == y]
    rows.append({"year": y, "named": len(nm), "furikae": sum(1 for d, k in extra.items() if d.year == y and k == "振替休日"),
                 "kokumin": sum(1 for d, k in extra.items() if d.year == y and k == "国民の休日"),
                 "special": sum(1 for d in special if d.year == y),
                 "named_on_sat": sum(1 for d in nm if d.weekday() == 5), "named_on_sun": sum(1 for d in nm if d.weekday() == 6),
                 "weekday_off": sum(1 for d in allh if d.year == y and d.weekday() < 5),
                 "run3": len(R3[y]), "run3_days": sum(n for _, n in R3[y]), "run4plus": sum(1 for _, n in R3[y] if n >= 4),
                 "run2_sun_only": len(R2[y])})
T = pd.DataFrame(rows); T["total"] = T.named + T.furikae + T.kokumin + T.special
T.to_csv(DATA / "holidays_by_year.csv", index=False)

# --- 月曜に移した4つの祝日を、もとの日付に戻した場合（2000年〜、特例のあった2020・2021年は除く）
FIX = {"成人の日": (1, 15, 2000), "体育の日": (10, 10, 2000), "スポーツの日": (10, 10, 2000), "体育の日（スポーツの日）": (10, 10, 2000),
       "海の日": (7, 20, 2003), "敬老の日": (9, 15, 2003)}
cf_named = {}
for d, nmv in named.items():
    if nmv in FIX and d.year >= FIX[nmv][2] and d.year not in (2020, 2021):
        cf_named[dt.date(d.year, FIX[nmv][0], FIX[nmv][1])] = nmv
    else:
        cf_named[d] = nmv
cf_extra = make_extra(cf_named, special)
cf_all = set(cf_named) | set(special) | set(cf_extra)
C3 = runs(offset(cf_all, True), Y0, Y1, 3)
CF = pd.DataFrame([{"year": y, "run3_actual": len(R3[y]), "run3_fixed": len(C3[y]),
                    "weekday_off_actual": int(T.loc[T.year == y, "weekday_off"].iloc[0]),
                    "weekday_off_fixed": sum(1 for d in cf_all if d.year == y and d.weekday() < 5),
                    "total_actual": int(T.loc[T.year == y, "total"].iloc[0]), "total_fixed": sum(1 for d in cf_all if d.year == y)}
                   for y in range(2000, Y1 + 1) if y not in (2020, 2021)])
CF.to_csv(DATA / "happy_monday_counterfactual.csv", index=False)

def per(a, b, col): return float(T[(T.year >= a) & (T.year <= b)][col].mean())
dec = []
for a, b in [(1955, 1965), (1966, 1972), (1973, 1985), (1986, 1999), (2000, 2002), (2003, 2015), (2016, 2026)]:
    dec.append({"period": f"{a}〜{b}", "years": b - a + 1, **{c: round(per(a, b, c), 2) for c in ["named", "total", "weekday_off", "run3", "run2_sun_only", "named_on_sat", "named_on_sun"]}})
DEC = pd.DataFrame(dec); DEC.to_csv(RES / "by_period.csv", index=False)
steps = T[T.named != T.named.shift(1)][["year", "named"]].to_dict("records")
cf03 = CF[CF.year >= 2003]
res = {"range": [Y0, Y1], "check_rule_vs_csv": check,
       "named_steps": steps,
       "y1955": T[T.year == 1955].iloc[0].to_dict(), "y2025": T[T.year == 2025].iloc[0].to_dict(),
       "total_min": {"n": int(T.total.min()), "years": T[T.total == T.total.min()].year.tolist()[:5]},
       "total_max": {"n": int(T.total.max()), "years": T[T.total == T.total.max()].year.tolist()},
       "furikae_total_1973_2026": int(T.furikae.sum()), "kokumin_total": int(T.kokumin.sum()), "special_days": {str(k): v for k, v in sorted(special.items())},
       "run3_mean": {"1955-1972": per(1955, 1972, "run3"), "1973-1999": per(1973, 1999, "run3"), "1990-1999": per(1990, 1999, "run3"),
                     "2000-2002": per(2000, 2002, "run3"), "2003-2019": per(2003, 2019, "run3"), "2003-2026": per(2003, 2026, "run3")},
       "run3_max": {"n": int(T.run3.max()), "years": T[T.run3 == T.run3.max()].year.tolist()},
       "run3_min_since2003": {"n": int(T[T.year >= 2003].run3.min()), "years": T[(T.year >= 2003) & (T.run3 == T[T.year >= 2003].run3.min())].year.tolist()},
       "run3_min_1990s": {"n": int(T[(T.year >= 1990) & (T.year <= 1999)].run3.min()), "max": int(T[(T.year >= 1990) & (T.year <= 1999)].run3.max())},
       "run2_sun_only_mean": {"1955-1972": per(1955, 1972, "run2_sun_only"), "1973-1999": per(1973, 1999, "run2_sun_only"), "2003-2026": per(2003, 2026, "run2_sun_only")},
       "happy_monday": {"years": len(cf03), "run3_actual_mean": float(cf03.run3_actual.mean()), "run3_fixed_mean": float(cf03.run3_fixed.mean()),
                        "run3_actual_min_max": [int(cf03.run3_actual.min()), int(cf03.run3_actual.max())], "run3_fixed_min_max": [int(cf03.run3_fixed.min()), int(cf03.run3_fixed.max())],
                        "weekday_off_actual_mean": float(cf03.weekday_off_actual.mean()), "weekday_off_fixed_mean": float(cf03.weekday_off_fixed.mean()),
                        "weekday_off_actual_sd": float(cf03.weekday_off_actual.std(ddof=0)), "weekday_off_fixed_sd": float(cf03.weekday_off_fixed.std(ddof=0)),
                        "total_actual_mean": float(cf03.total_actual.mean()), "total_fixed_mean": float(cf03.total_fixed.mean())},
       "named_on_sat_share": {"1955-2026": float(T.named_on_sat.sum() / T.named.sum()), "2003-2026": float(T[T.year >= 2003].named_on_sat.sum() / T[T.year >= 2003].named.sum()),
                              "1955-1999": float(T[T.year <= 1999].named_on_sat.sum() / T[T.year <= 1999].named.sum())},
       "named_on_sun_share": {"1955-1999": float(T[T.year <= 1999].named_on_sun.sum() / T[T.year <= 1999].named.sum()),
                              "2003-2026": float(T[T.year >= 2003].named_on_sun.sum() / T[T.year >= 2003].named.sum())},
       "weekday_off_mean": {"1955-1965": per(1955, 1965, "weekday_off"), "1986-1999": per(1986, 1999, "weekday_off"), "2016-2026": per(2016, 2026, "weekday_off")},
       "weekday_off_min_max_2016_2026": [int(T[T.year >= 2016].weekday_off.min()), int(T[T.year >= 2016].weekday_off.max())],
       "by_period": dec}
json.dump(res, open(RES / "a366_main.json", "w"), ensure_ascii=False, indent=1, default=str)

# 図1：1年の祝日・休日の数
fig, ax = plt.subplots(figsize=(9.4, 4.4))
ax.bar(T.year, T.named, color=BLUE, width=0.8, label="国民の祝日")
ax.bar(T.year, T.furikae + T.kokumin, bottom=T.named, color=ORANGE, width=0.8, label="振替休日・国民の休日")
ax.bar(T.year, T.special, bottom=T.named + T.furikae + T.kokumin, color=GRAY, width=0.8, label="その年だけの休日")
for yy, lab, hh in [(1966, "1966年 11日\n1967年 12日", 15.5), (1989, "1989年 13日", 21.0), (1996, "1996年 14日", 22.3), (2007, "2007年 15日", 21.5), (2016, "2016年 16日", 23.2)]:
    ax.annotate(lab, (yy, float(T.loc[T.year == yy, "named"].iloc[0])), xytext=(yy - 1.5, hh), ha="right", fontsize=7.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.6))
ax.set_ylim(0, 26); ax.set_ylabel("日"); ax.set_title("祝日は9日から16日に増えた。振替休日などを足すと、多い年は年に20日を超える")
ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=9, bbox_to_anchor=(0.0, 1.0))
save(fig, "a366_holidays_per_year.png", SRC)

# 図2：3連休以上の回数
fig, ax = plt.subplots(figsize=(9.4, 4.4))
ax.bar(T.year, T.run3, color=LIGHT, width=0.8, label="実際の暦（土日を休みとして数えた回数）")
ax.plot(CF.year, CF.run3_fixed, color=ORANGE, lw=0, marker="o", ms=4, label="4つの祝日を元の日付（1/15・7/20・9/15・10/10）に戻した場合")
ax.axvline(1999.5, color=GRAY, lw=0.8, ls="--"); ax.text(1999.3, 12.4, "2000年〜 成人の日・体育の日が月曜に", ha="right", fontsize=8, color=INK)
ax.axvline(2002.5, color=GRAY, lw=0.8, ls="--"); ax.text(2002.3, 11.6, "2003年〜 海の日・敬老の日も", ha="right", fontsize=8, color=INK)
ax.set_ylim(0, 13); ax.set_ylabel("3連休以上の回数（回／年）"); ax.set_title("3連休以上は1990年代の年5.8回から年8.5回に。祝日を月曜に移した分は年に約2回")
ax.legend(frameon=False, loc="upper left", fontsize=8.5, bbox_to_anchor=(0.0, 0.84))
save(fig, "a366_long_weekends.png", SRC + "\n3連休以上＝土曜・日曜・祝日・休日が3日以上続くかたまり。年末年始の休みは入れていない。2020・2021年は特例で日付が動いたため、戻した場合の点はない")

# 図3：祝日が土曜・日曜に重なった数と、平日の休みの数
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
ax = axes[0]
ax.bar(T.year, T.named_on_sun, color=LIGHT, width=0.8, label="日曜と重なった祝日")
ax.bar(T.year, T.named_on_sat, bottom=T.named_on_sun, color=ORANGE, width=0.8, label="土曜と重なった祝日")
ax.set_ylim(0, 9.5); ax.set_ylabel("日"); ax.set_title("土曜・日曜と重なった祝日の数", fontsize=11); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax = axes[1]
ax.plot(T.year, T.weekday_off, color=BLUE, lw=1.2, marker="o", ms=2.5)
ax.plot(T.year, T.weekday_off.rolling(7, center=True).mean(), color=INK, lw=1.6, label="前後7年の平均")
ax.set_ylim(0, 20); ax.set_ylabel("日"); ax.set_title("月〜金に当たった祝日・休日の数", fontsize=11); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
fig.suptitle("土曜に重なった祝日は振り替えられない。月〜金に当たる休みは、年6日ほどから15日ほどになった", fontsize=12.5, y=1.0)
fig.tight_layout()
save(fig, "a366_weekend_overlap.png", SRC)
print(json.dumps({k: res[k] for k in ["check_rule_vs_csv", "named_steps", "total_min", "total_max", "run3_mean", "run3_max", "run3_min_since2003", "run3_min_1990s", "run2_sun_only_mean", "happy_monday", "named_on_sat_share", "named_on_sun_share", "weekday_off_mean", "weekday_off_min_max_2016_2026", "furikae_total_1973_2026", "kokumin_total"]}, ensure_ascii=False, indent=0, default=str))
print(DEC.to_string()); print(T[T.year.isin([1955, 1966, 1973, 1989, 1996, 2000, 2003, 2016, 2019, 2025, 2026])].to_string())
