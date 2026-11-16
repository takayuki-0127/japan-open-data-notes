"""主な分析：回線の種類ごとの割合の推移、固定系を使わない世帯の目安、属性別の比較、仮説、頑健性。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "lines.csv")
bb = pd.read_csv(ROOT / "data" / "bb_contracts.csv")


def r(x, k=1):
    return round(float(x), k)


def tab(group, category=None):
    x = d[d.group == group]
    if category is not None:
        x = x[x.category == category]
    return x.pivot_table(index="year", columns="line", values="pct", aggfunc="first")


a = tab("世帯全体")
a["no_fixed"] = 100 - a.fixed - a.no_answer
a["fixed_excl_na"] = 100 * a.fixed / (100 - a.no_answer)
a["mobile_excl_na"] = 100 * a.mobile / (100 - a.no_answer)
a.round(2).to_csv(R / "overall_by_year.csv")

# 属性別（固定系・光・携帯）
rows = []
for grp in ["世帯主年齢", "世帯人員", "世帯類型", "世帯年収", "都市区分", "地方"]:
    x = d[(d.group == grp) & (d.line.isin(["fixed", "ftth", "mobile", "no_answer"]))]
    for (cat, y), g in x.groupby(["category", "year"]):
        v = g.set_index("line").pct
        rows.append({"group": grp, "category": cat, "year": int(y), "fixed": v.get("fixed"), "ftth": v.get("ftth"),
                     "mobile": v.get("mobile"), "no_fixed": r(100 - v.get("fixed") - v.get("no_answer"), 1)})
sub = pd.DataFrame(rows)
sub.to_csv(R / "by_attribute.csv", index=False)


def sv(grp, cat, y, k):
    return float(sub[(sub.group == grp) & (sub.category == cat) & (sub.year == y)][k].iloc[0])


mob = a.mobile
inc = (mob.diff().loc[2020:] > 0)
gap19 = sv("世帯年収", "1000~1500万円未満", 2019, "fixed") - sv("世帯年収", "200万円未満", 2019, "fixed")
gap25 = sv("世帯年収", "1000~1500万円未満", 2025, "fixed") - sv("世帯年収", "200万円未満", 2025, "fixed")
hyp = {
    "H1": {"mobile_by_year": {int(k): float(v) for k, v in mob.items()}, "years_not_up": [int(y) for y in inc.index[~inc]],
           "verdict": "支持" if inc.all() else "外れ"},
    "H2": {"single_fixed_2019": sv("世帯人員", "単身", 2019, "fixed"), "single_fixed_2025": sv("世帯人員", "単身", 2025, "fixed"),
           "verdict": "支持" if sv("世帯人員", "単身", 2025, "fixed") < sv("世帯人員", "単身", 2019, "fixed") else "外れ"},
    "H3": {"gap_2019": r(gap19), "gap_2025": r(gap25), "verdict": "支持" if gap25 < gap19 else "外れ"},
    "H4": {"mobile_2023": float(mob[2023]), "mobile_2024": float(mob[2024]), "diff": r(mob[2024] - mob[2023]),
           "verdict": "支持" if mob[2024] - mob[2023] >= 5 else "外れ"},
}

# 頑健性
rob = []
for lab, y0, y1, src in [("本線：全体（無回答を含む）", 2019, 2025, a), ("同じ選択肢の期間：全体", 2019, 2023, a)]:
    rob.append({"check": lab, "period": f"{y0}→{y1}", "fixed": f"{src.fixed[y0]:.1f}→{src.fixed[y1]:.1f}", "ftth": f"{src.ftth[y0]:.1f}→{src.ftth[y1]:.1f}",
                "mobile": f"{src.mobile[y0]:.1f}→{src.mobile[y1]:.1f}", "no_fixed": f"{src.no_fixed[y0]:.1f}→{src.no_fixed[y1]:.1f}"})
rob.append({"check": "無回答を除いて割り戻す：全体", "period": "2019→2025", "fixed": f"{a.fixed_excl_na[2019]:.1f}→{a.fixed_excl_na[2025]:.1f}",
            "ftth": "—", "mobile": f"{a.mobile_excl_na[2019]:.1f}→{a.mobile_excl_na[2025]:.1f}", "no_fixed": "—"})
for grp, cat in [("世帯主年齢", "20~29歳"), ("世帯主年齢", "70~79歳"), ("世帯類型", "単独世帯(非高齢者)"), ("世帯人員", "単身")]:
    q = sub[(sub.group == grp) & (sub.category == cat)].set_index("year")
    if 2019 not in q.index:
        continue
    rob.append({"check": f"{grp}：{cat}", "period": "2019→2025", "fixed": f"{q.fixed[2019]:.1f}→{q.fixed[2025]:.1f}", "ftth": f"{q.ftth[2019]:.1f}→{q.ftth[2025]:.1f}",
                "mobile": f"{q.mobile[2019]:.1f}→{q.mobile[2025]:.1f}", "no_fixed": f"{q.no_fixed[2019]:.1f}→{q.no_fixed[2025]:.1f}"})
ft = bb[bb.service == "FTTH"].set_index("date").contracts
rob.append({"check": "FTTH の契約数（事業者の報告）", "period": f"{ft.index[0]}→{ft.index[-1]}", "fixed": "—",
            "ftth": f"{ft.iloc[0] / 1e4:,.0f}万→{ft.iloc[-1] / 1e4:,.0f}万（{100 * (ft.iloc[-1] / ft.iloc[0] - 1):+.1f}%）", "mobile": "—", "no_fixed": "—"})
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)

main = {
    "overall": {int(y): {k: r(a.loc[y, k], 1) for k in ["fixed", "ftth", "catv", "dsl", "mobile", "lte", "g5", "home_router", "no_contract", "no_answer", "no_fixed"] if pd.notna(a.loc[y, k])} for y in a.index},
    "ftth_contracts_first": {"date": ft.index[0], "value": float(ft.iloc[0])}, "ftth_contracts_last": {"date": ft.index[-1], "value": float(ft.iloc[-1])},
    "ftth_contracts_change_pct": r(100 * (ft.iloc[-1] / ft.iloc[0] - 1), 2),
    "hypotheses": hyp,
    "note": "通信利用動向調査は複数回答の割合（%）。対象は過去1年にインターネットを使った世帯。2024年から選択肢にホームルーターが加わった。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(hyp, ensure_ascii=False))
print(a[["fixed", "ftth", "mobile", "lte", "g5", "home_router", "no_fixed", "no_contract"]])
print(pd.read_csv(R / "robustness.csv").to_string())
