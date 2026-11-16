"""03_analysis.py : 職業の構成のずれ（ミスマッチ指標）を年度ごとに計算する（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data" / "occupation_fy.csv")
MAJOR = ["管理", "専門・技術", "事務", "販売", "サービス", "保安", "農林漁業", "生産工程", "輸送・機械運転", "建設・採掘", "運搬・清掃・包装等"]


def r(x, k=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def table(era, level, vs="有効求人_パート含む", us="有効求職_パート含む"):
    d = df[df.era == era]
    if level == "major":
        d = d[d.level == "major"]
        key = "major"
    else:  # 中分類（中分類のない大分類は大分類を使う）
        d = d[(d.level == "sub") | ((d.level == "major") & d.row.isin([6, 41, 42]))]
        key = "row"
    v = d[d.series == vs].pivot_table(index="fy", columns=key, values="value")
    u = d[d.series == us].pivot_table(index="fy", columns=key, values="value")
    return v, u


def mm(v, u, drop=None):
    if drop:
        v, u = v.drop(columns=drop), u.drop(columns=drop)
    vs = v.div(v.sum(axis=1), axis=0)
    us = u.div(u.sum(axis=1), axis=0)
    return 0.5 * (us - vs).abs().sum(axis=1)


res = {}
rows = []
for era in ["H23分類", "R4分類"]:
    v, u = table(era, "major")
    vm, um = table(era, "sub")
    vp, up = table(era, "major", "有効求人_パート除く", "有効求職_パート除く")
    vn, un = table(era, "major", "新規求人_パート含む", "新規求職_パート含む")
    s = pd.DataFrame({"mm_major": mm(v, u), "mm_sub": mm(vm, um), "mm_major_excl_office": mm(v, u, ["事務"]),
                      "mm_major_parttime_excl": mm(vp, up), "mm_major_new": mm(vn, un),
                      "jobs_ratio_total": v.sum(axis=1) / u.sum(axis=1)})
    s["era"] = era
    rows.append(s)
    # 職業ごとの構成比
    sh = pd.concat({"求人の構成比": v.div(v.sum(axis=1), axis=0) * 100, "求職の構成比": u.div(u.sum(axis=1), axis=0) * 100,
                    "求人倍率": v / u}, axis=1)
    sh.round(4).to_csv(RES / ("major_shares_h23.csv" if era == "H23分類" else "major_shares_r4.csv"))
    res[era] = (v, u)
ts = pd.concat(rows).reset_index()
ts.round(5).to_csv(RES / "mismatch_timeseries.csv", index=False)

# 段差（2022年度）
a = ts[(ts.era == "H23分類") & (ts.fy == 2022)].iloc[0]
b = ts[(ts.era == "R4分類") & (ts.fy == 2022)].iloc[0]
main = {"step_2022": {k: {"H23": r(a[k]), "R4": r(b[k]), "diff": r(b[k] - a[k])} for k in ["mm_major", "mm_sub", "mm_major_excl_office", "mm_major_parttime_excl", "mm_major_new", "jobs_ratio_total"]}}


# 接続した系列（2012〜2021年度は H23 の値 + 2022年度の段差、2022〜2025年度は R4 の値）
def linked(col):
    h = ts[ts.era == "H23分類"].set_index("fy")[col]
    n = ts[ts.era == "R4分類"].set_index("fy")[col]
    step = n.loc[2022] - h.loc[2022]
    return pd.concat([h.loc[:2021] + step, n]), step


link = pd.DataFrame({c: linked(c)[0] for c in ["mm_major", "mm_sub", "mm_major_excl_office", "mm_major_parttime_excl", "mm_major_new"]})
link["jobs_ratio_total"] = pd.concat([ts[ts.era == "H23分類"].set_index("fy").jobs_ratio_total.loc[:2021], ts[ts.era == "R4分類"].set_index("fy").jobs_ratio_total])
link.index.name = "fy"
link.round(5).to_csv(RES / "mismatch_linked.csv")


def early_late(s):
    e, l_ = s.loc[2012:2014].mean(), s.loc[2023:2025].mean()
    return {"early_2012_2014": r(e), "late_2023_2025": r(l_), "diff": r(l_ - e)}


main["mm_by_fy"] = {"H23分類": {int(k): r(v) for k, v in ts[ts.era == "H23分類"].set_index("fy").mm_major.items()},
                    "R4分類": {int(k): r(v) for k, v in ts[ts.era == "R4分類"].set_index("fy").mm_major.items()}}
main["jobs_ratio_by_fy"] = {int(k): r(v, 3) for k, v in link.jobs_ratio_total.items()}
main["H1"] = early_late(link.mm_major)
main["H1_unlinked_H23_only_2012_2021"] = {"2012": r(main["mm_by_fy"]["H23分類"][2012]), "2021": r(main["mm_by_fy"]["H23分類"][2021]),
                                          "max_fy": int(ts[ts.era == "H23分類"].set_index("fy").mm_major.idxmax())}
# H2：2025年度の |差|
v, u = res["R4分類"]
vs = v.div(v.sum(axis=1), axis=0) * 100
us = u.div(u.sum(axis=1), axis=0) * 100
gap = (us - vs)
main["gap_2025_pt"] = {k: r(gap.loc[2025, k], 2) for k in MAJOR}
main["H2_top_abs_gap_2025"] = gap.loc[2025].abs().idxmax()
vh, uh = res["H23分類"]
gh = uh.div(uh.sum(axis=1), axis=0) * 100 - vh.div(vh.sum(axis=1), axis=0) * 100
main["gap_2012_pt"] = {k: r(gh.loc[2012, k], 2) for k in MAJOR}
main["jobs_ratio_major"] = {"2012": {k: r(vh.loc[2012, k] / uh.loc[2012, k], 2) for k in MAJOR},
                            "2025": {k: r(v.loc[2025, k] / u.loc[2025, k], 2) for k in MAJOR}}
# H3：相関（接続した系列、年度）
c = np.corrcoef(link.mm_major, link.jobs_ratio_total)[0, 1]
dd = link[["mm_major", "jobs_ratio_total"]].diff().dropna()
cd = np.corrcoef(dd.mm_major, dd.jobs_ratio_total)[0, 1]
main["H3"] = {"corr_level": r(c, 3), "corr_diff": r(cd, 3), "n": int(len(link))}
main["H4"] = early_late(link.mm_major_excl_office)
# 寄与（2012→2019、2012→2025 の |差|/2 の変化。分類をまたぐので、2012→2021 は H23、2022→2025 は R4）
contrib = pd.DataFrame({"H23_2012": 0.5 * gh.loc[2012].abs(), "H23_2019": 0.5 * gh.loc[2019].abs(), "H23_2021": 0.5 * gh.loc[2021].abs(),
                        "H23_2022": 0.5 * gh.loc[2022].abs(), "R4_2022": 0.5 * gap.loc[2022].abs(), "R4_2025": 0.5 * gap.loc[2025].abs()})
contrib["chg_2012_2021_H23"] = contrib.H23_2021 - contrib.H23_2012
contrib["chg_2022_2025_R4"] = contrib.R4_2025 - contrib.R4_2022
contrib.round(3).to_csv(RES / "contribution_by_major.csv")
main["contribution_pt"] = {k: {"2012_2021": r(contrib.loc[k, "chg_2012_2021_H23"], 2), "2022_2025": r(contrib.loc[k, "chg_2022_2025_R4"], 2),
                               "level_2025": r(contrib.loc[k, "R4_2025"], 2)} for k in MAJOR}

# 問い直し：職業別の求人倍率の散らばり（大分類、求職者数で重みづけした対数の標準偏差）
disp = []
for era, (vv, uu) in res.items():
    lr = np.log(vv / uu)
    w = uu.div(uu.sum(axis=1), axis=0)
    m = (lr * w).sum(axis=1)
    sd = np.sqrt(((lr.sub(m, axis=0)) ** 2 * w).sum(axis=1))
    for fy in vv.index:
        disp.append({"era": era, "fy": int(fy), "wsd_log_ratio": sd.loc[fy], "max_ratio": (vv / uu).loc[fy].max(), "min_ratio": (vv / uu).loc[fy].min(),
                     "office_ratio": (vv / uu).loc[fy, "事務"]})
disp = pd.DataFrame(disp)
disp.round(4).to_csv(RES / "requestion_ratio_dispersion.csv", index=False)
main["requestion"] = {f"{row.era}_{row.fy}": {"wsd": r(row.wsd_log_ratio, 3), "office_ratio": r(row.office_ratio, 2)}
                      for row in disp.itertuples() if row.fy in (2012, 2019, 2020, 2021, 2022, 2025)}

# 頑健性
rb = []
for col, name in [("mm_major", "主：大分類・有効・パート含む"), ("mm_sub", "1 中分類"), ("mm_major_parttime_excl", "2 パートを除く常用"),
                  ("mm_major_new", "3 新規（フロー）"), ("mm_major_excl_office", "H4 事務を除く")]:
    el = early_late(link[col])
    rb.append({"check": name, "early_2012_2014": el["early_2012_2014"], "late_2023_2025": el["late_2023_2025"], "diff": el["diff"],
               "step_2022": main["step_2022"][col]["diff"]})
n = ts[ts.era == "R4分類"].set_index("fy")
rb.append({"check": "4 令和4年改定の分類だけ（2022→2025年度）", "early_2012_2014": r(n.mm_major.loc[2022]), "late_2023_2025": r(n.mm_major.loc[2025]),
           "diff": r(n.mm_major.loc[2025] - n.mm_major.loc[2022]), "step_2022": None})
h = ts[ts.era == "H23分類"].set_index("fy")
rb.append({"check": "5 平成23年改定の分類だけ（2012→2021年度）", "early_2012_2014": r(h.mm_major.loc[2012]), "late_2023_2025": r(h.mm_major.loc[2021]),
           "diff": r(h.mm_major.loc[2021] - h.mm_major.loc[2012]), "step_2022": None})
rbd = pd.DataFrame(rb)
rbd.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
main["judgement"] = {"H1": "支持" if main["H1"]["diff"] > 0 else "外れ", "H2": "支持" if main["H2_top_abs_gap_2025"] == "事務" else "外れ",
                     "H3": "支持" if main["H3"]["corr_level"] > 0 else "外れ", "H4": "支持" if main["H4"]["diff"] > 0 else "外れ"}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True))
