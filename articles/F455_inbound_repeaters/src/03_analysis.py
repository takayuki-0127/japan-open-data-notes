"""国籍・地域別のリピーターの割合、10回以上の割合、地域のまとまり、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "visits_long.csv")
sh = d.pivot_table(index=["year", "nation"], columns="visit", values="share").reset_index()
sh["repeat2"] = 100 - sh["1回目"]
sh["repeat3"] = 100 - sh["1回目"] - sh["2回目"]
sh["heavy10"] = sh["10~19回"] + sh["20回以上"]
cnt = d[d.visit == "1回目"].set_index(["year", "nation"])["count"]
tot = d.groupby(["year", "nation"])["count"].sum()
sh = sh.set_index(["year", "nation"]); sh["n_resp"] = tot; sh = sh.reset_index()
sh.to_csv(R / "repeat_by_nation_year.csv", index=False, float_format="%.3f")
P = sh.pivot(index="nation", columns="year", values="repeat2")
H10 = sh.pivot(index="nation", columns="year", values="heavy10")
R3 = sh.pivot(index="nation", columns="year", values="repeat3")
N = sh.pivot(index="nation", columns="year", values="n_resp")
nat = [c for c in P.index if c not in ("全体", "その他") and not pd.isna(P.loc[c, 2014]) and not pd.isna(P.loc[c, 2025])]
EA = ["韓国", "台湾", "香港", "中国"]; SEA = ["タイ", "シンガポール", "マレーシア", "インドネシア", "フィリピン", "ベトナム", "インド"]
WEST = ["英国", "ドイツ", "フランス", "イタリア", "スペイン", "米国", "カナダ", "オーストラリア"]
Q = [2023, 2024, 2025]
main = {"overall_repeat": {int(y): round(float(P.loc["全体", y]), 1) for y in P.columns},
        "overall_heavy10": {int(y): round(float(H10.loc["全体", y]), 1) for y in H10.columns},
        "nations_compared": nat, "n_nations": len(nat),
        "n_up_2014_2025": int((P.loc[nat, 2025] > P.loc[nat, 2014]).sum()),
        "china": {int(y): round(float(P.loc["中国", y]), 1) for y in P.columns},
        "repeat_2014": {c: round(float(P.loc[c, 2014]), 1) for c in nat}, "repeat_2025": {c: round(float(P.loc[c, 2025]), 1) for c in nat},
        "repeat_2019": {c: round(float(P.loc[c, 2019]), 1) for c in nat}}
main["china_diff"] = round(main["china"][2025] - main["china"][2014], 1)
main["heavy10_diff"] = round(main["overall_heavy10"][2025] - main["overall_heavy10"][2014], 1)
g = lambda grp, ys: float(P.loc[grp, ys].mean(axis=1).mean())
main["ea_2325"] = round(g(EA, Q), 1); main["sea_2325"] = round(g(SEA, Q), 1); main["west_2325"] = round(g(WEST, Q), 1)
main["ea_2014"] = round(g(EA, [2014]), 1); main["sea_2014"] = round(g(SEA, [2014]), 1); main["west_2014"] = round(g(WEST, [2014]), 1)
main["h4_gap"] = round(main["ea_2325"] - main["west_2325"], 1)
main["hypotheses"] = {"H1": "支持" if main["n_up_2014_2025"] >= 12 else "外れ", "H2": "支持" if main["china_diff"] >= 15 else "外れ",
                      "H3": "支持" if main["heavy10_diff"] >= 3 else "外れ", "H4": "支持" if main["h4_gap"] >= 20 else "外れ"}
chg = pd.DataFrame({"r2014": P.loc[nat, 2014], "r2019": P.loc[nat, 2019], "r2025": P.loc[nat, 2025]})
chg["d_14_19"] = chg.r2019 - chg.r2014; chg["d_19_25"] = chg.r2025 - chg.r2019; chg["d_14_25"] = chg.r2025 - chg.r2014
chg.to_csv(R / "repeat_change_by_nation.csv", float_format="%.2f")
main["n_up_2014_2019"] = int((chg.d_14_19 > 0).sum()); main["n_up_2019_2025"] = int((chg.d_19_25 > 0).sum())
rb = []
a = P.loc[nat, [2015, 2016]].mean(axis=1); b = P.loc[nat, Q].mean(axis=1)
rb.append(dict(check="比べる年を2015〜16年平均→2023〜25年平均にする：上がった国・地域の数", value=int((b > a).sum()), unit=f"/{len(nat)}"))
rb.append(dict(check="同：中国の上がり幅", value=round(float(b["中国"] - a["中国"]), 1), unit="ポイント"))
rb.append(dict(check="リピーターを「3回目以上」にする：2014→2025年に上がった国・地域の数", value=int((R3.loc[nat, 2025] > R3.loc[nat, 2014]).sum()), unit=f"/{len(nat)}"))
rb.append(dict(check="同：全体の3回目以上の割合の変化（2014→2025年）", value=round(float(R3.loc["全体", 2025] - R3.loc["全体", 2014]), 1), unit="ポイント"))
big = [c for c in nat if N.loc[c, [2014, 2015, 2016, 2017, 2018, 2019, 2023, 2024, 2025]].min() >= 300]
rb.append(dict(check=f"回答数が毎年300以上の国・地域（{len(big)}）だけ：上がった数", value=int((P.loc[big, 2025] > P.loc[big, 2014]).sum()), unit=f"/{len(big)}"))
wavg = lambda grp, ys: float(sum((P.loc[grp, y] * N.loc[grp, y]).sum() / N.loc[grp, y].sum() for y in ys) / len(ys))
rb.append(dict(check="回答数で重みをつけた平均：東アジア − 欧米豪（2023〜25年）", value=round(wavg(EA, Q) - wavg(WEST, Q), 1), unit="ポイント"))
rb.append(dict(check="全体の10回以上の割合の変化（2014→2019年）", value=round(float(H10.loc["全体", 2019] - H10.loc["全体", 2014]), 1), unit="ポイント"))
rbd = pd.DataFrame(rb); rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = {r.check: r.value for r in rbd.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in main.items() if k not in ("repeat_2014", "repeat_2025", "repeat_2019")}, ensure_ascii=False, indent=1)); print(chg.round(1).to_string()); print(rbd.to_string())
