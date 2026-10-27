"""年齢別出生率の分解と、Bongaarts–Feeney のテンポ調整、コーホートの完結出生率との比較"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, AGES, mean_age, bf_adjust

RES.mkdir(exist_ok=True)
asfr = pd.read_csv(DATA / "asfr_single_year.csv").set_index("year")
A = asfr[[str(a) for a in AGES]]
order = pd.read_csv(DATA / "order_tfr_mab.csv").set_index("year")
cum = pd.read_csv(DATA / "cohort_cumulative.csv", index_col="age")
cum.columns = cum.columns.astype(int)

# ---------- 1) 年ごとの TFR・平均出生年齢・テンポ調整（全体） ----------
yr = pd.DataFrame(index=A.index)
yr["tfr"] = A.sum(1)
yr["mab"] = A.apply(mean_age, axis=1)
yr["bf_total"], yr["r_total"] = bf_adjust(yr.tfr, yr.mab)

# 出生順位別（1975年以降は毎年）：Σ TFR_i / (1 - r_i)
o = order.loc[1975:].copy()
parts = ["1", "2", "3", "4", "5p"]


def bf_order(o, how="center", smooth=1):
    s = 0
    for p in parts:
        adj, _ = bf_adjust(o["tfr" + p], o["mab" + p], how=how, smooth=smooth)
        s = s + adj
    return s


o["bf_order"] = bf_order(o)
o["r1"] = (o.mab1.shift(-1) - o.mab1.shift(1)) / 2
yr = yr.join(o[["bf_order", "r1", "mab1", "tfr1", "tfr2", "tfr3"]], how="left")
yr["tempo_effect"] = yr.tfr - yr.bf_order
yr.to_csv(RES / "tfr_mab_bf.csv")

# 公表の平均出生年齢と自分の計算の差（確認用）
chk = (yr.mab - order.mab).dropna()

# ---------- 2) TFR の変化を年齢に分ける（各歳の差の合計＝TFR の差） ----------
groups = {"15-24": range(15, 25), "25-29": range(25, 30), "30-34": range(30, 35),
          "35-39": range(35, 40), "40-49": range(40, 50)}
periods = [(1950, 1975), (1975, 2005), (2005, 2015), (2015, 2023), (1975, 2023)]
rows = []
for a, b in periods:
    d = A.loc[b] - A.loc[a]
    r = dict(period=f"{a}→{b}", tfr_a=A.loc[a].sum(), tfr_b=A.loc[b].sum(), change=d.sum())
    for g, ages in groups.items():
        r[g] = d[[str(x) for x in ages]].sum()
    r["under30"] = d[[str(x) for x in range(15, 30)]].sum()
    r["30plus"] = d[[str(x) for x in range(30, 50)]].sum()
    rows.append(r)
dec = pd.DataFrame(rows)
dec.to_csv(RES / "decomp_periods.csv", index=False)

# 1年ごとの年齢別の寄与（図用）
step = A.diff().dropna()
step_g = pd.DataFrame({g: step[[str(x) for x in ages]].sum(1) for g, ages in groups.items()})
step_g.to_csv(RES / "decomp_yearly.csv")

# ---------- 3) コーホート（生まれ年）ごとの完結出生率 ----------
coh = pd.DataFrame({"year15": cum.columns})
coh["birth"] = coh.year15 - 15
coh["cfr49"] = [cum.loc[49, c] if c + 34 <= 2023 else np.nan for c in cum.columns]
coh["cum39"] = [cum.loc[39, c] if c + 24 <= 2023 else np.nan for c in cum.columns]
coh["cum29"] = [cum.loc[29, c] if c + 14 <= 2023 else np.nan for c in cum.columns]
# 完結したコーホートの平均出生年齢（累積の差から）
mab_c = []
for c in cum.columns:
    if c + 34 <= 2023:
        f = cum[c].diff().fillna(cum[c].iloc[0]).values
        mab_c.append(float(((AGES + 0.5) * f).sum() / f.sum()))
    else:
        mab_c.append(np.nan)
coh["mab"] = mab_c
coh["year_at_mab"] = coh.birth + coh.mab
coh.to_csv(RES / "cohort_cfr.csv", index=False)

# ---------- 4) 頑健性：テンポ調整の作り方を変える ----------
rob = pd.DataFrame(index=o.index)
rob["基本（順位別・中心差分）"] = o.bf_order
rob["順位別・後退差分"] = bf_order(o, how="back")
rob["順位別・平均年齢を3年移動平均"] = bf_order(o, smooth=3)
rob["順位別・平均年齢を5年移動平均"] = bf_order(o, smooth=5)
rob["全体（順位別にしない）"] = yr.bf_total.loc[o.index]
rob["公表TFR"] = o.tfr
rob.to_csv(RES / "robustness_bf.csv")

def pmean(s, a, b):
    return float(s.loc[a:b].mean())

summary = {}
for col in rob.columns:
    summary[col] = {p: round(pmean(rob[col], *rg), 3) for p, rg in
                    {"1980-89": (1980, 1989), "1990-2004": (1990, 2004), "2005-14": (2005, 2014), "2015-22": (2015, 2022)}.items()}

# 期間の端を1年ずらしても、年齢の寄与の割合が変わらないか
shift_rows = []
for a, b in [(1975, 2005), (2015, 2023)]:
    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            aa, bb = a + da, min(b + db, 2023)
            d = A.loc[bb] - A.loc[aa]
            shift_rows.append(dict(base=f"{a}→{b}", a=aa, b=bb, change=d.sum(),
                                   share_under30=d[[str(x) for x in range(15, 30)]].sum() / d.sum()))
shift = pd.DataFrame(shift_rows).drop_duplicates()
shift.to_csv(RES / "robustness_period_ends.csv", index=False)

# ---------- 5) 主な数字 ----------
key = {
    "mab_check_maxdiff_vs_published": round(float(chk.abs().max()), 3),
    "tfr": {y: round(float(yr.tfr.loc[y]), 3) for y in (1975, 2005, 2015, 2023)},
    "mab": {y: round(float(yr.mab.loc[y]), 2) for y in (1975, 2005, 2015, 2023)},
    "mab1": {y: float(order.mab1.loc[y]) for y in (1975, 2005, 2015, 2023)},
    "decomp": dec.round(3).to_dict(orient="records"),
    "bf_period_means": summary,
    "bf_order": {y: round(float(o.bf_order.loc[y]), 3) for y in (1985, 1995, 2000, 2005, 2010, 2015, 2019, 2022) if y in o.index},
    "tempo_effect_mean": {p: round(pmean(yr.tempo_effect, *rg), 3) for p, rg in {"1980-2004": (1980, 2004), "2005-14": (2005, 2014), "2015-22": (2015, 2022)}.items()},
    "r1_mean": {p: round(pmean(yr.r1, *rg), 3) for p, rg in {"1980-2004": (1980, 2004), "2005-14": (2005, 2014), "2015-22": (2015, 2022)}.items()},
    "cohort": coh.dropna(subset=["cfr49"]).iloc[[0, -10, -5, -1]][["birth", "cfr49", "mab"]].round(3).to_dict(orient="records"),
    "cohort_cum39": coh.dropna(subset=["cum39"]).iloc[[-15, -10, -5, -1]][["birth", "cum39"]].round(3).to_dict(orient="records"),
    "shift_share_under30_range": {b: [round(float(g.share_under30.min()), 3), round(float(g.share_under30.max()), 3)] for b, g in shift.groupby("base")},
}
json.dump(key, open(RES / "key_numbers.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(key, ensure_ascii=False, indent=1))
