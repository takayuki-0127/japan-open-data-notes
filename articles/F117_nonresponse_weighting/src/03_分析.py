"""F117 03 分析：
A. 国民生活基礎調査と国勢調査で、世帯の構成（人数・世帯主の年齢・世帯構造）がどれだけずれるか。回収率との関係。
B. 2024年の所得を、国勢調査（2025年）の構成に合わせて重み付けし直すと、平均・中央値・低所得の割合がどれだけ動くか。
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from common import Bins, rake, kish_deff, SIZES, AGES, STRUCTS

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
R = ROOT / "results"
R.mkdir(exist_ok=True)

# ---------------- A. 構成のずれ ----------------
sv = pd.read_csv(D / "survey_households_size.csv").set_index("year")
cs = pd.read_csv(D / "census_households_size.csv").set_index("year")
rr = pd.read_csv(D / "response_rates.csv").set_index("year")


def shares(df, y):
    r = df.loc[y]
    return r[SIZES] / r[SIZES].sum() * 100


rows = []
for y in [1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]:
    c = shares(cs, y)
    if y == 2020:  # 2020年は調査なし：2019年と2021年の平均
        s = (shares(sv, 2019) + shares(sv, 2021)) / 2
        note = "調査は2019年と2021年の平均"
    else:
        s = shares(sv, y)
        note = "1995年の調査は兵庫県を除く" if y == 1995 else ""
    rr_y = {1995: 90.0, 2005: None, 2010: 79.4, 2015: 78.5, 2020: rr.loc[2019, "rr_household"], 2025: 62.6}.get(y)
    rr_note = {1995: "1996年の値", 2020: "2019年の値"}.get(y, "")
    rows.append(dict(year=y, census_single=c["n1"], survey_single=s["n1"], gap_single=c["n1"] - s["n1"],
                     census_2=c["n2"], survey_2=s["n2"], census_4p=c[["n4", "n5", "n6p"]].sum(),
                     survey_4p=s[["n4", "n5", "n6p"]].sum(),
                     tvd=float(np.abs(c - s).sum() / 2), rr_household=rr_y, rr_note=rr_note, note=note))
gap = pd.DataFrame(rows)
gap.to_csv(R / "gap_size_years.csv", index=False)

# 世帯構造（1995〜2025）
svs = pd.read_csv(D / "survey_households_structure.csv").set_index("year")
svs["other3"] = svs.three_gen + svs.other
csf = pd.read_csv(D / "census_households_structure.csv")
csf["year"] = csf.year.astype(int)
csf = csf.set_index("year")
csf["other3"] = csf["other"]
rows = []
for y in [1995, 2000, 2005, 2010, 2015, 2020, 2025]:
    c = csf.loc[y, STRUCTS] / csf.loc[y, STRUCTS].sum() * 100
    if y == 2020:
        s = ((svs.loc[2019, STRUCTS] / svs.loc[2019, STRUCTS].sum()) + (svs.loc[2021, STRUCTS] / svs.loc[2021, STRUCTS].sum())) / 2 * 100
    else:
        s = svs.loc[y, STRUCTS] / svs.loc[y, STRUCTS].sum() * 100
    for k in STRUCTS:
        rows.append(dict(year=y, structure=k, census=c[k], survey=s[k], gap=c[k] - s[k]))
pd.DataFrame(rows).to_csv(R / "gap_structure_years.csv", index=False)

# 世帯主の年齢別の単独世帯の割合（国勢調査）と、2025年の世帯主の年齢の構成（所得票 vs 国勢調査）
ca = pd.read_csv(D / "census_headage.csv")
i26 = pd.read_csv(D / "income_by_headage_2024.csv")
i22 = pd.read_csv(D / "income_by_size_2024.csv")
i24 = pd.read_csv(D / "income_by_structure_2024.csv")
i24["other3"] = i24.three_gen + i24.other
c25a = ca[ca.year == 2025].set_index("a").loc[AGES, "n"]
age_cmp = pd.DataFrame(dict(census=c25a / c25a.sum() * 100,
                            survey_income=i26[AGES].sum() / i26[AGES].sum().sum() * 100))
age_cmp["ratio"] = age_cmp.census / age_cmp.survey_income
age_cmp.to_csv(R / "compare_headage_2025.csv")

c25s = cs.loc[2025, SIZES]
size_cmp = pd.DataFrame(dict(census=c25s / c25s.sum() * 100,
                             survey_household=shares(sv, 2025),
                             survey_income=i22[SIZES].sum() / i22[SIZES].sum().sum() * 100))
size_cmp["ratio_income"] = size_cmp.census / size_cmp.survey_income
size_cmp.to_csv(R / "compare_size_2025.csv")

c25f = csf.loc[2025, STRUCTS]
struct_cmp = pd.DataFrame(dict(census=c25f / c25f.sum() * 100,
                               survey_household=svs.loc[2025, STRUCTS] / svs.loc[2025, STRUCTS].sum() * 100,
                               survey_income=i24[STRUCTS].sum() / i24[STRUCTS].sum().sum() * 100))
struct_cmp["ratio_income"] = struct_cmp.census / struct_cmp.survey_income
struct_cmp.to_csv(R / "compare_structure_2025.csv")

# ---------------- B. 重み付けのし直し ----------------
bins = Bins(i22.lo, i22.hi)
nk = i22.total.values.astype(float)  # 所得階級の度数（1万対）
base = bins.stats(nk)
PUB_MEAN = 575.2  # 公表の平均所得（万円）
MEAN_SIZE = pd.read_csv(D / "mean_income_by_size_2024.csv").iloc[0]
MEAN_STR = pd.read_csv(D / "mean_income_by_structure_2024.csv").iloc[0]
w3 = i24[["three_gen", "other"]].sum()
MEAN_STR["other3"] = (MEAN_STR.three_gen * w3.three_gen + MEAN_STR.other * w3.other) / w3.sum()

# 調査の側の表（1万対）：人数×所得、年齢×所得、世帯構造×所得
T_size = i22[SIZES].values.T.astype(float)        # 6 × 25
T_age = i26[AGES].values.T.astype(float)          # 7 × 25
T_str = i24[STRUCTS].values.T.astype(float)       # 5 × 25
# 年齢の表の合計（年齢不詳を除く）を所得階級ごとに全体に合わせる
nk_age = T_age.sum(axis=0)

# 人数×年齢×所得の同時分布を、「所得階級が同じなら人数と年齢は独立」とみなして作る（仮定）
J = np.einsum("sk,ak->sak", T_size, T_age / np.where(nk_age > 0, nk_age, 1))

c_size = cs.loc[2025, SIZES].values.astype(float)
c_age = c25a.values.astype(float)
c_joint = pd.read_csv(D / "census2025_headage_by_size.csv").set_index("a").loc[AGES, SIZES].values.T.astype(float)  # 6×7
c_str = csf.loc[2025, STRUCTS].values.astype(float)

results = []
deff = {}


def add(method, w_k, exact_mean=None, extra=None):
    st = bins.stats(w_k)
    st_mid = bins.stats(w_k, within="mid")
    mean_scaled = st["mean"] / base["mean"] * PUB_MEAN  # 階級からの平均のずれを、公表の平均で割り戻す
    rec = dict(method=method, mean_from_bins=st["mean"], mean_scaled=mean_scaled, mean_exact=exact_mean,
               median=st["median"], median_mid=st_mid["median"], p20=st["p20"], p80=st["p80"],
               below200=st["below200"], below300=st["below300"], above1000=st["above1000"])
    if extra:
        rec.update(extra)
    results.append(rec)


add("公表どおり（重み付けなし）", nk, exact_mean=PUB_MEAN)

# 1) 世帯人員で事後層化
f_size = c_size / c_size.sum() / (T_size.sum(axis=1) / T_size.sum())
w_k = (T_size * f_size[:, None]).sum(axis=0)
ex = float((c_size / c_size.sum() * MEAN_SIZE[SIZES].values).sum())
add("世帯人員（6区分）", w_k, exact_mean=ex)
deff["世帯人員（6区分）"] = kish_deff(f_size, T_size.sum(axis=1))

# 2) 世帯構造で事後層化
f_str = c_str / c_str.sum() / (T_str.sum(axis=1) / T_str.sum())
w_k = (T_str * f_str[:, None]).sum(axis=0)
ex = float((c_str / c_str.sum() * MEAN_STR[STRUCTS].values.astype(float)).sum())
add("世帯構造（5区分）", w_k, exact_mean=ex)
deff["世帯構造（5区分）"] = kish_deff(f_str, T_str.sum(axis=1))

# 3) 世帯主の年齢で事後層化
f_age = c_age / c_age.sum() / (T_age.sum(axis=1) / T_age.sum())
w_k = (T_age * f_age[:, None]).sum(axis=0)
w_k = w_k / w_k.sum() * nk.sum()
add("世帯主の年齢（7区分）", w_k)
deff["世帯主の年齢（7区分）"] = kish_deff(f_age, T_age.sum(axis=1))

# 4) 人数と年齢でレーキング（周辺だけ合わせる）
Jr, it = rake(J, {0: c_size, 1: c_age})
add("人数＋年齢のレーキング", Jr.sum(axis=(0, 1)), extra=dict(iterations=it))
deff["人数＋年齢のレーキング"] = kish_deff(Jr.sum(axis=2) / np.where(J.sum(axis=2) > 0, J.sum(axis=2), 1), J.sum(axis=2))

# 5) 人数×年齢の同時分布で事後層化
cell = J.sum(axis=2)
f_joint = (c_joint / c_joint.sum()) / np.where(cell > 0, cell / cell.sum(), np.nan)
f_joint = np.nan_to_num(f_joint)
w_k = (J * f_joint[:, :, None]).sum(axis=(0, 1))
add("人数×年齢の事後層化（42セル）", w_k)
deff["人数×年齢の事後層化（42セル）"] = kish_deff(f_joint, cell)

res = pd.DataFrame(results)
res["deff"] = res.method.map(deff)
res.to_csv(R / "reweight_2024.csv", index=False)

# 重みの大きさ（人数・年齢）
pd.DataFrame(dict(group=SIZES, weight=f_size)).to_csv(R / "weights_size.csv", index=False)
pd.DataFrame(dict(group=AGES, weight=f_age)).to_csv(R / "weights_age.csv", index=False)
pd.DataFrame(dict(group=STRUCTS, weight=f_str)).to_csv(R / "weights_structure.csv", index=False)

# 人数の層ごとの所得（重みをかける前）：重み付けで何が起きるかの説明用
by_size = []
for i, s in enumerate(SIZES):
    st = bins.stats(T_size[i])
    by_size.append(dict(group=s, survey_share=T_size[i].sum() / T_size.sum() * 100, census_share=c_size[i] / c_size.sum() * 100,
                        mean_pub=MEAN_SIZE[s], median=st["median"], below200=st["below200"]))
pd.DataFrame(by_size).to_csv(R / "by_size_2024.csv", index=False)

# ---------------- 頑健性：目標の置き方 ----------------
rob = []
# (a) 国勢調査の単独世帯から会社の独身寮の単身者を除く（所得票は寮・寄宿舎を調査しない）
dorm = pd.read_csv(D / "census2025_dorm.csv").iloc[0]
c_size_b = c_size.copy()
c_size_b[0] -= dorm.dorm_single
# (b) 2020年の国勢調査の構成を使う（時点のずれ）
c_size_c = cs.loc[2020, SIZES].values.astype(float)
# (c) 単独世帯の差の半分だけを埋める（国勢調査と調査の定義の違いを大きめに見る）
sv_sh = T_size.sum(axis=1) / T_size.sum()
cs_sh = c_size / c_size.sum()
c_size_d = (sv_sh + cs_sh) / 2
# (d) 世帯票の構成（所得票ではなく、同じ調査の世帯票）に合わせる
c_size_e = sv.loc[2025, SIZES].values.astype(float)
for name, target in [("基本（2025年国勢調査）", c_size), ("独身寮の単身者を除く", c_size_b), ("2020年国勢調査", c_size_c),
                     ("差の半分だけ埋める", c_size_d), ("同じ調査の世帯票に合わせる", c_size_e)]:
    f = target / target.sum() / sv_sh
    w_k = (T_size * f[:, None]).sum(axis=0)
    st = bins.stats(w_k)
    ex = float((target / target.sum() * MEAN_SIZE[SIZES].values).sum())
    rob.append(dict(target=name, single_target=target[0] / target.sum() * 100, mean_exact=ex, median=st["median"],
                    below200=st["below200"], below300=st["below300"]))
pd.DataFrame(rob).to_csv(R / "robust_targets.csv", index=False)

# 階級の中の仮定（一様／中央の値）とパレートの α
rob2 = []
for name, w_k in [("重み付けなし", nk), ("世帯人員", (T_size * f_size[:, None]).sum(axis=0)), ("人数＋年齢のレーキング", Jr.sum(axis=(0, 1)))]:
    for within in ["uniform", "mid"]:
        for a in [None, 2.5, 4.0]:
            st = bins.stats(w_k, within=within, alpha=a)
            rob2.append(dict(method=name, within=within, alpha=st["alpha"], mean=st["mean"], median=st["median"],
                             below200=st["below200"]))
pd.DataFrame(rob2).to_csv(R / "robust_within.csv", index=False)

summary = dict(
    base=base, pub_mean=PUB_MEAN,
    gap=gap.to_dict(orient="records"),
)
json.dump(summary, open(R / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 220)
print(gap.round(2))
print(size_cmp.round(2)); print(age_cmp.round(2)); print(struct_cmp.round(2))
print(res.round(2).to_string())
print(pd.DataFrame(rob).round(2))
print(pd.DataFrame(rob2).round(2))
