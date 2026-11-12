"""337：1966年（丙午）に、出生はどれだけ減ったのか。1906年の丙午と比べる。
年ごとの出生数（男女別）・乳児死亡・母の年齢別の出生数を使う。1966年の月ごとの出生数は、公開の表では取れなかった。
"""
import csv, json, re
import numpy as np, pandas as pd, xlrd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：厚生労働省「人口動態統計」（総務省統計局「日本の長期統計系列」2-24・2-26・2-27・2-29）をもとに作成者が加工して作成"
def sheet(name):
    s = xlrd.open_workbook(DATA / "raw" / name).sheet_by_index(0)
    return [s.row_values(r) for r in range(s.nrows)]
def year(v):
    m = re.match(r"\s*(\d{4})", str(v)); return int(m.group(1)) if m else None
f = lambda v: float(v) if isinstance(v, (int, float)) else np.nan

B = pd.DataFrame([(year(r[1]), f(r[2]), f(r[3]), f(r[4])) for r in sheet("chouki_02-24.xls") if year(r[1])], columns=["year", "births", "male", "female"]).set_index("year")
I = pd.DataFrame([(year(r[1]), f(r[3]), f(r[4]), f(r[5]), f(r[6])) for r in sheet("chouki_02-26.xls") if year(r[1])], columns=["year", "inf", "inf_m", "inf_f", "imr"]).set_index("year")
Nn = pd.DataFrame([(year(r[1]), f(r[2]), f(r[3]), f(r[4]), f(r[5])) for r in sheet("chouki_02-27.xls") if year(r[1])], columns=["year", "neo", "neo_m", "neo_f", "nmr"]).set_index("year")
AGE = ["15歳未満", "15〜19歳", "20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜44歳", "45〜49歳", "50歳以上"]
Ma = pd.DataFrame([[year(r[1])] + [f(x) for x in r[3:12]] for r in sheet("chouki_02-29-a.xls") if year(r[1])], columns=["year"] + AGE).set_index("year")
Y = B.join(I).join(Nn); Y["sex_ratio"] = Y.male / Y.female * 100
Y.loc[1895:1915].to_csv(DATA / "births_1895_1915.csv"); Y.loc[1955:1975].to_csv(DATA / "births_1955_1975.csv"); Ma.loc[1960:1972].to_csv(DATA / "births_by_mother_age_1960_1972.csv")

def expected(col, hy, before, after):
    """丙午の前年・当年・翌年を除いた前後の年に、対数の直線を当てて「ふだんの数」を作る"""
    yrs = list(before) + list(after)
    k = np.polyfit(yrs, np.log(Y.loc[yrs, col].values), 1)
    return {y: float(np.exp(np.polyval(k, y))) for y in (hy - 1, hy, hy + 1)}
out = {}
for hy, before, after in ((1966, range(1961, 1965), range(1968, 1972)), (1906, range(1901, 1905), range(1908, 1912))):
    o = {}
    for col in ("births", "male", "female"):
        e = expected(col, hy, before, after)
        o[col] = {str(y): {"actual": int(Y.loc[y, col]), "expected": round(e[y]), "diff": round(Y.loc[y, col] - e[y]), "diff_pct": round((Y.loc[y, col] / e[y] - 1) * 100, 1)} for y in e}
        o[col]["net_3yr"] = round(sum(Y.loc[y, col] - e[y] for y in e)); o[col]["shifted_share_pct"] = round(-(o[col][str(hy - 1)]["diff"] + o[col][str(hy + 1)]["diff"]) / o[col][str(hy)]["diff"] * 100, 1)
    # 簡単な見込み：前年と翌年の平均
    o["vs_mean_of_neighbors_pct"] = {c: round((Y.loc[hy, c] / Y.loc[[hy - 1, hy + 1], c].mean() - 1) * 100, 1) for c in ("births", "male", "female")}
    o["vs_prev_year_pct"] = {c: round((Y.loc[hy, c] / Y.loc[hy - 1, c] - 1) * 100, 1) for c in ("births", "male", "female")}
    o["sex_ratio"] = {str(y): round(float(Y.loc[y, "sex_ratio"]), 1) for y in range(hy - 3, hy + 4)}
    o["imr"] = {str(y): float(Y.loc[y, "imr"]) for y in range(hy - 2, hy + 3)}; o["nmr"] = {str(y): float(Y.loc[y, "nmr"]) for y in range(hy - 2, hy + 3)}
    o["neonatal_sex_ratio"] = {str(y): round(float(Y.loc[y, "neo_m"] / Y.loc[y, "neo_f"] * 100), 1) for y in range(hy - 2, hy + 3)}
    # 女の出生が「男の出生÷ふだんの性比」より何人少ないか（ふだんの性比＝前後の年の平均。前年・翌年を除く）
    base = [y for y in list(before) + list(after)]
    sr = float((Y.loc[base, "male"].sum() / Y.loc[base, "female"].sum()))
    o["usual_sex_ratio"] = round(sr * 100, 1)
    o["female_gap_vs_usual_ratio"] = {str(y): round(Y.loc[y, "female"] - Y.loc[y, "male"] / sr) for y in (hy - 1, hy, hy + 1)}
    out[str(hy)] = o
# 窓を変える（前後3年・5年）
rob = {}
for w in (3, 5):
    for hy in (1966, 1906):
        e = expected("births", hy, range(hy - 1 - w, hy - 1), range(hy + 2, hy + 2 + w))
        rob[f"{hy}_w{w}"] = {str(y): round((Y.loc[y, "births"] / e[y] - 1) * 100, 1) for y in e}
out["robust_window"] = rob
# 母の年齢別：1966年を前年・翌年の平均と比べる
ma = {a: round(float(Ma.loc[1966, a] / Ma.loc[[1965, 1967], a].mean() - 1) * 100, 1) for a in AGE[1:8]}
out["mother_age_1966_vs_neighbors_pct"] = ma
out["mother_age_share_of_drop_pct"] = {a: round(float((Ma.loc[[1965, 1967], a].mean() - Ma.loc[1966, a]) / (Ma.loc[[1965, 1967], AGE].sum(axis=1).mean() - Ma.loc[1966, AGE].sum()) * 100), 1) for a in AGE[1:8]}
# 月別（1960・1965・1970年だけ表にある）：12月と1月の割合
rows = list(csv.reader(open(DATA / "raw" / "jinkou_r7_jokan_4-2_births_by_month.csv", encoding="utf-8")))
mon = {}
for r in rows:
    if len(r) >= 14 and r[0].strip().isdigit() and int(r[0]) in (1955, 1960, 1965, 1970, 1975) and int(r[0]) not in mon:
        v = [float(x) for x in r[2:14]]; days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if int(r[0]) % 4 == 0: days[1] = 29
        per = np.array(v) / np.array(days); mon[int(r[0])] = {"dec_vs_year_avg": round(float(per[11] / (sum(v) / sum(days))), 3), "jan_vs_year_avg": round(float(per[0] / (sum(v) / sum(days))), 3),
                                                              "nov_vs_year_avg": round(float(per[10] / (sum(v) / sum(days))), 3)}
out["monthly_available_years"] = mon
json.dump(out, open(RES / "a337_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：出生数 1955〜1975年と、ふだんの数
fig, ax = plt.subplots(figsize=(8.6, 4.3))
yy = list(range(1955, 1976)); ax.bar(yy, Y.loc[yy, "births"] / 1e4, color=[ORANGE if y == 1966 else (BLUE if y in (1965, 1967) else LIGHT) for y in yy])
o = out["1966"]["births"]
ax.plot([1965, 1966, 1967], [o[str(y)]["expected"] / 1e4 for y in (1965, 1966, 1967)], "o--", color=INK, ms=4, lw=1, label="前後の年から見込んだ数")
for y, dx, yy_, col in ((1965, -1.6, 196, INK), (1966, 0, 100, "white"), (1967, 1.6, 207, INK)):
    ax.text(y + dx, yy_, f"{o[str(y)]['diff'] / 1e4:+.1f}万人\n（{o[str(y)]['diff_pct']:+.1f}%）", ha="center", fontsize=8.5, color=col)
ax.set_ylabel("出生数（万人）"); ax.set_ylim(0, 230); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title(f"1966年の出生は見込みより{-o['1966']['diff'] / 1e4:.0f}万人少なく、前年と翌年は合わせて{(o['1965']['diff'] + o['1967']['diff']) / 1e4:.0f}万人多かった")
save(fig, "a337_births_1966.png", SRC + "。見込みは1961〜64年と1968〜71年の出生数に当てた対数の直線")

# 図2：出生性比（女100人に対する男）— 1906年と1966年
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, hy in zip(axes, (1906, 1966)):
    yy = list(range(hy - 6, hy + 7)); ax.plot(yy, Y.loc[yy, "sex_ratio"], "-o", color=BLUE, ms=4)
    ax.axhline(out[str(hy)]["usual_sex_ratio"], color=GRAY, lw=0.8, ls="--")
    for y in (hy - 1, hy, hy + 1):
        ax.annotate(f"{y}年 {Y.loc[y, 'sex_ratio']:.1f}", (y, Y.loc[y, "sex_ratio"]), xytext=(0, 9) if y == hy else ((-6, -4) if y < hy else (6, -4)), textcoords="offset points",
                    ha="center" if y == hy else ("right" if y < hy else "left"), fontsize=9, color=ORANGE if y == hy else INK)
    ax.set_title(f"{hy}年の前後"); ax.set_xlabel("年"); ax.set_ylim(102, 109.6); ax.grid(axis="y", color="#e6e6e3", lw=0.6)
axes[0].set_ylabel("女100人に対する男の出生数")
fig.suptitle("1906年は、丙午の年だけ男が多く、前後の年は女が多い。1966年の動きは小さい", fontsize=12.5, y=1.02)
save(fig, "a337_sex_ratio.png", SRC + "。点線は前後の年（丙午の前年・翌年を除く）の平均")

# 図3：母の年齢別の減り方（1966年、前年と翌年の平均との比）
fig, ax = plt.subplots(figsize=(8.2, 4))
k = list(ma); ax.bar(k, [ma[a] for a in k], color=ORANGE)
for i, a in enumerate(k): ax.text(i, ma[a] - 0.8 if ma[a] < 0 else ma[a] + 0.8, f"{ma[a]:+.0f}%", ha="center", va="top" if ma[a] < 0 else "bottom", fontsize=9.5, color=INK)
ax.set_ylim(-36, 11)
ax.set_ylabel("前年と翌年の平均との差（%）"); ax.axhline(0, color=INK, lw=0.6)
ax.set_title("1966年の出生は、母の年齢が20〜39歳のどの層でも2〜3割少なかった")
save(fig, "a337_mother_age.png", SRC)

print(out["monthly_available_years"])
