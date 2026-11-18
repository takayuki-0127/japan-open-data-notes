"""03 分析（オフライン）：貸家と持家（ほか）の着工戸数の差の差、年ごとの差の動き、超過戸数の目安、都道府県の分布、頑健性。
出力：results/main.json, national_gap.csv, event_pref.csv, pref_did.csv, robustness.csv"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
         "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
         "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
METRO = ["埼玉県", "千葉県", "東京都", "神奈川県", "岐阜県", "静岡県", "愛知県", "三重県", "京都府", "大阪府", "兵庫県", "奈良県"]
BASE, POST, PRE_OLD = [2010, 2011, 2012], [2014, 2015, 2016, 2017], [2003, 2004, 2005, 2006]


def load():
    d = pd.read_csv(DATA / "starts_pref.csv")
    tot = d[(d.struct == "計") & (d.type == "計")].pivot_table(index=["area", "year"], columns="tenure", values="units").reset_index()
    r = d[(d.tenure == "貸家") & (d.type == "計") & d.struct.isin(["木造", "鉄骨造"])].groupby(["area", "year"]).units.sum().rename("貸家_木造鉄骨")
    tot = tot.merge(r.reset_index(), on=["area", "year"])
    tot["持家+分譲"] = tot["持家"] + tot["分譲住宅"]
    return d, tot.sort_values(["area", "year"]).reset_index(drop=True)


def gap(t, treat="貸家", ctrl="持家"):
    return np.log(t[treat]) - np.log(t[ctrl])


def did(t, treat="貸家", ctrl="持家", base=BASE, post=POST):
    g = t.assign(G=gap(t, treat, ctrl))
    return g[g.year.isin(post)].G.mean() - g[g.year.isin(base)].G.mean()


def excess(t, treat="貸家", ctrl="持家", base=BASE, years=range(2013, 2019)):
    tb = t[t.year.isin(base)]
    rb, cb = tb[treat].mean(), tb[ctrl].mean()
    s = t.set_index("year")
    cf = rb * s.loc[list(years), ctrl] / cb
    return float((s.loc[list(years), treat] - cf).sum())


def main():
    d, t = load()
    nat = t[t.area == "全国"].copy()
    prefs = t[t.area != "全国"].copy()
    m = {}
    # 全国の水準
    ns = nat.set_index("year")
    m["levels"] = {k: {"base_2010_12": round(ns.loc[BASE, k].mean(), 1), "post_2014_17": round(ns.loc[POST, k].mean(), 1),
                       "pct": round(100 * (ns.loc[POST, k].mean() / ns.loc[BASE, k].mean() - 1), 1),
                       "2025": int(ns.loc[2025, k]), "peak_year_2000_2025": int(ns.loc[2000:2025, k].idxmax()),
                       "peak_2013_2025_year": int(ns.loc[2013:2025, k].idxmax()), "peak_2013_2025": int(ns.loc[2013:2025, k].max())}
                   for k in ["貸家", "持家", "分譲住宅", "計"]}
    m["rental_share_pct"] = {str(y): round(100 * ns.loc[y, "貸家"] / ns.loc[y, "計"], 1) for y in [2010, 2011, 2012, 2016, 2017, 2025]}
    # 全国の差 G（2012年＝0）
    ng = pd.DataFrame({"year": ns.index, "G_owner": gap(ns), "G_forsale": gap(ns, ctrl="分譲住宅"), "G_ownfs": gap(ns, ctrl="持家+分譲"),
                       "rental": ns["貸家"], "owner": ns["持家"], "forsale": ns["分譲住宅"]})
    for c in ["G_owner", "G_forsale", "G_ownfs"]:
        ng[c + "_rel2012"] = ng[c] - ng.loc[ng.year == 2012, c].iloc[0]
    ng = ng[ng.year >= 2000].round(5)
    ng.to_csv(RES / "national_gap.csv", index=False)
    # H1：全国の差の差
    d_nat = did(nat)
    m["did_national"] = round(d_nat, 4)
    m["did_national_pct"] = round(100 * (np.exp(d_nat) - 1), 1)
    m["excess_units_2013_2018_vs_owner"] = round(excess(nat))
    m["rental_units_2013_2018"] = int(ns.loc[2013:2018, "貸家"].sum())
    # H3：見直し前の動き（2003〜06年 vs 2010〜12年）
    pre = did(nat, base=PRE_OLD, post=BASE)
    m["pre_did_2003_06_to_2010_12"] = round(pre, 4)
    # H2：山からの戻り
    gs = ns.assign(G=gap(ns)).G
    base_g = gs.loc[BASE].mean()
    peak_year = int(gs.loc[POST].idxmax())
    g2022 = gs.loc[[2020, 2021, 2022]].mean()
    back = (gs.loc[peak_year] - g2022) / (gs.loc[peak_year] - base_g)
    m["H2_detail"] = {"peak_year": peak_year, "G_peak_minus_base": round(gs.loc[peak_year] - base_g, 4),
                      "G_2020_22_minus_base": round(g2022 - base_g, 4), "share_returned": round(back, 3),
                      "G_2023_25_minus_base": round(gs.loc[[2023, 2024, 2025]].mean() - base_g, 4)}
    # 都道府県ごと
    rows = []
    for p, tp in prefs.groupby("area", sort=False):
        rows.append({"area": p, "metro": p in METRO, "did_owner": did(tp), "did_forsale": did(tp, ctrl="分譲住宅"),
                     "did_ownfs": did(tp, ctrl="持家+分譲"), "pre_did": did(tp, base=PRE_OLD, post=BASE),
                     "did_owner_base0508": did(tp, base=[2005, 2006, 2007, 2008]),
                     "rental_pct": 100 * (tp[tp.year.isin(POST)]["貸家"].mean() / tp[tp.year.isin(BASE)]["貸家"].mean() - 1),
                     "owner_pct": 100 * (tp[tp.year.isin(POST)]["持家"].mean() / tp[tp.year.isin(BASE)]["持家"].mean() - 1),
                     "excess_units": excess(tp), "rental_base": tp[tp.year.isin(BASE)]["貸家"].mean()})
    pdid = pd.DataFrame(rows)
    order = PREFS  # 全国地方公共団体コードの順（北から南）
    assert set(order) == set(pdid.area)
    pdid["order"] = pdid.area.map({a: i for i, a in enumerate(order)})
    pdid = pdid.sort_values("order").drop(columns="order").round(4)
    pdid.to_csv(RES / "pref_did.csv", index=False)
    m["pref"] = {"median_did_owner": round(pdid.did_owner.median(), 4), "n_positive": int((pdid.did_owner > 0).sum()),
                 "n_above_015": int((pdid.did_owner >= 0.15).sum()), "q25": round(pdid.did_owner.quantile(0.25), 4),
                 "q75": round(pdid.did_owner.quantile(0.75), 4),
                 "median_metro": round(pdid[pdid.metro].did_owner.median(), 4), "median_local": round(pdid[~pdid.metro].did_owner.median(), 4),
                 "excess_metro": round(pdid[pdid.metro].excess_units.sum()), "excess_local": round(pdid[~pdid.metro].excess_units.sum()),
                 "median_pre_did": round(pdid.pre_did.median(), 4)}
    # 地方別（北から南）
    REG = {"北海道": ["北海道"], "東北": order[1:7], "関東": order[7:14], "中部": order[14:23], "近畿": order[23:30], "中国": order[30:35],
           "四国": order[35:39], "九州・沖縄": order[39:47]}
    assert REG["東北"][0] == "青森県" and REG["関東"][-1] == "神奈川県" and REG["中部"][-1] == "愛知県" and REG["近畿"][0] == "三重県" \
        and REG["中国"][0] == "鳥取県" and REG["四国"][0] == "徳島県" and REG["九州・沖縄"][-1] == "沖縄県"
    assert sum(len(v) for v in REG.values()) == 47
    reg = {}
    for r, ps in REG.items():
        tr = prefs[prefs.area.isin(ps)].groupby("year")[["貸家", "持家", "分譲住宅"]].sum().reset_index()
        reg[r] = {"did_owner": round(did(tr), 4), "rental_pct": round(100 * (tr[tr.year.isin(POST)]["貸家"].mean() / tr[tr.year.isin(BASE)]["貸家"].mean() - 1), 1),
                  "owner_pct": round(100 * (tr[tr.year.isin(POST)]["持家"].mean() / tr[tr.year.isin(BASE)]["持家"].mean() - 1), 1)}
    m["regions"] = reg
    # 年ごとの差の動き（都道府県の平均と標準誤差、2012年＝0）
    pg = prefs.assign(G=gap(prefs))
    pg = pg.merge(pg[pg.year == 2012][["area", "G"]].rename(columns={"G": "G12"}), on="area")
    pg["rel"] = pg.G - pg.G12
    ev = pg[pg.year >= 2000].groupby("year").rel.agg(["mean", "std", "count"]).reset_index()
    ev["se"] = ev["std"] / np.sqrt(ev["count"])
    ev["lo"], ev["hi"] = ev["mean"] - 1.96 * ev.se, ev["mean"] + 1.96 * ev.se
    ev = ev.round(5)
    ev.to_csv(RES / "event_pref.csv", index=False)
    pre_ev = ev[(ev.year >= 2003) & (ev.year <= 2006)]
    m["event_pref"] = {str(int(r.year)): {"mean": r["mean"], "lo": r.lo, "hi": r.hi} for _, r in ev.iterrows()}
    # 仮説
    m["hypotheses"] = {
        "H1": {"result": "支持" if d_nat >= 0.15 else "外れ", "did": round(d_nat, 4)},
        "H2": {"result": "支持" if back >= 0.5 else "外れ", "share_returned": round(back, 3)},
        "H3": {"result": "支持" if abs(pre) <= 0.10 else "外れ", "pre_did": round(pre, 4)},
        "H4": {"result": "支持" if m["pref"]["median_local"] > m["pref"]["median_metro"] else "外れ",
               "median_metro": m["pref"]["median_metro"], "median_local": m["pref"]["median_local"]}}
    # 頑健性
    variants = [("基準：対照＝持家、2014〜17 vs 2010〜12", dict()),
                ("対照＝分譲住宅", dict(ctrl="分譲住宅")),
                ("対照＝持家＋分譲住宅", dict(ctrl="持家+分譲")),
                ("後を2015〜17年（消費税の前後を除く）", dict(post=[2015, 2016, 2017])),
                ("基準を2009〜12年", dict(base=[2009, 2010, 2011, 2012])),
                ("貸家を木造・鉄骨造だけに", dict(treat="貸家_木造鉄骨")),
                ("基準を2005〜08年（2009年の落ち込みの前）", dict(base=[2005, 2006, 2007, 2008])),
                ("基準を2005〜08年・対照＝分譲住宅", dict(base=[2005, 2006, 2007, 2008], ctrl="分譲住宅")),
                ("基準を2005〜08年・貸家を木造・鉄骨造だけに", dict(base=[2005, 2006, 2007, 2008], treat="貸家_木造鉄骨"))]
    rb = []
    for name, kw in variants:
        dn = did(nat, **kw)
        pv = [did(tp, **kw) for _, tp in prefs.groupby("area", sort=False)]
        ex = excess(nat, **{k: v for k, v in kw.items() if k in ("treat", "ctrl", "base")})
        rb.append({"variant": name, "did_national": round(dn, 4), "pct": round(100 * (np.exp(dn) - 1), 1),
                   "pref_median": round(float(np.median(pv)), 4), "pref_n_positive": int(sum(v > 0 for v in pv)),
                   "excess_units_2013_2018": round(ex)})
    # 東日本大震災の復興の建設が重なる岩手・宮城・福島を除く（全国＝残り44都道府県の合計）
    ex3 = prefs[~prefs.area.isin(["岩手県", "宮城県", "福島県"])]
    n44 = ex3.groupby("year")[["貸家", "持家", "分譲住宅", "持家+分譲", "貸家_木造鉄骨"]].sum().reset_index()
    pv = [did(tp) for _, tp in ex3.groupby("area", sort=False)]
    dn = did(n44)
    rb.append({"variant": "岩手・宮城・福島を除く（44都道府県）", "did_national": round(dn, 4), "pct": round(100 * (np.exp(dn) - 1), 1),
               "pref_median": round(float(np.median(pv)), 4), "pref_n_positive": int(sum(v > 0 for v in pv)),
               "excess_units_2013_2018": round(excess(n44))})
    rb = pd.DataFrame(rb)
    rb.to_csv(RES / "robustness.csv", index=False)
    m["robustness"] = rb.set_index("variant").to_dict(orient="index")
    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True, default=float) + "\n", encoding="utf-8")
    print(json.dumps({k: m[k] for k in ["levels", "rental_share_pct", "did_national", "did_national_pct", "excess_units_2013_2018_vs_owner",
                                        "rental_units_2013_2018", "pre_did_2003_06_to_2010_12", "H2_detail", "pref", "regions", "hypotheses"]},
                     ensure_ascii=False, indent=1, default=float))
    print(rb.to_string())
    print(ng[["year", "rental", "owner", "forsale", "G_owner_rel2012", "G_forsale_rel2012"]].to_string())
    print(ev[["year", "mean", "lo", "hi"]].to_string())


if __name__ == "__main__":
    main()
