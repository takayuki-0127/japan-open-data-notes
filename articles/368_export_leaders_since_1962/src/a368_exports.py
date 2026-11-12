"""368：日本の輸出の主役は、何から何へ入れ替わったのか（1962〜2025年）。
1962〜2004年は「日本の長期統計系列」18-1-b・18-3（外国貿易概況）、1988〜2025年は財務省貿易統計の概況品別の年別推移。
割合は、その年の輸出総額に対する金額の割合。
"""
import json, csv
import numpy as np, pandas as pd, xlrd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：総務省統計局「日本の長期統計系列」18-1-b・18-3（日本関税協会「外国貿易概況」）、財務省「貿易統計」輸出入額の推移（主要商品別）をもとに作成者が加工して作成"
num = lambda v: float(v) if isinstance(v, (int, float)) else np.nan
# --- 長期統計系列 18-1-b（商品分野別、1962〜2004年）
s = xlrd.open_workbook(DATA / "raw" / "chouki_18-01-b.xls").sheet_by_index(0)
B = {"total": 2, "textile": 3, "chemical": 4, "steel": 8, "general_machinery": 11, "electrical": 12, "transport": 13, "precision": 14, "metal_all": 7}
rec = []
for r in range(s.nrows):
    y = s.cell_value(r, 1)
    if isinstance(y, float) and 1900 < y < 2100: rec.append({"year": int(y), **{k: num(s.cell_value(r, c)) for k, c in B.items()}})
OLD = pd.DataFrame(rec).set_index("year")
# --- 長期統計系列 18-3（品別、1969〜2004年）
s = xlrd.open_workbook(DATA / "raw" / "chouki_18-03.xls").sheet_by_index(0)
head = {}; cur = None
for c in range(2, s.ncols):
    a = str(s.cell_value(5, c)).strip(); b = str(s.cell_value(7, c)).strip(); u = str(s.cell_value(9, c)).replace("\n", "").strip()
    if a: cur = a
    if u == "価額": head.setdefault(cur if not b else cur + ">" + b, c)
ITEM = {"cars": "自動車", "car_parts": "自動車の部分品", "ships": "船舶", "semiconductors": "半導体等電子部品", "av_video": "映像機器", "av_audio": "音響機器", "motorcycles": "二輪自動車類",
        "office_machines": "事務用機器", "optical": "科学光学機器"}
rec = []
for r in range(s.nrows):
    y = s.cell_value(r, 1)
    if isinstance(y, float) and 1900 < y < 2100: rec.append({"year": int(y), **{k: num(s.cell_value(r, head[v])) for k, v in ITEM.items()}})
OLDI = pd.DataFrame(rec).set_index("year")
# --- 財務省 貿易統計（概況品別、1988〜2025年、千円）
rows = list(csv.reader(open(DATA / "raw" / "d51ca.csv", encoding="cp932")))
hdr, nm, code = rows[2], rows[3], rows[4]
lab = {}
for j in range(2, len(hdr), 2):
    key = (hdr[j].strip() or nm[j].strip()); lab[(key, code[j].strip())] = j + 1
def col(codev): return next(c for (k, cd), c in lab.items() if cd == codev)
C = {"textile": "'607'", "chemical": "'5'", "steel": "'611'", "general_machinery": "'701'", "electrical": "'703'", "transport": "'705'", "cars": "'70503'", "car_parts": "'70505'",
     "ships": "'7051301'", "semiconductors": "'70323'", "semi_equipment": "'70131'", "food": "'0'+'1'", "fuel": "'3'", "optical": "'81101'", "computers": "'7010505'"}
rec = []
for r in rows[7:]:
    if r and r[0].strip().isdigit():
        d = {"year": int(r[0]), "total": float(r[1])}
        for k, cd in C.items():
            v = r[col(cd)].strip(); d[k] = float(v) if v not in ("-", "") else np.nan
        rec.append(d)
NEW = pd.DataFrame(rec).set_index("year")
labels_used = {k: [kk for (kk, cd) in lab if cd == v][0] for k, v in C.items()}

SO = OLD.div(OLD.total, axis=0) * 100; SOI = OLDI.div(OLD.total.reindex(OLDI.index), axis=0) * 100
SN = NEW.div(NEW.total, axis=0) * 100
# 重なる年（1988〜2004年）の差
ov = {}
for k in ["textile", "chemical", "steel", "general_machinery", "electrical", "transport"]:
    d = (SO[k] - SN[k]).dropna(); ov[k] = {"mean_diff": round(float(d.mean()), 2), "max_abs": round(float(d.abs().max()), 2)}
for k in ["cars", "ships", "semiconductors", "car_parts"]:
    d = (SOI[k] - SN[k]).dropna(); ov[k] = {"mean_diff": round(float(d.mean()), 2), "max_abs": round(float(d.abs().max()), 2)}
tot_ratio = (OLD.total.loc[1988:2004] * 1000 / NEW.total.loc[1988:2004])
# つなぐ：1987年までは長期統計系列、1988年からは貿易統計
SEC = ["textile", "steel", "chemical", "general_machinery", "electrical", "transport"]
S = pd.concat([SO.loc[:1987, SEC], SN.loc[1988:, SEC]])
I = pd.concat([SOI.loc[:1987, ["cars", "car_parts", "ships", "semiconductors"]], SN.loc[1988:, ["cars", "car_parts", "ships", "semiconductors"]]])
ALL = S.join(I, how="left"); ALL.round(3).to_csv(DATA / "export_shares_1962_2025.csv")
NEW.to_csv(DATA / "exports_customs_1988_2025.csv"); OLD.join(OLDI, how="left").to_csv(DATA / "exports_chouki_1962_2004.csv")
JP = {"textile": "繊維", "steel": "鉄鋼", "chemical": "化学製品", "general_machinery": "一般機械", "electrical": "電気機器", "transport": "輸送用機器", "cars": "自動車", "ships": "船舶", "semiconductors": "半導体等電子部品", "car_parts": "自動車の部分品"}
# 6分野の1位（一般機械・電気・輸送がそろう1969年〜）
full = S.loc[1969:]
top = full.idxmax(axis=1); chg = [(int(y), JP[top[y]]) for y in top.index if y == top.index[0] or top[y] != top[y - 1]]
top3 = full.apply(lambda r: r.sort_values(ascending=False).head(3).sum(), axis=1)
# 品目（繊維・鉄鋼・自動車・半導体等電子部品・船舶）で1位
P = ALL.loc[1969:, ["textile", "steel", "cars", "semiconductors", "ships"]]
ptop = P.idxmax(axis=1); pchg = [(int(y), JP[ptop[y]]) for y in ptop.index if y == ptop.index[0] or ptop[y] != ptop[y - 1]]
def peak(sr): return {"year": int(sr.idxmax()), "share": round(float(sr.max()), 1)}
def cross(a, b):
    d = (a - b).dropna(); ys = [int(y) for y in d.index[1:] if d[y] > 0 and d[y - 1] <= 0]; return ys
res = {"units": "1978年まで1,000ドル、1979年から100万円（長期統計系列）／千円（貿易統計）。割合は同じ年の総額で割るので単位の違いは影響しない",
       "labels_customs": labels_used, "overlap_1988_2004_share_diff_pt": ov, "total_ratio_chouki_vs_customs": [round(float(tot_ratio.min()), 5), round(float(tot_ratio.max()), 5)],
       "share": {int(y): {JP[k]: (None if pd.isna(v) else round(float(v), 1)) for k, v in ALL.loc[y].items()} for y in [1962, 1965, 1969, 1970, 1975, 1980, 1985, 1987, 1988, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]},
       "peak": {JP[k]: peak(ALL[k].dropna()) for k in ALL.columns},
       "sector_top_changes_since_1969": chg, "sector_top_years": {JP[k]: int((top == k).sum()) for k in SEC},
       "item_top_changes_since_1969": pchg,
       "top3_sector_share": {"1969": round(float(top3.loc[1969]), 1), "max": {"year": int(top3.idxmax()), "share": round(float(top3.max()), 1)}, "2025": round(float(top3.loc[2025]), 1), "min": {"year": int(top3.idxmin()), "share": round(float(top3.min()), 1)}},
       "machinery3_share": {int(y): round(float(S.loc[y, ["general_machinery", "electrical", "transport"]].sum()), 1) for y in [1969, 1980, 1990, 2000, 2010, 2020, 2025]},
       "steel_over_textile": cross(ALL.steel, ALL.textile), "cars_over_steel": cross(ALL.cars, ALL.steel), "cars_over_textile": cross(ALL.cars, ALL.textile),
       "transport_over_electrical": cross(S.transport, S.electrical), "electrical_over_transport": cross(S.electrical, S.transport),
       "textile_below_10": int(ALL.textile[ALL.textile < 10].index.min()), "textile_below_5": int(ALL.textile[ALL.textile < 5].index.min()), "steel_below_10": int(ALL.steel.loc[1975:][ALL.steel.loc[1975:] < 10].index.min()),
       "chemical_over_10": int(ALL.chemical[ALL.chemical > 10].index.min()),
       "customs_2025": {k: round(float(SN.loc[2025, k]), 1) for k in C}, "customs_1988": {k: round(float(SN.loc[1988, k]), 1) for k in C},
       "semi_equipment_peak": peak(SN.semi_equipment), "computers_peak": peak(SN.computers)}
json.dump(res, open(RES / "a368_main.json", "w"), ensure_ascii=False, indent=1)

COL = {"textile": GRAY, "steel": INK, "chemical": GREEN, "general_machinery": LIGHT, "electrical": ORANGE, "transport": BLUE}
# 図1：6分野の割合
fig, ax = plt.subplots(figsize=(9.2, 4.6))
for k in SEC:
    ax.plot(S.index, S[k], color=COL[k], lw=2, label=JP[k])
    ax.annotate(f"{JP[k]} {S[k].iloc[-1]:.0f}%", (2025, S[k].iloc[-1]), xytext=(5, 0), textcoords="offset points", fontsize=8.5, color=INK, va="center")
ax.axvline(1987.5, color=GRAY, lw=0.7, ls="--"); ax.text(1988, 31.5, "1988年〜 貿易統計", fontsize=8, color=INK)
ax.set_xlim(1960, 2034); ax.set_ylim(0, 33); ax.set_ylabel("輸出総額に占める割合（%）")
ax.set_title("1962年に26%だった繊維は1%に。1969年からの57年のうち48年は、輸送用機器が1位")
save(fig, "a368_sector_shares.png", SRC + "\n一般機械・電気機器・輸送用機器は1969年から。1987年以前と1988年以降は品目の分け方が変わり、つながらない品目がある")

# 図2：品目で見る（繊維・鉄鋼・自動車・半導体等電子部品・船舶）
fig, ax = plt.subplots(figsize=(9.2, 4.6))
for k, c in [("textile", GRAY), ("steel", INK), ("ships", LIGHT), ("cars", BLUE), ("semiconductors", ORANGE)]:
    d = ALL[k].dropna(); ax.plot(d.index, d, color=c, lw=2, label=JP[k])
    pk = peak(d); ax.annotate(f"{JP[k]}の山 {pk['year']}年 {pk['share']:.0f}%", (pk["year"], pk["share"]), xytext=(4, 6), textcoords="offset points", fontsize=8, color=INK)
ax.axvline(1987.5, color=GRAY, lw=0.7, ls="--")
ax.set_xlim(1960, 2027); ax.set_ylim(0, 30); ax.set_ylabel("輸出総額に占める割合（%）")
ax.set_title("品目で見ると、繊維→鉄鋼→自動車の順に山が来た"); ax.legend(frameon=False, ncol=5, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
save(fig, "a368_item_peaks.png", SRC + "\n自動車・船舶・半導体等電子部品は1969年から", y=-0.07)

# 図3：年ごとの構成（10年おき）
ys = [1969, 1980, 1990, 2000, 2010, 2020, 2025]
fig, ax = plt.subplots(figsize=(9.2, 4.4)); bot = np.zeros(len(ys)); x = np.arange(len(ys))
for k in ["textile", "steel", "chemical", "general_machinery", "electrical", "transport"]:
    v = S.loc[ys, k].values; ax.bar(x, v, bottom=bot, color=COL[k], width=0.7, label=JP[k])
    for i, (vv, bb) in enumerate(zip(v, bot)):
        if vv >= 4: ax.text(i, bb + vv / 2, f"{vv:.0f}", ha="center", va="center", fontsize=8.5, color="white" if k in ("steel", "transport", "electrical", "textile", "chemical") else INK)
    bot += v
oth = 100 - bot; ax.bar(x, oth, bottom=bot, color="#e5e4df", width=0.7, label="その他")
for i, (vv, bb) in enumerate(zip(oth, bot)): ax.text(i, bb + vv / 2, f"{vv:.0f}", ha="center", va="center", fontsize=8.5, color=INK)
ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in ys]); ax.set_ylabel("輸出総額に占める割合（%）"); ax.set_ylim(0, 100)
ax.set_title("機械の3分野は1969年の39%から1990年に70%へ。2025年は化学製品と「その他」が増えて57%", pad=10)
ax.legend(frameon=False, ncol=7, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
save(fig, "a368_composition.png", SRC, y=-0.07)
print(json.dumps(res, ensure_ascii=False, indent=0)[:7000])
