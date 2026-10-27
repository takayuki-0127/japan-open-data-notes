"""03 分析：エンゲル係数の上昇を、価格・消費水準・世帯構成・外食/中食・残りに分ける"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import RAW, DATA, RES, AGE6

ann = pd.read_csv(DATA / "annual_long.csv", index_col=0)
cpi = pd.read_csv(DATA / "cpi_annual.csv", index_col=0)
P = pd.read_csv(DATA / "age_panel.csv")

# ---- 物価：食料の相対価格と、食料の内訳の価格 ----
wts = pd.read_csv(RAW / "cpi_subset.csv", dtype=str)
w = wts[wts["類・品目"].str.startswith("ウエイト１万分比")].iloc[0]
W = {k: float(w[k]) for k in ["食料", "外食", "調理食品"]}
cpi["RP"] = cpi["食料"] / cpi["総合"]
# 外食・調理食品を除いた「素材など」の価格（ウエイトで食料から差し引く）
cpi["素材など"] = (W["食料"] * cpi["食料"] - W["外食"] * cpi["外食"] - W["調理食品"] * cpi["調理食品"]) / (W["食料"] - W["外食"] - W["調理食品"])
for k in ["RP", "総合", "食料", "外食", "調理食品", "素材など"]:
    cpi[k + "_n"] = cpi[k] / cpi.loc[2020, k]

# ---- 1) エンゲル係数の推移（用途分類＝第3-2表の平均、品目分類＝長期時系列） ----
two = P[(P.kind == "two")].copy()
avg = two[two.group == "平均"].set_index("year")
E = pd.DataFrame(index=range(2000, 2026))
E["E_品目"] = 100 * ann["食料"] / ann["消費支出"]
E["外食_品目"] = 100 * ann["外食"] / ann["消費支出"]
E["調理食品_品目"] = 100 * ann["調理食品"] / ann["消費支出"]
E["E_用途"] = 100 * avg["F"] / avg["C"]
E["外食_用途"] = 100 * avg["out"] / avg["C"]
E["調理食品_用途"] = 100 * avg["ready"] / avg["C"]
E["RP"] = cpi["RP_n"]
# 価格を2020年にそろえたエンゲル係数（食料の実質 ÷ 消費支出の実質）
E["E_実質_品目"] = E["E_品目"] / E["RP"]
E["E_実質_用途"] = E["E_用途"] / E["RP"]
# 内訳ごとに自分の価格で実質化
for src, Fx, Ox, Rx in [("品目", ann["食料"], ann["外食"], ann["調理食品"]), ("用途", avg["F"], avg["out"], avg["ready"])]:
    Cx = ann["消費支出"] if src == "品目" else avg["C"]
    pc = cpi["総合_n"]
    E[f"外食_実質_{src}"] = 100 * (Ox / cpi["外食_n"]) / (Cx / pc)
    E[f"調理食品_実質_{src}"] = 100 * (Rx / cpi["調理食品_n"]) / (Cx / pc)
    E[f"素材など_実質_{src}"] = 100 * ((Fx - Ox - Rx) / cpi["素材など_n"]) / (Cx / pc)
E["実質消費支出_指数"] = (ann["消費支出"] / cpi["総合_n"]) / (ann.loc[2013, "消費支出"] / cpi.loc[2013, "総合_n"]) * 100
E.to_csv(RES / "engel_series.csv", float_format="%.3f")

# ---- 2) 価格による分解（2013→2025 など） ----
def price_split(a, b, col):
    dE = E.loc[b, col] - E.loc[a, col]
    # ln E = ln E_real + ln RP を対数平均で点数に直す
    Lm = (E.loc[b, col] - E.loc[a, col]) / np.log(E.loc[b, col] / E.loc[a, col])
    d_price = Lm * np.log(E.loc[b, "RP"] / E.loc[a, "RP"])
    return dE, d_price, dE - d_price
rows = []
for a, b in [(2000, 2025), (2005, 2025), (2008, 2025), (2013, 2025), (2019, 2025)]:
    for col in ["E_品目", "E_用途"]:
        if np.isnan(E.loc[a, col]):
            continue
        dE, dp, dq = price_split(a, b, col)
        rows.append({"期間": f"{a}→{b}", "系列": col, "E_始": E.loc[a, col], "E_終": E.loc[b, col], "変化": dE,
                     "相対価格の分": dp, "数量の分": dq, "相対価格の変化%": 100 * (E.loc[b, "RP"] / E.loc[a, "RP"] - 1)})
pd.DataFrame(rows).to_csv(RES / "price_split.csv", index=False, float_format="%.3f")

# ---- 3) 世帯主の年齢構成による分解（シフト・シェア） ----
def shift_share(kind, a, b):
    d = P[(P.kind == kind) & P.group.isin(AGE6)].copy()
    d["CW"] = d["w"] * d["C"]
    d["s"] = d["CW"] / d.groupby("year")["CW"].transform("sum")
    d["Eg"] = 100 * d["F"] / d["C"]
    A = d[d.year == a].set_index("group").loc[AGE6]
    B = d[d.year == b].set_index("group").loc[AGE6]
    within = ((A.s + B.s) / 2 * (B.Eg - A.Eg)).sum()
    between = ((A.Eg + B.Eg) / 2 * (B.s - A.s)).sum()
    Ea, Eb = (A.s * A.Eg).sum(), (B.s * B.Eg).sum()
    tab = pd.DataFrame({"世帯の割合_始": A.w / A.w.sum(), "世帯の割合_終": B.w / B.w.sum(),
                        "支出の割合_始": A.s, "支出の割合_終": B.s, "E_始": A.Eg, "E_終": B.Eg})
    return Ea, Eb, within, between, tab
ss_rows = []
for kind in ("two", "work"):
    for a, b in [(2008, 2025), (2013, 2025), (2019, 2025)]:
        Ea, Eb, wi, be, tab = shift_share(kind, a, b)
        ss_rows.append({"世帯": kind, "期間": f"{a}→{b}", "E_始": Ea, "E_終": Eb, "変化": Eb - Ea, "年齢区分の中": wi, "年齢構成": be})
        if kind == "two" and (a, b) == (2013, 2025):
            tab.to_csv(RES / "shift_share_table_2013_2025.csv", float_format="%.4f")
SS = pd.DataFrame(ss_rows)
SS.to_csv(RES / "shift_share.csv", index=False, float_format="%.3f")

# ---- 4) 世帯主の年齢×年のパネルでエンゲル曲線を推定 ----
def panel(kind, scale="sqrt", years=None, inc="C"):
    d = P[(P.kind == kind) & P.group.isin(AGE6)].copy()
    if years is not None:
        d = d[d.year.isin(years)]
    d = d.merge(cpi[["総合_n", "RP_n"]], left_on="year", right_index=True)
    eq = {"sqrt": np.sqrt(d.hh), "pc": d.hh, "hh": 1.0}[scale]
    d["lnY"] = np.log(d[inc] / d["総合_n"] / eq)
    d["lnRP"] = np.log(d["RP_n"])
    d["E"] = 100 * d["F"] / d["C"]
    d = d.rename(columns={"C": "Cons"})
    d["D2018"] = (d.year >= 2018).astype(int)       # 家計簿の改正（2018年1月）
    d["Dcovid"] = d.year.isin([2020, 2021]).astype(int)
    terms = ["lnY", "lnRP", "Dcovid", "C(group)"]
    if d["D2018"].nunique() > 1:
        terms.insert(2, "D2018")
    m = smf.wls("E ~ " + " + ".join(terms), data=d, weights=d["w"]).fit(cov_type="cluster", cov_kwds={"groups": d["year"]})
    return m, d
models = {}
specs = {
    "基本（二人以上・消費支出・√世帯人員）": dict(kind="two"),
    "1人あたり": dict(kind="two", scale="pc"),
    "世帯あたり": dict(kind="two", scale="hh"),
    "勤労者世帯・消費支出": dict(kind="work"),
    "勤労者世帯・可処分所得": dict(kind="work", inc="DI"),
    "2013年以降": dict(kind="two", years=range(2013, 2026)),
    "2018年以降（家計簿改正後）": dict(kind="two", years=range(2018, 2026)),
}
coef = []
for name, sp in specs.items():
    m, d = panel(**sp)
    models[name] = (m, d)
    ci = m.conf_int()
    coef.append({"設定": name, "n": int(m.nobs), "所得（消費水準）の係数": m.params["lnY"], "下": ci.loc["lnY", 0], "上": ci.loc["lnY", 1],
                 "相対価格の係数": m.params["lnRP"], "相対価格_下": ci.loc["lnRP", 0], "相対価格_上": ci.loc["lnRP", 1],
                 "家計簿改正": m.params.get("D2018", np.nan), "コロナ": m.params["Dcovid"], "R2": m.rsquared})
COEF = pd.DataFrame(coef)
COEF.to_csv(RES / "engel_curve_coef.csv", index=False, float_format="%.3f")

# ---- 5) まとめの分解（2013→2025、二人以上の世帯） ----
def full_decomp(name, a, b):
    m, d = models[name]
    kind = "work" if "勤労者" in name else "two"
    Ea, Eb, wi, be, tab = shift_share(kind, a, b)
    A = d[d.year == a].set_index("group").loc[AGE6]
    B = d[d.year == b].set_index("group").loc[AGE6]
    sbar = (tab["支出の割合_始"] + tab["支出の割合_終"]) / 2
    inc = (sbar * m.params["lnY"] * (B.lnY - A.lnY)).sum()
    price = m.params["lnRP"] * (B.lnRP.iloc[0] - A.lnRP.iloc[0])
    dum = m.params.get("D2018", 0.0) * (B.D2018.iloc[0] - A.D2018.iloc[0]) + m.params["Dcovid"] * (B.Dcovid.iloc[0] - A.Dcovid.iloc[0])
    rest = wi - inc - price - dum
    return {"設定": name, "期間": f"{a}→{b}", "変化": Eb - Ea, "相対価格": price, "所得（消費水準）": inc, "年齢構成": be,
            "家計簿改正・コロナ": dum, "残り（好み・外食/中食など）": rest}
dec = []
for name in specs:
    if name.startswith("2018"):
        pairs = [(2018, 2025)]
    elif name.startswith("2013"):
        pairs = [(2013, 2025)]
    else:
        pairs = [(2008, 2025), (2013, 2025), (2019, 2025)]
    for a, b in pairs:
        dec.append(full_decomp(name, a, b))
DEC = pd.DataFrame(dec)
DEC.to_csv(RES / "decomposition.csv", index=False, float_format="%.3f")

# ---- 6) 外食・中食の寄与（数量ベース、2013→2025） ----
fo = []
for src in ["品目", "用途"]:
    for a, b in [(2000, 2025), (2013, 2025), (2019, 2025)]:
        if np.isnan(E.loc[a, f"外食_実質_{src}"]):
            continue
        fo.append({"系列": src, "期間": f"{a}→{b}",
                   "実質E_変化": E.loc[b, f"E_実質_{src}"] - E.loc[a, f"E_実質_{src}"],
                   "外食": E.loc[b, f"外食_実質_{src}"] - E.loc[a, f"外食_実質_{src}"],
                   "調理食品": E.loc[b, f"調理食品_実質_{src}"] - E.loc[a, f"調理食品_実質_{src}"],
                   "素材など": E.loc[b, f"素材など_実質_{src}"] - E.loc[a, f"素材など_実質_{src}"]})
pd.DataFrame(fo).to_csv(RES / "food_components.csv", index=False, float_format="%.3f")

# ---- 7) 「生活苦」を見る別の物差し ----
wk = P[(P.kind == "work") & (P.group == "平均")].set_index("year").join(cpi[["総合_n"]])
two_a = avg.join(cpi[["総合_n", "食料_n"]])
life = pd.DataFrame({
    "実質消費支出_二人以上(2013=100)": 100 * (two_a.C / two_a["総合_n"]) / (two_a.loc[2013, "C"] / two_a.loc[2013, "総合_n"]),
    "実質食料_二人以上(2013=100)": 100 * (two_a.F / two_a["食料_n"]) / (two_a.loc[2013, "F"] / two_a.loc[2013, "食料_n"]),
    "実質可処分所得_勤労者(2013=100)": 100 * (wk.DI / wk["総合_n"]) / (wk.loc[2013, "DI"] / wk.loc[2013, "総合_n"]),
    "実質消費支出_等価(2013=100)": 100 * (two_a.C / two_a["総合_n"] / np.sqrt(two_a.hh)) / (two_a.loc[2013, "C"] / two_a.loc[2013, "総合_n"] / np.sqrt(two_a.loc[2013, "hh"])),
    "実質可処分所得_勤労者_等価(2013=100)": 100 * (wk.DI / wk["総合_n"] / np.sqrt(wk.hh)) / (wk.loc[2013, "DI"] / wk.loc[2013, "総合_n"] / np.sqrt(wk.loc[2013, "hh"])),
    "世帯人員_二人以上": two_a.hh, "世帯主の年齢_二人以上": two_a.age,
})
life.to_csv(RES / "living_standard.csv", float_format="%.2f")

print(E.loc[[2000, 2005, 2008, 2013, 2019, 2025], ["E_品目", "E_用途", "RP", "E_実質_用途", "外食_用途", "調理食品_用途"]].round(2))
print(pd.read_csv(RES / "price_split.csv").round(2).to_string())
print(SS.round(2).to_string())
print(COEF.round(3).to_string())
print(DEC.round(2).to_string())
print(pd.read_csv(RES / "food_components.csv").round(2).to_string())
print(life.loc[[2008, 2013, 2019, 2023, 2024, 2025]].round(1).T)
