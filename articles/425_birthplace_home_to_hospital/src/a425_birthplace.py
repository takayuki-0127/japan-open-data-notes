"""A425 出生の場所（施設内・自宅）の入れ替わり。人口動態統計 上巻 4-7（市部・郡部別）"""
import csv, json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
SRC = "出典：厚生労働省「人口動態統計」（2025年確定数 上巻 4-7・4-8 出生の場所別にみた出生数）をもとに作成者が加工して作成"
num = lambda s: float(str(s).replace(",", "")) if str(s).strip() not in ("-", "…", "") else np.nan
raw = [r for r in csv.reader(open(DATA / "jinkou_r7_jokan_4-7_birthplace.csv", encoding="utf-8"))]
area = None; rec = []
for r in raw:
    if not r: continue
    k = r[0].replace("　", "").replace(" ", "")
    if k in ("全国", "市部", "郡部"): area = k; continue
    if r[0].strip().isdigit() and area:
        rec.append([area, int(r[0])] + [num(x) for x in r[1:7]])
d = pd.DataFrame(rec, columns=["area", "year", "total", "inst", "hospital", "clinic", "midwife", "home"])
for c in ["inst", "hospital", "clinic", "midwife", "home"]: d[c + "_pct"] = d[c] / d.total * 100
d.to_csv(RES / "a425_birthplace.csv", index=False)
# 公表の百分率（4-8）と突き合わせ
pub = [r for r in csv.reader(open(DATA / "jinkou_r7_jokan_4-8_birthplace_pct.csv", encoding="utf-8"))]
area = None; chk = []
for r in pub:
    if not r: continue
    k = r[0].replace("　", "").replace(" ", "")
    if k in ("全国", "市部", "郡部"): area = k; continue
    if r[0].strip().isdigit() and area: chk.append([area, int(r[0]), num(r[2]), num(r[6])])
c = pd.DataFrame(chk, columns=["area", "year", "inst_pub", "home_pub"]).merge(d, on=["area", "year"])
maxdiff = float((c.inst_pct.round(1) - c.inst_pub).abs().max())
N = d[d.area == "全国"].set_index("year"); S = d[d.area == "市部"].set_index("year"); G = d[d.area == "郡部"].set_index("year")
out = {"max_diff_vs_published_pct": round(maxdiff, 2), "years": [int(x) for x in N.index]}
for y in [1947, 1950, 1955, 1960, 1965, 1970, 1975, 1980, 1990, 2000, 2010, 2020, 2025]:
    out[f"y{y}"] = {"national": {k: (None if pd.isna(N.loc[y, k]) else round(float(N.loc[y, k]), 1)) for k in ["inst_pct", "hospital_pct", "clinic_pct", "midwife_pct", "home_pct"]},
                    "home_n": int(N.loc[y, "home"]), "shi_inst": round(float(S.loc[y, "inst_pct"]), 1), "gun_inst": round(float(G.loc[y, "inst_pct"]), 1)}
def cross(T, t):
    """調査年のあいだを直線でつないで、割合が t を超えた時期を出す（1947〜2010年は5年おきの数字しかない）"""
    ys = list(T.index)
    for y0, y1 in zip(ys[:-1], ys[1:]):
        v0, v1 = T.loc[y0, "inst_pct"], T.loc[y1, "inst_pct"]
        if v0 < t <= v1: return {"between": [int(y0), int(y1)], "interp": round(y0 + (y1 - y0) * (t - v0) / (v1 - v0), 1)}
out["cross"] = {a: {str(t): cross(T, t) for t in [10, 50, 90, 99]} for a, T in [("national", N), ("shi", S), ("gun", G)]}
out["years_50_to_90"] = {a: round(out["cross"][a]["90"]["interp"] - out["cross"][a]["50"]["interp"], 1) for a in ["national", "shi", "gun"]}
out["years_10_to_90"] = {a: round(out["cross"][a]["90"]["interp"] - out["cross"][a]["10"]["interp"], 1) for a in ["national", "shi", "gun"]}
out["gap_shi_gun"] = {str(y): round(float(S.loc[y, "inst_pct"] - G.loc[y, "inst_pct"]), 1) for y in [1947, 1950, 1955, 1960, 1965, 1970, 1975, 1980]}
out["midwife_peak"] = {"year": int(N.midwife_pct.idxmax()), "pct": round(float(N.midwife_pct.max()), 1), "n": int(N.loc[N.midwife_pct.idxmax(), "midwife"])}
out["clinic_peak"] = {"year": int(N.clinic_pct.idxmax()), "pct": round(float(N.clinic_pct.max()), 1)}
out["hospital_over_half_first"] = int(N[N.hospital_pct >= 50].index[0])
out["home_min"] = {"year": int(N.home.idxmin()), "n": int(N.home.min())}
out["home_1990_vs_2005"] = {"1990": int(N.loc[1990, "home"]), "2005": int(N.loc[2005, "home"]), "2025": int(N.loc[2025, "home"])}
out["home_1950_1960_change"] = {"births": int(N.loc[1960, "total"] - N.loc[1950, "total"]), "home": int(N.loc[1960, "home"] - N.loc[1950, "home"]), "inst": int(N.loc[1960, "inst"] - N.loc[1950, "inst"])}
# 全国の施設内の割合の上がり（1950→1970）を、市部・郡部それぞれの中の変化と、市部に住む人が増えた分に分ける
def decomp(y0, y1):
    w0 = np.array([S.loc[y0, "total"], G.loc[y0, "total"]]); w0 = w0 / w0.sum(); w1 = np.array([S.loc[y1, "total"], G.loc[y1, "total"]]); w1 = w1 / w1.sum()
    p0 = np.array([S.loc[y0, "inst_pct"], G.loc[y0, "inst_pct"]]); p1 = np.array([S.loc[y1, "inst_pct"], G.loc[y1, "inst_pct"]])
    within = float((((w0 + w1) / 2) * (p1 - p0)).sum()); between = float((((p0 + p1) / 2) * (w1 - w0)).sum())
    return {"total": round(within + between, 1), "within": round(within, 1), "between": round(between, 1), "shi_share_births": [round(float(w0[0] * 100), 1), round(float(w1[0] * 100), 1)]}
out["decomp_1950_1970"] = decomp(1950, 1970); out["decomp_1950_1960"] = decomp(1950, 1960)
# 頑健性：1947年は「事件発生地」、1950年は「母の住所地」、1955年以降は「子の住所地」で数えている（表の注）
out["note_definition"] = "1947年は事件発生地、1950年は母の住所地、1955年以降は子の住所地"
json.dump(out, open(RES / "a425_main.json", "w"), ensure_ascii=False, indent=1)

fig, ax = plt.subplots(figsize=(9, 4.8)); m = N[N.index >= 1950]
ax.stackplot(m.index, m.hospital_pct, m.clinic_pct, m.midwife_pct, m.home_pct, colors=[BLUE, LIGHT, GREEN, ORANGE], labels=["病院", "診療所", "助産所", "自宅・その他"])
ax.set_xlim(1950, 2025); ax.set_ylim(0, 100); ax.legend(frameon=True, facecolor="white", framealpha=.9, loc="center right"); ax.set_ylabel("出生に占める割合（%）")
ax.set_title("自宅での出生は1950年の95%から、1960年に5割、1970年に4%になった"); save(fig, "a425_stack.png", SRC + "（1947年は施設の内訳がないため1950年から）")
fig, ax = plt.subplots(figsize=(9, 4.8)); mm = d[d.year <= 1990]
for a_, col in [("市部", BLUE), ("郡部", ORANGE), ("全国", INK)]:
    t = mm[mm.area == a_]; ax.plot(t.year, t.inst_pct, color=col, lw=2.2, marker="o", ms=4, label=a_)
    for y in [1950, 1960, 1970]: ax.annotate(f"{t.set_index('year').loc[y,'inst_pct']:.0f}%", (y, t.set_index("year").loc[y, "inst_pct"]), textcoords="offset points", xytext=(6, -12 if a_ == "郡部" else 6), fontsize=8.5, color=col)
ax.axhline(50, color="#cccccc", lw=.8); ax.axhline(90, color="#cccccc", lw=.8); ax.set_ylim(0, 102); ax.legend(frameon=False, loc="lower right"); ax.set_ylabel("病院・診療所・助産所での出生の割合（%）")
ax.set_title("市部は1950年代後半に、郡部は1960年代前半に5割を超えた"); save(fig, "a425_shi_gun.png", SRC)
fig, ax = plt.subplots(figsize=(9, 4.8)); m = N[N.index >= 1950]
ax.plot(m.index, m.hospital_pct, color=BLUE, lw=2.2, label="病院"); ax.plot(m.index, m.clinic_pct, color=GRAY, lw=2.2, label="診療所"); ax.plot(m.index, m.midwife_pct, color=GREEN, lw=2.2, label="助産所")
ax.legend(frameon=False); ax.set_ylabel("出生に占める割合（%）"); ax.set_title("助産所での出生は1965年の13%が山で、1990年からは1%以下"); save(fig, "a425_facility_type.png", SRC)
print(json.dumps(out, ensure_ascii=False))
