"""貸出先の区分ごとの割合と、増加への寄与（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
G = ["製造業", "不動産業：SPC", "不動産業：個人による貸家業", "不動産業：その他", "金融業・保険業", "その他の非製造業（法人）",
     "地方公共団体", "個人：住宅・消費（割賦返済分）", "個人：その他", "海外円借款・国内店名義現地貸"]
LAST = None

def wide(long, acc, size="all"):
    s = long[(long.account == acc) & (long["size"] == size)]
    return s.pivot(index="quarter", columns="sector", values="oku_yen").sort_index()

def groups(w):
    g = pd.DataFrame(index=w.index)
    g["製造業"] = w["製造業"]
    spc = w.get("不動産流動化等を目的とするSPC"); hr = w.get("個人による貸家業")
    g["不動産業：SPC"] = spc
    g["不動産業：個人による貸家業"] = hr
    g["不動産業：その他"] = w["不動産業"] - spc - hr
    g["金融業・保険業"] = w["金融業、保険業"]
    g["その他の非製造業（法人）"] = w["非製造業（法人計＜含金融＞）"] - w["不動産業"] - w["金融業、保険業"]
    g["地方公共団体"] = w["地方公共団体"]
    g["個人：住宅・消費（割賦返済分）"] = w["住宅・消費（割賦返済分）"]
    g["個人：その他"] = w["個人"] - w["住宅・消費（割賦返済分）"]
    g["海外円借款・国内店名義現地貸"] = w["海外円借款、国内店名義現地貸"]
    g["総貸出"] = w["総貸出"]
    g["差（総貸出−区分の合計）"] = w["総貸出"] - g[G].sum(axis=1, min_count=len(G))
    return g

def contrib(g, a, b):
    d = g.loc[b, G] - g.loc[a, G]
    tot = g.loc[b, "総貸出"] - g.loc[a, "総貸出"]
    return pd.DataFrame({"from": a, "to": b, "group": G, "level_from": g.loc[a, G].values, "level_to": g.loc[b, G].values,
                         "increase": d.values, "share_of_increase": (d / tot).values, "total_increase": tot})

def main():
    long = pd.read_csv(ROOT / "data" / "loans_long.csv")
    bank = wide(long, "bank"); last = bank.index[-1]
    g = groups(bank).loc["2009Q2":]
    assert g["差（総貸出−区分の合計）"].abs().max() < 100, g["差（総貸出−区分の合計）"].abs().max()  # 100億円未満
    sh = g[G].div(g["総貸出"], axis=0)
    sh.round(5).to_csv(RES / "shares_bank.csv")
    starts = ["2009Q2", "2013Q1", "2019Q4"]
    con = pd.concat([contrib(g, a, last) for a in starts]); con.round(4).to_csv(RES / "contributions_bank.csv", index=False)
    c13 = con[con["from"] == "2013Q1"].set_index("group")
    re_groups = ["不動産業：SPC", "不動産業：個人による貸家業", "不動産業：その他"]
    ind_groups = ["個人：住宅・消費（割賦返済分）", "個人：その他"]
    h1 = float(c13.loc[re_groups + ind_groups, "share_of_increase"].sum())
    # 長い推移：銀行勘定の不動産業・製造業・個人の割合（1992年〜）、3勘定合算（1970年〜）
    long_rows = {}
    for acc in ("bank", "3acc"):
        w = wide(long, acc)
        for s in ("不動産業", "製造業", "個人", "地方公共団体"):
            long_rows[(acc, s)] = (w[s] / w["総貸出"])
    lr = pd.DataFrame({f"{a}|{s}": v for (a, s), v in long_rows.items()}).sort_index()
    lr.round(5).to_csv(RES / "long_shares.csv")
    re_b = lr["bank|不動産業"].dropna(); re_3 = lr["3acc|不動産業"].dropna()
    # 不動産業の中の構成
    re_tot = g[re_groups].sum(axis=1)
    re_mix = g[re_groups].div(re_tot, axis=0); re_mix.round(5).to_csv(RES / "realestate_mix_bank.csv")
    # 規模
    sz = {k: wide(long, "bank", k) for k in ("sme", "mid", "large")}
    corp = pd.DataFrame({k: v["総貸出"] for k, v in sz.items()}).loc["2009Q2":]
    corp_sh = corp.div(corp.sum(axis=1), axis=0); corp_sh.round(5).to_csv(RES / "size_shares_bank.csv")
    m = {
        "last_quarter": last,
        "total": {q: round(float(g.loc[q, "総貸出"]) / 1e4, 2) for q in starts + [last]},  # 兆円
        "share": {q: {k: round(float(sh.loc[q, k]) * 100, 2) for k in G} for q in starts + [last]},
        "share_realestate": {q: round(float(sh.loc[q, re_groups].sum()) * 100, 2) for q in starts + [last]},
        "share_individual": {q: round(float(sh.loc[q, ind_groups].sum()) * 100, 2) for q in starts + [last]},
        "contrib_2013": {k: round(float(c13.loc[k, "share_of_increase"]) * 100, 2) for k in G},
        "increase_2013_tn": round(float(c13["total_increase"].iloc[0]) / 1e4, 2),
        "contrib_2013_realestate": round(float(c13.loc[re_groups, "share_of_increase"].sum()) * 100, 2),
        "contrib_2013_individual": round(float(c13.loc[ind_groups, "share_of_increase"].sum()) * 100, 2),
        "contrib_2013_re_plus_ind": round(h1 * 100, 2),
        "long_bank_re_max": {"quarter": re_b.idxmax(), "share": round(float(re_b.max()) * 100, 2), "first": re_b.index[0]},
        "long_3acc_re_max": {"quarter": re_3.idxmax(), "share": round(float(re_3.max()) * 100, 2), "first": re_3.index[0]},
        "long_3acc_re_last": round(float(re_3.iloc[-1]) * 100, 2),
        "long_3acc_re_1990": round(float(re_3.loc["1990Q4"]) * 100, 2),
        "long_3acc_mfg_1970": round(float(lr["3acc|製造業"].loc["1970Q1"]) * 100, 2),
        "long_3acc_mfg_last": round(float(lr["3acc|製造業"].iloc[-1]) * 100, 2),
        "re_mix": {q: {k: round(float(re_mix.loc[q, k]) * 100, 2) for k in re_groups} for q in ["2009Q2", "2013Q1", "2016Q4", "2019Q4", last]},
        "re_mix_hr_peak": {"quarter": re_mix["不動産業：個人による貸家業"].idxmax(), "share": round(float(re_mix["不動産業：個人による貸家業"].max()) * 100, 2)},
        "size_share": {q: {k: round(float(corp_sh.loc[q, k]) * 100, 2) for k in corp_sh.columns} for q in starts + [last]},
    }
    m["H1"] = "支持" if h1 >= 0.5 else "外れ"
    m["H2"] = "支持" if (m["long_bank_re_max"]["quarter"] == last and m["long_3acc_re_max"]["quarter"] == last) else ("一部支持" if (m["long_bank_re_max"]["quarter"] == last or m["long_3acc_re_max"]["quarter"] == last) else "外れ")
    m["H3"] = "支持" if re_mix.loc[last, "不動産業：個人による貸家業"] < re_mix.loc["2009Q2", "不動産業：個人による貸家業"] and re_mix.loc[last, "不動産業：SPC"] > re_mix.loc["2009Q2", "不動産業：SPC"] and re_mix.loc[last, "不動産業：その他"] > re_mix.loc["2009Q2", "不動産業：その他"] else "外れ"
    m["H4"] = "支持" if (sh.loc["2009Q2", "製造業"] - sh.loc[last, "製造業"]) >= 0.005 else "外れ"
    m["H4_mfg_share_change_pt"] = round(float(sh.loc[last, "製造業"] - sh.loc["2009Q2", "製造業"]) * 100, 2)
    m["max_abs_residual_oku"] = float(g["差（総貸出−区分の合計）"].abs().max())

    # 頑健性
    rob = []
    for a in starts:
        c = con[con["from"] == a].set_index("group")
        rob.append({"check": f"R1 起点 {a}（銀行勘定）", "realestate_contrib_pct": round(float(c.loc[re_groups, 'share_of_increase'].sum()) * 100, 1),
                    "individual_contrib_pct": round(float(c.loc[ind_groups, 'share_of_increase'].sum()) * 100, 1),
                    "mfg_contrib_pct": round(float(c.loc['製造業', 'share_of_increase']) * 100, 1),
                    "realestate_share_last_pct": round(float(sh.loc[last, re_groups].sum()) * 100, 1)})
    for acc, lab in (("3acc", "R2 3勘定合算"), ("shinkin", "R3 信用金庫")):
        w = wide(long, acc); gg = groups(w)
        assert gg.loc["2013Q1":, "差（総貸出−区分の合計）"].abs().max() < 100
        c = contrib(gg, "2013Q1", last).set_index("group")
        rob.append({"check": f"{lab}（起点 2013Q1）", "realestate_contrib_pct": round(float(c.loc[re_groups, 'share_of_increase'].sum()) * 100, 1),
                    "individual_contrib_pct": round(float(c.loc[ind_groups, 'share_of_increase'].sum()) * 100, 1),
                    "mfg_contrib_pct": round(float(c.loc['製造業', 'share_of_increase']) * 100, 1),
                    "realestate_share_last_pct": round(float(gg.loc[last, re_groups].sum() / gg.loc[last, '総貸出']) * 100, 1)})
    dom = [x for x in G if x not in ("海外円借款・国内店名義現地貸", "金融業・保険業")]
    gd = g[dom]; tot_d = gd.sum(axis=1)
    dd = (gd.loc[last] - gd.loc["2013Q1"]) / (tot_d.loc[last] - tot_d.loc["2013Q1"])
    rob.append({"check": "R4 国内の非金融の借り手向け（海外・金融を除く、起点 2013Q1）",
                "realestate_contrib_pct": round(float(dd[re_groups].sum()) * 100, 1), "individual_contrib_pct": round(float(dd[ind_groups].sum()) * 100, 1),
                "mfg_contrib_pct": round(float(dd["製造業"]) * 100, 1), "realestate_share_last_pct": round(float(gd.loc[last, re_groups].sum() / tot_d.loc[last]) * 100, 1)})
    # R5：2009年6月の業種分類の改定による段差（2009Q1→Q2）を除いた不動産業の割合（3勘定合算）
    jump = float(re_3.loc["2009Q2"] - re_3.loc["2009Q1"])
    adj = re_3.copy(); adj.loc["2009Q2":] = adj.loc["2009Q2":] - jump
    m["R5_jump_2009Q2_pt"] = round(jump * 100, 2)
    m["R5_adj_last"] = round(float(adj.iloc[-1]) * 100, 2)
    m["R5_adj_max_before_2026"] = {"quarter": adj.loc[:"2025Q4"].idxmax(), "share": round(float(adj.loc[:"2025Q4"].max()) * 100, 2)}
    m["R5_pre2009_max"] = {"quarter": re_3.loc[:"2009Q1"].idxmax(), "share": round(float(re_3.loc[:"2009Q1"].max()) * 100, 2)}
    rob.append({"check": "R5 2009年の分類改定の段差を除く（3勘定合算、不動産業の割合）", "realestate_contrib_pct": None, "individual_contrib_pct": None,
                "mfg_contrib_pct": None, "realestate_share_last_pct": round(float(adj.iloc[-1]) * 100, 1)})
    # R6（レビューで追加）：1970年以降で前の期から1ポイント以上動いた段差（2004Q1・2006Q3・2009Q2）を、
    # すべて分類の変更とみなして除いても、最新が最も高いか（3勘定合算）
    big = [q for q in re_3.index[1:] if abs(float(re_3.loc[q] - re_3.shift(1).loc[q])) >= 0.01]
    adj6 = re_3.copy()
    for q in big:
        adj6.loc[q:] = adj6.loc[q:] - float(re_3.loc[q] - re_3.shift(1).loc[q])
    m["R6_steps"] = {q: round(float(re_3.loc[q] - re_3.shift(1).loc[q]) * 100, 2) for q in big}
    m["R6_adj_last"] = round(float(adj6.iloc[-1]) * 100, 2)
    m["R6_adj_max_before_last"] = {"quarter": adj6.iloc[:-1].idxmax(), "share": round(float(adj6.iloc[:-1].max()) * 100, 2)}
    m["R6_last_is_max"] = bool(adj6.iloc[-1] > adj6.iloc[:-1].max())
    rob.append({"check": "R6 1ポイント以上の段差3つ（2004Q1・2006Q3・2009Q2）をすべて除く（3勘定合算、レビューで追加）", "realestate_contrib_pct": None,
                "individual_contrib_pct": None, "mfg_contrib_pct": None, "realestate_share_last_pct": round(float(adj6.iloc[-1]) * 100, 1)})
    rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)
    m["robustness"] = rob.to_dict(orient="records")
    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: m[k] for k in ["H1", "H2", "H3", "H4", "contrib_2013_re_plus_ind", "contrib_2013_realestate", "contrib_2013_individual", "long_bank_re_max", "long_3acc_re_max", "long_3acc_re_last", "long_3acc_re_1990", "H4_mfg_share_change_pt", "re_mix", "re_mix_hr_peak", "size_share", "share_realestate", "share_individual", "total", "contrib_2013", "increase_2013_tn", "max_abs_residual_oku"]}, ensure_ascii=False, indent=0))
    print(rob.to_string())

if __name__ == "__main__":
    main()
