"""03_analysis.py : 年齢別のデジタルコンテンツ支出、年齢の差の推移、分解（年齢・全国）、頑健性（オフライン）。"""
import json
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
A10 = ["A:-34", "A:35-44", "A:45-54", "A:55-64", "A:65-74", "A:75-84", "A:85-"]
YOUNG, OLD = "A:-34", "A:65-74"


def r(x, k=4):
    return None if x is None or pd.isna(x) else round(float(x), k)


def load():
    a = pd.read_csv(ROOT / "data" / "age_items.csv")
    w = a[a.table == "t1_2"].pivot_table(index=["hh", "year", "age"], columns="item", values="value")
    w["D"] = w["ebook"] + w["download"]
    w["r_order"] = w["net_total"] / w["net_total_per_orderer"]          # ネットで注文した世帯の割合（表の中で一貫した値）
    t = a[a.table == "t4_2"].pivot_table(index=["hh", "year", "age"], columns="item", values="value")
    w = w.join(t[["order_pct"]])
    w["r_order_42"] = w["order_pct"] / 100                               # 第4-2表の割合（頑健性）
    w["d_per_orderer"] = w["D"] / w["r_order"]
    w["D_per_person"] = w["D"] / w["hh_size"]
    w["digital_share_content"] = w["D"] / (w["D"] + w["soft"] + w["book"])
    return w


def gap(w, hh="total", young=YOUNG, old=OLD, col="D"):
    g = w.loc[hh][col].unstack("age")
    return g[young] / g[old]


def main():
    w = load()
    T = w.loc["total"]
    # 年齢×年の表
    keep = ["D", "ebook", "download", "soft", "book", "net_total", "r_order", "d_per_orderer", "hh_size", "D_per_person",
            "digital_share_content", "weight"]
    tab = w.reset_index()
    tab = tab[tab.age.isin(["平均"] + A10 + ["5:-34", "5:70-74"])][["hh", "year", "age"] + keep]
    tab.round(4).to_csv(RES / "age_year_table.csv", index=False)

    M = {"years": [2015, 2025], "young": YOUNG, "old": OLD}
    D = T["D"].unstack("age")
    M["D_2025"] = {a: r(D.loc[2025, a], 0) for a in ["平均"] + A10}
    M["D_2015"] = {a: r(D.loc[2015, a], 0) for a in ["平均"] + A10}
    for k in ["ebook", "download"]:
        x = T[k].unstack("age")
        M[f"{k}_2025"] = {a: r(x.loc[2025, a], 0) for a in ["平均", YOUNG, OLD]}
        M[f"{k}_2015"] = {a: r(x.loc[2015, a], 0) for a in ["平均", YOUNG, OLD]}
    G = gap(w)
    M["ratio_young_old_by_year"] = {int(y): r(v, 3) for y, v in G.items()}
    M["ratio_2015_2017"] = r(G.loc[2015:2017].mean(), 3); M["ratio_2023_2025"] = r(G.loc[2023:2025].mean(), 3)
    M["growth_2015_2025"] = {a: r(D.loc[2025, a] / D.loc[2015, a], 3) for a in ["平均"] + A10}
    # 年齢の分解（2025年、～34歳 vs 65～74歳）
    R = T["r_order"].unstack("age"); Dd = T["d_per_orderer"].unstack("age")
    dec = []
    for y in range(2015, 2026):
        lg = np.log(D.loc[y, YOUNG] / D.loc[y, OLD])
        lr = np.log(R.loc[y, YOUNG] / R.loc[y, OLD])
        ld = np.log(Dd.loc[y, YOUNG] / Dd.loc[y, OLD])
        dec.append({"year": y, "log_gap": lg, "log_rate": lr, "log_amount": ld, "rate_share": lr / lg,
                    "r_young": R.loc[y, YOUNG], "r_old": R.loc[y, OLD], "d_young": Dd.loc[y, YOUNG], "d_old": Dd.loc[y, OLD]})
    dec = pd.DataFrame(dec).round(4)
    dec.to_csv(RES / "age_gap_decomposition.csv", index=False)
    d25 = dec[dec.year == 2025].iloc[0]
    M["decomp_2025"] = {k: r(d25[k], 4) for k in d25.index if k != "year"}
    M["r_order_2025"] = {a: r(R.loc[2025, a], 4) for a in ["平均"] + A10}
    M["d_per_orderer_2025"] = {a: r(Dd.loc[2025, a], 0) for a in ["平均"] + A10}
    # デジタルの割合（紙の本・パッケージを含むコンテンツのうち）
    S = T["digital_share_content"].unstack("age")
    M["digital_share_2015"] = {a: r(S.loc[2015, a], 4) for a in ["平均", YOUNG, OLD]}
    M["digital_share_2025"] = {a: r(S.loc[2025, a], 4) for a in ["平均", YOUNG, OLD]}

    # 全国の分解：支出世帯の割合 s（1万分比→比）と支出世帯あたりの額 m
    n = pd.read_csv(ROOT / "data" / "national_items.csv")
    n = n[n.hh == "total"].pivot_table(index=["item", "year"], columns="table", values="value")
    n.columns = ["m_yen", "s_per10000"]
    n["s"] = n["s_per10000"] / 10000
    n["D_impl"] = n["m_yen"] * n["s"]
    n.round(4).to_csv(RES / "national_payers.csv")
    nat = {}
    for it, (y0, y1) in [("ebook", (2015, 2025)), ("download", (2015, 2025)), ("digital", (2019, 2025))]:
        a0, a1 = n.loc[(it, y0)], n.loc[(it, y1)]
        lg = np.log(a1.D_impl / a0.D_impl); ls = np.log(a1.s / a0.s); lm = np.log(a1.m_yen / a0.m_yen)
        nat[it] = {"from": y0, "to": y1, "s0": r(a0.s), "s1": r(a1.s), "m0": r(a0.m_yen, 0), "m1": r(a1.m_yen, 0),
                   "growth": r(a1.D_impl / a0.D_impl, 3), "share_from_payers": r(ls / lg, 4)}
    M["national"] = nat

    # 仮説
    H = {}
    rat25 = D.loc[2025, YOUNG] / D.loc[2025, OLD]
    H["H1"] = {"ratio_2025": r(rat25, 3), "rule": ">=3", "result": "支持" if rat25 >= 3 else "外れ"}
    H["H2"] = {"ratio_2015_2017": M["ratio_2015_2017"], "ratio_2023_2025": M["ratio_2023_2025"], "rule": "後が小さい",
               "result": "支持" if G.loc[2023:2025].mean() < G.loc[2015:2017].mean() else "外れ"}
    H["H3"] = {"rate_share_2025": r(d25.rate_share), "rule": "<0.5", "result": "支持" if d25.rate_share < 0.5 else "外れ"}
    H["H4"] = {"digital_2019_2025_share_from_payers": nat["digital"]["share_from_payers"],
               "ebook_2015_2025": nat["ebook"]["share_from_payers"], "download_2015_2025": nat["download"]["share_from_payers"],
               "rule": ">=0.5（合わせた額は2019→2025年で判定）",
               "result": "支持" if nat["digital"]["share_from_payers"] >= 0.5 else "外れ"}
    M["hypotheses"] = H

    # 頑健性：～34歳 ÷ 65～74歳 の比（2025年、2015〜17年平均、2023〜25年平均）と、注文の割合で説明できる割合
    rb = []

    def add(name, Gs, rate_share=None, note=""):
        rb.append({"check": name, "ratio_2025": r(Gs.loc[2025], 3), "ratio_2015_2017": r(Gs.loc[2015:2017].mean(), 3),
                   "ratio_2023_2025": r(Gs.loc[2023:2025].mean(), 3), "rate_share_2025": r(rate_share), "note": note})
    add("基本（総世帯、10歳階級）", G, d25.rate_share)
    w2 = w.loc["two_plus"]
    G2 = w2["D"].unstack("age"); R2 = w2["r_order"].unstack("age"); Dd2 = w2["d_per_orderer"].unstack("age")
    add("二人以上の世帯", G2[YOUNG] / G2[OLD],
        np.log(R2.loc[2025, YOUNG] / R2.loc[2025, OLD]) / np.log(G2.loc[2025, YOUNG] / G2.loc[2025, OLD]))
    add("世帯人員1人あたり", gap(w, col="D_per_person"))
    G3 = G.rolling(3, center=True).mean()
    Dsm = D.rolling(3).mean()
    add("3年平均の額で比べる", Dsm[YOUNG] / Dsm[OLD], note="2025年の値は2023〜25年の平均の額どうしの比")
    yrs = np.array(G.index, float)
    def slope(idx):
        x = yrs[idx]; yv = np.log(G.values[idx])
        return np.polyfit(x, yv, 1)[0]
    allidx = np.arange(len(G)); ex = np.array([y not in (2020, 2021) for y in G.index])
    M["log_ratio_trend_per_year"] = r(slope(allidx)); M["log_ratio_trend_per_year_ex2020_21"] = r(slope(ex))
    rb.append({"check": "2020・2021年を除いた傾向（比の log の年あたりの変化）", "ratio_2025": None, "ratio_2015_2017": None,
               "ratio_2023_2025": None, "rate_share_2025": None,
               "note": f"全年 {slope(allidx):+.3f}、除いた場合 {slope(ex):+.3f}（年あたり、log）"})
    add("5歳階級：～34歳 ÷ 70～74歳", gap(w, young="5:-34", old="5:70-74"))
    add("～34歳 ÷ 全体の平均", gap(w, old="平均"))
    R42 = T["r_order_42"].unstack("age")
    rs42 = np.log(R42.loc[2025, YOUNG] / R42.loc[2025, OLD]) / d25.log_gap
    add("注文の割合を第4-2表の値にする", G, rs42)
    add("電子書籍だけ", gap(w, col="ebook")); add("ダウンロード版だけ", gap(w, col="download"))
    rbd = pd.DataFrame(rb)
    rbd.to_csv(RES / "robustness.csv", index=False)
    M["robustness"] = [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in x.items()} for x in rbd.to_dict("records")]
    (RES / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(M, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
