"""369：エネルギーの主役は、石炭から石油へ、いつ入れ替わったのか（1953〜2023年度）。
一次エネルギー国内供給のエネルギー源別の割合。
1953〜1989年度：日本の長期統計系列 10-15-a（旧計算表）／1990〜2013年度：日本統計年鑑 第65回 11-1／2014〜2023年度：日本統計年鑑 第66〜75回 11-1（各年度のバランス表）。
"""
import json, glob, re
import numpy as np, pandas as pd, xlrd, openpyxl
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：資源エネルギー庁「総合エネルギー統計」（総務省統計局「日本の長期統計系列」10-15-a、「日本統計年鑑」第65〜75回 11-1 から）をもとに作成者が加工して作成"
RAW = DATA / "raw"
def rows(f):
    f = str(f)
    if f.endswith(".xls"):
        s = xlrd.open_workbook(f).sheet_by_index(0); return [[s.cell_value(r, c) for c in range(s.ncols)] for r in range(s.nrows)]
    ws = openpyxl.load_workbook(f, data_only=True).worksheets[0]; return [[("" if v is None else v) for v in r] for r in ws.iter_rows(values_only=True)]
num = lambda v: float(v) if isinstance(v, (int, float)) else 0.0
def year_of(r, c=1):
    v = r[c]
    if isinstance(v, (int, float)) and 1900 < v < 2100: return int(v)
    m = re.search(r"(19|20)\d\d", str(v)); return int(m.group()) if m else None
# 旧計算表（1953〜2000年度）
R = rows(RAW / "chouki_10-15-a.xls"); rec = []
for r in R:
    y = year_of(r)
    if y: rec.append({"fy": y, "total": num(r[2]), "coal": num(r[7]) + num(r[8]), "oil": num(r[9]) + num(r[10]), "gas": num(r[11]), "hydro": num(r[12]), "nuclear": num(r[13]), "other": num(r[14]) + num(r[15])})
OLD = pd.DataFrame(rec).set_index("fy")
# 1990〜2013年度（年鑑第65回）
R = rows(RAW / "nenkan65_1101.xls"); rec = []
for r in R:
    y = year_of(r)
    if y: rec.append({"fy": y, "total": num(r[3]), "coal": num(r[8]) + num(r[9]), "oil": num(r[10]) + num(r[11]), "gas": num(r[12]), "other": num(r[13]), "hydro": num(r[14]), "nuclear": num(r[15])})
MID = pd.DataFrame(rec).set_index("fy")
# 2014〜2023年度（年鑑第66〜75回、各年度）
ERA = {"平成26": 2014, "平成27": 2015, "平成28": 2016, "平成29": 2017, "平成30": 2018, "令和元": 2019, "令和２": 2020, "令和３": 2021, "令和４": 2022, "令和５": 2023}
rec = []
for f in sorted(glob.glob(str(RAW / "nenkan*_1101.xls*"))):
    if "nenkan65" in f: continue
    R = rows(f); title = str(R[0][0]); y = next(v for k, v in ERA.items() if k in title)
    hdr = next(r for r in R if "石炭" in [str(x).strip() for x in r]); h = [str(x).replace("\n", "").strip() for x in hdr]
    dom = next(r for r in R if any(str(x).strip().startswith("一次エネルギー国内供給") for x in r))
    g = lambda key: sum(num(dom[j]) for j, t in enumerate(h) if t.startswith(key))
    rec.append({"fy": y, "total": g("合計"), "coal": g("石炭"), "oil": g("原油") + g("石油製品"), "gas": g("天然ガス") + g("都市ガス"),
                "other": g("再生可能") + g("未活用"), "hydro": g("水力発電") + g("事業用水力"), "nuclear": g("原子力")})
NEW = pd.DataFrame(rec).set_index("fy").sort_index()
SRCS = ["coal", "oil", "gas", "hydro", "nuclear", "other"]
for D in (OLD, MID, NEW): D["resid"] = D.total - D[SRCS].sum(axis=1)
T = pd.concat([OLD.loc[:1989].assign(basis="旧計算表"), MID.assign(basis="年鑑65"), NEW.assign(basis="年鑑66-75")])
S = T[SRCS].div(T[SRCS].sum(axis=1), axis=0) * 100
S["fossil"] = S.coal + S.oil + S.gas; S["basis"] = T.basis; S["total_pj"] = T.total
S.round(3).to_csv(DATA / "primary_energy_shares_fy1953_2023.csv")
SO = OLD[SRCS].div(OLD[SRCS].sum(axis=1), axis=0) * 100; SM = MID[SRCS].div(MID[SRCS].sum(axis=1), axis=0) * 100
ov = {k: {"mean_diff": round(float((SO[k] - SM[k]).dropna().mean()), 2), "max_abs": round(float((SO[k] - SM[k]).dropna().abs().max()), 2)} for k in SRCS}
def cross(a, b):
    d = a - b; return [int(y) for y in d.index[1:] if d[y] > 0 and d[y - 1] <= 0]
def pk(sr): return {"fy": int(sr.idxmax()), "share": round(float(sr.max()), 1)}
def mn(sr): return {"fy": int(sr.idxmin()), "share": round(float(sr.min()), 1)}
res = {"years": [int(S.index.min()), int(S.index.max())], "resid_max_abs_pct": {"old": round(float((OLD.resid / OLD.total).abs().max() * 100), 2), "mid": round(float((MID.resid / MID.total).abs().max() * 100), 2), "new": round(float((NEW.resid / NEW.total).abs().max() * 100), 2)},
       "overlap_1990_2000_share_diff_pt": ov,
       "share": {int(y): {k: round(float(S.loc[y, k]), 1) for k in SRCS + ["fossil"]} for y in [1953, 1955, 1960, 1961, 1962, 1965, 1970, 1973, 1975, 1979, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2011, 2012, 2013, 2014, 2015, 2020, 2023]},
       "oil_over_coal": cross(S.oil, S.coal), "oil_over_50": int(S.oil[S.oil > 50].index.min()), "oil_below_50_after_peak": int(S.oil.loc[1973:][S.oil.loc[1973:] < 50].index.min()),
       "oil_below_40": int(S.oil.loc[1973:][S.oil.loc[1973:] < 40].index.min()),
       "coal_below_30": int(S.coal[S.coal < 30].index.min()), "coal_below_20": int(S.coal[S.coal < 20].index.min()),
       "peak": {k: pk(S[k]) for k in SRCS + ["fossil"]}, "min": {"coal": mn(S.coal), "oil_after_1973": mn(S.oil.loc[1973:]), "fossil_after_1973": mn(S.fossil.loc[1973:]), "nuclear_after_2011": mn(S.nuclear.loc[2011:])},
       "oil_1973_to_1985_pt": round(float(S.oil.loc[1985] - S.oil.loc[1973]), 1), "replaced_1973_1985": {k: round(float(S.loc[1985, k] - S.loc[1973, k]), 1) for k in SRCS},
       "oil_per_year_1953_1973": round(float((S.oil.loc[1973] - S.oil.loc[1953]) / 20), 2), "oil_per_year_1973_1985": round(float((S.oil.loc[1985] - S.oil.loc[1973]) / 12), 2),
       "oil_per_year_1985_2010": round(float((S.oil.loc[2010] - S.oil.loc[1985]) / 25), 2),
       "coal_over_gas_last": {"coal_2023": round(float(S.coal.loc[2023]), 1), "gas_2023": round(float(S.gas.loc[2023]), 1)},
       "gas_over_coal": cross(S.gas, S.coal), "coal_over_gas": cross(S.coal, S.gas),
       "total_pj": {int(y): round(float(T.total.loc[y]), 0) for y in [1953, 1973, 1990, 2000, 2010, 2023]}, "total_peak": {"fy": int(T.total.idxmax()), "pj": round(float(T.total.max()), 0)},
       "total_x_1953_1973": round(float(T.total.loc[1973] / T.total.loc[1953]), 1), "oil_pj_x_1953_1973": round(float(T.oil.loc[1973] / T.oil.loc[1953]), 1), "coal_pj_x_1953_1973": round(float(T.coal.loc[1973] / T.coal.loc[1953]), 2),
       "oil_pj": {int(y): round(float(T.oil.loc[y]), 0) for y in [1953, 1961, 1973, 1985, 1996, 2010, 2023]}, "oil_pj_peak": {"fy": int(T.oil.idxmax()), "pj": round(float(T.oil.max()), 0)},
       "coal_pj": {int(y): round(float(T.coal.loc[y]), 0) for y in [1953, 1961, 1973, 1985, 2010, 2023]}, "coal_pj_peak": {"fy": int(T.coal.idxmax()), "pj": round(float(T.coal.max()), 0)}}
json.dump(res, open(RES / "a369_main.json", "w"), ensure_ascii=False, indent=1)

JP = {"coal": "石炭", "oil": "石油", "gas": "天然ガス", "hydro": "水力", "nuclear": "原子力", "other": "再生可能エネルギーなど"}
COL = {"coal": INK, "oil": ORANGE, "gas": BLUE, "hydro": LIGHT, "nuclear": GREEN, "other": GRAY}
# 図1：割合の推移
fig, ax = plt.subplots(figsize=(9.4, 4.7))
for k in SRCS:
    ax.plot(S.index, S[k], color=COL[k], lw=2.1 if k in ("coal", "oil") else 1.6)
    ax.annotate(f"{JP[k]} {S[k].iloc[-1]:.0f}%", (S.index[-1], S[k].iloc[-1]), xytext=(5, {"hydro": -7, "nuclear": 5}.get(k, 0)), textcoords="offset points", fontsize=8.5, va="center", color=INK)
c = res["oil_over_coal"][0]; ax.annotate(f"{c}年度に石油が石炭を上回る", (c, S.oil.loc[c]), xytext=(c + 2, 22), fontsize=8.5, arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.7))
p = res["peak"]["oil"]; ax.annotate(f"{p['fy']}年度 {p['share']:.0f}%", (p["fy"], p["share"]), xytext=(p["fy"] + 2, p["share"] + 2), fontsize=8.5)
for x0 in (1989.5, 2013.5): ax.axvline(x0, color=GRAY, lw=0.6, ls=":")
ax.set_xlim(1951, 2037); ax.set_ylim(0, 86); ax.set_ylabel("一次エネルギー国内供給に占める割合（%）")
ax.set_title(f"石油は{c}年度に石炭を上回り、{p['fy']}年度の{p['share']:.0f}%が山。そこから50年で{S.oil.iloc[-1]:.0f}%に")
save(fig, "a369_shares.png", SRC + "\n点線の前後（1989／1990年度、2013／2014年度）で、もとの表の作り方が変わる。石油＝原油＋石油製品、石炭＝石炭＋石炭製品")

# 図2：量（ペタジュール）
fig, ax = plt.subplots(figsize=(9.4, 4.5)); bot = np.zeros(len(T))
for k in ["coal", "oil", "gas", "hydro", "nuclear", "other"]:
    v = T[k].clip(lower=0).values; ax.bar(T.index, v, bottom=bot, color=COL[k], width=0.9, label=JP[k]); bot += v
ax.set_ylabel("ペタジュール"); ax.set_title(f"供給の量は1953→1973年度に{res['total_x_1953_1973']:.0f}倍。増えた分のほとんどが石油だった")
ax.legend(frameon=False, ncol=6, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
save(fig, "a369_supply_pj.png", SRC, y=-0.07)

# 図3：1973→1985年度、石油が減った分を何が埋めたか
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axes[0]; d = pd.Series(res["replaced_1973_1985"]); order = ["oil", "gas", "nuclear", "coal", "other", "hydro"]
ax.barh([JP[k] for k in order][::-1], [d[k] for k in order][::-1], color=[COL[k] for k in order][::-1])
for i, k in enumerate(order[::-1]): ax.text(d[k] + (0.6 if d[k] >= 0 else -0.6), i, f"{d[k]:+.1f}", va="center", ha="left" if d[k] >= 0 else "right", fontsize=9)
ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-27, 14); ax.set_xlabel("割合の変化（ポイント）"); ax.set_title("1973→1985年度の割合の変化", fontsize=11)
ax = axes[1]
ax.plot(S.index, S.fossil, color=INK, lw=2); ax.set_ylim(50, 100); ax.set_ylabel("%"); ax.set_title("石炭・石油・天然ガスの合計の割合", fontsize=11)
for y, dx, dy in [(1953, 26, -8), (1973, 0, 8), (2010, -4, -30), (2012, 4, 9), (2023, 2, -30)]:
    ax.annotate(f"{y}年度\n{S.fossil.loc[y]:.0f}%", (y, S.fossil.loc[y]), xytext=(dx, dy), textcoords="offset points", ha="center", fontsize=8)
fig.suptitle("石油危機のあと、石油が減った分は天然ガスと原子力が埋めた", fontsize=12.5, y=1.0); fig.tight_layout()
save(fig, "a369_after_oil_crisis.png", SRC)
print(json.dumps(res, ensure_ascii=False)[:5000])
