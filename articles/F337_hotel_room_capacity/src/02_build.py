"""宿泊旅行統計調査（年確定値）の第7表（利用客室数）・第8表（客室稼働率）の年計から、全国の値を取り出す（オフライン）。
出力：data/rooms_national.csv（year, group, used_rooms, occupancy_pct, supply_rooms）
group：all（全体）、emp0_9・emp10_29・emp30_99・emp100（従業者数）、施設タイプ名。supply ＝ 利用客室数 ÷ 稼働率（推計）。"""
import pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
SIZE = {"0～9人": "emp0_9", "10～29人": "emp10_29", "30～99人": "emp30_99", "100人以上": "emp100"}
TYPES = ["旅館", "リゾートホテル", "ビジネスホテル", "シティホテル", "簡易宿所", "会社・団体の宿泊所"]
def norm(s): return re.sub(r"[\s\n]", "", str(s)) if pd.notna(s) else ""
def national(path, sheet):
    v = pd.read_excel(path, sheet_name=sheet, header=None)
    row = next(i for i in range(4, 15) if norm(v.iloc[i, 0]).startswith("全国") or "1～12月計" in norm(v.iloc[i, 0]))
    cols = {"all": 1}
    for j in range(2, v.shape[1]):
        h = [norm(v.iloc[i, j]) for i in range(3, row)]
        for lab, key in SIZE.items():
            if key not in cols and any(x == lab or x.startswith(lab) for x in h): cols[key] = j
        for t in TYPES:
            if t not in cols and any(x.startswith(t) for x in h): cols[t] = j
    return {k: float(pd.to_numeric(v.iloc[row, j], errors="coerce")) for k, j in cols.items()}
recs = []
for p in sorted(q for q in RAW.glob("shukuhaku_*.xls*") if q.suffix in (".xls", ".xlsx")):
    y = int(re.search(r"_(\d{4})\.", p.name).group(1))
    u = national(p, "第7表(年計)"); o = national(p, "第8表(年計)")
    for k in u:
        if k in o and o[k] > 0:
            recs.append(dict(year=y, group=k, used_rooms=u[k], occupancy_pct=o[k], supply_rooms=u[k] / (o[k] / 100)))
d = pd.DataFrame(recs)
# 従業者10人以上の合計（2012年調査は10人以上の区分だけのため、年をまたいで比べるときに使う）
g = d[d.group.isin(["emp10_29", "emp30_99", "emp100"])].groupby("year")[["used_rooms", "supply_rooms"]].sum().reset_index()
g["group"] = "emp10plus"; g["occupancy_pct"] = 100 * g.used_rooms / g.supply_rooms
d = pd.concat([d, g[d.columns]], ignore_index=True).sort_values(["group", "year"])
d.round(4).to_csv(DATA / "rooms_national.csv", index=False)
print(d.pivot(index="year", columns="group", values="occupancy_pct").round(1).to_string())
