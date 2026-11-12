"""298 1人あたりの住まいの広さは、広くなったのか（住宅・土地統計調査 時系列 第13表・第14-1表・第27表）

- 1人当たり居住室の畳数を、「1住宅当たりの畳数」と「1住宅当たりの人数」に分ける
  （1住宅当たりの人数 = 1住宅当たり畳数 ÷ 1人当たり畳数、で求める。平均どうしの比なので近似）
- 1人当たり畳数の分布（全国の主世帯）：6畳未満と15畳以上の割合（1988 → 2023）
- 持ち家・借家、建て方別
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, rows, num, year_from_label, save_json, savefig, setup_font, DATA

setup_font()
D = load()

# --- 第14-1表（所有の関係別、1968〜2023） ---
R = rows(D["t045__014_1"])
SECT = {"１住宅当たり居住室数": "rooms", "１住宅当たり居住室の畳数": "tatami_dw", "１住宅当たり延べ面積": "floor_dw",
        "住宅の１人当たり居住室の畳数": "tatami_pp", "住宅の１室当たり人員": "pp_room"}
COLS = ["総数", "持ち家", "借家", "公営の借家", "UR・公社の借家", "民営借家（木造・設備専用）", "民営借家（木造・設備共用）",
        "民営借家（非木造・設備専用）", "民営借家（非木造・設備共用）", "給与住宅"]
recs, sect, seen = [], None, set()
for r in R:
    lab = r[1]
    for k, v in SECT.items():
        if lab.startswith(k):
            sect = v
    if sect and r[2].isdigit() and len(r[2]) == 4:
        y = int(r[2])
        key = (sect, y)
        # 1973年は沖縄を含まない値と含む値の2行がある。沖縄を含む2行目を使う
        vals = [num(x) for x in r[4:14]]
        rec = dict(sect=sect, year=y, **dict(zip(COLS, vals)))
        if key in seen:
            recs = [x for x in recs if not (x["sect"] == sect and x["year"] == y)]
        seen.add(key); recs.append(rec)
t14 = pd.DataFrame(recs)
t14.to_csv(os.path.join(DATA, "t14_by_tenure_long.csv"), index=False)
W = t14.pivot(index="year", columns="sect", values="総数")
W["persons_dw"] = W.tatami_dw / W.tatami_pp            # 1住宅当たりの人数（近似）
W["floor_pp"] = W.floor_dw / W.persons_dw              # 1人当たり延べ面積（近似）
W.round(3).to_csv(os.path.join(DATA, "national_series.csv"))

def lchg(a, b, col):
    return float(np.log(W.loc[b, col] / W.loc[a, col]))
def decomp(a, b):
    tpp = lchg(a, b, "tatami_pp"); tdw = lchg(a, b, "tatami_dw"); pdw = lchg(a, b, "persons_dw")
    return dict(period=f"{a}-{b}", tatami_pp_ratio=round(W.loc[b, "tatami_pp"] / W.loc[a, "tatami_pp"], 3),
                share_from_bigger_dwellings=round(tdw / tpp * 100, 1), share_from_fewer_persons=round(-pdw / tpp * 100, 1),
                tatami_dw=(round(W.loc[a, "tatami_dw"], 2), round(W.loc[b, "tatami_dw"], 2)),
                persons_dw=(round(W.loc[a, "persons_dw"], 3), round(W.loc[b, "persons_dw"], 3)),
                tatami_pp=(W.loc[a, "tatami_pp"], W.loc[b, "tatami_pp"]))
dec = [decomp(1968, 2023), decomp(1968, 2003), decomp(2003, 2023), decomp(1993, 2023)]

# --- 第13表（建て方別、1993〜2023） ---
R = rows(D["t044__013"])
recs13, sect = [], None
for r in R:
    lab = r[1]
    for k, v in SECT.items():
        if lab.startswith(k):
            sect = v
    if sect and r[2].isdigit() and len(r[2]) == 4:
        recs13.append(dict(sect=sect, year=int(r[2]), 総数=num(r[4]), 一戸建=num(r[5]), 長屋建=num(r[6]), 共同住宅=num(r[7]), その他=num(r[8])))
t13 = pd.DataFrame(recs13)
t13.to_csv(os.path.join(DATA, "t13_by_building_long.csv"), index=False)
b13 = t13[t13.sect == "tatami_pp"].set_index("year")[["一戸建", "共同住宅"]]
f13 = t13[t13.sect == "floor_dw"].set_index("year")[["一戸建", "共同住宅"]]

# --- 第27表（1人当たり畳数の分布、全国） ---
dist = {}
for k in sorted(x for x in D if x.startswith("t062__")):
    R = rows(D[k]); y = None
    ncls = 14 if any("18.0畳以上" in c for r in R[:12] for c in r) else 13
    for r in R:
        yy = year_from_label(r[1]) if r[1].startswith("その") else None
        if yy: y = yy
        if y and (r[2] == "Japan" or r[3] == "Japan" or r[2] == "全国"):
            off = 3 if r[2] == "Japan" else 4
            vals = [num(x) for x in r[off:off + 1 + ncls]]
            dist[y] = vals; break
# 階級：総数, 3未満(2.9以下), 3.0-3.4, 3.5-3.9, 4.0-4.4, 4.5-4.9, 5.0-5.9, 6.0-6.9, 7.0-7.9, 8.0-8.9, 9.0-9.9, 10-11.9, 12-14.9, 15以上(2023は15-17.9と18以上)
dd = []
for y, v in sorted(dist.items()):
    tot = v[0]; cls = v[1:]
    under6 = sum(cls[0:6]); over15 = sum(x for x in cls[12:] if x is not None)
    known = sum(x for x in cls if x is not None)
    dd.append(dict(year=y, total=tot, known=known, under6=round(under6 / tot * 100, 2), over15=round(over15 / tot * 100, 2),
                   under6_known=round(under6 / known * 100, 2), over15_known=round(over15 / known * 100, 2)))
dd = pd.DataFrame(dd); dd.to_csv(os.path.join(DATA, "tatami_pp_distribution_share.csv"), index=False)

T = t14[t14.sect == "tatami_pp"].set_index("year")
out = dict(
    national={int(y): dict(tatami_pp=W.loc[y, "tatami_pp"], tatami_dw=W.loc[y, "tatami_dw"], floor_dw=W.loc[y, "floor_dw"],
                           persons_dw=round(W.loc[y, "persons_dw"], 3), floor_pp=round(W.loc[y, "floor_pp"], 1)) for y in [1968, 1983, 1993, 2003, 2013, 2023]},
    floor_dw_peak_year=int(W.floor_dw.idxmax()), floor_dw_peak=float(W.floor_dw.max()),
    decomposition=dec,
    tenure_tatami_pp={int(y): dict(持ち家=T.loc[y, "持ち家"], 借家=T.loc[y, "借家"], 民営非木造専用=T.loc[y, "民営借家（非木造・設備専用）"]) for y in [1993, 2003, 2023]},
    tenure_floor_dw={int(y): dict(持ち家=t14[(t14.sect == "floor_dw") & (t14.year == y)]["持ち家"].iloc[0], 借家=t14[(t14.sect == "floor_dw") & (t14.year == y)]["借家"].iloc[0]) for y in [1993, 2003, 2023]},
    building_tatami_pp={int(y): b13.loc[y].to_dict() for y in [1993, 2023]},
    building_floor_dw={int(y): f13.loc[y].to_dict() for y in [1993, 2003, 2023]},
    distribution={int(r.year): dict(under6=r.under6, over15=r.over15, under6_known=r.under6_known, over15_known=r.over15_known) for r in dd.itertuples()},
)
save_json("a298_main.json", out)

# --- 図 ---
fig, ax = plt.subplots(figsize=(7.5, 4.5))
base = W.loc[1968]
for col, lab, c in [("tatami_pp", "1人当たりの畳数", "#d62728"), ("tatami_dw", "1住宅当たりの畳数", "#1f77b4"), ("persons_dw", "1住宅当たりの人数", "#7f7f7f")]:
    s = W[col] / base[col] * 100
    ax.plot(W.index, s, marker="o", ms=3.5, lw=2, color=c, label=lab)
    ax.text(2024, s.loc[2023], f"{lab}\n{W.loc[2023, col]:.2f}" + ("人" if col == "persons_dw" else "畳"), fontsize=8.5, color=c, va="center")
ax.axhline(100, color="gray", lw=0.8, ls=":")
ax.axvline(2003, color="gray", lw=0.6, ls="--"); ax.text(2003.5, 268, "2003年", fontsize=8, color="gray")
ax.set_xlim(1965, 2034); ax.set_ylabel("1968年を100とした値")
ax.set_title("2003年からは家は広くならず、1人当たりは人数が減った分だけ広がった", fontsize=10.5)
ax.text(1966, 38, "出典：総務省「住宅・土地統計調査」時系列表 第14-1表。人数は畳数÷1人当たり畳数で求めた近似", fontsize=7.2, color="gray")
ax.set_ylim(35, 280)
savefig(fig, "a298_decompose.png")

fig, ax = plt.subplots(figsize=(7.2, 4.2))
yrs = [1988, 1998, 2008, 2023]
x = np.arange(len(yrs)); wd = 0.38
u = [float(dd[dd.year == y].under6.iloc[0]) for y in yrs]; o = [float(dd[dd.year == y].over15.iloc[0]) for y in yrs]
ax.bar(x - wd / 2, u, wd, color="#d62728", label="1人当たり6畳未満")
ax.bar(x + wd / 2, o, wd, color="#1f77b4", label="1人当たり15畳以上")
for i in range(len(yrs)):
    ax.text(x[i] - wd / 2, u[i] + 0.8, f"{u[i]:.1f}%", ha="center", fontsize=9)
    ax.text(x[i] + wd / 2, o[i] + 0.8, f"{o[i]:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x, [f"{y}年" for y in yrs]); ax.set_ylabel("主世帯に占める割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, 52)
ax.set_title("狭い住まいの世帯は5分の1から20分の1に、広い住まいの世帯は半分近くに", fontsize=10.5)
savefig(fig, "a298_distribution.png")

fig, ax = plt.subplots(figsize=(7.5, 4.3))
for col, c in [("持ち家", "#2ca02c"), ("借家", "#ff7f0e"), ("民営借家（非木造・設備専用）", "#9467bd"), ("公営の借家", "#8c564b")]:
    s = T[col].dropna()
    ax.plot(s.index, s, marker="o", ms=3.2, lw=1.8, color=c, label=col)
    dy = {"借家": 0.12, "民営借家（非木造・設備専用）": -0.3}.get(col, 0)
    ax.text(2024, s.loc[2023] + dy, f"{col.replace('（非木造・設備専用）', '(非木造)')} {s.loc[2023]:.1f}", fontsize=8.3, color=c, va="center")
ax.set_xlim(1965, 2036); ax.set_ylabel("1人当たり居住室の畳数（畳）")
ax.set_title("1人当たりの畳数は持ち家・借家とも増え、差は4.3畳から5.5畳に", fontsize=10.5)
savefig(fig, "a298_tenure.png")
