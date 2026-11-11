"""F270 03 分析：名目・実質の円・実質ドル・各国の実質の現地通貨で1人あたり支出の「過去最多」を確かめ、国籍の構成で分ける。"""
import os, json
import pandas as pd, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "data", "processed"); R = os.path.join(HERE, "..", "results"); os.makedirs(R, exist_ok=True)
pc = pd.read_csv(os.path.join(P, "per_capita_by_nat.csv"))
arr = pd.read_csv(os.path.join(P, "arrivals_by_nat.csv"))
cpi = pd.read_csv(os.path.join(P, "cpi_japan_annual.csv")).set_index("year")
fx = pd.read_csv(os.path.join(P, "fx_prices_annual.csv")).set_index("year")
YRS = [y for y in sorted(pc.year.unique())]
MAIN = [y for y in YRS if y != 2022]           # 2020〜2022年を除く（2020・2021年は調査なし）
OUT = {}

# ---- 全国籍の系列 ----
tot = pc[pc.nat == "全体"].set_index("year")
s = pd.DataFrame(index=YRS)
s["pc_nom"] = tot.pc_pkg
s["pc_exc"] = tot.pc_exc
s["nights"] = tot.nights
s["arrivals"] = arr[arr.nat == "全体"].set_index("year").visitors.reindex(YRS)
for k in ["cpi_all", "cpi_core", "cpi_eatout", "cpi_transport", "cpi_recserv"]:
    s[k] = cpi[k].reindex(YRS)
s["cpi_travel"] = s[["cpi_eatout", "cpi_transport", "cpi_recserv"]].mean(axis=1)
s["pc_real"] = s.pc_nom / s.cpi_all * 100
s["pc_real_core"] = s.pc_nom / s.cpi_core * 100
s["pc_real_travel"] = s.pc_nom / s.cpi_travel * 100
s["pc_exc_real"] = s.pc_exc / s.cpi_all * 100
s["jpy_usd"] = fx.AEXJPUS.reindex(YRS)
s["us_cpi"] = fx.CPIAUCSL.reindex(YRS) / fx.CPIAUCSL.loc[2020] * 100
s["pc_usd_nom"] = s.pc_nom / s.jpy_usd
s["pc_usd_real"] = s.pc_usd_nom / s.us_cpi * 100
s["total_nom_oku"] = s.pc_nom * s.arrivals / 1e8      # 1人あたり×訪日客数（概算、クルーズ客を区別しない）
s["pc_real_per_night"] = s.pc_real / s.nights
s.to_csv(os.path.join(R, "A_series.csv"), float_format="%.4f")

def is_record(col, y, years):
    prev = [x for x in years if x < y]
    return bool(prev) and s.loc[y, col] > s.loc[prev, col].max()

# 訪日客数の過去最多（JNTO 2003年以降の年で判定。2002年以前はどの年も2010年の861万人より少ない）
arr_tot = arr[arr.nat == "全体"].set_index("year").visitors
jn = pd.read_csv(os.path.join(HERE, "..", "data", "raw", "jnto_monthly_2003_2026.csv"))
allarr = jn[(jn.market == "総数") & (jn.year <= 2025)].groupby("year").visitors.sum()
arr_rec = [y for y in MAIN if allarr.loc[y] > allarr.loc[:y - 1].max()]
OUT["arrival_record_years"] = arr_rec
recs = {}
for col in ["pc_nom", "pc_real", "pc_real_core", "pc_real_travel", "pc_usd_nom", "pc_usd_real", "pc_exc", "pc_exc_real", "pc_real_per_night"]:
    recs[col] = [y for y in MAIN if is_record(col, y, MAIN)]
OUT["per_capita_record_years"] = recs

# H1：実質の円で2025年が最多か
prev_max_real = s.loc[[y for y in MAIN if y < 2025], "pc_real"]
OUT["H1"] = dict(real_2025=s.loc[2025, "pc_real"], prev_max=prev_max_real.max(), prev_max_year=int(prev_max_real.idxmax()),
                 ratio=s.loc[2025, "pc_real"] / prev_max_real.max(), supported=bool(s.loc[2025, "pc_real"] > prev_max_real.max()))
# H2：実質ドルで2025年は2011〜2019年の最大を15%以上下回るか
pre = s.loc[[y for y in MAIN if y <= 2019], "pc_usd_real"]
gap = s.loc[2025, "pc_usd_real"] / pre.max() - 1
OUT["H2"] = dict(usd_real_2025=s.loc[2025, "pc_usd_real"], pre_max=pre.max(), pre_max_year=int(pre.idxmax()), gap=gap, supported=bool(gap <= -0.15))
# H4：訪日客が最多の年のうち、実質の円の1人あたりも最多だった年の数
hit = [y for y in arr_rec if y in recs["pc_real"]]
OUT["H4"] = dict(arrival_records=arr_rec, both=hit, share=len(hit) / len(arr_rec), supported=bool(len(hit) / len(arr_rec) < 0.5))

# ---- 国籍の構成の分解 ----
NATS = [n for n in pc.nat.unique() if n not in ("全体", "その他")]
def table(y):
    p = pc[(pc.year == y)].set_index("nat").pc_pkg
    a = arr[arr.year == y].set_index("nat").visitors
    names = [n for n in NATS if n in p.index and n in a.index and not np.isnan(p[n])]
    w = a.reindex(names).astype(float)
    other = a["全体"] - w.sum()
    w["その他"] = other; pp = p.reindex(names); pp["その他"] = p["その他"]
    w = w / w.sum()
    return w, pp
def decompose(y0, y1, weight="avg"):
    w0, p0 = table(y0); w1, p1 = table(y1)
    names = [n for n in w0.index if n in w1.index]
    w0, w1, p0, p1 = (x.reindex(names) for x in (w0, w1, p0, p1))
    w0, w1 = w0 / w0.sum(), w1 / w1.sum()
    P0, P1 = (w0 * p0).sum(), (w1 * p1).sum()
    if weight == "avg":
        within = ((w0 + w1) / 2 * (p1 - p0)).sum(); mix = ((p0 + p1) / 2 * (w1 - w0)).sum()
    elif weight == "w_end":      # 国籍の中の変化を後の年の割合で、構成の変化を前の年の単価で測る
        within = (w1 * (p1 - p0)).sum(); mix = (p0 * (w1 - w0)).sum()
    else:                         # "w_start"：国籍の中の変化を前の年の割合で、構成の変化を後の年の単価で測る
        within = (w0 * (p1 - p0)).sum(); mix = (p1 * (w1 - w0)).sum()
    contrib = pd.DataFrame(dict(w0=w0, w1=w1, p0=p0, p1=p1, within=(w0 + w1) / 2 * (p1 - p0), mix=(p0 + p1) / 2 * (w1 - w0)))
    return dict(y0=y0, y1=y1, weight=weight, P0=P0, P1=P1, official0=s.loc[y0, "pc_nom"], official1=s.loc[y1, "pc_nom"],
                change=P1 - P0, within=within, mix=mix, mix_share=abs(mix) / abs(P1 - P0) if P1 != P0 else np.nan), contrib
dec = []
for y0, y1 in [(2019, 2025), (2015, 2025), (2024, 2025), (2015, 2019), (2011, 2019), (2019, 2024)]:
    for wt in ["avg", "w_end", "w_start"]:
        d, c = decompose(y0, y1, wt); dec.append(d)
        if wt == "avg":
            c.to_csv(os.path.join(R, f"B_decomp_{y0}_{y1}_by_nat.csv"), float_format="%.6f")
dec = pd.DataFrame(dec); dec.to_csv(os.path.join(R, "B_decomposition.csv"), index=False, float_format="%.4f")
d19 = dec[(dec.y0 == 2019) & (dec.y1 == 2025)]
OUT["H3"] = dict(avg=d19[d19.weight == "avg"].iloc[0].to_dict(), mix_share_range=[d19.mix_share.min(), d19.mix_share.max()],
                 supported=bool(d19[d19.weight == "avg"].mix_share.iloc[0] < 0.25))

# ---- 国別：実質の現地通貨（M4） ----
CC = {"韓国": ("AEXKOUS", "KOR", "per_usd"), "中国": ("AEXCHUS", "CHN", "per_usd"), "香港": ("AEXHKUS", "HKG", "per_usd"),
      "タイ": ("AEXTHUS", "THA", "per_usd"), "シンガポール": ("AEXSIUS", "SGP", "per_usd"), "マレーシア": ("AEXMAUS", "MYS", "per_usd"),
      "インド": ("AEXINUS", "IND", "per_usd"), "カナダ": ("AEXCAUS", "CAN", "per_usd"), "英国": ("AEXUSUK", "GBR", "usd_per"),
      "ドイツ": ("AEXUSEU", "DEU", "usd_per"), "フランス": ("AEXUSEU", "FRA", "usd_per"), "オーストラリア": ("AEXUSAL", "AUS", "usd_per"),
      "米国": (None, "USA", None)}
rows = []
for n, (fxs, c, kind) in CC.items():
    if kind is None:
        jpy_per_local = fx.AEXJPUS; lcpi = fx.CPIAUCSL / fx.CPIAUCSL.loc[2020] * 100
    else:
        jpy_per_local = fx.AEXJPUS / fx[fxs] if kind == "per_usd" else fx.AEXJPUS * fx[fxs]
        g = (1 + fx[c] / 100)
        lcpi = g.cumprod(); lcpi = lcpi / lcpi.loc[2020] * 100
    for y in YRS:
        p = pc[(pc.year == y) & (pc.nat == n)].pc_pkg
        if len(p) and not np.isnan(p.iloc[0]):
            rows.append(dict(nat=n, year=y, pc_jpy=p.iloc[0], jpy_per_local=jpy_per_local.get(y, np.nan), local_cpi=lcpi.get(y, np.nan),
                             jp_cpi=s.loc[y, "cpi_all"]))
m4 = pd.DataFrame(rows)
m4["pc_local_nom"] = m4.pc_jpy / m4.jpy_per_local
m4["pc_local_real"] = m4.pc_local_nom / m4.local_cpi * 100
m4["pc_jpy_real"] = m4.pc_jpy / m4.jp_cpi * 100
m4.to_csv(os.path.join(R, "C_by_country_local.csv"), index=False, float_format="%.4f")
cs = []
for n, g in m4.groupby("nat"):
    g = g.set_index("year")
    pre_ = g.loc[[y for y in g.index if y <= 2019]]
    cs.append(dict(nat=n, jpy_real_2025_vs_premax=g.loc[2025, "pc_jpy_real"] / pre_.pc_jpy_real.max() - 1,
                   local_real_2025_vs_premax=g.loc[2025, "pc_local_real"] / pre_.pc_local_real.max() - 1,
                   local_real_2025_vs_2019=g.loc[2025, "pc_local_real"] / g.loc[2019, "pc_local_real"] - 1,
                   jpy_real_2025_vs_2019=g.loc[2025, "pc_jpy_real"] / g.loc[2019, "pc_jpy_real"] - 1,
                   n_resp_2025=float(pc[(pc.year == 2025) & (pc.nat == n)].n_resp.iloc[0])))
cs = pd.DataFrame(cs).sort_values("local_real_2025_vs_premax"); cs.to_csv(os.path.join(R, "C_country_summary.csv"), index=False, float_format="%.4f")
OUT["M4"] = dict(n=len(cs), local_real_above_premax=int((cs.local_real_2025_vs_premax > 0).sum()),
                 jpy_real_above_premax=int((cs.jpy_real_2025_vs_premax > 0).sum()),
                 local_real_median=float(cs.local_real_2025_vs_premax.median()))

# ---- 頑健性 ----
rob = {}
for col in ["pc_real", "pc_real_core", "pc_real_travel", "pc_exc", "pc_exc_real", "pc_nom", "pc_usd_nom", "pc_usd_real"]:
    prev = s.loc[[y for y in MAIN if y < 2025], col]
    rob[col] = dict(v2025=s.loc[2025, col], prev_max=prev.max(), prev_year=int(prev.idxmax()), ratio=s.loc[2025, col] / prev.max())
# 調査の切れ目ごと（同じ方式の中だけで比べる）
seg = {"2011-2017": [y for y in YRS if y <= 2017], "2018-2023": [2018, 2019, 2023], "2024-2025": [2024, 2025]}
rob["segments_real_max_year"] = {k: int(s.loc[v, "pc_real"].idxmax()) for k, v in seg.items()}
# 2022年を入れた場合
rob["with_2022"] = dict(nom_max_year=int(s.pc_nom.idxmax()), real_max_year=int(s.pc_real.idxmax()))
# 実質ドルで1人あたりがいちばん大きい年
rob["usd_real_max_year"] = int(s.loc[MAIN, "pc_usd_real"].idxmax())
# レビュー後に追加：調査の方式ごとの実質ドル、比べられる年での順位、2022年を入れた場合
rob["usd_real_vs_2018_19_max"] = s.loc[2025, "pc_usd_real"] / s.loc[[2018, 2019], "pc_usd_real"].max() - 1
rob["usd_real_vs_2011_17_max"] = s.loc[2025, "pc_usd_real"] / s.loc[[y for y in YRS if y <= 2017], "pc_usd_real"].max() - 1
rob["n_years_compared"] = len(MAIN)
rob["real_rank_2025_main"] = int(s.loc[MAIN, "pc_real"].rank(ascending=False)[2025])
rob["real_rank_2025_with_2022"] = int(s.pc_real.rank(ascending=False)[2025])
rob["usd_real_rank_2025_from_top_main"] = int(s.loc[MAIN, "pc_usd_real"].rank(ascending=False)[2025])
rec22 = [y for y in YRS if y != YRS[0] and s.loc[y, "pc_real"] > s.loc[[x for x in YRS if x < y], "pc_real"].max()]
rob["H4_with_2022"] = dict(per_capita_real_records=rec22, both=[y for y in arr_rec if y in rec22], share=len([y for y in arr_rec if y in rec22]) / len(arr_rec))
# 組み立てた全国籍の値と公表値のずれ、公表値での差
rob["recon_gap"] = {int(y): float(dec[(dec.y0 == y) & (dec.weight == "avg")].P0.iloc[0] / s.loc[y, "pc_nom"] - 1) for y in [2019, 2024]}
rob["recon_gap"][2025] = float(dec[(dec.y1 == 2025) & (dec.weight == "avg")].P1.iloc[0] / s.loc[2025, "pc_nom"] - 1)
rob["published_diff"] = {f"{a}-{b}": float(s.loc[b, "pc_nom"] - s.loc[a, "pc_nom"]) for a, b in [(2019, 2025), (2015, 2019), (2024, 2025), (2015, 2025), (2011, 2019), (2019, 2024)]}
rob["us_cpi_2025_months"] = 11  # FRED の CPIAUCSL は2025年10月が欠け（11か月の平均）
OUT["robust"] = rob

# ---- 問い直し（結果を見た後に追加）：1人あたりの増減は「1泊あたり」と「泊数」のどちらから来たか ----
reask = []
for y0, y1 in [(2024, 2025), (2019, 2025), (2015, 2025), (2019, 2024), (2023, 2024)]:
    a, b = s.loc[y0], s.loc[y1]
    reask.append(dict(y0=y0, y1=y1, pc_nom_chg=b.pc_nom / a.pc_nom - 1, nights_chg=b.nights / a.nights - 1,
                      per_night_nom_chg=(b.pc_nom / b.nights) / (a.pc_nom / a.nights) - 1,
                      per_night_real_chg=b.pc_real_per_night / a.pc_real_per_night - 1,
                      share_from_nights=np.log(b.nights / a.nights) / np.log(b.pc_nom / a.pc_nom)))
reask = pd.DataFrame(reask); reask.to_csv(os.path.join(R, "D_reask_nights.csv"), index=False, float_format="%.5f")
# 国籍別：2024→2025年の1人あたり（名目）の増減と泊数の増減
rn = []
for n in NATS + ["全体"]:
    g = pc[pc.nat == n].set_index("year")
    if 2024 in g.index and 2025 in g.index:
        rn.append(dict(nat=n, pc_chg=g.loc[2025, "pc_pkg"] / g.loc[2024, "pc_pkg"] - 1, nights_chg=g.loc[2025, "nights"] / g.loc[2024, "nights"] - 1,
                       per_night_chg=(g.loc[2025, "pc_pkg"] / g.loc[2025, "nights"]) / (g.loc[2024, "pc_pkg"] / g.loc[2024, "nights"]) - 1,
                       n_resp_2025=g.loc[2025, "n_resp"]))
rn = pd.DataFrame(rn); rn.to_csv(os.path.join(R, "D_reask_nights_by_nat_2024_2025.csv"), index=False, float_format="%.5f")
OUT["reask"] = dict(table=reask.to_dict("records"), per_night_real_record_2025=bool(2025 in recs["pc_real_per_night"]),
                    nat_per_night_down=int((rn[rn.nat != "全体"].per_night_chg < 0).sum()), nat_n=int((rn.nat != "全体").sum()),
                    nat_nights_up=int((rn[rn.nat != "全体"].nights_chg > 0).sum()))

def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating,)): return round(float(o), 6)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, float): return round(o, 6)
    return o
json.dump(clean(OUT), open(os.path.join(R, "main.json"), "w"), ensure_ascii=False, indent=1)
print(s[["arrivals", "pc_nom", "pc_real", "pc_real_core", "pc_real_travel", "pc_usd_nom", "pc_usd_real", "nights", "pc_real_per_night"]].round(1).to_string())
print(json.dumps(clean(OUT), ensure_ascii=False, indent=1)[:4000])
print(cs.round(3).to_string(index=False))
print(dec.round(3).to_string(index=False))
print(reask.round(4).to_string(index=False))
print(rn.round(3).to_string(index=False))
