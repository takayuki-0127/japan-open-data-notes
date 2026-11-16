"""03b 問い直し（結果を見てから足した）：
戻りがいちばん鈍いのは、60歳以上ではなく30〜50代の男性だった。これは人口あたり（出国率）で見ても残るのか。
ふだんの年（2018→2019年）の男女差の動きと比べてどうか。人口の変化（高齢化・減少）で説明できる分はどれだけか。
出力：results/requestion_sex_age.csv、results/requestion.json"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
d = pd.read_csv(DATA / "outbound_pref_age_sex.csv")
pop = pd.read_csv(DATA / "pop_pref_age_sex.csv")
PREFS = sorted(pop.pref.unique())
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70+"]
G = {"0-4": "0〜19歳", "5-9": "0〜19歳", "10-14": "0〜19歳", "15-19": "0〜19歳", "20-24": "20代", "25-29": "20代", "30-34": "30代", "35-39": "30代",
     "40-44": "40代", "45-49": "40代", "50-54": "50代", "55-59": "50代", "60-64": "60歳以上", "65-69": "60歳以上", "70+": "60歳以上"}
ORDER = ["0〜19歳", "20代", "30代", "40代", "50代", "60歳以上"]
r = lambda x: float(round(x, 4))
x = d[d.pref.isin(PREFS) & d.age.isin(AGES)].copy(); x["g"] = x.age.map(G)
p = pop.copy(); p["g"] = p.age.map(G)
n = x.groupby(["year", "sex", "g"]).n.sum()
pp = p.groupby(["year", "sex", "g"]).pop_k.sum()
rows = []
for sex in ["男", "女"]:
    for g in ORDER:
        rows.append(dict(sex=sex, ageg=g,
                         rate_2019=round(n[(2019, sex, g)] / pp[(2019, sex, g)], 1), rate_2024=round(n[(2024, sex, g)] / pp[(2024, sex, g)], 1),
                         count_ratio_2025=r(n[(2025, sex, g)] / n[(2019, sex, g)]), count_ratio_2024=r(n[(2024, sex, g)] / n[(2019, sex, g)]),
                         count_ratio_2019_2018=r(n[(2019, sex, g)] / n[(2018, sex, g)]),
                         count_ratio_2019_2015=r(n[(2019, sex, g)] / n[(2015, sex, g)])))
t = pd.DataFrame(rows)
t["rate_ratio_2024"] = (t.rate_2024 / t.rate_2019).round(4)
t.to_csv(RES / "requestion_sex_age.csv", index=False)
Q = {}
w = t.set_index(["sex", "ageg"])
mid = ["30代", "40代", "50代"]
for k, lab in [("count_ratio_2025", "2025"), ("rate_ratio_2024", "rate2024"), ("count_ratio_2019_2018", "normal_2019_2018"), ("count_ratio_2019_2015", "pre_2019_2015")]:
    Q[f"gap_women_minus_men_mid_{lab}_pt"] = {g: r((w.loc[("女", g), k] - w.loc[("男", g), k]) * 100) for g in ORDER}
# 30〜59歳の男性・女性（人数で合わせた戻り率）
for sex in ["男", "女"]:
    a = sum(n[(2025, sex, g)] for g in mid); b = sum(n[(2019, sex, g)] for g in mid)
    Q[f"R2025_30_59_{sex}"] = r(a / b)
    a4 = sum(n[(2024, sex, g)] for g in mid) / sum(pp[(2024, sex, g)] for g in mid); b4 = sum(n[(2019, sex, g)] for g in mid) / sum(pp[(2019, sex, g)] for g in mid)
    Q[f"rate_ratio_2024_30_59_{sex}"] = r(a4 / b4)
    Q[f"rate_2019_30_59_{sex}"] = round(float(b4), 1)
    Q[f"R2019_2015_30_59_{sex}"] = r(sum(n[(2019, sex, g)] for g in mid) / sum(n[(2015, sex, g)] for g in mid))
dec = (n.loc[2019] - n.loc[2025])
Q["decline_share_men_30_59"] = r(sum(dec[("男", g)] for g in mid) / dec.sum())
Q["share_men_30_59_2019"] = r(sum(n[(2019, "男", g)] for g in mid) / n.loc[2019].sum())
# 人口の変化で説明できる分（2019→2024）：2019年の出国率のまま 2024年の人口に当てた見込み
xs = x.groupby(["year", "pref", "age", "sex"]).n.sum()
ps = pop.set_index(["year", "pref", "age", "sex"]).pop_k
rate19 = (xs.loc[2019] / ps.loc[2019])
exp24 = float((rate19 * ps.loc[2024]).sum()); act19 = float(xs.loc[2019].sum()); act24 = float(xs.loc[2024].sum())
Q["actual_2019_pref_known"] = int(act19); Q["actual_2024_pref_known"] = int(act24); Q["expected_2024_if_rates_2019"] = int(round(exp24))
Q["pop_effect_ratio"] = r(exp24 / act19)
Q["pop_effect_share_of_decline"] = r((act19 - exp24) / (act19 - act24))
(RES / "requestion.json").write_text(json.dumps(Q, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(t.to_string()); print(json.dumps(Q, ensure_ascii=False, indent=1))
