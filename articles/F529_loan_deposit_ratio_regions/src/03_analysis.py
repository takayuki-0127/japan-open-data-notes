"""預貸率の推移と、預金・貸出の伸びへの分解（オフライン）。地域は北から南の順に並べる（悪い方からの順位は作らない）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
UNITS = ["北海道", "東北", "関東（東京を除く）", "東京", "北陸", "中部", "近畿", "中国", "四国", "九州・沖縄"]
REG = {"北海道": "北海道", "東北計": "東北", "関東計": "関東", "北陸計": "北陸", "中部計": "中部", "近畿計": "近畿", "中国計": "中国", "四国計": "四国", "九州・沖縄計": "九州・沖縄"}
PERIODS = [(1998, 2025), (1998, 2012), (2012, 2022), (2022, 2025)]

def load():
    df = pd.read_csv(ROOT / "data" / "pref_monthly.csv", dtype={"ym": str})
    df["fy"] = df.ym.str[:4].astype(int) - (df.ym.str[4:].astype(int) < 4).astype(int)
    return df

def fy_avg(df, how="mean"):
    d = df[(df.fy >= 1998) & (df.fy <= 2025)]
    if how == "march":
        d = d[d.ym.str[4:] == "03"]
    g = d.groupby(["kind", "area", "item", "fy"], sort=True).oku_yen.mean().reset_index()
    return g

def units_table(g):
    """10の地域単位（関東を東京と東京以外に分ける）× 項目 × 年度。"""
    reg = g[g.kind == "地方"].copy(); reg["unit"] = reg.area.map(REG)
    hk = g[(g.kind == "都道府県") & (g.area == "北海道")].copy(); hk["unit"] = "北海道"
    tk = g[(g.kind == "都道府県") & (g.area == "東京")].copy(); tk["unit"] = "東京"
    u = pd.concat([reg[reg.unit != "北海道"], hk, tk])
    w = u.pivot_table(index=["item", "fy"], columns="unit", values="oku_yen")
    w["関東（東京を除く）"] = w["関東"] - w["東京"]
    w = w[UNITS]
    nat = g[g.kind == "全国"].pivot_table(index=["item", "fy"], columns="area", values="oku_yen")["全国計"]
    w["全国"] = nat
    w["全国（東京を除く）"] = w["全国"] - w["東京"]
    return w

def ratio(w, num="loans", den=("deposits",)):
    d = sum(w.xs(k, level="item") for k in den)
    return w.xs(num, level="item") / d

def main():
    df = load(); g = fy_avg(df)
    w = units_table(g)
    r = ratio(w) * 100
    r.round(3).to_csv(RES / "ldr_by_region_fy.csv")
    # 都道府県
    p = g[g.kind == "都道府県"].pivot_table(index=["item", "fy"], columns="area", values="oku_yen")
    rp = (p.xs("loans", level="item") / p.xs("deposits", level="item")) * 100
    reg_of = df[df.kind == "都道府県"].drop_duplicates("area").set_index("area").region
    # 分解
    dec = []
    for a, b in PERIODS:
        for u in UNITS + ["全国"]:
            L = w.xs("loans", level="item")[u]; D = w.xs("deposits", level="item")[u]
            dec.append({"from": a, "to": b, "unit": u, "ldr_from": round(float(r.loc[a, u]), 2), "ldr_to": round(float(r.loc[b, u]), 2),
                        "ldr_change_pt": round(float(r.loc[b, u] - r.loc[a, u]), 2),
                        "dlog_loans_pct": round(float(np.log(L[b] / L[a])) * 100, 2), "dlog_deposits_pct": round(float(np.log(D[b] / D[a])) * 100, 2),
                        "dlog_ldr_pct": round(float(np.log(L[b] / L[a] / (D[b] / D[a]))) * 100, 2)})
    dec = pd.DataFrame(dec); dec.to_csv(RES / "decomposition_by_region.csv", index=False)
    # 都道府県の分散分解
    def var_dec(a, b, excl=()):
        L = p.xs("loans", level="item"); D = p.xs("deposits", level="item")
        cols = [c for c in L.columns if c not in excl]
        dl = np.log(L.loc[b, cols] / L.loc[a, cols]); dd = np.log(D.loc[b, cols] / D.loc[a, cols]); dr = dl - dd
        return {"n": len(cols), "var_ldr": float(dr.var(ddof=0)), "var_loans": float(dl.var(ddof=0)), "var_deposits": float(dd.var(ddof=0)),
                "minus2cov": float(-2 * np.cov(dl, dd, ddof=0)[0, 1]), "corr_loans_deposits": float(np.corrcoef(dl, dd)[0, 1])}
    vd = var_dec(1998, 2025)
    # 都道府県の表（北から南＝都道府県コードの順）
    pref_order = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野",
                  "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知",
                  "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
    assert sorted(pref_order) == sorted(rp.columns)
    L = p.xs("loans", level="item"); D = p.xs("deposits", level="item")
    pt = pd.DataFrame({"pref": pref_order, "region": [reg_of[x] for x in pref_order],
                       "ldr_1998": rp.loc[1998, pref_order].round(2).values, "ldr_2012": rp.loc[2012, pref_order].round(2).values,
                       "ldr_2022": rp.loc[2022, pref_order].round(2).values, "ldr_2025": rp.loc[2025, pref_order].round(2).values,
                       "dlog_loans_98_25": (np.log(L.loc[2025, pref_order] / L.loc[1998, pref_order]) * 100).round(2).values,
                       "dlog_deposits_98_25": (np.log(D.loc[2025, pref_order] / D.loc[1998, pref_order]) * 100).round(2).values})
    pt.to_csv(RES / "pref_table.csv", index=False)
    # 直近12か月（2025/10〜2026/9）
    last12 = df[(df.ym >= "202510") & (df.ym <= "202609")]
    nat12 = last12[(last12.kind == "全国")].groupby("item").oku_yen.mean()
    d98 = dec[(dec["from"] == 1998) & (dec.to == 2025)].set_index("unit")
    d22 = dec[(dec["from"] == 2022)].set_index("unit")
    others = [u for u in UNITS if u != "東京"]
    m = {
        "fy_range": [1998, 2025],
        "national_ldr": {int(y): round(float(r.loc[y, "全国"]), 2) for y in r.index},
        "national_ldr_last12": round(float(nat12["loans"] / nat12["deposits"]) * 100, 2),
        "national_ex_tokyo_ldr": {int(y): round(float(r.loc[y, "全国（東京を除く）"]), 2) for y in (1998, 2012, 2021, 2022, 2025)},
        "national_min": {"fy": int(r["全国"].idxmin()), "ldr": round(float(r["全国"].min()), 2)},
        "units_1998_2025": d98.to_dict(orient="index"),
        "units_2022_2025": d22[["ldr_from", "ldr_to", "ldr_change_pt"]].to_dict(orient="index"),
        "tokyo_change_pt": float(d98.loc["東京", "ldr_change_pt"]),
        "others_median_change_pt": float(d98.loc[others, "ldr_change_pt"].median()),
        "n_units_up_2022_2025": int((d22.loc[UNITS, "ldr_change_pt"] > 0).sum()),
        "var_decomp_1998_2025": {k: round(v, 5) for k, v in vd.items()},
        "pref_ldr_2025_range": [round(float(rp.loc[2025].min()), 1), round(float(rp.loc[2025].max()), 1)],
        "pref_ldr_1998_range": [round(float(rp.loc[1998].min()), 1), round(float(rp.loc[1998].max()), 1)],
        "n_pref_down_98_25": int((rp.loc[2025] < rp.loc[1998]).sum()),
        "n_pref_up_22_25": int((rp.loc[2025] > rp.loc[2022]).sum()),
    }
    nch = m["national_ldr"][2025] - m["national_ldr"][1998]
    m["national_change_pt"] = round(nch, 2)
    m["H1"] = "支持" if nch <= -10 else "外れ"
    m["H2"] = "支持" if m["others_median_change_pt"] < m["tokyo_change_pt"] else "外れ"
    m["H3"] = "支持" if m["n_units_up_2022_2025"] >= 5 else "外れ"
    m["H4"] = "支持" if vd["var_loans"] > vd["var_deposits"] else "外れ"

    # 頑健性
    rob = []
    def summ(rr, lab):
        ch = rr.loc[2025] - rr.loc[1998]; ch2 = rr.loc[2025] - rr.loc[2022]
        rob.append({"check": lab, "national_1998": round(float(rr.loc[1998, "全国"]), 1), "national_2025": round(float(rr.loc[2025, "全国"]), 1),
                    "tokyo_change_pt": round(float(ch["東京"]), 1), "others_median_change_pt": round(float(ch[others].median()), 1),
                    "n_units_up_2022_2025": int((ch2[UNITS] > 0).sum())})
    summ(r, "基本：貸出÷預金合計（年度平均）")
    summ(ratio(w, den=("deposits", "cd")) * 100, "R1 分母に譲渡性預金を足す")
    summ(ratio(w, den=("general",)) * 100, "R2 分母を一般預金にする（公金・金融機関預金を除く）")
    gm = fy_avg(df, how="march"); summ(ratio(units_table(gm)) * 100, "R3 3月末の残高")
    rob = pd.DataFrame(rob)
    vd4 = var_dec(1998, 2025, excl=("東京", "大阪"))
    rob["var_loans_gt_var_deposits"] = None
    rob = pd.concat([rob, pd.DataFrame([{"check": "R4 東京・大阪を除く45道府県で H4", "var_loans_gt_var_deposits": vd4["var_loans"] > vd4["var_deposits"]}])])
    rob.to_csv(RES / "robustness.csv", index=False)
    m["R4_var_decomp"] = {k: round(v, 5) for k, v in vd4.items()}
    m["robustness"] = json.loads(rob.to_json(orient="records", force_ascii=False))
    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: m[k] for k in ["H1", "H2", "H3", "H4", "national_change_pt", "national_min", "national_ldr_last12", "tokyo_change_pt", "others_median_change_pt", "n_units_up_2022_2025", "var_decomp_1998_2025", "R4_var_decomp", "pref_ldr_2025_range", "pref_ldr_1998_range", "n_pref_down_98_25", "n_pref_up_22_25"]}, ensure_ascii=False, indent=0))
    print({y: m["national_ldr"][y] for y in (1998, 2005, 2012, 2019, 2020, 2022, 2023, 2024, 2025)})
    print(dec[dec["from"].isin([1998, 2022]) & dec.to.isin([2025])].to_string())
    print(rob.to_string())

if __name__ == "__main__":
    main()
