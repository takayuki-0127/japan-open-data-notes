"""元の Excel から、使う値だけを抜き出して data/ に CSV で置く。行・列は見出しの文字で選ぶ。"""
import json, re
import pandas as pd
from common import RAW, DATA, rows_of, clean, kind_of, num, FIVE_TO_TS, TS_AGES

checks = {}

# ---- 時系列表（第1表）----
rows = rows_of("ssb_timeseries_t1_learning.xlsx")
yr_row = next(i for i, r in enumerate(rows) if sum(1 for c in r if c == 1986) >= 5)
main_row = next(i for i, r in enumerate(rows) if any(clean(c) == "外国語" for c in r))
sub_row = next(i for i, r in enumerate(rows) if any(clean(c) == "英語" for c in r))
colkind = {}
cur_main = None
for j, y in enumerate(rows[yr_row]):
    if y == 1986:  # かたまりの始まり。小区分の見出しがあればそれ、なければ大区分の見出し
        if rows[main_row][j]:
            cur_main = rows[main_row][j]
        lab = rows[sub_row][j] if rows[sub_row][j] else cur_main
        k = kind_of(lab)
    if isinstance(y, int) and 1980 < y < 2030 and k:
        colkind[j] = (k, y)
recs = []
sex = None
for r in rows[yr_row + 1:]:
    lab = clean(r[1])
    if not lab:
        continue
    if lab in ("男", "女"):
        sex, age = lab, "総数"
    elif lab == "総数" and sex is None:
        sex, age = "総数", "総数"
    else:
        age = lab
    for j, (k, y) in colkind.items():
        v = num(r[j])
        recs.append({"sex": sex, "age": age, "kind": k, "year": y, "rate": v})
ts = pd.DataFrame(recs)
ts = ts.sort_values(["sex", "age", "kind", "year"]).reset_index(drop=True)
ts.to_csv(DATA / "ts_rates.csv", index=False)
checks["ts_kinds"] = sorted(ts.kind.unique().tolist())
checks["ts_sex_age_rows"] = int(ts[["sex", "age"]].drop_duplicates().shape[0])

# ---- 2016・2021年の第1-4表（目的別）----
def read_t14(fname, year):
    rows = rows_of(fname)
    hi = next(i for i, r in enumerate(rows) if "男女" in [clean(c) for c in r] and "目的" in [clean(c) for c in r])
    h = [clean(c) for c in rows[hi]]
    cs, ch, cp, ca = (h.index(x) for x in ("男女", "ふだんの健康状態", "目的", "年齢"))
    prow = next(i for i, r in enumerate(rows) if "推定人口" in [clean(c) for c in r])
    cpop = [clean(c) for c in rows[prow]].index("推定人口")
    krow = next(i for i, r in enumerate(rows) if "0_総数" in [clean(c) for c in r] and any(clean(c) == "1_外国語" for c in r))
    kcols = {j: kind_of(c) for j, c in enumerate(rows[krow]) if kind_of(c)}
    out = []
    for r in rows[hi + 1:]:
        if not re.match(r"^\d_", clean(r[cs])):
            continue
        if clean(r[ch]) != "0_総数":  # 健康の状態は総数の行だけ使う
            continue
        sx = re.sub(r"^\d_", "", clean(r[cs])); pu = re.sub(r"^\d+_", "", clean(r[cp])); ag = re.sub(r"^[A-Z]?\d+_", "", clean(r[ca]))
        pop = num(r[cpop])
        for j, k in kcols.items():
            out.append({"year": year, "sex": sx, "purpose": pu, "age": ag, "kind": k, "pop_1000": pop, "rate": num(r[j])})
    return pd.DataFrame(out)

pu = pd.concat([read_t14("ssb2016_t1-4_purpose_rate.xlsx", 2016), read_t14("ssb2021_t1-4_purpose_rate.xlsx", 2021)])
pu = pu.sort_values(["year", "sex", "purpose", "age", "kind"]).reset_index(drop=True)
pu.to_csv(DATA / "purpose_2016_2021.csv", index=False)
checks["purposes"] = sorted(pu.purpose.unique().tolist())

# 推定人口を時系列表の年齢区分にまとめる（目的＝総数、種類＝総数の行）
p = pu[(pu.purpose == "総数") & (pu.kind == "total") & pu.age.isin(FIVE_TO_TS)].copy()
p["ts_age"] = p.age.map(FIVE_TO_TS)
w = p.groupby(["year", "sex", "ts_age"], sort=True).pop_1000.sum().reset_index()
w.to_csv(DATA / "pop_weights.csv", index=False)

# ---- 読み取りの確かめ ----
# (1) 時系列表と第1-4表で、同じ年齢区分の値が同じか（2016・2021年、25〜29・60〜64・65〜69歳と総数、全種類）
diffs = []
for y in (2016, 2021):
    for sx in ("総数", "男", "女"):
        for ag in ("総数", "25～29歳", "60～64歳", "65～69歳"):
            for k in ts.kind.unique():
                a = ts[(ts.sex == sx) & (ts.age == ag) & (ts.kind == k) & (ts.year == y)].rate
                b = pu[(pu.year == y) & (pu.sex == sx) & (pu.age == ag) & (pu.kind == k) & (pu.purpose == "総数")].rate
                if len(a) == 1 and len(b) == 1:
                    diffs.append(abs(a.iloc[0] - b.iloc[0]))
checks["ts_vs_t14_same_cells"] = len(diffs)
checks["ts_vs_t14_max_abs_diff"] = round(max(diffs), 6)
# (2) 5歳階級の率を人口で重みをつけてまとめた値と、時系列表の10歳区分の値の差（四捨五入の範囲か）
gap = []
for y in (2016, 2021):
    q = pu[(pu.year == y) & (pu.sex == "総数") & (pu.purpose == "総数") & (pu.kind == "total") & pu.age.isin(FIVE_TO_TS)].copy()
    q["ts_age"] = q.age.map(FIVE_TO_TS)
    for ag, g in q.groupby("ts_age", sort=True):
        est = (g.rate * g.pop_1000).sum() / g.pop_1000.sum()
        tv = ts[(ts.sex == "総数") & (ts.age == ag) & (ts.kind == "total") & (ts.year == y)].rate.iloc[0]
        gap.append({"year": y, "age": ag, "from_5yr": round(est, 3), "ts": tv, "diff": round(est - tv, 3)})
checks["aggregate_5yr_vs_ts"] = gap
# (3) 結果の要約（PDF）の 39.6%・+2.7ポイント
t21 = ts[(ts.sex == "総数") & (ts.age == "総数") & (ts.kind == "total") & (ts.year == 2021)].rate.iloc[0]
t16 = ts[(ts.sex == "総数") & (ts.age == "総数") & (ts.kind == "total") & (ts.year == 2016)].rate.iloc[0]
checks["summary_pdf_39.6_and_2.7"] = {"2021": t21, "diff": round(t21 - t16, 1)}
# (4) 男女の人口の和＝総数の人口
s = w.pivot_table(index=["year", "ts_age"], columns="sex", values="pop_1000")
checks["pop_male_plus_female_minus_total_max"] = float((s["男"] + s["女"] - s["総数"]).abs().max())
json.dump(checks, open(DATA / "build_checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(checks, ensure_ascii=False, indent=1))
