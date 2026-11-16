"""03 分析（オフライン）：ペット関連の支出（フード・用品・サービス。動物病院代は除く）の伸びを、物価・量、
購入の回数・1回あたりの額、世帯主の年齢・年間収入に分ける。仮説 H1〜H4 と頑健性。出力：results/main.json と CSV"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "pet_items.csv")
cpi = pd.read_csv(DATA / "cpi_pet.csv").set_index("year")
FOOD_P = "ペットフード（犬・猫の加重平均）"
r = lambda x: float(round(x, 4))
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
QS = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ"]
w = d[d.code == "hh_weight"].set_index(["table", "year", "group"]).amount
hh = d[d.code == "hh_size"].set_index(["table", "year", "group"]).amount
x = d[d.code.isin(["848", "84Y", "841"])].copy()

def deflator(item, year, mode):
    if mode == "main":
        if item == "ペットフード":
            return cpi.loc[year, FOOD_P]
        if item == "ペット用品":
            return cpi.loc[year, "ペットトイレ用品"]
        if item == "ペット関連サービス":
            return cpi.loc[year, "ペット美容院代"]
        return cpi.loc[year, "他の教養娯楽用品"]  # 2014年までの用品・サービス
    if mode == "long":  # 長い期間：フード以外は他の教養娯楽用品で通す
        return cpi.loc[year, FOOD_P] if item == "ペットフード" else cpi.loc[year, "他の教養娯楽用品"]
    if mode == "class":
        return cpi.loc[year, "他の教養娯楽用品"]
    if mode == "all":
        return cpi.loc[year, "総合"]
for mode in ["main", "long", "class", "all"]:
    x[f"real_{mode}"] = [a / deflator(i, y, mode) * 100 for a, i, y in zip(x.amount, x["item"], x.year)]
x["kind"] = np.where(x["item"] == "ペットフード", "フード", "用品・サービス")
x.to_csv(RES / "pet_items_real.csv", index=False, float_format="%.4f")

def total(table, group, col="amount", kinds=("フード", "用品・サービス"), items=None):
    s = x[(x.table == table) & (x.group == group) & x.kind.isin(kinds)]
    if items is not None:
        s = s[s["item"].isin(items)]
    return s.groupby("year")[col].sum()
M = {}
nom = total("age", "平均"); rl = total("age", "平均", "real_long"); rm = total("age", "平均", "real_main")
food_n = total("age", "平均", kinds=("フード",)); food_r = total("age", "平均", "real_main", kinds=("フード",))
gs_n = total("age", "平均", kinds=("用品・サービス",)); gs_rl = total("age", "平均", "real_long", kinds=("用品・サービス",))
ts = pd.DataFrame({"year": nom.index, "nominal_total": nom.values, "nominal_food": food_n.values, "nominal_goods_services": gs_n.values,
                   "real_total_long": rl.round(1).values, "real_food": food_r.round(1).values, "real_goods_services_long": gs_rl.round(1).values,
                   "cpi_food": cpi[FOOD_P].round(2).values, "cpi_other_recreation_goods": cpi["他の教養娯楽用品"].values, "cpi_all": cpi["総合"].values})
ts.to_csv(RES / "total_by_year.csv", index=False)
for y in (2005, 2019, 2025):
    M[f"nominal_total_{y}"] = int(nom[y]); M[f"nominal_food_{y}"] = int(food_n[y]); M[f"nominal_goods_services_{y}"] = int(gs_n[y])
M["nominal_growth_2005_2019"] = r(nom[2019] / nom[2005] - 1); M["nominal_growth_2019_2025"] = r(nom[2025] / nom[2019] - 1)
M["nominal_growth_2005_2025"] = r(nom[2025] / nom[2005] - 1)
M["real_growth_2005_2019_long"] = r(rl[2019] / rl[2005] - 1); M["real_growth_2019_2025_long"] = r(rl[2025] / rl[2019] - 1)
M["real_growth_2019_2025_main"] = r(rm[2025] / rm[2019] - 1)
M["H1"] = "支持" if M["real_growth_2005_2019_long"] >= 0.20 else "外れ"
M["food_nominal_growth_2019_2025"] = r(food_n[2025] / food_n[2019] - 1); M["food_real_growth_2019_2025"] = r(food_r[2025] / food_r[2019] - 1)
M["food_price_growth_2019_2025"] = r(cpi.loc[2025, FOOD_P] / cpi.loc[2019, FOOD_P] - 1)
M["food_price_growth_2005_2019"] = r(cpi.loc[2019, FOOD_P] / cpi.loc[2005, FOOD_P] - 1)
M["food_real_growth_2005_2019"] = r((food_n[2019] / cpi.loc[2019, FOOD_P]) / (food_n[2005] / cpi.loc[2005, FOOD_P]) - 1)
# 名目の伸び（対数）のうち物価の分
M["price_share_of_nominal_growth_2019_2025_main"] = r(1 - np.log(rm[2025] / rm[2019]) / np.log(nom[2025] / nom[2019]))
M["price_share_of_food_growth_2019_2025"] = r(np.log(cpi.loc[2025, FOOD_P] / cpi.loc[2019, FOOD_P]) / np.log(food_n[2025] / food_n[2019]))
M["price_share_of_nominal_growth_2005_2019_long"] = r(1 - np.log(rl[2019] / rl[2005]) / np.log(nom[2019] / nom[2005]))
M["share_of_consumption_note"] = "消費支出に占める割合は計算していない"
# 品目（2015年から、2019→2025）
rows = []
for it in ["ペットフード", "ペット用品", "ペット関連サービス"]:
    s = x[(x.table == "age") & (x.group == "平均") & (x["item"] == it)].set_index("year")
    rows.append(dict(item=it, nominal_2019=int(s.amount[2019]), nominal_2025=int(s.amount[2025]), nominal_growth=r(s.amount[2025] / s.amount[2019] - 1),
                     real_growth=r(s.real_main[2025] / s.real_main[2019] - 1), real_growth_avg2=r(s.real_main.loc[2024:2025].mean() / s.real_main.loc[2018:2019].mean() - 1),
                     freq_2019=float(s.freq[2019]), freq_2025=float(s.freq[2025]), freq_growth=r(s.freq[2025] / s.freq[2019] - 1),
                     per_purchase_2019=round(s.amount[2019] / s.freq[2019] * 100, 1), per_purchase_2025=round(s.amount[2025] / s.freq[2025] * 100, 1)))
items = pd.DataFrame(rows); items["per_purchase_growth"] = (items.per_purchase_2025 / items.per_purchase_2019 - 1).round(4)
items.to_csv(RES / "items.csv", index=False)
M["items"] = {row["item"]: {k: row[k] for k in ["nominal_growth", "real_growth", "freq_growth", "per_purchase_growth"]} for row in items.to_dict("records")}
# H2：ペットフードの回数と1回の額
f = x[(x.table == "age") & (x.group == "平均") & (x["item"] == "ペットフード")].set_index("year")
pp = f.amount / f.freq * 100
M["food_freq_2005"] = float(f.freq[2005]); M["food_freq_2019"] = float(f.freq[2019]); M["food_freq_2025"] = float(f.freq[2025])
M["food_freq_growth_2019_2025"] = r(f.freq[2025] / f.freq[2019] - 1); M["food_freq_growth_2005_2019"] = r(f.freq[2019] / f.freq[2005] - 1)
M["food_per_purchase_2019"] = round(float(pp[2019]), 1); M["food_per_purchase_2025"] = round(float(pp[2025]), 1)
M["food_per_purchase_growth_2019_2025"] = r(pp[2025] / pp[2019] - 1)
M["food_per_purchase_real_growth_2019_2025"] = r((pp[2025] / cpi.loc[2025, FOOD_P]) / (pp[2019] / cpi.loc[2019, FOOD_P]) - 1)
L = np.log(f.amount[2025] / f.amount[2019])
M["food_log_share_freq"] = r(np.log(f.freq[2025] / f.freq[2019]) / L)
M["food_log_share_price"] = r(np.log(cpi.loc[2025, FOOD_P] / cpi.loc[2019, FOOD_P]) / L)
M["food_log_share_real_per_purchase"] = r(1 - M["food_log_share_freq"] - M["food_log_share_price"])
M["H2"] = "支持" if (M["food_freq_growth_2019_2025"] < 0.10 and M["food_log_share_freq"] < 0.5) else "外れ"
fq = pd.DataFrame({"year": f.index, "food_freq_per100": f.freq.values, "food_per_purchase_yen": pp.round(1).values,
                   "food_per_purchase_real": (pp / cpi[FOOD_P] * 100).round(1).values})
fq.to_csv(RES / "food_freq.csv", index=False)
# H3：年齢の寄与（実質 main、2019→2025）
def age_contrib(col="real_main", y0=2019, y1=2025):
    out = {}
    for g in AGES:
        v0 = total("age", g, col)[y0] if not isinstance(y0, list) else None
        out[g] = (w[("age", y1, g)] * total("age", g, col)[y1] - w[("age", y0, g)] * total("age", g, col)[y0]) / 10000
    return out
ac = age_contrib(); tot_ch = sum(ac.values())
M["age_contrib_yen"] = {k: round(float(v), 1) for k, v in ac.items()}; M["age_contrib_total_yen"] = round(float(tot_ch), 1)
M["age_contrib_check_published_change"] = round(float(rm[2025] - rm[2019]), 1)
M["share_contrib_60plus"] = r((ac["60～69歳"] + ac["70歳以上"]) / tot_ch)
M["H3"] = "支持" if M["share_contrib_60plus"] >= 0.5 else "外れ"
# 世帯の割合の変化の分と、1世帯あたりの額の変化の分に分ける（70歳以上）
for g in ["60～69歳", "70歳以上"]:
    s0, s1 = total("age", g, "real_main")[2019], total("age", g, "real_main")[2025]
    w0, w1 = w[("age", 2019, g)], w[("age", 2025, g)]
    M[f"contrib_{g}_from_share"] = round(float((w1 - w0) * s0 / 10000), 1); M[f"contrib_{g}_from_spending"] = round(float(w1 * (s1 - s0) / 10000), 1)
grows = []
for table, groups in [("age", AGES), ("income", QS)]:
    for g in groups:
        s = total(table, g, "real_main"); sn = total(table, g)
        grows.append(dict(table=table, group=g, nominal_2019=int(sn[2019]), nominal_2025=int(sn[2025]), real_growth=r(s[2025] / s[2019] - 1),
                          real_growth_2024=r(s[2024] / s[2019] - 1), real_growth_avg2=r(s.loc[2024:2025].mean() / s.loc[2018:2019].mean() - 1),
                          real_growth_class=r(total(table, g, "real_class")[2025] / total(table, g, "real_class")[2019] - 1),
                          real_growth_per_person=r((s[2025] / hh[(table, 2025, g)]) / (s[2019] / hh[(table, 2019, g)]) - 1),
                          real_growth_food_goods=r(total(table, g, "real_main", items=["ペットフード", "ペット用品"])[2025] / total(table, g, "real_main", items=["ペットフード", "ペット用品"])[2019] - 1),
                          real_growth_2019_2018=r(s[2019] / s[2018] - 1),
                          weight_2019=float(w[(table, 2019, g)]), weight_2025=float(w[(table, 2025, g)])))
G = pd.DataFrame(grows); G.to_csv(RES / "groups.csv", index=False)
gi = G.set_index(["table", "group"])
M["real_growth_age"] = dict(zip(AGES, gi.loc["age"].real_growth.astype(float)))
M["real_growth_income"] = dict(zip(QS, gi.loc["income"].real_growth.astype(float)))
M["H4_gap_pt"] = r((gi.loc[("income", "Ⅴ"), "real_growth"] - gi.loc[("income", "Ⅰ"), "real_growth"]) * 100)
M["H4"] = "支持" if M["H4_gap_pt"] >= 10 else "外れ"
M["normal_2019_2018_income_range_pt"] = r((gi.loc["income"].real_growth_2019_2018.max() - gi.loc["income"].real_growth_2019_2018.min()) * 100)
M["normal_2019_2018_age_range_pt"] = r((gi.loc["age"].real_growth_2019_2018.max() - gi.loc["age"].real_growth_2019_2018.min()) * 100)
M["nominal_level_2025_age"] = dict(zip(AGES, gi.loc["age"].nominal_2025.astype(int)))
M["nominal_level_2025_income"] = dict(zip(QS, gi.loc["income"].nominal_2025.astype(int)))
# 頑健性
rob = []
def add(c, v, val):
    rob.append(dict(check=c, variant=v, value=r(val)))
rm_c = total("age", "平均", "real_class"); rm_a = total("age", "平均", "real_all")
add("2019→2025 実質の伸び（全体）", "基本（品目ごとの物価）", M["real_growth_2019_2025_main"])
add("2019→2025 実質の伸び（全体）", "他の教養娯楽用品（類）の物価で一括", rm_c[2025] / rm_c[2019] - 1)
add("2019→2025 実質の伸び（全体）", "総合の物価で一括", rm_a[2025] / rm_a[2019] - 1)
add("2019→2025 実質の伸び（全体）", "2年平均どうし（2024〜25÷2018〜19）", rm.loc[2024:2025].mean() / rm.loc[2018:2019].mean() - 1)
add("2019→2025 実質の伸び（全体）", "2024÷2019", rm[2024] / rm[2019] - 1)
add("2019→2025 実質の伸び（全体）", "1人あたり", (rm[2025] / hh[("age", 2025, "平均")]) / (rm[2019] / hh[("age", 2019, "平均")]) - 1)
add("2019→2025 実質の伸び（全体）", "サービスを除く（フード＋用品）", total("age", "平均", "real_main", items=["ペットフード", "ペット用品"])[2025] / total("age", "平均", "real_main", items=["ペットフード", "ペット用品"])[2019] - 1)
add("H1 2005→2019 実質の伸び", "基本（フード以外は他の教養娯楽用品で割り引き）", M["real_growth_2005_2019_long"])
add("H1 2005→2019 実質の伸び", "総合の物価で一括", rm_a[2019] / rm_a[2005] - 1)
add("H1 2005→2019 実質の伸び", "1人あたり", (rl[2019] / hh[("age", 2019, "平均")]) / (rl[2005] / hh[("age", 2005, "平均")]) - 1)
add("H1 2005→2019 実質の伸び", "3年平均どうし（2017〜19÷2005〜07）", rl.loc[2017:2019].mean() / rl.loc[2005:2007].mean() - 1)
def share60(col, y0=2019, y1=2025):
    a = age_contrib(col, y0, y1); return (a["60～69歳"] + a["70歳以上"]) / sum(a.values())
add("H3 60歳以上の寄与の割合", "基本", M["share_contrib_60plus"])
add("H3 60歳以上の寄与の割合", "他の教養娯楽用品で一括", share60("real_class"))
add("H3 60歳以上の寄与の割合", "名目", share60("amount"))
add("H3 60歳以上の寄与の割合", "2024年まで", share60("real_main", 2019, 2024))
add("H3 60歳以上の寄与の割合", "2018年から", share60("real_main", 2018, 2025))
# 計画の基準での判定（H3_plan_rule）は残し、確かめ方で基準の0.5をまたぐときは「判定できず」とする（独立レビューで追加）
M["H3_plan_rule"] = M["H3"]
_h3 = [q["value"] for q in rob if q["check"] == "H3 60歳以上の寄与の割合"]
if min(_h3) < 0.5 <= max(_h3):
    M["H3"] = "判定できず"
for col, lab in [("real_growth_class", "他の教養娯楽用品で一括"), ("real_growth_avg2", "2年平均どうし"), ("real_growth_2024", "2024÷2019"),
                 ("real_growth_per_person", "1人あたり"), ("real_growth_food_goods", "サービスを除く")]:
    add("H4 第V−第I五分位（ポイント）", lab, (gi.loc[("income", "Ⅴ"), col] - gi.loc[("income", "Ⅰ"), col]) * 100)
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
M["robustness"] = {f"{q['check']}｜{q['variant']}": q["value"] for q in rob}
(RES / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(M, ensure_ascii=False, indent=1)); print(items.to_string()); print(G.to_string())
