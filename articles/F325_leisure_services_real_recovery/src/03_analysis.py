"""03 分析（オフライン）：レジャー・娯楽サービス10品目の支出を物価で割り引き、2025年÷2019年の「実質の戻り率」を
品目・世帯主の年齢・年間収入五分位ごとに出す。仮説 H1〜H4 の判定と頑健性。出力：results/main.json と CSV"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "leisure_items.csv")
cpi = pd.read_csv(DATA / "cpi_leisure.csv").set_index("year")
ITEMS = ["宿泊料", "国内パック旅行費", "外国パック旅行費", "映画・演劇等入場料", "スポーツ観覧料", "スポーツクラブ使用料",
         "他のスポーツ施設使用料", "文化施設入場料", "遊園地入場・乗物代", "他の入場・ゲーム代"]
cpi["映画・演劇"] = (cpi["映画観覧料"] + cpi["演劇観覧料"]) / 2
DEF = {"宿泊料": "宿泊料", "国内パック旅行費": "宿泊料", "外国パック旅行費": "外国パック旅行費", "映画・演劇等入場料": "映画・演劇",
       "スポーツ観覧料": "プロ野球観覧料", "スポーツクラブ使用料": "フィットネスクラブ使用料", "他のスポーツ施設使用料": "入場・観覧・ゲーム代",
       "文化施設入場料": "文化施設入場料", "遊園地入場・乗物代": "テーマパーク入場料", "他の入場・ゲーム代": "入場・観覧・ゲーム代"}
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
QS = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ"]
r = lambda x: float(round(x, 4))
it = d[d.item.isin(ITEMS)].copy()
w = d[d.code == "hh_weight"].set_index(["table", "year", "group"]).amount
hh = d[d.code == "hh_size"].set_index(["table", "year", "group"]).amount

def real(df, deflate="item"):
    x = df.copy()
    defl = x.item.map(DEF) if deflate == "item" else pd.Series("教養娯楽サービス", index=x.index)
    x["real"] = [a / cpi.loc[y, c] * 100 for a, y, c in zip(x.amount, x.year, defl)]  # 2025年の価格で数えた額
    return x

R = real(it); Rc = real(it, "class")
M = {}
def tot(x, table, group, items=ITEMS, col="real"):
    return x[(x.table == table) & (x.group == group) & x.item.isin(items)].groupby("year")[col].sum()

# --- 全体の推移 ---
nom = tot(R, "age", "平均", col="amount"); re_ = tot(R, "age", "平均")
ts = pd.DataFrame({"year": nom.index, "nominal": nom.values, "real_2025prices": re_.round(0).values,
                   "nominal_vs_2019": (nom / nom[2019]).round(4).values, "real_vs_2019": (re_ / re_[2019]).round(4).values})
ts.to_csv(RES / "total_by_year.csv", index=False)
M["nominal_2019"] = int(nom[2019]); M["nominal_2025"] = int(nom[2025])
M["real_2019_in_2025prices"] = int(round(re_[2019])); M["real_2025"] = int(round(re_[2025]))
M["R_nominal_2025"] = r(nom[2025] / nom[2019]); M["R_real_2025"] = r(re_[2025] / re_[2019]); M["R_real_2024"] = r(re_[2024] / re_[2019])
M["price_rise_implied"] = r(M["R_nominal_2025"] / M["R_real_2025"])
M["H1"] = "支持" if M["R_real_2025"] < 0.95 else "外れ"
yoy = (re_.loc[2015:2019].pct_change().dropna())
M["normal_yoy_sd_2015_2019"] = r(yoy.std())

# --- 品目 ---
rows = []
for name in ITEMS:
    a = R[(R.table == "age") & (R.group == "平均") & (R.item == name)].set_index("year")
    c = Rc[(Rc.table == "age") & (Rc.group == "平均") & (Rc.item == name)].set_index("year")
    rows.append(dict(item=name, nominal_2019=int(a.amount[2019]), nominal_2025=int(a.amount[2025]),
                     R_nominal=r(a.amount[2025] / a.amount[2019]), price_ratio=r(cpi.loc[2025, DEF[name]] / cpi.loc[2019, DEF[name]]),
                     R_real=r(a.real[2025] / a.real[2019]), R_real_2024=r(a.real[2024] / a.real[2019]),
                     R_real_classdefl=r(c.real[2025] / c.real[2019]), R_real_base1719=r(a.real[2025] / a.real.loc[2017:2019].mean()),
                     R_real_avg2=r(a.real.loc[2024:2025].mean() / a.real.loc[2018:2019].mean()),
                     share_2019=r(a.amount[2019] / nom[2019])))
items_t = pd.DataFrame(rows)
items_t.to_csv(RES / "items.csv", index=False)
M["R_real_item"] = dict(zip(items_t.item, items_t.R_real.astype(float)))
M["R_nominal_item"] = dict(zip(items_t.item, items_t.R_nominal.astype(float)))
M["price_ratio_item"] = dict(zip(items_t.item, items_t.price_ratio.astype(float)))
M["H2_foreign_lt_0.6"] = bool(M["R_real_item"]["外国パック旅行費"] < 0.6)
M["H2_lodging_ge_0.9"] = bool(M["R_real_item"]["宿泊料"] >= 0.9)
M["H2_amusement_ge_0.9"] = bool(M["R_real_item"]["遊園地入場・乗物代"] >= 0.9)
M["H2"] = "支持" if (M["H2_foreign_lt_0.6"] and M["H2_lodging_ge_0.9"] and M["H2_amusement_ge_0.9"]) else "一部外れ"
# 減った分（2019年→2025年、実質）の品目ごとの寄与
chg = {n: float(R[(R.table == "age") & (R.group == "平均") & (R.item == n)].set_index("year").real.pipe(lambda s: s[2025] - s[2019])) for n in ITEMS}
M["real_change_yen_by_item"] = {k: int(round(v)) for k, v in chg.items()}
M["real_change_yen_total"] = int(round(sum(chg.values())))
ex = [n for n in ITEMS if n != "外国パック旅行費"]
M["R_real_ex_foreign"] = r(tot(R, "age", "平均", ex)[2025] / tot(R, "age", "平均", ex)[2019])
trav = ["宿泊料", "国内パック旅行費", "外国パック旅行費"]; ent = [n for n in ITEMS if n not in trav]
M["R_real_travel3"] = r(tot(R, "age", "平均", trav)[2025] / tot(R, "age", "平均", trav)[2019])
M["R_real_entertainment7"] = r(tot(R, "age", "平均", ent)[2025] / tot(R, "age", "平均", ent)[2019])
M["R_real_item_avg2"] = dict(zip(items_t.item, items_t.R_real_avg2.astype(float)))
M["R_real_travel3_classdefl"] = r(tot(Rc, "age", "平均", trav)[2025] / tot(Rc, "age", "平均", trav)[2019])
M["R_real_entertainment7_classdefl"] = r(tot(Rc, "age", "平均", ent)[2025] / tot(Rc, "age", "平均", ent)[2019])
M["R_real_travel3_avg2"] = r(tot(R, "age", "平均", trav).loc[2024:2025].mean() / tot(R, "age", "平均", trav).loc[2018:2019].mean())
M["R_real_entertainment7_avg2"] = r(tot(R, "age", "平均", ent).loc[2024:2025].mean() / tot(R, "age", "平均", ent).loc[2018:2019].mean())
M["R_nominal_travel3"] = r(tot(R, "age", "平均", trav, col="amount")[2025] / tot(R, "age", "平均", trav, col="amount")[2019])
M["R_nominal_entertainment7"] = r(tot(R, "age", "平均", ent, col="amount")[2025] / tot(R, "age", "平均", ent, col="amount")[2019])
M["R_real_domestic_travel2"] = r(tot(R, "age", "平均", ["宿泊料", "国内パック旅行費"])[2025] / tot(R, "age", "平均", ["宿泊料", "国内パック旅行費"])[2019])

# --- 年齢・収入 ---
def grp_ratio(x, table, groups, y1=2025, y0=2019, items=ITEMS, per_person=False):
    out = {}
    for g in groups:
        s = tot(x, table, g, items)
        if per_person:
            s = s / hh.xs((table, g), level=["table", "group"]) if False else s / pd.Series({y: hh[(table, y, g)] for y in s.index})
        out[g] = (s[y1] / (s[y0] if not isinstance(y0, list) else s.loc[y0].mean()))
    return out
def pooled(x, groups, y1=2025, y0=2019, items=ITEMS):
    """年齢の区分をまとめる：世帯数分布で重みをつけた平均の額の比"""
    def val(y):
        return sum(tot(x, "age", g, items)[y] * w[("age", y, g)] for g in groups) / sum(w[("age", y, g)] for g in groups)
    return val(y1) / (val(y0) if not isinstance(y0, list) else np.mean([val(k) for k in y0]))
age_r = grp_ratio(R, "age", AGES); inc_r = grp_ratio(R, "income", QS)
rows = []
for table, groups in [("age", AGES), ("income", QS)]:
    for g in groups:
        s = tot(R, table, g); sn = tot(R, table, g, col="amount")
        rows.append(dict(table=table, group=g, real_2019=int(round(s[2019])), real_2025=int(round(s[2025])), nominal_2025=int(sn[2025]),
                         R_real=r(s[2025] / s[2019]), R_real_2024=r(s[2024] / s[2019]), R_real_base1719=r(s[2025] / s.loc[2017:2019].mean()),
                         R_real_classdefl=r(tot(Rc, table, g)[2025] / tot(Rc, table, g)[2019]),
                         R_real_ex_foreign=r(tot(R, table, g, ex)[2025] / tot(R, table, g, ex)[2019]),
                         R_real_per_person=r((s[2025] / hh[(table, 2025, g)]) / (s[2019] / hh[(table, 2019, g)])),
                         R_real_2019_2018=r(s[2019] / s[2018])))
grp_t = pd.DataFrame(rows); grp_t.to_csv(RES / "groups.csv", index=False)
M["R_real_age"] = {k: r(v) for k, v in age_r.items()}; M["R_real_income"] = {k: r(v) for k, v in inc_r.items()}
young, old = ["29歳以下", "30～39歳"], ["60～69歳", "70歳以上"]
def h3(y1=2025, y0=2019, x=R, items=ITEMS):
    return (pooled(x, young, y1, y0, items) - pooled(x, old, y1, y0, items)) * 100
M["R_real_under40"] = r(pooled(R, young)); M["R_real_60plus"] = r(pooled(R, old))
M["H3_gap_pt"] = r(h3()); M["H3"] = "支持" if M["H3_gap_pt"] >= 10 else "外れ"
M["H4_gap_pt"] = r((inc_r["Ⅴ"] - inc_r["Ⅰ"]) * 100); M["H4"] = "支持" if M["H4_gap_pt"] >= 10 else "外れ"
gi = grp_t.set_index(["table", "group"])
M["normal_2019_2018_age_range_pt"] = r((gi.loc["age"].R_real_2019_2018.max() - gi.loc["age"].R_real_2019_2018.min()) * 100)
M["normal_2019_2018_income_range_pt"] = r((gi.loc["income"].R_real_2019_2018.max() - gi.loc["income"].R_real_2019_2018.min()) * 100)

# --- 頑健性 ---
rob = []
def add(check, variant, val):
    rob.append(dict(check=check, variant=variant, value=r(val)))
add("H1 全体の実質の戻り率", "基本（品目ごとの物価で割り引き、2025÷2019）", M["R_real_2025"])
add("H1 全体の実質の戻り率", "教養娯楽サービスの物価で一括に割り引き", tot(Rc, "age", "平均")[2025] / tot(Rc, "age", "平均")[2019])
add("H1 全体の実質の戻り率", "基準を2017〜19年平均", re_[2025] / re_.loc[2017:2019].mean())
add("H1 全体の実質の戻り率", "2024÷2019", M["R_real_2024"])
add("H1 全体の実質の戻り率", "外国パック旅行費を除く", M["R_real_ex_foreign"])
add("H1 全体の実質の戻り率", "2年平均どうし（2024〜25年÷2018〜19年）", re_.loc[2024:2025].mean() / re_.loc[2018:2019].mean())
add("H1 全体の実質の戻り率", "1人あたり（世帯人員で割る）", (re_[2025] / hh[("age", 2025, "平均")]) / (re_[2019] / hh[("age", 2019, "平均")]))
add("H3 40歳未満−60歳以上（ポイント）", "基本", M["H3_gap_pt"])
add("H3 40歳未満−60歳以上（ポイント）", "教養娯楽サービスの物価で一括", h3(x=Rc))
add("H3 40歳未満−60歳以上（ポイント）", "基準を2017〜19年平均", h3(y0=[2017, 2018, 2019]))
add("H3 40歳未満−60歳以上（ポイント）", "2024÷2019", h3(y1=2024))
add("H3 40歳未満−60歳以上（ポイント）", "外国パック旅行費を除く", h3(items=ex))
def h4(col):
    return (gi.loc[("income", "Ⅴ"), col] - gi.loc[("income", "Ⅰ"), col]) * 100
add("H4 第V五分位−第I五分位（ポイント）", "基本", M["H4_gap_pt"])
for col, lab in [("R_real_classdefl", "教養娯楽サービスの物価で一括"), ("R_real_base1719", "基準を2017〜19年平均"), ("R_real_2024", "2024÷2019"),
                 ("R_real_ex_foreign", "外国パック旅行費を除く"), ("R_real_per_person", "1人あたり")]:
    add("H4 第V五分位−第I五分位（ポイント）", lab, h4(col))
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
M["robustness"] = {f"{x['check']}｜{x['variant']}": x["value"] for x in rob}
(RES / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(M, ensure_ascii=False, indent=1)); print(items_t.to_string()); print(grp_t.to_string())
