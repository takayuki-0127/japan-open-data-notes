"""主な分析：東京都・東京圏の割合、立地係数、集中度（HHI）、地方別の割合、仮説、頑健性。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
c = pd.read_csv(ROOT / "data" / "census.csv")
e = pd.read_csv(ROOT / "data" / "ecensus2021.csv")
YEARS = ["y2005", "y2010", "y2015", "y2020"]
KEN = [11, 12, 13, 14]
REGION = {"北海道": [1], "東北": list(range(2, 8)), "関東": list(range(8, 15)), "中部": list(range(15, 24)),
          "近畿": list(range(24, 31)), "中国": list(range(31, 36)), "四国": list(range(36, 40)), "九州・沖縄": list(range(40, 48))}
REG_OF = {p: k for k, v in REGION.items() for p in v}
IND_NAME = {"G": "情報通信業", "J": "金融業・保険業", "L": "学術研究・専門技術サービス業", "total": "全産業"}


def r(x, k=1):
    return round(float(x), k)


def shares(df, col, ind, sex="総数"):
    x = df[(df.sex == sex) & (df.ind == ind)].set_index("pref_code")[col]
    return x / x.sum() * 100


def hhi(s):
    return float(((s / 100) ** 2).sum() * 10000)


rows = []
for sex in ["総数", "男", "女"]:
    for ind in ["G", "J", "L", "total"]:
        for col in YEARS + ["y2015c", "y2020c"]:
            s = shares(c, col, ind, sex)
            st = shares(c, col, "total", sex)
            rows.append({"sex": sex, "ind": ind, "year": col, "tokyo": r(s[13], 2), "tokyo_area": r(s[KEN].sum(), 2),
                         "lq_tokyo": r(s[13] / st[13], 3), "hhi": r(hhi(s), 0),
                         "n_total": int(c[(c.sex == sex) & (c.ind == ind)][col].sum())})
sh = pd.DataFrame(rows)
sh.to_csv(R / "concentration.csv", index=False)

# 地方別の割合（情報通信業、総数）
reg = []
for col in YEARS:
    s = shares(c, col, "G")
    t = shares(c, col, "total")
    for k in REGION:
        reg.append({"year": int(col[1:]), "region": k, "share_G": r(s[REGION[k]].sum(), 2), "share_total": r(t[REGION[k]].sum(), 2)})
rg = pd.DataFrame(reg)
rg.to_csv(R / "region_share.csv", index=False)

# 経済センサス（働く場所）
es = {}
for ind in ["G", "J", "L", "total"]:
    x = e[e.ind == ind].set_index("pref_code").workers
    s = x / x.sum() * 100
    es[ind] = s
ec = pd.DataFrame({"ind": ["G", "J", "L", "total"],
                   "tokyo": [r(es[i][13], 2) for i in ["G", "J", "L", "total"]],
                   "tokyo_area": [r(es[i][KEN].sum(), 2) for i in ["G", "J", "L", "total"]],
                   "hhi": [r(hhi(es[i]), 0) for i in ["G", "J", "L", "total"]]})
ec["lq_tokyo"] = (ec.tokyo / float(es["total"][13])).round(3)
ec.to_csv(R / "ecensus2021_concentration.csv", index=False)


def get(sex, ind, year, k):
    return float(sh[(sh.sex == sex) & (sh.ind == ind) & (sh.year == year)][k].iloc[0])


lq20 = get("総数", "G", "y2020", "lq_tokyo")
t05, t20 = get("総数", "G", "y2005", "tokyo"), get("総数", "G", "y2020", "tokyo")
ka20 = get("総数", "G", "y2020", "tokyo_area")
e_tokyo = float(ec[ec.ind == "G"].tokyo.iloc[0])
hyp = {
    "H1": {"lq_tokyo_2020": lq20, "verdict": "支持" if lq20 >= 2 else "外れ"},
    "H2": {"tokyo_2005": t05, "tokyo_2020": t20, "verdict": "支持" if t20 > t05 else "外れ"},
    "H3": {"tokyo_area_2020": ka20, "verdict": "支持" if ka20 >= 50 else "外れ"},
    "H4": {"tokyo_workplace_2021": e_tokyo, "tokyo_residence_2020": t20, "diff_pt": r(e_tokyo - t20, 2),
           "verdict": "支持" if e_tokyo - t20 >= 10 else "外れ"},
}
n = c[(c.sex == "総数") & (c.ind == "G")]
main = {
    "n_G": {y[1:]: int(n[y].sum()) for y in YEARS},
    "n_G_tokyo": {y[1:]: int(n[n.pref_code == 13][y].iloc[0]) for y in YEARS},
    "tokyo_share_G": {y[1:]: get("総数", "G", y, "tokyo") for y in YEARS},
    "tokyo_share_total": {y[1:]: get("総数", "total", y, "tokyo") for y in YEARS},
    "tokyo_area_share_G": {y[1:]: get("総数", "G", y, "tokyo_area") for y in YEARS},
    "tokyo_area_share_total": {y[1:]: get("総数", "total", y, "tokyo_area") for y in YEARS},
    "lq_tokyo_G": {y[1:]: get("総数", "G", y, "lq_tokyo") for y in YEARS},
    "hhi_G": {y[1:]: get("総数", "G", y, "hhi") for y in YEARS},
    "hhi_total": {y[1:]: get("総数", "total", y, "hhi") for y in YEARS},
    "ecensus2021": {row.ind: {"tokyo": row.tokyo, "tokyo_area": row.tokyo_area, "lq_tokyo": row.lq_tokyo, "hhi": row.hhi} for row in ec.itertuples()},
    "hypotheses": hyp,
    "note": "国勢調査は常住地（住む場所）、経済センサスは事業所の所在地（働く場所）。経済センサスの全産業は公務を除く民営事業所。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# 頑健性の表
rob = []
for lab, sex, ind, y0, y1 in [("本線：情報通信業・総数（原数値）", "総数", "G", "y2005", "y2020"),
                              ("不詳補完値（2015→2020）", "総数", "G", "y2015c", "y2020c"),
                              ("原数値（2015→2020）", "総数", "G", "y2015", "y2020"),
                              ("男", "男", "G", "y2005", "y2020"), ("女", "女", "G", "y2005", "y2020"),
                              ("金融業・保険業", "総数", "J", "y2005", "y2020"),
                              ("学術研究・専門技術サービス業", "総数", "L", "y2005", "y2020"),
                              ("全産業", "総数", "total", "y2005", "y2020")]:
    rob.append({"check": lab, "period": f"{y0[1:5]}→{y1[1:5]}", "tokyo0": get(sex, ind, y0, "tokyo"), "tokyo1": get(sex, ind, y1, "tokyo"),
                "tokyo_area0": get(sex, ind, y0, "tokyo_area"), "tokyo_area1": get(sex, ind, y1, "tokyo_area"),
                "lq0": get(sex, ind, y0, "lq_tokyo"), "lq1": get(sex, ind, y1, "lq_tokyo")})
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
