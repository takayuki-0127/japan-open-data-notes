"""F281 03 分析：計画の目標と実績の差を、分子・分母と品目に分ける（H1〜H5）と頑健性。

出力：results/main.json、results/A_h27_items.csv、results/B_plans_gap.csv、results/C_production_achievement.csv、
      results/D_feed.csv、results/E_robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(281)

series = pd.read_csv(P / "series_long.csv")
ssr = pd.read_csv(P / "ssr_series.csv")
maff = pd.read_csv(P / "maff_item_kcal_2025.csv").set_index("item")
plans = pd.read_csv(ROOT / "data" / "plans.csv").set_index("plan")
prodt = pd.read_csv(ROOT / "data" / "plans_production.csv").set_index("item")
h27 = pd.read_csv(ROOT / "data" / "h27_consumption.csv").set_index("item")
FBS = {2025: pd.read_csv(P / "fbs_items_2025.csv").set_index("item"), 2024: pd.read_csv(P / "fbs_items_2024.csv").set_index("item")}


def ssr_of(ind, fy):
    v = ssr[(ssr.indicator == ind) & (ssr.fy == fy)]["value"]
    return float(v.iloc[0]) if len(v) else np.nan


def ser(item, var, fy):
    v = series[(series.item == item) & (series["var"] == var) & (series.fy == fy)]["value"]
    return float(v.iloc[0]) if len(v) else np.nan


S_TOT = {fy: ser("合計", "kcal", fy) for fy in range(1990, 2026)}
for fy in range(1990, 2026):
    if np.isnan(S_TOT[fy]):
        # 累年表の合計行の名前を探す
        v = series[(series["var"] == "kcal") & (series.fy == fy) & (series.item.str.contains("合計|計$", regex=True))]["value"]
        S_TOT[fy] = float(v.max()) if len(v) else np.nan
S_TOT[2025] = 2237.4


def split(Na, Sa, Nt, St):
    """実績−目標（ポイント）を分子の分と分母の分に分ける（2つの順番の平均＝正確に足し合う）。"""
    num = (Na - Nt) * 0.5 * (1 / Sa + 1 / St) * 100
    den = 0.5 * (Na + Nt) * (1 / Sa - 1 / St) * 100
    return num, den, (Na / Sa - Nt / St) * 100


# ---------------- H1：2015年計画（2025年度）全体 ----------------
Nt, St = plans.loc["H27", "N_target"], plans.loc["H27", "S_target"]
Na, Sa = maff.loc["合計", "N_2025"], 2237.4
num, den, tot = split(Na, Sa, Nt, St)
H1 = {"N_target": Nt, "S_target": St, "N_actual": Na, "S_actual": Sa, "ssr_target": Nt / St * 100, "ssr_actual": Na / Sa * 100,
      "gap_pt": tot, "numerator_pt": num, "denominator_pt": den,
      "order_num_first": {"num": (Na - Nt) / Sa * 100, "den": Nt * (1 / Sa - 1 / St) * 100},
      "order_den_first": {"num": (Na - Nt) / St * 100, "den": Na * (1 / Sa - 1 / St) * 100}}
H1["verdict"] = "支持" if (den > 0 and num < tot) else "外れ"
# R1：2024・2025年度の平均（どちらも分子が公表されている年度）
Na2, Sa2 = (maff.loc["合計", "N_2025"] + maff.loc["合計", "N_2024"]) / 2, (2237.4 + 2248.0) / 2
H1["R1_2yr"] = dict(zip(["numerator_pt", "denominator_pt", "gap_pt"], split(Na2, Sa2, Nt, St)))

# ---------------- H2：品目に分ける ----------------
LIVE = ["生乳", "牛肉", "豚肉", "鶏肉", "鶏卵"]
SSR_IND = {"米": "米", "小麦": "小麦", "大麦・はだか麦": "大麦・はだか麦", "大豆": "うち食用", "かんしょ": "かんしょ", "ばれいしょ": "ばれいしょ",
           "野菜": "野菜", "果実": "果実", "生乳": "牛乳・乳製品", "牛肉": "牛肉", "豚肉": "豚肉", "鶏肉": "鶏肉", "鶏卵": "鶏卵", "魚介類": "うち食用"}
MAFF_GROUP = {"米": "米", "小麦": "小麦", "大麦・はだか麦": "その他", "大豆": "大豆", "かんしょ": "いも類", "ばれいしょ": "いも類", "野菜": "野菜",
              "果実": "果実", "生乳": "畜産物", "牛肉": "畜産物", "豚肉": "畜産物", "鶏肉": "畜産物", "鶏卵": "畜産物", "魚介類": "魚介類"}


def ssr_item(item, fy):
    ind = SSR_IND[item]
    if item == "大豆":  # 大豆の「うち食用」は豆類_大豆の下の行
        sub = ssr[(ssr.fy == fy) & (ssr.indicator == "うち食用")]["value"].tolist()
        return sub[0]
    if item == "魚介類":
        sub = ssr[(ssr.fy == fy) & (ssr.indicator == "うち食用")]["value"].tolist()
        return sub[1]
    return ssr_of(ind, fy)


def ssr_feed(item, fy):
    ind = SSR_IND[item] + "（飼料自給率考慮）"
    return ssr_of(ind, fy)


def fbs_val(fbs, item, col):
    if item == "大麦・はだか麦":
        return fbs.loc["大麦", col] + fbs.loc["はだか麦", col]
    if item == "生乳":
        return fbs.loc["牛乳及び乳製品", col]
    return fbs.loc[item, col]


def h27_items(fy=2025, calibrate=True, feed_mode="item", rice_mode="official", feed_target=40.0):
    fbs = FBS[fy]
    feed_a = ssr_of("飼料自給率", fy)
    rows = []
    for item, r in h27.iterrows():
        S_a = fbs_val(fbs, item, "kcal")
        kg_a = fbs_val(fbs, item, "kg")
        S_t = S_a * r["kg_2025t"] / kg_a
        ssr_t = r["prod_2025t"] / r["use_2025t"] * 100
        if item in LIVE:
            w_a, f_a = ssr_item(item, fy), ssr_feed(item, fy)
            ssr_a = f_a
            if feed_mode == "item":  # 品目ごとの「飼料を考えた自給率 ÷ 重量の自給率」を目標の飼料自給率で伸ばす
                ssr_t_eff = ssr_t * (f_a / w_a) * (feed_target / feed_a)
            else:  # 一律：重量の自給率 × 飼料自給率
                ssr_a = w_a * feed_a / 100
                ssr_t_eff = ssr_t * feed_target / 100
        elif item == "大豆":
            # 計画の大豆は油用を含む全体（生産÷国内消費仕向量）。実績の国産熱量は食用の自給率で計算される。
            # 目標は「全体の自給率の比」で食用の自給率を伸ばす（食用の自給率 × 目標の全体自給率 ÷ 実績の全体自給率）。
            food_a, total_a = ssr_item("大豆", fy), ssr_of("大豆", fy)
            ssr_a = food_a
            ssr_t_eff = ssr_t * food_a / total_a
        else:
            ssr_a = ssr_item(item, fy)
            if item == "米" and rice_mode == "production":
                ssr_a = fbs_val(fbs, item, "prod") / fbs_val(fbs, item, "use") * 100
            ssr_t_eff = ssr_t
        N_a_rec = S_a * ssr_a / 100
        rows.append({"item": item, "S_a": S_a, "S_t": S_t, "kg_a": kg_a, "kg_t": r["kg_2025t"], "ssr_a": ssr_a, "ssr_t": ssr_t,
                     "ssr_t_eff": ssr_t_eff, "N_a_rec": N_a_rec, "N_t_rec": S_t * ssr_t_eff / 100})
    df = pd.DataFrame(rows).set_index("item")
    col = f"N_{fy}"
    if calibrate:  # 農林水産省の品目別の国産熱量に合わせる（同じグループの中は組み立てた値の比で配る）
        df["N_a"] = np.nan
        for g, sub in df.groupby(df.index.map(MAFF_GROUP)):
            if g == "その他":
                df.loc[sub.index, "N_a"] = sub["N_a_rec"]
                continue
            df.loc[sub.index, "N_a"] = sub["N_a_rec"] / sub["N_a_rec"].sum() * maff.loc[g, col]
        df["N_t"] = df["N_a"] * df["N_t_rec"] / df["N_a_rec"]
    else:
        df["N_a"], df["N_t"] = df["N_a_rec"], df["N_t_rec"]
    return df, feed_a


def decompose(df, Na, Sa, Nt, St):
    Nt_rec = Na + (df["N_t"] - df["N_a"]).sum()
    St_rec = Sa + (df["S_t"] - df["S_a"]).sum()
    k_num, k_den = 0.5 * (1 / Sa + 1 / St) * 100, 0.5 * (Na + Nt) / (Sa * St) * 100
    out = df.copy()
    out["shortfall_kcal"] = out["N_t"] - out["N_a"]
    out["num_pt"] = (out["N_a"] - out["N_t"]) * k_num
    out["den_pt"] = (out["S_t"] - out["S_a"]) * k_den
    other = pd.DataFrame([{"shortfall_kcal": Nt - Nt_rec, "num_pt": (Nt_rec - Nt) * k_num, "den_pt": (St - St_rec) * k_den}],
                         index=["表にない品目・換算の差"])
    out = pd.concat([out, other])
    out["total_pt"] = out["num_pt"] + out["den_pt"]
    return out, Nt_rec, St_rec


items, feed_a = h27_items()
A, Nt_rec, St_rec = decompose(items, Na, Sa, Nt, St)
A.to_csv(RES / "A_h27_items.csv")
pos = A.drop(index="表にない品目・換算の差")["shortfall_kcal"].clip(lower=0)
share = lambda names: float(pos[[n for n in names if n in pos.index]].sum() / pos.sum())
live_fish = share(LIVE + ["魚介類"])
rice = share(["米"])
# 畜産物の不足を「生産」と「飼料自給率」に分ける
items_nofeed, _ = h27_items(feed_target=feed_a)
live_short_total = float(A.loc[LIVE, "shortfall_kcal"].sum())
live_short_prod = float((items_nofeed.loc[LIVE, "N_t"] - items_nofeed.loc[LIVE, "N_a"]).sum())
H2 = {"N_t_rec": Nt_rec, "S_t_rec": St_rec, "N_plan": Nt, "S_plan": St, "feed_actual": feed_a,
      "shortfall_pos_sum": float(pos.sum()), "share_livestock_fish": live_fish, "share_rice": rice,
      "share_livestock": share(LIVE), "share_fish": share(["魚介類"]),
      "livestock_shortfall_kcal": live_short_total, "livestock_from_production": live_short_prod,
      "livestock_from_feed": live_short_total - live_short_prod,
      "verdict": "支持" if (live_fish > 0.5 and rice < 0.25) else "外れ"}
# 計画どおりの生産・消費だったら（品目の組み立てだけで）何%か
H2["ssr_if_all_items_on_plan"] = Nt_rec / St_rec * 100
H2["ssr_if_production_on_plan_consumption_actual"] = (Na + (A.drop(index="表にない品目・換算の差")["N_t"] * A.drop(index="表にない品目・換算の差")["S_a"] / A.drop(index="表にない品目・換算の差")["S_t"] - A.drop(index="表にない品目・換算の差")["N_a"]).sum()) / Sa * 100

# ---------------- H3：過去の計画 ----------------
rows = []
for pl in ["H12", "H17", "H22", "H27"]:
    p = plans.loc[pl]
    ty = int(p.target_fy)
    for mode in ["single", "avg3"]:
        yrs = [ty] if mode == "single" else [ty - 2, ty - 1, ty]
        ssr_a = np.mean([ssr_of("供給熱量ベースの総合食料自給率", y) for y in yrs])
        S_a = np.mean([S_TOT[y] for y in yrs])
        if pl == "H27" and mode == "single":
            N_a, ssr_a = 830.0, 830 / 2237.4 * 100
        else:
            N_a = ssr_a / 100 * S_a
        rec = {"plan": pl, "target_fy": ty, "mode": mode, "ssr_target": p.ssr_target, "ssr_actual": ssr_a, "gap_pt": ssr_a - p.ssr_target, "S_actual": S_a}
        if not np.isnan(p.S_target):
            N_t = p.N_target if not np.isnan(p.N_target) else p.ssr_target / 100 * p.S_target
            n_, d_, t_ = split(N_a, S_a, N_t, p.S_target)
            rec.update({"S_target": p.S_target, "N_target": N_t, "N_actual": N_a, "numerator_pt": n_, "denominator_pt": d_, "num_share": n_ / t_})
        rows.append(rec)
B = pd.DataFrame(rows)
B.to_csv(RES / "B_plans_gap.csv", index=False)
b1 = B[B["mode"] == "single"]
H3 = {"gaps": dict(zip(b1.plan, b1.gap_pt.round(2))), "num_share": dict(zip(b1.plan, b1.num_share.round(3))),
      "all_gap_ge5": bool((b1.gap_pt <= -5).all()), "num_ge80": bool((b1.dropna(subset=["num_share"]).num_share >= 0.8).all())}
H3["verdict"] = "支持" if (H3["all_gap_ge5"] and H3["num_ge80"]) else "外れ"
H3["avg3"] = {r.plan: {"gap_pt": round(r.gap_pt, 2), "num_share": (round(r.num_share, 3) if not np.isnan(r.get("num_share", np.nan)) else None)} for _, r in B[B["mode"] == "avg3"].iterrows()}

# ---------------- H4：目標の高さと届いた割合 ----------------
SER_ITEM = {"米": ["穀類_米"], "小麦": ["穀類_小麦"], "大麦・はだか麦": ["穀類_大麦", "穀類_はだか麦"], "大豆": ["豆類_大豆"], "かんしょ": ["いも類_かんしょ"],
            "ばれいしょ": ["いも類_ばれいしょ"], "野菜": ["野菜"], "果実": ["果実"], "生乳": ["牛乳及び乳製品"], "牛肉": ["肉類_牛肉"], "豚肉": ["肉類_豚肉"],
            "鶏肉": ["肉類_鶏肉"], "鶏卵": ["鶏卵"], "魚介類": ["魚介類"]}


def prod_actual(item, years):
    return np.mean([sum(ser(s, "prod", y) for s in SER_ITEM[item]) for y in years]) / 10  # 千トン→万トン


rows = []
for pl in ["H12", "H17", "H22", "H27"]:
    ty = int(plans.loc[pl, "target_fy"])
    for item in prodt.index:
        base, tgt = prodt.loc[item, f"{pl}_base"], prodt.loc[item, f"{pl}_target"]
        rows.append({"plan": pl, "item": item, "base": base, "target": tgt, "actual": prod_actual(item, [ty]),
                     "actual_avg3": prod_actual(item, [ty - 2, ty - 1, ty]), "target_fy": ty})
C = pd.DataFrame(rows)
C["ambition"] = C.target / C.base
C["achieve"] = C.actual / C.target
C["achieve_avg3"] = C.actual_avg3 / C.target
C["reached"] = C.achieve >= 1
C.to_csv(RES / "C_production_achievement.csv", index=False)


def spear(df, col="achieve", nperm=20000):
    rho = spearmanr(df.ambition, df[col]).correlation
    a = df[col].to_numpy()
    perm = np.array([spearmanr(df.ambition, rng.permutation(a)).correlation for _ in range(nperm)])
    return float(rho), float((np.sum(perm <= rho) + 1) / (nperm + 1)), int(len(df))


rho, p, n = spear(C)
H4 = {"spearman": rho, "p_one_sided": p, "n": n, "verdict": "支持" if rho < -0.3 else "外れ",
      "reached_share": float(C.reached.mean()), "reached_by_plan": C.groupby("plan").reached.mean().round(3).to_dict(),
      "median_achieve_by_plan": C.groupby("plan").achieve.median().round(3).to_dict(),
      "ambitious_items": C[C.ambition >= 1.1][["plan", "item", "ambition", "achieve"]].round(3).to_dict("records")}

# ---------------- H5：飼料自給率 ----------------
D = []
for pl in ["H12", "H17", "H22", "H27"]:
    ty = int(plans.loc[pl, "target_fy"])
    a = ssr_of("飼料自給率", ty)
    D.append({"plan": pl, "target_fy": ty, "feed_target": plans.loc[pl, "feed_target"], "feed_actual": a,
              "feed_actual_avg3": np.mean([ssr_of("飼料自給率", y) for y in [ty - 2, ty - 1, ty]]), "gap": a - plans.loc[pl, "feed_target"]})
D = pd.DataFrame(D)
D.to_csv(RES / "D_feed.csv", index=False)
H5 = {"gaps": dict(zip(D.plan, D.gap)), "verdict": "支持" if (D.gap <= -8).all() else "外れ"}

# ---------------- 頑健性 ----------------
rob = []
def h2_summary(tag, df_items, Na_, Sa_):
    A_, ntr, str_ = decompose(df_items, Na_, Sa_, Nt, St)
    pos_ = A_.drop(index="表にない品目・換算の差")["shortfall_kcal"].clip(lower=0)
    lf = float(pos_[LIVE + ["魚介類"]].sum() / pos_.sum())
    rc = float(pos_["米"] / pos_.sum())
    rob.append({"check": tag, "share_livestock_fish": lf, "share_rice": rc, "N_t_rec": ntr, "S_t_rec": str_,
                "unexplained_N": Nt - ntr, "unexplained_S": St - str_, "H2": "支持" if (lf > 0.5 and rc < 0.25) else "外れ"})

h2_summary("基本（2025年度・農林水産省の品目値に合わせる）", items, Na, Sa)
it24, _ = h27_items(fy=2024)
h2_summary("R2 2024年度の値で換算", it24, maff.loc["合計", "N_2024"], 2248.0)
it_u, _ = h27_items(feed_mode="uniform")
h2_summary("R3 畜産物：重量の自給率×飼料自給率で一律", it_u, Na, Sa)
it_r, _ = h27_items(rice_mode="production")
h2_summary("R4 米：国内生産量÷国内消費仕向量", it_r, Na, Sa)
it_nc, _ = h27_items(calibrate=False)
h2_summary("R6 品目値に合わせない（組み立てたまま）", it_nc, Na, Sa)
for tag, sub in [("R5 魚介類を除く", C[C.item != "魚介類"]), ("R5 牛肉・豚肉を除く", C[~C.item.isin(["牛肉", "豚肉"])]),
                 ("R5 2010年計画（平成22年）を除く", C[C.plan != "H22"])]:
    r_, p_, n_ = spear(sub, nperm=5000)
    rob.append({"check": tag, "spearman": r_, "p_one_sided": p_, "n": n_, "H4": "支持" if r_ < -0.3 else "外れ"})
r_, p_, n_ = spear(C, col="achieve_avg3", nperm=5000)
rob.append({"check": "R1 3年度平均の生産量", "spearman": r_, "p_one_sided": p_, "n": n_, "H4": "支持" if r_ < -0.3 else "外れ"})
E = pd.DataFrame(rob)
E.to_csv(RES / "E_robustness.csv", index=False)

main = {"H1": H1, "H2": H2, "H3": H3, "H4": H4, "H5": H5, "S_total_by_target_year": {y: S_TOT[y] for y in [2010, 2015, 2020, 2023, 2024, 2025]}}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=float))
pd.set_option("display.width", 200)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if not isinstance(vv, (list, dict))} if isinstance(v, dict) else v for k, v in main.items()}, ensure_ascii=False, indent=1, default=float))
print(A.round(2).to_string())
print(B.round(2).to_string())
print(C.round(3).to_string())
print(D.to_string())
print(E.round(3).to_string())
