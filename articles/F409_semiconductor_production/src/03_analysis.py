"""主な分析：基準をつないだ指数、2019年との比、輸出入の実質化、相関（H1〜H4）と頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
NAMES = {"mining_mfg": "鉱工業", "ecd": "電子部品・デバイス工業", "ic": "集積回路", "equip": "半導体・FPD製造装置"}
LAST12 = (202510, 202609)


def link(g, how="2018"):
    """2015年基準を2020年基準につなぐ。how='2018'：2018年平均の比。how='overlap'：重なる全期間（2018-01〜2023-04）の平均の比。"""
    out = {}
    for (s, v), x in g.groupby(["series", "var"], sort=True):
        a = x[x.base == 2020].set_index("ym")["value"]
        b = x[x.base == 2015].set_index("ym")["value"]
        if a.notna().sum() == 0:
            continue  # 製造装置の在庫は公表されていない
        if how == "2018":
            idx = [m for m in a.index if 201801 <= m <= 201812]
        else:
            idx = [m for m in a.index if m in b.index and b[m] == b[m] and a[m] == a[m]]
        ratio = a[idx].mean() / b[idx].mean()
        early = b[b.index < 201801] * ratio
        out[(s, v)] = pd.concat([early, a]).sort_index()
    df = pd.DataFrame(out)
    df.columns = [f"{s}_{v}" for s, v in df.columns]
    df.index.name = "ym"
    return df


def avg(s, lo, hi):
    return float(s[(s.index >= lo) & (s.index <= hi)].mean())


def pct(a, b):
    return round((a / b - 1) * 100, 2)


def yoy(s):
    return np.log(s / s.shift(12))


def corr(a, b, lo=201601, hi=202609, drop_covid=False):
    x = pd.concat([a, b], axis=1).dropna()
    x = x[(x.index >= lo) & (x.index <= hi)]
    if drop_covid:
        x = x[(x.index < 202001) | (x.index > 202112)]
    return round(float(x.iloc[:, 0].corr(x.iloc[:, 1])), 3), int(len(x))


def main():
    g = pd.read_csv(D / "iip_gyoshu_long.csv")
    L = link(g, "2018")
    L2 = link(g, "overlap")
    L.round(4).to_csv(R / "iip_linked_monthly.csv")
    m = {"last12": "2025年10月〜2026年9月"}

    # 年の平均
    yr = L.copy(); yr["year"] = yr.index // 100
    ann = yr[yr.year <= 2025].groupby("year").mean().round(2)
    last = L[(L.index >= LAST12[0]) & (L.index <= LAST12[1])].mean().round(2)
    ann.loc["last12"] = last
    ann.to_csv(R / "iip_annual.csv")

    comp = []
    for s in NAMES:
        for v in ["prod", "ship", "inv"]:
            c = f"{s}_{v}"
            if c not in L.columns:
                continue
            r = {"series": s, "name": NAMES[s], "var": v,
                 "y2013": avg(L[c], 201301, 201312), "y2018": avg(L[c], 201801, 201812), "y2019": avg(L[c], 201901, 201912),
                 "y2025": avg(L[c], 202501, 202512), "last12": avg(L[c], *LAST12),
                 "peak_ym": int(L[c].rolling(12).mean().idxmax()), "peak12": float(L[c].rolling(12).mean().max())}
            r["last12_vs_2019_pct"] = pct(r["last12"], r["y2019"])
            r["y2025_vs_2019_pct"] = pct(r["y2025"], r["y2019"])
            r["last12_vs_2018_pct"] = pct(r["last12"], r["y2018"])
            r["last12_vs_2013_pct"] = pct(r["last12"], r["y2013"])
            r["last12_vs_peak_pct"] = pct(r["last12"], r["peak12"])
            r["last12_vs_2013_pct_overlaplink"] = pct(avg(L2[c], *LAST12), avg(L2[c], 201301, 201312))
            comp.append(r)
    comp = pd.DataFrame(comp)
    comp.round(3).to_csv(R / "compare_2019.csv", index=False)
    cp = comp.set_index(["series", "var"])

    def g_(s, v, k):
        return float(cp.loc[(s, v), k])
    for s in NAMES:
        for k in ["y2013", "y2019", "y2025", "last12", "last12_vs_2019_pct", "y2025_vs_2019_pct", "last12_vs_2018_pct", "last12_vs_2013_pct", "last12_vs_peak_pct"]:
            m[f"{s}_prod_{k}"] = round(g_(s, "prod", k), 2)
        m[f"{s}_prod_peak_ym"] = int(cp.loc[(s, "prod"), "peak_ym"])
        m[f"{s}_ship_last12_vs_2019_pct"] = round(g_(s, "ship", "last12_vs_2019_pct"), 2)
        if (s, "inv") in cp.index:
            m[f"{s}_inv_last12_vs_2019_pct"] = round(g_(s, "inv", "last12_vs_2019_pct"), 2)
    m["ic_latest_month"] = int(L.index.max())
    m["ic_prod_latest"] = float(L["ic_prod"].iloc[-1])
    m["ic_prod_2025_09"] = float(L.loc[202509, "ic_prod"])
    m["ic_prod_latest_yoy_pct"] = pct(L["ic_prod"].iloc[-1], L.loc[202509, "ic_prod"])
    m["H1"] = "支持" if m["ic_prod_last12_vs_2019_pct"] >= 10 else "外れ"
    m["H2"] = "支持" if m["equip_prod_last12_vs_2019_pct"] > m["ic_prod_last12_vs_2019_pct"] else "外れ"

    # 貿易：実質化
    t = pd.read_csv(D / "trade_monthly.csv").set_index("ym")
    p = pd.read_csv(D / "price_monthly.csv").set_index("ym")
    tp = t.join(p, how="inner")
    tp = tp[tp.index <= LAST12[1]]
    tp["ex_ic_real"] = tp["ex_ic"] / tp["px_ic_yen"] * 100
    tp["im_ic_real"] = tp["im_ic"] / tp["pm_ic_yen"] * 100
    tp["ex_ic_real_ppi"] = tp["ex_ic"] / tp["ppi_ic"] * 100
    tp.round(4).to_csv(R / "trade_real_monthly.csv")
    tr = {}
    for c in ["ex_ic", "im_ic", "ex_ic_real", "im_ic_real", "ex_ic_real_ppi", "ex_equip", "px_ic_yen", "pm_ic_yen", "px_ic_contract", "px_mem_contract"]:
        a19, al = avg(tp[c], 201901, 201912), avg(tp[c], *LAST12)
        tr[c] = {"y2019": a19, "last12": al, "pct": pct(al, a19)}
        m[f"{c}_last12_vs_2019_pct"] = pct(al, a19)
    ma = tp["ex_ic_real"].rolling(12).mean() / avg(tp["ex_ic_real"], 201901, 201912) * 100
    m["ex_ic_real_ma12_peak_ym"] = int(ma.idxmax()); m["ex_ic_real_ma12_peak"] = round(float(ma.max()), 2)
    m["ex_ic_2019_oku"] = round(avg(tp["ex_ic"], 201901, 201912) * 12 / 1e5, 0)
    m["ex_ic_last12_oku"] = round(avg(tp["ex_ic"], *LAST12) * 12 / 1e5, 0)
    m["im_ic_2019_oku"] = round(avg(tp["im_ic"], 201901, 201912) * 12 / 1e5, 0)
    m["im_ic_last12_oku"] = round(avg(tp["im_ic"], *LAST12) * 12 / 1e5, 0)
    m["ex_equip_2019_oku"] = round(avg(tp["ex_equip"], 201901, 201912) * 12 / 1e5, 0)
    m["ex_equip_last12_oku"] = round(avg(tp["ex_equip"], *LAST12) * 12 / 1e5, 0)
    pd.DataFrame(tr).T.round(3).to_csv(R / "trade_compare_2019.csv")

    # H3：実質の IC 輸出と IC の出荷（前年同月比）
    yy = pd.DataFrame({"ic_ship": yoy(L["ic_ship"]), "ic_prod": yoy(L["ic_prod"]), "ex_ic_real": yoy(tp["ex_ic_real"]),
                       "ex_ic_nom": yoy(tp["ex_ic"]), "ex_ic_real_ppi": yoy(tp["ex_ic_real_ppi"]), "im_ic_real": yoy(tp["im_ic_real"])})
    yy.round(5).to_csv(R / "yoy_monthly.csv")
    m["H3_corr"], m["H3_n"] = corr(yy["ex_ic_real"], yy["ic_ship"])
    m["H3_corr_nominal"], _ = corr(yy["ex_ic_nom"], yy["ic_ship"])
    m["H3"] = "支持" if m["H3_corr"] >= 0.5 else ("弱く支持" if m["H3_corr"] >= 0.3 else "外れ")

    # H4：メモリの生産と世界の値動き（契約通貨ベースのメモリ輸出物価）
    it = pd.read_csv(D / "iip_items_prod.csv").pivot(index="ym", columns="series", values="value")
    mem = yoy(it["ic_memory"])
    pm = yoy(p["px_mem_contract"])
    lag = []
    for k in range(0, 13):
        c, n = corr(mem, pm.shift(k), lo=201901)
        c2, _ = corr(mem, pm.shift(k), lo=201901, drop_covid=True)
        lag.append({"lag_months": k, "corr": c, "n": n, "corr_excl_2020_21": c2})
    lag = pd.DataFrame(lag)
    lag.to_csv(R / "h4_memory_price_lag.csv", index=False)
    best = lag.loc[lag["corr"].abs().idxmax()]
    m["H4_best_lag"], m["H4_best_corr"], m["H4_n"] = int(best["lag_months"]), float(best["corr"]), int(best["n"])
    m["H4_corr_lag0"] = float(lag.loc[0, "corr"])
    m["H4_max_pos_corr"] = float(lag["corr"].max())
    m["H4_max_pos_lag"] = int(lag.loc[lag["corr"].idxmax(), "lag_months"])
    m["H4"] = "支持" if m["H4_max_pos_corr"] >= 0.4 else ("外れ" if m["H4_max_pos_corr"] < 0.2 else "判定できず")
    m["memory_prod_last12_vs_2019_pct"] = pct(avg(it["ic_memory"], *LAST12), avg(it["ic_memory"], 201901, 201912))
    m["px_mem_contract_peak_ym"] = int(p["px_mem_contract"].idxmax())

    # 在庫の動き（集積回路、四半期ごとの前年同期比）
    q = pd.DataFrame({"ship": L["ic_ship"], "inv": L["ic_inv"]})
    q["q"] = (q.index // 100).astype(str) + "Q" + (((q.index % 100) - 1) // 3 + 1).astype(str)
    qq = q.groupby("q", sort=True).mean()
    qq = qq[qq.index >= "2014Q1"]
    qq["ship_yoy"] = (qq["ship"] / qq["ship"].shift(4) - 1) * 100
    qq["inv_yoy"] = (qq["inv"] / qq["inv"].shift(4) - 1) * 100
    qq.dropna().round(3).to_csv(R / "ic_inventory_cycle_q.csv")
    qd = qq.dropna()
    cyc = {k: round(float(qd["inv_yoy"].corr(qd["ship_yoy"].shift(k))), 3) for k in range(0, 5)}
    m["inv_ship_lag_corr"] = cyc
    m["inv_ship_best_lag_q"] = int(max(cyc, key=cyc.get)); m["inv_ship_best_corr"] = max(cyc.values())
    m["ic_inv_peak_ym"] = int(L["ic_inv"].idxmax())
    m["ic_inv_latest"] = float(L["ic_inv"].iloc[-1])
    m["ic_inv_2019"] = round(avg(L["ic_inv"], 201901, 201912), 2)

    # 頑健性の表
    rob = [
        ("H1 集積回路の生産", "基本：直近12か月 ÷ 2019年", m["ic_prod_last12_vs_2019_pct"]),
        ("H1 集積回路の生産", "2025年1〜12月 ÷ 2019年", m["ic_prod_y2025_vs_2019_pct"]),
        ("H1 集積回路の生産", "直近12か月 ÷ 2018年", m["ic_prod_last12_vs_2018_pct"]),
        ("H1 集積回路の生産（2013年比）", "基本：2018年平均でつなぐ", m["ic_prod_last12_vs_2013_pct"]),
        ("H1 集積回路の生産（2013年比）", "つなぎ方を重なる全期間の平均に", float(cp.loc[("ic", "prod"), "last12_vs_2013_pct_overlaplink"])),
        ("H1 電子部品・デバイス工業", "直近12か月 ÷ 2019年", m["ecd_prod_last12_vs_2019_pct"]),
        ("H2 製造装置 − 集積回路", "基本（ポイント差）", round(m["equip_prod_last12_vs_2019_pct"] - m["ic_prod_last12_vs_2019_pct"], 2)),
        ("H2 製造装置 − 集積回路", "2025年 ÷ 2019年（ポイント差）", round(m["equip_prod_y2025_vs_2019_pct"] - m["ic_prod_y2025_vs_2019_pct"], 2)),
        ("H2 製造装置 − 集積回路", "直近12か月 ÷ 2018年（ポイント差）", round(m["equip_prod_last12_vs_2018_pct"] - m["ic_prod_last12_vs_2018_pct"], 2)),
        ("実質の IC 輸出の伸び（2019年比、%）", "基本：輸出物価（円ベース）で割る", m["ex_ic_real_last12_vs_2019_pct"]),
        ("実質の IC 輸出の伸び（2019年比、%）", "国内企業物価の集積回路で割る", m["ex_ic_real_ppi_last12_vs_2019_pct"]),
        ("H3 相関", "基本：2016年1月〜2026年9月", m["H3_corr"]),
        ("H3 相関", "コロナの時期（2020〜21年）を除く", corr(yy["ex_ic_real"], yy["ic_ship"], drop_covid=True)[0]),
        ("H3 相関", "国内企業物価の集積回路で割る", corr(yy["ex_ic_real_ppi"], yy["ic_ship"])[0]),
        ("H3 相関", "出荷ではなく生産と", corr(yy["ex_ic_real"], yy["ic_prod"])[0]),
        ("H4 最大の相関", "基本：2019年1月〜（ずれ0〜12か月）", m["H4_max_pos_corr"]),
        ("H4 最大の相関", "コロナの時期を除く", float(lag["corr_excl_2020_21"].max())),
    ]
    rob = pd.DataFrame(rob, columns=["check", "variant", "value"])
    rob.to_csv(R / "robustness.csv", index=False)
    rv = dict(zip(rob["check"] + "|" + rob["variant"], rob["value"]))
    m["rob_H3_excl_covid"] = rv["H3 相関|コロナの時期（2020〜21年）を除く"]
    m["rob_H3_ppi"] = rv["H3 相関|国内企業物価の集積回路で割る"]
    m["rob_H3_prod"] = rv["H3 相関|出荷ではなく生産と"]
    m["rob_H4_excl_covid"] = rv["H4 最大の相関|コロナの時期を除く"]
    m["rob_ic_2013_overlaplink"] = rv["H1 集積回路の生産（2013年比）|つなぎ方を重なる全期間の平均に"]

    (R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
