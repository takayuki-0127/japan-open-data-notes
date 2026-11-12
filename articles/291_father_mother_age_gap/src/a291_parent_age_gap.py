"""291 父親の年齢は、母親より速く上がっているのか
人口動態統計 確定数 上巻 4-19（母の平均年齢）・4-20（父の平均年齢）・4-22（第1子出生までの父母の結婚期間）
"""
import numpy as np, pandas as pd
from common import rows, num, save_json, savefig, plt, RES


def mean_table(name):
    r = rows(name)
    d = {int(x[0][:4]): [num(v) for v in x[1:5]] for x in r if x and x[0][:4].isdigit() and len(x) >= 5}
    return pd.DataFrame(d, index=["total", "1st", "2nd", "3rd"]).T


mo = mean_table("jinkou_r7_jokan_4-19_mother_mean_age.csv")
fa = mean_table("jinkou_r7_jokan_4-20_father_mean_age.csv")
yrs = [y for y in fa.index if y in mo.index]
gap = (fa.loc[yrs] - mo.loc[yrs]).round(2)
both = pd.concat({"mother": mo.loc[yrs], "father": fa.loc[yrs], "gap": gap}, axis=1)
both.to_csv(RES / "a291_parent_mean_age.csv")

r = rows("jinkou_r7_jokan_4-22_marriage_to_first_birth.csv")
hdr = next(x for x in r if x and x[0] == "" and len(x) > 5 and x[1][:4].isdigit())
dy = [int(v[:4]) for v in hdr[1:] if v[:4].isdigit()]
dur = pd.Series([num(v) for v in next(x for x in r if x and x[0].startswith("平均期間"))[1:1 + len(dy)]], index=dy)
lt1 = pd.Series([num(v) for v in next(x for x in r if x and x[0] == "1年未満")[1:1 + len(dy)]], index=dy)
ge3 = pd.Series(100 - np.array([num(v) for v in next(x for x in r if x and x[0] == "1年未満")[1:1 + len(dy)]])
                - np.array([num(v) for v in next(x for x in r if x and x[0] == "1～2年")[1:1 + len(dy)]])
                - np.array([num(v) for v in next(x for x in r if x and x[0] == "2～3年")[1:1 + len(dy)]]), index=dy)
dd = pd.DataFrame({"mean_years": dur, "under1y_pct": lt1, "3y_plus_pct": ge3.round(1)})
dd.to_csv(RES / "a291_marriage_to_first_birth.csv")

# 母の第1子の平均年齢の上がり方を、結婚から第1子までの期間の延びと、それ以外に分ける（近似：両表は対象が少し違う）
def split(a, b):
    d_age = mo.loc[b, "1st"] - mo.loc[a, "1st"]; d_dur = dur.loc[b] - dur.loc[a]
    return dict(mother_first_change=d_age, duration_change=d_dur, other=d_age - d_dur, duration_share=d_dur / d_age)

sp = {f"{a}-{b}": split(a, b) for a, b in [(1975, 2025), (1975, 2000), (2000, 2025), (2015, 2025)]}

def ch(s, a, b): return float(s.loc[b] - s.loc[a])
per = [(1975, 1995), (1995, 2015), (2015, 2025)]
speed = {f"{a}-{b}": dict(mother_1st=ch(mo["1st"], a, b) / (b - a) * 10, father_1st=ch(fa["1st"], a, b) / (b - a) * 10,
                          mother_total=ch(mo["total"], a, b) / (b - a) * 10, father_total=ch(fa["total"], a, b) / (b - a) * 10) for a, b in per}
# 年ごとの変化（差）で、父の上がり方が母を上回った年の数
dm = mo.loc[yrs, "1st"].diff(); df_ = fa.loc[yrs, "1st"].diff()
ann = [y for y in yrs if y >= 1995]
father_faster_years = int(sum(df_.loc[y] > dm.loc[y] for y in ann if not np.isnan(dm.loc[y])))
mother_faster_years = int(sum(df_.loc[y] < dm.loc[y] for y in ann if not np.isnan(dm.loc[y])))
out = dict(
    mother={y: mo.loc[y].to_dict() for y in (1975, 1995, 2015, 2025)}, father={y: fa.loc[y].to_dict() for y in (1975, 1995, 2015, 2025)},
    gap={y: gap.loc[y].to_dict() for y in (1975, 1985, 1995, 2005, 2015, 2025)},
    gap_1st_min_year=int(gap["1st"].idxmin()), gap_1st_max_year=int(gap["1st"].idxmax()),
    change_1975_2025=dict(mother_1st=ch(mo["1st"], 1975, 2025), father_1st=ch(fa["1st"], 1975, 2025),
                          mother_total=ch(mo["total"], 1975, 2025), father_total=ch(fa["total"], 1975, 2025)),
    speed_per_decade=speed, father_faster_years_1996_2025=father_faster_years, mother_faster_years_1996_2025=mother_faster_years,
    duration={y: dd.loc[y].to_dict() for y in (1975, 2000, 2015, 2025)}, split=sp,
    father_1st_flat_since=int(min(y for y in yrs if fa.loc[y, "1st"] >= fa.loc[2025, "1st"])),
)
save_json(out)

# 図1：父と母の平均年齢（第1子）
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(mo.index[mo.index >= 1950], mo.loc[mo.index >= 1950, "1st"], color="#d93025", lw=2, marker="o", ms=3, label="母（第1子）")
ax.plot(fa.index, fa["1st"], color="#1a73e8", lw=2, marker="o", ms=3, label="父（第1子）")
ax.plot(mo.index[mo.index >= 1950], mo.loc[mo.index >= 1950, "total"], color="#d93025", lw=1, ls="--", label="母（全体）")
ax.plot(fa.index, fa["total"], color="#1a73e8", lw=1, ls="--", label="父（全体）")
ax.set_ylabel("平均年齢（歳）"); ax.legend(frameon=False, fontsize=9, ncol=2)
ax.set_title("第1子が生まれたときの父と母の平均年齢")
savefig(fig, "a291_mean_age.png")

# 図2：父と母の差（出生順位別）
fig, ax = plt.subplots(figsize=(8, 3.9))
for k, c, lab in [("1st", "#1a73e8", "第1子"), ("2nd", "#7baaf7", "第2子"), ("3rd", "#9aa0a6", "第3子"), ("total", "#202124", "全体")]:
    ax.plot(gap.index, gap[k], color=c, lw=2 if k in ("1st", "total") else 1.2, marker="o", ms=3, label=lab)
ax.set_ylabel("父の平均年齢 − 母の平均年齢（歳）"); ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9, ncol=4)
ax.set_title("父と母の年齢の差は、どの出生順位でも縮んでいる")
savefig(fig, "a291_gap.png")

# 図3：結婚から第1子までの期間
fig, ax1 = plt.subplots(figsize=(8, 3.9))
ax1.plot(dd.index, dd["mean_years"], color="#174ea6", lw=2, marker="o", ms=3, label="平均の期間（年、左）")
ax1.set_ylabel("平均の期間（年）", color="#174ea6"); ax1.set_ylim(0, None)
ax2 = ax1.twinx()
ax2.plot(dd.index, dd["under1y_pct"], color="#d93025", lw=1.5, marker="s", ms=3, label="1年未満の割合（%、右）")
ax2.plot(dd.index, dd["3y_plus_pct"], color="#f29900", lw=1.5, marker="^", ms=3, label="3年以上の割合（%、右）")
ax2.set_ylabel("割合（%）"); ax2.set_ylim(0, None)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3)
ax1.set_title("結婚してから第1子が生まれるまでの期間（嫡出の第1子）")
savefig(fig, "a291_marriage_duration.png")
print(gap.loc[[1975, 1985, 1995, 2005, 2015, 2020, 2025]].to_string()); print(speed); print(sp); print(father_faster_years, mother_faster_years, out["father_1st_flat_since"])
