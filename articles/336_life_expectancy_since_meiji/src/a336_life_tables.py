"""336：平均寿命が44歳だった時代に、65歳まで生きた人はあと何年生きたのか。
完全生命表 第1回（1891〜98年）〜第19回（2000年）と第23回（2020年）の生存数・平均余命を並べ、
0歳の平均余命の延びを年齢ごとに分ける（Arriaga の分け方）。
"""
import json, re
import numpy as np, pandas as pd, xlrd, openpyxl
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：厚生労働省「完全生命表」（総務省統計局「日本の長期統計系列」2-35、第23回生命表）をもとに作成者が加工して作成"
PERIOD = {1: (1891, 1898), 2: (1899, 1903), 3: (1909, 1913), 4: (1921, 1925), 5: (1926, 1930), 6: (1935, 1936), 8: (1947, 1947), 9: (1950, 1952),
          10: (1955, 1955), 11: (1960, 1960), 12: (1965, 1965), 13: (1970, 1970), 14: (1975, 1975), 15: (1980, 1980), 16: (1985, 1985),
          17: (1990, 1990), 18: (1995, 1995), 19: (2000, 2000), 23: (2020, 2020)}
num = lambda v: float(v) if isinstance(v, (int, float)) else np.nan

# ---- 第1〜19回（長期統計系列 2-35）
s = xlrd.open_workbook(DATA / "raw" / "chouki_02-35.xls").sheet_by_index(0)
head = s.row_values(3)
rec = []
for c in range(2, s.ncols, 6):
    m = re.search(r"第\s*([0-9０-９]+)\s*回", str(head[c]).replace("１", "1").replace("8", "8"))
    if not m:
        continue
    t = int(m.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789")))
    for r in range(9, s.nrows):
        a = re.sub(r"[\s　歳]", "", str(s.cell_value(r, 0)))
        if not re.fullmatch(r"\d+(\.0)?", a):
            continue
        age = int(float(a))
        for k, sex in ((0, "男"), (3, "女")):
            lx, qx, ex = (num(s.cell_value(r, c + k + j)) for j in range(3))
            if not np.isnan(lx):
                rec.append((t, sex, age, lx, qx, ex))
# ---- 第23回（e-Stat）
for f, sex in (("lt23_male.xlsx", "男"), ("lt23_female.xlsx", "女")):
    ws = openpyxl.load_workbook(DATA / "raw" / f, data_only=True).worksheets[0]
    for row in ws.iter_rows(values_only=True):
        a = str(row[1] or "")
        if re.fullmatch(r"\d+年", a) and isinstance(row[2], (int, float)):
            rec.append((23, sex, int(a[:-1]), float(row[2]), float(row[5]), float(row[9])))
L = pd.DataFrame(rec, columns=["table", "sex", "age", "lx", "qx", "ex"]).drop_duplicates(["table", "sex", "age"])
L["start"] = L.table.map(lambda t: PERIOD[t][0]); L["end"] = L.table.map(lambda t: PERIOD[t][1])
L = L.sort_values(["table", "sex", "age"]); L.to_csv(DATA / "life_tables.csv", index=False)
TAB = sorted(L.table.unique())
g = {(t, sx): d.set_index("age") for (t, sx), d in L.groupby(["table", "sex"])}

# ---- 各回の主な数字
rows = []
for t in TAB:
    for sx in ("男", "女"):
        d = g[(t, sx)]
        rows.append({"table": t, "start": PERIOD[t][0], "end": PERIOD[t][1], "sex": sx, "e0": d.ex[0], "e20": d.ex[20], "e40": d.ex[40], "e65": d.ex[65], "e80": d.ex[80],
                     "surv1": d.lx[1] / 1000, "surv5": d.lx[5] / 1000, "surv20": d.lx[20] / 1000, "surv65": d.lx[65] / 1000, "surv80": d.lx[80] / 1000,
                     "surv65_given20": d.lx[65] / d.lx[20] * 100, "age_death_if65": 65 + d.ex[65]})
M = pd.DataFrame(rows); M.to_csv(RES / "summary_by_table.csv", index=False)

# ---- 0歳の平均余命の延びを年齢で分ける（Arriaga）
GROUPS = [(0, 1, "0歳"), (1, 5, "1〜4歳"), (5, 15, "5〜14歳"), (15, 40, "15〜39歳"), (40, 65, "40〜64歳"), (65, 80, "65〜79歳"), (80, None, "80歳以上")]
def arriaga(A, B):
    TA, TB = A.lx * A.ex, B.lx * B.ex
    out = []
    for a, b, name in GROUPS:
        if b is None:
            d = A.lx[a] / A.lx[0] * (TB[a] / B.lx[a] - TA[a] / A.lx[a])
        else:
            LA, LB = TA[a] - TA[b], TB[a] - TB[b]
            d = A.lx[a] / A.lx[0] * (LB / B.lx[a] - LA / A.lx[a]) + TB[b] / A.lx[0] * (A.lx[a] / B.lx[a] - A.lx[b] / B.lx[b])
        out.append(d)
    return np.array(out)
dec = []
PAIRS = [(1, 23), (1, 6), (6, 12), (12, 23), (1, 8), (8, 23)]
for a, b in PAIRS:
    for sx in ("男", "女"):
        c = arriaga(g[(a, sx)], g[(b, sx)])
        tot = g[(b, sx)].ex[0] - g[(a, sx)].ex[0]
        for (lo, hi, name), v in zip(GROUPS, c):
            dec.append({"from": a, "to": b, "sex": sx, "age_group": name, "years": v, "share_pct": v / tot * 100, "e0_gain": tot, "sum_check": c.sum()})
D = pd.DataFrame(dec); D.to_csv(RES / "decomposition.csv", index=False)

def sh(a, b, sx, names):
    d = D[(D["from"] == a) & (D.to == b) & (D.sex == sx)]
    return round(float(d[d.age_group.isin(names)].share_pct.sum()), 1), round(float(d[d.age_group.isin(names)].years.sum()), 2)
mm = M.set_index(["table", "sex"])
out = {"tables": [int(t) for t in TAB]}
for sx in ("男", "女"):
    o = {}
    for t in (1, 4, 6, 8, 12, 19, 23):
        o[str(t)] = {k: round(float(mm.loc[(t, sx), k]), 2) for k in ("e0", "e20", "e40", "e65", "e80", "surv1", "surv5", "surv20", "surv65", "surv80", "surv65_given20", "age_death_if65")}
    o["gain_1_to_23"] = {k: round(float(mm.loc[(23, sx), k] - mm.loc[(1, sx), k]), 2) for k in ("e0", "e20", "e40", "e65", "e80")}
    o["ratio_1_to_23"] = {k: round(float(mm.loc[(23, sx), k] / mm.loc[(1, sx), k]), 2) for k in ("e0", "e65")}
    for a, b in PAIRS:
        o[f"dec_{a}_{b}"] = {"under1": sh(a, b, sx, ["0歳"]), "under5": sh(a, b, sx, ["0歳", "1〜4歳"]), "under15": sh(a, b, sx, ["0歳", "1〜4歳", "5〜14歳"]),
                             "15_64": sh(a, b, sx, ["15〜39歳", "40〜64歳"]), "65plus": sh(a, b, sx, ["65〜79歳", "80歳以上"]),
                             "e0_gain": round(float(D[(D["from"] == a) & (D.to == b) & (D.sex == sx)].e0_gain.iloc[0]), 2),
                             "sum_check": round(float(D[(D["from"] == a) & (D.to == b) & (D.sex == sx)].years.sum()), 2)}
    # e65 の延びが始まった時期：回ごとの差
    o["e65_by_table"] = {str(t): round(float(mm.loc[(t, sx), "e65"]), 2) for t in TAB}
    o["e0_by_table"] = {str(t): round(float(mm.loc[(t, sx), "e0"]), 2) for t in TAB}
    out[sx] = o
# 確かめ：分ける向きを逆（新しい表を基準）にしたときの割合
rev = {}
for sx in ("男", "女"):
    c = -arriaga(g[(23, sx)], g[(1, sx)]); tot = c.sum()
    rev[sx] = {"under5": round(float(c[:2].sum() / tot * 100), 1), "15_64": round(float(c[3:5].sum() / tot * 100), 1), "65plus": round(float(c[5:].sum() / tot * 100), 1)}
out["reverse_base_1_23"] = rev
# 確かめ：0歳の定常人口の合計を、生存数の台形で積み直した値と比べる（第1回・第23回）
chk = {}
for t in (1, 23):
    for sx in ("男", "女"):
        d = g[(t, sx)]; lx = d.lx.values
        e0_trap = (lx[:-1] + lx[1:]).sum() / 2 / lx[0] + (0 if np.isnan(d.ex.values[-1]) else lx[-1] * d.ex.values[-1] / lx[0])
        chk[f"{t}_{sx}"] = [round(float(d.ex[0]), 2), round(float(e0_trap), 2)]
out["check_e0_published_vs_trapezoid"] = chk
json.dump(out, open(RES / "a336_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1：0歳・20歳・65歳の平均余命
mid = lambda t: (PERIOD[t][0] + PERIOD[t][1]) / 2
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, sx in zip(axes, ("男", "女")):
    d = M[M.sex == sx]; x = [mid(t) for t in d.table]
    for k, c, lab in (("e0", BLUE, "0歳"), ("e20", GREEN, "20歳"), ("e65", ORANGE, "65歳")):
        ax.plot(x, d[k], "-o", color=c, ms=3.5, lw=1.8)
        ax.annotate(f"{lab} {d[k].iloc[0]:.1f}年", (x[0], d[k].iloc[0]), xytext=(4, -15 if k == "e20" else 9), textcoords="offset points", fontsize=8.5, color=c)
        ax.annotate(f"{d[k].iloc[-1]:.1f}年", (x[-1], d[k].iloc[-1]), xytext=(-2, 6), textcoords="offset points", fontsize=8.5, color=c, ha="right")
    ax.set_title(f"{sx}：その年齢まで生きた人の、残りの年数"); ax.set_xlabel("生命表の対象の年"); ax.grid(axis="y", color="#e6e6e3", lw=0.6)
axes[0].set_ylabel("平均余命（年）")
fig.suptitle("0歳の平均余命は約2倍に延びた。65歳の平均余命が延びはじめたのは戦後から", fontsize=12.5, y=1.02)
save(fig, "a336_expectancy.png", SRC + "（第7回は作られていない。2001〜19年の回は使っていない）")

# ---- 図2：10万人のうち、その年齢まで生きている人
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, sx in zip(axes, ("男", "女")):
    for t, c, lab in ((1, GRAY, "1891〜98年"), (6, LIGHT, "1935〜36年"), (12, GREEN, "1965年"), (23, BLUE, "2020年")):
        d = g[(t, sx)]
        ax.plot(d.index, d.lx / 1000, color=c, lw=2, label=lab)
    ax.axvline(65, color=ORANGE, lw=0.8, ls="--")
    for t, c in ((1, GRAY), (23, BLUE)):
        v = g[(t, sx)].lx[65] / 1000
        ax.annotate(f"65歳まで {v:.0f}%", (65, v), xytext=(-62 if t == 1 else 6, -4 if t == 1 else 8), textcoords="offset points", fontsize=9, color=INK)
    ax.set_title(sx); ax.set_xlabel("年齢"); ax.set_xlim(0, 105); ax.grid(axis="y", color="#e6e6e3", lw=0.6)
axes[0].set_ylabel("生まれた人のうち生きている割合（%）"); axes[0].legend(frameon=False, fontsize=9, loc="lower left")
fig.suptitle("最初の生命表では、5歳までに4分の1が亡くなり、65歳まで生きたのは3人に1人ほど", fontsize=12.5, y=1.02)
save(fig, "a336_survival.png", SRC)

# ---- 図3：0歳の平均余命の延び（第1回→第23回）を年齢で分ける
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, sx in zip(axes, ("男", "女")):
    d = D[(D["from"] == 1) & (D.to == 23) & (D.sex == sx)]
    col = [ORANGE, ORANGE, LIGHT, LIGHT, LIGHT, BLUE, BLUE]
    ax.barh(d.age_group[::-1], d.years[::-1], color=col[::-1])
    for y, (v, p) in enumerate(zip(d.years[::-1], d.share_pct[::-1])):
        ax.text(v + 0.2, y, f"{v:.1f}年（{p:.0f}%）", va="center", fontsize=9)
    ax.set_title(f"{sx}：0歳の平均余命 +{d.e0_gain.iloc[0]:.1f}年 の内訳"); ax.set_xlabel("延びた年数"); ax.set_xlim(0, max(D[(D['from'] == 1) & (D.to == 23)].years) * 1.35)
u5 = [out[x]["dec_1_23"]["under5"][0] for x in ("男", "女")]; o65 = [out[x]["dec_1_23"]["65plus"][0] for x in ("男", "女")]
fig.suptitle(f"延びの半分近く（男{u5[0]:.0f}%・女{u5[1]:.0f}%）は5歳未満の死亡が減った分。65歳以上の分は男{o65[0]:.0f}%・女{o65[1]:.0f}%", fontsize=12.5, y=1.02)
save(fig, "a336_decomposition.png", SRC + "。分け方は Arriaga の方法（年齢ごとの死亡率を新しい表に入れ替えたときの寄与）")
print({k: out["女"][k] for k in ("1","23","gain_1_to_23","ratio_1_to_23","dec_1_23","dec_1_6","dec_6_12","dec_12_23","e65_by_table")}); print(out["reverse_base_1_23"]); print(out["男"]["e0_by_table"])
print(out["check_e0_published_vs_trapezoid"])
