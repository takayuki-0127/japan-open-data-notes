"""03 分析: 外国人住民の空間的な集中度と、増え方の分解。
- 単位: 市区町村（政令指定都市は区、東京都は特別区）。浜松市は2024年の区の再編のため市にまとめる。
- 集中度: 非類似度指数 D（外国人と日本人の分布の違い）、ジニ係数、立地係数、上位5%の市区町村の占める割合
- 増え方: 地域（三大都市圏・地方圏）× 種類（特別区・政令市の区／市／町村）別の増加率と寄与
- 分解: 住民基本台帳の動態（国内の転入出・国外との転入出・出生と死亡・その他）
- 国籍: 在留外国人統計（2015年末・2022年末）の市区町村×国籍の表
"""
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
np.random.seed(140)

p = pd.read_csv(ROOT / "data/juki_panel.csv", dtype={"code5": str})
p = p[~p.is_city_total].copy()
# 浜松市の区を市にまとめる
ham = p.name.str.startswith("浜松市")
p.loc[ham, "code5"] = "22130"
p.loc[ham, "name"] = "浜松市"
num = [c for c in p.columns if c.endswith("_for") or c.endswith("_tot")]
num = [c for c in num if p[c].dtype != object]
p = p.groupby(["year", "code5", "pref", "name"], as_index=False)[num].sum()
p["jp"] = p.pop_tot - p.pop_for

TOKYO = {"埼玉県", "千葉県", "東京都", "神奈川県"}
NAGOYA = {"岐阜県", "愛知県", "三重県"}
OSAKA = {"京都府", "大阪府", "兵庫県", "奈良県"}


def area(pref):
    if pref in TOKYO:
        return "東京圏"
    if pref in NAGOYA:
        return "名古屋圏"
    if pref in OSAKA:
        return "大阪圏"
    return "地方圏"


def mtype(name):
    if name.endswith("区"):
        return "特別区・政令市の区"
    if name.endswith("市"):
        return "市"
    return "町村"


p["area"] = p.pref.map(area)
p["mtype"] = p.name.map(mtype)
base = p[p.year == 2014].set_index("code5")
p["size14"] = p.code5.map(base.pop_tot)
p["size_cls"] = pd.cut(p.size14, [0, 1e4, 5e4, 2e5, 1e9],
                       labels=["1万人未満", "1万〜5万人", "5万〜20万人", "20万人以上"])
p.to_csv(ROOT / "data/panel_units.csv", index=False)


def dissim(f, j):
    f = np.asarray(f, float); j = np.asarray(j, float)
    return 0.5 * np.abs(f / f.sum() - j / j.sum()).sum()


def gini(f, j):
    """外国人と日本人のローレンツ曲線（外国人の割合の低い順）から求めるジニ係数"""
    f = np.asarray(f, float); j = np.asarray(j, float)
    o = np.argsort(f / (f + j))
    x = np.concatenate([[0], np.cumsum(j[o]) / j.sum()])
    y = np.concatenate([[0], np.cumsum(f[o]) / f.sum()])
    return 1 - np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]))


def theil(f, j):
    f = np.asarray(f, float); j = np.asarray(j, float)
    t = f + j; s = f / t; S = f.sum() / t.sum()
    w = t / t.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        e = np.where(s > 0, s * np.log(s / S), 0) + np.where(s < 1, (1 - s) * np.log((1 - s) / (1 - S)), 0)
    E = -(S * np.log(S) + (1 - S) * np.log(1 - S))
    return float((w * e).sum() / E)


def top_share(f, q=0.05):
    f = np.sort(np.asarray(f, float))[::-1]
    k = int(np.ceil(len(f) * q))
    return f[:k].sum() / f.sum()


out = {}
# ---------- 1. 集中度の推移 ----------
rows = []
for y, g in p.groupby("year"):
    pr = g.groupby("pref")[["pop_for", "jp"]].sum()
    rows.append(dict(year=y, foreign=g.pop_for.sum(), total=g.pop_tot.sum(),
                     share=g.pop_for.sum() / g.pop_tot.sum(),
                     D_muni=dissim(g.pop_for, g.jp), gini_muni=gini(g.pop_for, g.jp),
                     theil_muni=theil(g.pop_for, g.jp), top5_muni=top_share(g.pop_for),
                     top5_pop=top_share(g.pop_tot),
                     D_pref=dissim(pr.pop_for, pr.jp), gini_pref=gini(pr.pop_for, pr.jp),
                     n_lq_gt1=int(((g.pop_for / g.pop_tot) > g.pop_for.sum() / g.pop_tot.sum()).sum()),
                     n_units=len(g),
                     share_chiho=g[g.area == "地方圏"].pop_for.sum() / g.pop_for.sum(),
                     share_chiho_pop=g[g.area == "地方圏"].pop_tot.sum() / g.pop_tot.sum(),
                     share_town=g[g.mtype == "町村"].pop_for.sum() / g.pop_for.sum(),
                     share_town_pop=g[g.mtype == "町村"].pop_tot.sum() / g.pop_tot.sum()))
conc = pd.DataFrame(rows)
conc.to_csv(RES / "concentration_by_year.csv", index=False)
out["concentration"] = conc.round(4).to_dict(orient="records")

# 都道府県の中での集中（D を都道府県間・都道府県内に分ける。Theil で分解）
def theil_decomp(g):
    T = theil(g.pop_for, g.jp)
    pr = g.groupby("pref")[["pop_for", "jp"]].sum()
    Tb = theil(pr.pop_for, pr.jp)
    return T, Tb, 1 - Tb / T


dec = []
for y in [2014, 2020, 2026]:
    T, Tb, w = theil_decomp(p[p.year == y])
    dec.append(dict(year=y, theil=T, between_pref=Tb, within_share=w))
out["theil_decomp"] = pd.DataFrame(dec).round(4).to_dict(orient="records")

# ---------- 2. 増え方（2014→2026） ----------
a0 = p[p.year == 2014].set_index("code5")
a1 = p[p.year == 2026].set_index("code5")
common = a0.index.intersection(a1.index)
e = a0.loc[common, ["pref", "name", "area", "mtype", "size_cls", "pop_for", "pop_tot", "jp"]].join(
    a1.loc[common, ["pop_for", "pop_tot", "jp"]], rsuffix="_26")
e["d_for"] = e.pop_for_26 - e.pop_for
e["d_jp"] = e.jp_26 - e.jp
out["n_common_units"] = int(len(e))
nat_d = e.d_for.sum()


def grp(by):
    g = e.groupby(by, observed=True).agg(for14=("pop_for", "sum"), for26=("pop_for_26", "sum"),
                                         jp14=("jp", "sum"), jp26=("jp_26", "sum"), n=("name", "size"))
    g["growth"] = g.for26 / g.for14 - 1
    g["contrib"] = (g.for26 - g.for14) / nat_d
    g["share14"] = g.for14 / g.for14.sum()
    g["share26"] = g.for26 / g.for26.sum()
    g["ratio14"] = g.for14 / (g.for14 + g.jp14)
    g["ratio26"] = g.for26 / (g.for26 + g.jp26)
    g["jp_growth"] = g.jp26 / g.jp14 - 1
    return g


g_area = grp("area"); g_type = grp("mtype"); g_size = grp("size_cls"); g_at = grp(["area", "mtype"])
for nm, g in [("area", g_area), ("type", g_type), ("size", g_size), ("area_type", g_at)]:
    g.to_csv(RES / f"growth_by_{nm}.csv")
out["growth_area"] = g_area.round(4).reset_index().to_dict(orient="records")
out["growth_type"] = g_type.round(4).reset_index().to_dict(orient="records")
out["growth_size"] = g_size.round(4).reset_index().astype({"size_cls": str}).to_dict(orient="records")
out["national_growth"] = float(e.pop_for_26.sum() / e.pop_for.sum() - 1)

# 個々の市区町村の伸び（外国人が10人以上いた市区町村）
m = e[e.pop_for >= 10].copy()
m["growth"] = m.pop_for_26 / m.pop_for - 1
out["muni_growth_quantiles"] = m.growth.quantile([.1, .25, .5, .75, .9]).round(3).to_dict()
out["share_doubled"] = float((m.growth >= 1).mean())
out["n_muni_jp_down_for_up"] = int(((e.d_jp < 0) & (e.d_for > 0)).sum())
out["share_muni_jp_down_for_up"] = float(((e.d_jp < 0) & (e.d_for > 0)).mean())
dn = e[e.d_jp < 0]
out["offset_ratio_jp_down_units"] = float(dn.d_for.sum() / -dn.d_jp.sum())
# 伸びと初めの割合の関係（追いつき）: 初めの外国人の割合が低い市区町村ほど速く伸びたか
m["ratio14"] = m.pop_for / m.pop_tot
rho = pd.Series(np.log1p(m.growth)).corr(pd.Series(np.log(m.ratio14)), method="spearman")
out["spearman_growth_vs_initial_ratio"] = float(rho)
# 割合の階級別の伸び
m["ratio_q"] = pd.qcut(m.ratio14, 5, labels=["最も低い20%", "2", "3", "4", "最も高い20%"])
gq = m.groupby("ratio_q", observed=True).agg(for14=("pop_for", "sum"), for26=("pop_for_26", "sum"),
                                            med_growth=("growth", "median"))
gq["growth"] = gq.for26 / gq.for14 - 1
gq.to_csv(RES / "growth_by_initial_ratio_quintile.csv")
out["growth_by_initial_ratio_quintile"] = gq.round(3).reset_index().astype({"ratio_q": str}).to_dict(orient="records")

# ---------- 3. 増え方の分解（動態） ----------
flow_cols = ["in_dom_for", "out_dom_for", "in_abr_for", "out_abr_for", "births_for", "deaths_for",
             "oth_in_for", "oth_out_for"]
f = p[p.year >= 2015].copy()  # year の表は前の年の動態（2015年表 = 2014年中）
f["net_dom"] = f.in_dom_for - f.out_dom_for
f["net_abr"] = f.in_abr_for - f.out_abr_for
f["natural"] = f.births_for - f.deaths_for
f["other"] = f.oth_in_for - f.oth_out_for
comp = ["net_dom", "net_abr", "natural", "other"]
yr = f.groupby("year")[comp].sum()
yr["flow_total"] = yr.sum(axis=1)
stock = p.groupby("year").pop_for.sum()
yr["stock_change"] = stock.diff().reindex(yr.index)
yr.index = yr.index - 1  # 動態の年
yr.to_csv(RES / "flows_by_year_national.csv")
out["flows_by_year"] = yr.round(0).reset_index().to_dict(orient="records")


def flow_grp(by):
    g = f.groupby(by)[comp].sum()
    st = p[p.year == 2014].groupby(by).pop_for.sum()
    g["stock14"] = st
    g["sum"] = g[comp].sum(axis=1)
    for c in comp:
        g[c + "_per_stock14"] = g[c] / g.stock14
    return g


fl_area = flow_grp("area"); fl_type = flow_grp("mtype"); fl_at = flow_grp(["area", "mtype"])
fl_size = f.groupby("size_cls", observed=True)[comp].sum()
for nm, g in [("area", fl_area), ("type", fl_type), ("area_type", fl_at), ("size", fl_size)]:
    g.to_csv(RES / f"flows_by_{nm}.csv")
out["flows_area"] = fl_area.round(3).reset_index().to_dict(orient="records")
out["flows_type"] = fl_type.round(3).reset_index().to_dict(orient="records")
out["flows_area_type"] = fl_at.round(3).reset_index().to_dict(orient="records")
out["flows_size"] = fl_size.round(0).reset_index().astype({"size_cls": str}).to_dict(orient="records")
# 国外からの純流入を100としたときの、国内移動で出ていった割合
fl_at["dom_over_abr"] = fl_at.net_dom / fl_at.net_abr
fl_type["dom_over_abr"] = fl_type.net_dom / fl_type.net_abr
fl_area["dom_over_abr"] = fl_area.net_dom / fl_area.net_abr
out["dom_over_abr_type"] = fl_type.dom_over_abr.round(3).to_dict()
out["dom_over_abr_area"] = fl_area.dom_over_abr.round(3).to_dict()
out["dom_over_abr_area_type"] = {f"{a}|{b}": round(v, 3) for (a, b), v in fl_at.dom_over_abr.items()}
# 日本人の国内移動と比べる（総計−外国人）
f["net_dom_jp"] = (f.in_dom_tot - f.in_dom_for) - (f.out_dom_tot - f.out_dom_for)
jpd = f.groupby("mtype")[["net_dom_jp"]].sum()
jpd["jp14"] = p[p.year == 2014].groupby("mtype").jp.sum()
jpd["per_jp14"] = jpd.net_dom_jp / jpd.jp14
out["jp_net_domestic_by_type"] = jpd.round(4).reset_index().to_dict(orient="records")

# ---------- 4. 国籍（在留外国人統計 2015年末・2022年末） ----------
zm = pd.read_csv(ROOT / "data/zairyu_muni_nat_raw.csv", dtype={"code5": str})
z15 = zm[zm.year == 2015].copy()
has_child = z15[z15.is_ward == True].groupby(["pref", "city"]).size()
z15["drop"] = (z15.is_ward == False) & z15.set_index(["pref", "city"]).index.isin(has_child.index)
z15 = z15[~z15["drop"]]
z15 = z15[z15.pref != z15.name]  # 都道府県の合計行


def mkname(r):
    if r.is_ward and (str(r.city).endswith("市") or str(r.city).endswith("郡")):
        return str(r.city) + r["name"]
    return r["name"]


z15["jname"] = z15.apply(mkname, axis=1)
j16 = pd.read_csv(ROOT / "data/juki_panel.csv", dtype={"code5": str})
j16 = j16[(j16.year == 2016) & ~j16.is_city_total]
key = dict(zip(zip(j16.pref, j16.name), j16.code5))
z15["code5"] = [key.get((pf, nm)) for pf, nm in zip(z15.pref, z15.jname)]
unmatched = z15[z15.code5.isna() & (z15.nat == "総数")]
out["zairyu2015_unmatched_units"] = int(len(unmatched))
out["zairyu2015_unmatched_people"] = float(unmatched.n.sum())
z15 = z15.dropna(subset=["code5"])
z22 = zm[(zm.year == 2022) & zm.code5.notna()].copy()
z22 = z22[~z22.code5.str.endswith("000")]
# 政令市の合計行（区がある市）と特別区部の合計行を除く
names22 = set(z22.name.astype(str))
wardcity = {re.match(r"(.+?市).+区$", n).group(1) for n in names22 if re.match(r"(.+?市).+区$", n)}
z22 = z22[~z22.name.astype(str).isin(wardcity) & (z22.code5 != "13100")]
z22 = z22[~z22.name.astype(str).str.contains("郡$|特別区部")]
z15.loc[z15.jname.astype(str).str.startswith("浜松市"), "code5"] = "22130"
z22.loc[z22.name.astype(str).str.startswith("浜松市"), "code5"] = "22130"
NATS = ["中国", "韓国", "フィリピン", "ブラジル", "ベトナム", "ネパール", "米国", "台湾", "その他", "総数"]
jp_for = {2015: 2016, 2022: 2023}
natrows = []
nat_tab = {}
for yr_, zz in [(2015, z15), (2022, z22)]:
    t = zz[zz.nat.isin(NATS)].pivot_table(index="code5", columns="nat", values="n", aggfunc="sum").fillna(0)
    if yr_ == 2022:
        extra = [c for c in ["インドネシア", "タイ"] if c in zz.nat.unique()]
        add = zz[zz.nat.isin(extra)].pivot_table(index="code5", columns="nat", values="n", aggfunc="sum").fillna(0)
        t["その他"] = t["その他"] + add.reindex(t.index).fillna(0).sum(axis=1)
    jj = p[p.year == jp_for[yr_]].set_index("code5")
    t = t.join(jj[["jp", "area", "mtype"]], how="inner")
    nat_tab[yr_] = t
    for n_ in NATS:
        natrows.append(dict(year=yr_, nat=n_, total=t[n_].sum(), D=dissim(t[n_], t.jp),
                            gini=gini(t[n_], t.jp), top5=top_share(t[n_]),
                            share_chiho=t.loc[t.area == "地方圏", n_].sum() / t[n_].sum(),
                            share_town=t.loc[t.mtype == "町村", n_].sum() / t[n_].sum(),
                            units=len(t)))
natdf = pd.DataFrame(natrows)
natdf.to_csv(RES / "nationality_concentration.csv", index=False)
out["nationality"] = natdf.round(4).to_dict(orient="records")
out["zairyu2015_total_matched"] = float(nat_tab[2015]["総数"].sum())
out["zairyu2022_total_matched"] = float(nat_tab[2022]["総数"].sum())
# 国籍別の増加の地域の内訳（2015→2022）
inc = []
for n_ in NATS:
    a = nat_tab[2015].groupby("area")[n_].sum(); b = nat_tab[2022].groupby("area")[n_].sum()
    d_ = b - a
    for ar in d_.index:
        inc.append(dict(nat=n_, area=ar, n15=a[ar], n22=b[ar], growth=b[ar] / a[ar] - 1,
                        contrib=d_[ar] / d_.sum() if d_.sum() != 0 else np.nan))
incdf = pd.DataFrame(inc)
incdf.to_csv(RES / "nationality_growth_by_area.csv", index=False)
out["nationality_growth_area"] = incdf.round(4).to_dict(orient="records")
# 国籍の構成の変化で、全体の D の変化をどれだけ説明できるか（シフトシェア型）
t15, t22 = nat_tab[2015], nat_tab[2022]
nats8 = [n_ for n_ in NATS if n_ != "総数"]
w15 = t15[nats8].sum() / t15[nats8].sum().sum(); w22 = t22[nats8].sum() / t22[nats8].sum().sum()
out["nat_mix_2015"] = w15.round(4).to_dict(); out["nat_mix_2022"] = w22.round(4).to_dict()
# 2015年の国籍ごとの分布のまま、構成だけ2022年にした場合の D
common_c = t15.index.intersection(t22.index)
sh15 = t15.loc[common_c, nats8] / t15.loc[common_c, nats8].sum()
f_cf = (sh15 * (w22 * t22.loc[common_c, nats8].sum().sum())).sum(axis=1)
out["D_2015_actual"] = dissim(t15.loc[common_c, nats8].sum(axis=1), t15.loc[common_c, "jp"])
out["D_2022_actual"] = dissim(t22.loc[common_c, nats8].sum(axis=1), t22.loc[common_c, "jp"])
out["D_2022_mix_only"] = dissim(f_cf, t22.loc[common_c, "jp"])

# ---------- 5. 頑健性 ----------
rb = {}
# (a) 単位: 政令市の区を市にまとめる・23区を1つにまとめる
def collapse_city(g):
    g = g.copy()
    w = g.name.str.match(r".+市.+区$")
    g.loc[w, "name"] = g.loc[w, "name"].str.extract(r"^(.+?市)")[0]
    tk = (g.pref == "東京都") & g.name.str.endswith("区")
    g.loc[tk, "name"] = "東京都区部"
    return g.groupby(["pref", "name"])[["pop_for", "jp", "pop_tot"]].sum()


for y in [2014, 2026]:
    c = collapse_city(p[p.year == y])
    rb[f"D_city_collapsed_{y}"] = dissim(c.pop_for, c.jp)
    rb[f"gini_city_collapsed_{y}"] = gini(c.pop_for, c.jp)
    q = p[(p.year == y) & (p.pref != "東京都")]
    rb[f"D_excl_tokyo_{y}"] = dissim(q.pop_for, q.jp)
# (b) 期間: コロナの前と後
for (y0, y1) in [(2014, 2020), (2020, 2023), (2023, 2026)]:
    c0, c1 = conc.set_index("year").loc[y0], conc.set_index("year").loc[y1]
    rb[f"D_change_{y0}_{y1}"] = float(c1.D_muni - c0.D_muni)
    rb[f"chiho_share_change_{y0}_{y1}"] = float(c1.share_chiho - c0.share_chiho)
    rb[f"town_share_change_{y0}_{y1}"] = float(c1.share_town - c0.share_town)
# (c) データ源: 在留外国人統計（年末）と住基（翌年1月1日）
zt = pd.read_csv(ROOT / "data/zairyu_muni_total.csv", dtype={"code5": str})
for zy, jy in [(2023, 2024), (2025, 2026)]:
    a = zt[zt.year == zy].copy()
    a.loc[a.name.astype(str).str.startswith("浜松市"), "code5"] = "22130"
    a = a.groupby("code5").n.sum()
    b = p[p.year == jy].set_index("code5")
    jn = b.join(a, how="inner")
    rb[f"zairyu{zy}_vs_juki{jy}_corr"] = float(np.corrcoef(jn.n, jn.pop_for)[0, 1])
    rb[f"zairyu{zy}_vs_juki{jy}_ratio"] = float(jn.n.sum() / jn.pop_for.sum())
    rb[f"D_zairyu{zy}"] = dissim(jn.n, jn.jp)
    rb[f"D_juki{jy}_same_units"] = dissim(jn.pop_for, jn.jp)
    rb[f"units_{zy}"] = int(len(jn))
rb["D_zairyu2015_nat_table"] = float(out["D_2015_actual"])
rb["D_zairyu2022_nat_table"] = float(out["D_2022_actual"])
# (d) ブートストラップ（市区町村を復元抽出）で D の変化の区間
g0 = p[p.year == 2014].set_index("code5"); g1 = p[p.year == 2026].set_index("code5")
cc = g0.index.intersection(g1.index)
rng = np.random.default_rng(140)
bs = []
for _ in range(1000):
    s = rng.choice(len(cc), len(cc), replace=True)
    i = cc[s]
    bs.append(dissim(g1.loc[i, "pop_for"], g1.loc[i, "jp"]) - dissim(g0.loc[i, "pop_for"], g0.loc[i, "jp"]))
rb["D_change_2014_2026_boot_ci"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
rb["D_change_2014_2026_point"] = float(dissim(g1.loc[cc, "pop_for"], g1.loc[cc, "jp"]) - dissim(g0.loc[cc, "pop_for"], g0.loc[cc, "jp"]))
# (e) 指標の違い（2014→2026 の変化の向き）
c0, c1 = conc.iloc[0], conc.iloc[-1]
rb["measure_change"] = {k: float(c1[k] - c0[k]) for k in ["D_muni", "gini_muni", "theil_muni", "top5_muni", "D_pref", "gini_pref"]}
out["robustness"] = rb

json.dump(out, open(RES / "results.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["national_growth", "n_common_units", "muni_growth_quantiles", "share_doubled",
                                     "share_muni_jp_down_for_up", "offset_ratio_jp_down_units",
                                     "spearman_growth_vs_initial_ratio", "dom_over_abr_type", "dom_over_abr_area",
                                     "dom_over_abr_area_type", "theil_decomp", "zairyu2015_unmatched_units",
                                     "zairyu2015_unmatched_people", "zairyu2015_total_matched", "zairyu2022_total_matched",
                                     "D_2015_actual", "D_2022_actual", "D_2022_mix_only"]}, ensure_ascii=False, indent=1, default=float))
print(conc[["year", "foreign", "share", "D_muni", "gini_muni", "theil_muni", "top5_muni", "D_pref", "n_lq_gt1", "share_chiho", "share_chiho_pop", "share_town", "share_town_pop"]].round(4).to_string())
print(g_at[["for14", "for26", "growth", "contrib", "share14", "share26", "ratio14", "ratio26", "jp_growth"]].round(3).to_string())
print(g_size[["growth", "contrib", "ratio14", "ratio26", "jp_growth"]].round(3).to_string())
print(gq.round(3).to_string())
print(fl_at.round(3).to_string())
print(yr.round(0).to_string())
print(jpd.round(4).to_string())
print(natdf.round(3).to_string())
print(incdf[incdf.area == "地方圏"].round(3).to_string())
print(json.dumps(rb, ensure_ascii=False, indent=1, default=float))
