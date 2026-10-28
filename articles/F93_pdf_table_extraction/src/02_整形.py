"""正解の表（ground truth）を、PDF の行の並びと同じ「1行＝数の列」の形にそろえる。
- T1：学歴×卒業年（1996〜2023年3月卒、112行）。PDF の行は 就職者数・3年目までの離職者数・1〜3年目・離職率… の9つの数。
       F07 の CSV にあるのは最初の6つ。残りの3つ（1〜3年目それぞれの離職率）は 離職者数÷就職者数 を小数1桁に丸めて作った
       （PDF の文字の層と 336セルすべてで一致することを確かめてある）。
- T2：大卒の産業別。PDF の1行＝1産業×4年分（就職者・3年目まで・2年目まで・1年目まで）の16の数。最後のページは 4＋3＋2＝9。
- T3：大卒の規模別。1行＝就職者数・離職者数・率・6規模×（離職者数・率）の15の数。
- T4：労働力調査の基準切替の段差。1行＝15歳以上人口・就業者・失業者・非労働力人口・失業率の5つ（符号つき）。"""
from common import *
EDU = ["中学", "高校", "短大等", "大学"]
rows = []
# T1
e = pd.read_csv(RAW / "turnover_by_education.csv")
e = e[e.grad_year <= 2023].copy(); e["o"] = e.education.map(EDU.index); e = e.sort_values(["o", "grad_year"])
for r in e.itertuples():
    rows.append(dict(table="T1", page=0, key=f"{r.education}_{r.grad_year}", vals=[r.hires, r.sep3y, r.sep_y1, r.sep_y2, r.sep_y3, r.rate3y] + [round(x / r.hires * 100 + 1e-9, 1) for x in (r.sep_y1, r.sep_y2, r.sep_y3)]))
# T2
d = pd.read_csv(RAW / "turnover_by_industry.csv"); d = d[d.education == "大学"].reset_index(drop=True)
pages = [[2003, 2004, 2005, 2006], [2007, 2008, 2009, 2010], [2011, 2012, 2013, 2014], [2015, 2016, 2017, 2018], [2019, 2020, 2021, 2022], [2023, 2024, 2025]]
for p, yrs in enumerate(pages):
    sub = d[d.grad_year.isin(yrs)]
    for ind in dict.fromkeys(sub.industry):
        v = []
        for y in yrs:
            r = sub[(sub.industry == ind) & (sub.grad_year == y)].iloc[0]
            v += [r.hires] + [r[c] for c in ["sep_cum3", "sep_cum2", "sep_cum1"] if not (y >= 2024 and (c == "sep_cum3" or (y == 2025 and c == "sep_cum2")))]
        rows.append(dict(table="T2", page=p, key=f"{ind}_{yrs[0]}", vals=v))
# T3
s = pd.read_csv(RAW / "turnover_by_size.csv"); s = s[s.education == "大学"]
SIZES = ["規模計", "5人未満", "5～29人", "30～99人", "100～499人", "500～999人", "1000人以上"]
for (y, k), g in s.groupby(["grad_year", "k"], sort=True):
    g = g.set_index("size")
    v = [g.loc["規模計", "hires"]]
    for z in SIZES: v += [g.loc[z, "sep_cum"], g.loc[z, "rate_cum"]]
    rows.append(dict(table="T3", page=0, key=f"{y}_{k}年目まで", vals=v))
# T4
o = pd.read_csv(RAW / "official_lfs_gaps.csv")
for r in o.itertuples():
    rows.append(dict(table="T4", page=2, key=r.switch, vals=[r.pop15, r.employed, r.unemployed, r.nilf, r.unemp_rate]))
gt = pd.DataFrame(rows)
gt["vals"] = gt.vals.apply(lambda v: [None if pd.isna(x) else float(x) for x in v])
gt.to_json(GT / "ground_truth_rows.json", orient="records", force_ascii=False, indent=0)
print(gt.groupby("table").agg(rows=("key", "size"), cells=("vals", lambda x: sum(len(v) for v in x))))
