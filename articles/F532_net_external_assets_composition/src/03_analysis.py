"""03 分析：項目別の純額、増減の分解（取引と残差）、財務省の試算の累計、頑健性、仮説の判定。
出力：results/net_by_item.csv、results/decomp_periods.csv、results/factors_net.csv、results/robustness.csv、results/main.json
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
iip = pd.read_csv(D / "iip_annual.csv").pivot_table(index="year", columns=["side", "item"], values="value_oku")
fa = pd.read_csv(D / "fin_account_annual.csv")
fan = fa.drop_duplicates("code").set_index("code")["name"]
fa = fa.pivot(index="year", columns="code", values="value_oku")
fx = pd.read_csv(D / "usdjpy_yearend.csv").set_index("year")["usdjpy_dec_end"]
fac = pd.read_csv(D / "factors.csv")
ITEMS = ["直接投資", "証券投資", "金融派生商品", "その他投資", "外貨準備"]
TN = 1e4  # 億円→兆円


def code_by_name(name):
    c = [k for k, v in fan.items() if v == name]
    assert len(c) == 1, name
    return c[0]


FA_NET = {"合計": code_by_name("金融収支/ネット"), "直接投資": code_by_name("直接投資/ネット"), "証券投資": code_by_name("証券投資/ネット"),
          "金融派生商品": code_by_name("金融派生商品/ネット"), "その他投資": code_by_name("その他投資/ネット"),
          "外貨準備": code_by_name("金融/外貨準備/ネット（資産）")}
FA_DI_ASSET = code_by_name("金融/直接投資/ネット（資産）")


def net_items():
    out = pd.DataFrame(index=iip.index)
    for it in ITEMS:
        a = iip[("assets", it)]
        l = iip[("liabilities", it)] if ("liabilities", it) in iip.columns else 0
        out[it] = a - l
    out["合計"] = iip[("net", "合計")]
    return out


def decomp(net, y0, y1, excl_deriv=False):
    """y0 年末→y1 年末の純資産の変化を、取引（金融収支の累計）と残差に分ける。"""
    yrs = list(range(y0 + 1, y1 + 1))
    flow = fa.loc[yrs, FA_NET["合計"]].sum()
    dn = net.loc[y1, "合計"] - net.loc[y0, "合計"]
    if excl_deriv:
        flow -= fa.loc[yrs, FA_NET["金融派生商品"]].sum()
        dn -= net.loc[y1, "金融派生商品"] - net.loc[y0, "金融派生商品"]
    return {"start": y0, "end": y1, "excl_derivatives": excl_deriv, "change_tn": round(dn / TN, 1),
            "flow_tn": round(flow / TN, 1), "residual_tn": round((dn - flow) / TN, 1),
            "flow_share_pct": round(flow / dn * 100, 1)}


def main():
    net = net_items()
    # 金融収支のネット＝項目の合計（外貨準備を含む）か確かめる
    parts = sum(fa[FA_NET[k]] for k in ITEMS)
    m = {"fa_identity_max_gap_oku": round(float((parts - fa[FA_NET["合計"]]).abs().max()), 1)}
    sh = net[ITEMS].div(net["合計"], axis=0) * 100
    out = (net / TN).round(2).join((sh).round(2), rsuffix="_share_pct")
    out["assets_total_tn"] = (iip[("assets", "合計")] / TN).round(1)
    out["liab_total_tn"] = (iip[("liabilities", "合計")] / TN).round(1)
    out["di_share_of_assets_pct"] = (iip[("assets", "直接投資")] / iip[("assets", "合計")] * 100).round(2)
    out["usdjpy_dec_end"] = fx.reindex(out.index)
    out["net_usd_bn"] = (net["合計"] * 1e8 / fx.reindex(net.index) / 1e9).round(1)
    out.to_csv(R / "net_by_item.csv")
    for y in [1996, 2000, 2012, 2014, 2025]:
        m[f"net_{y}_tn"] = round(float(net.loc[y, "合計"]) / TN, 1)
        for it in ITEMS:
            m[f"net_{it}_{y}_tn"] = round(float(net.loc[y, it]) / TN, 1)
            m[f"share_{it}_{y}_pct"] = round(float(sh.loc[y, it]), 1)
        m[f"di_share_of_assets_{y}_pct"] = float(out.loc[y, "di_share_of_assets_pct"])
        m[f"assets_{y}_tn"] = float(out.loc[y, "assets_total_tn"]); m[f"liab_{y}_tn"] = float(out.loc[y, "liab_total_tn"])
    m["net_peak_year"] = int(net["合計"].idxmax())
    big = sh[ITEMS].idxmax(axis=1)
    m["largest_item_by_year"] = {int(y): v for y, v in big.items()}
    di_big = [int(y) for y in big.index if big[y] == "直接投資"]
    m["first_year_di_largest"] = di_big[0] if di_big else None
    m["di_largest_since"] = next(y for y in di_big if all(big[z] == "直接投資" for z in big.index if z >= y))
    m["largest_item_2012"] = sh.loc[2012, ITEMS].idxmax(); m["largest_item_2025"] = sh.loc[2025, ITEMS].idxmax()
    # 直接投資の純額が証券投資の純額を初めて上回った年
    cross = [y for y in net.index if net.loc[y, "直接投資"] > net.loc[y, "証券投資"]]
    m["first_year_di_gt_portfolio"] = int(cross[0]) if cross else None
    m["years_di_gt_portfolio"] = [int(y) for y in cross]

    # H2 と頑健性：期間別の分解
    per = [decomp(net, 2012, 2025), decomp(net, 2014, 2025), decomp(net, 2000, 2025), decomp(net, 2012, 2025, True), decomp(net, 2018, 2025)]
    pd.DataFrame(per).to_csv(R / "decomp_periods.csv", index=False)
    m["decomp_2012_2025"] = per[0]
    # H4：直接投資の資産
    yrs = list(range(2013, 2026))
    di_flow = fa.loc[yrs, FA_DI_ASSET].sum(); di_ch = iip.loc[2025, ("assets", "直接投資")] - iip.loc[2012, ("assets", "直接投資")]
    m["di_assets_change_2012_2025_tn"] = round(di_ch / TN, 1); m["di_assets_flow_2013_2025_tn"] = round(di_flow / TN, 1)
    m["di_assets_flow_share_pct"] = round(di_flow / di_ch * 100, 1)

    # H3：財務省の試算（2019〜2025年）
    n = fac[(fac["side"] == "net")].set_index("year")[["prev", "curr", "change", "flow", "fx", "other"]]
    n.to_csv(R / "factors_net.csv")
    s = n[["change", "flow", "fx", "other"]].sum()
    m["mof_2019_2025"] = {k: round(float(v) / 1000, 1) for k, v in s.items()}   # 10億円→兆円
    m["mof_fx_share_of_change_pct"] = round(float(s["fx"] / s["change"]) * 100, 1)
    m["mof_flow_share_of_change_pct"] = round(float(s["flow"] / s["change"]) * 100, 1)
    m["mof_years_fx_positive"] = [int(y) for y in n.index if n.loc[y, "fx"] > 0]
    # 項目別（資産・負債）の為替の累計
    it = fac[fac["item"] != "合計"].groupby(["side", "item"])[["flow", "fx", "other", "change"]].sum() / 1000
    it.round(1).to_csv(R / "factors_by_item_2019_2025.csv")
    m["mof_fx_assets_2019_2025_tn"] = round(float(fac[(fac.side == "assets") & (fac.item == "合計")]["fx"].sum()) / 1000, 1)
    m["mof_fx_liab_2019_2025_tn"] = round(float(fac[(fac.side == "liabilities") & (fac.item == "合計")]["fx"].sum()) / 1000, 1)

    # 金融収支（いまの値）と、財務省の試算の取引（公表時の値）の照らし合わせ
    fc = pd.DataFrame({"bop_now_tn": (fa.loc[2019:2025, FA_NET["合計"]] / TN).round(1),
                       "mof_at_release_tn": (n["flow"] / 1000).round(1)})
    fc["diff_tn"] = (fc["bop_now_tn"] - fc["mof_at_release_tn"]).round(1)
    fc.index.name = "year"
    fc.to_csv(R / "flow_check_bop_vs_mof.csv")
    m["flow_check_max_abs_diff_tn"] = float(fc["diff_tn"].abs().max()); m["flow_check_max_diff_year"] = int(fc["diff_tn"].abs().idxmax())
    # 頑健性の表
    rob = []
    for p in per:
        lab = f"{p['start']}年末→{p['end']}年末" + ("（金融派生商品を除く）" if p["excl_derivatives"] else "")
        rob.append({"check": "取引と残差：" + lab, "change_tn": p["change_tn"], "flow_tn": p["flow_tn"], "other_tn": p["residual_tn"],
                    "flow_share_pct": p["flow_share_pct"]})
    # 残差の方法と財務省の試算の照らし合わせ（2019〜2025）
    d1 = decomp(net, 2018, 2025)
    rob.append({"check": "財務省の試算 2019〜2025年の累計（取引／為替＋その他）", "change_tn": m["mof_2019_2025"]["change"],
                "flow_tn": m["mof_2019_2025"]["flow"], "other_tn": round(m["mof_2019_2025"]["fx"] + m["mof_2019_2025"]["other"], 1),
                "flow_share_pct": m["mof_flow_share_of_change_pct"]})
    # ドル建て
    u12, u25 = float(out.loc[2012, "net_usd_bn"]), float(out.loc[2025, "net_usd_bn"])
    rob.append({"check": "ドル建ての純資産 2012年末→2025年末（10億ドル）", "change_tn": None, "flow_tn": None, "other_tn": None, "flow_share_pct": None,
                "usd_2012_bn": u12, "usd_2025_bn": u25, "usd_change_pct": round((u25 / u12 - 1) * 100, 1),
                "yen_change_pct": round((net.loc[2025, "合計"] / net.loc[2012, "合計"] - 1) * 100, 1)})
    rob = pd.DataFrame(rob)
    rob.to_csv(R / "robustness.csv", index=False)
    m["robustness"] = [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in rob.to_dict(orient="records")]
    m["usd_2012_bn"], m["usd_2025_bn"] = u12, u25
    m["usd_change_2012_2025_pct"] = round((u25 / u12 - 1) * 100, 1)
    m["yen_change_2012_2025_pct"] = round(float(net.loc[2025, "合計"] / net.loc[2012, "合計"] - 1) * 100, 1)
    m["usd_peak_year"] = int(out["net_usd_bn"].idxmax()); m["usd_peak_bn"] = float(out["net_usd_bn"].max())
    m["usdjpy_2012"], m["usdjpy_2025"] = float(fx[2012]), float(fx[2025])

    # 仮説
    m["H1"] = "支持" if net.loc[2012, "証券投資"] > net.loc[2012, "直接投資"] else "外れ"
    m["H2"] = "支持" if per[0]["flow_share_pct"] >= 50 else "外れ"
    m["H3"] = "支持" if (s["fx"] > 0 and s["fx"] / s["change"] >= 0.25) else "外れ"
    m["H4"] = "支持" if m["di_assets_flow_share_pct"] >= 70 else "外れ"
    json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in m.items() if k != "robustness"}, ensure_ascii=False, indent=0)[:4000])
    print(rob.to_string())


if __name__ == "__main__":
    main()
