"""03 分析：産業構成（と職業構成）による要因分解。results/ に CSV と summary.json を書き出す。"""
import os, json
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results"); os.makedirs(R, exist_ok=True)
I = pd.read_csv(os.path.join(ROOT, "data", "telework_industry.csv"))
O = pd.read_csv(os.path.join(ROOT, "data", "telework_occupation.csv"))
PREFS = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
 "新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県",
 "和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県","大分県",
 "宮崎県","鹿児島県","沖縄県"]
BLOCK = {}
for b, ps in {"北海道・東北": PREFS[0:7], "関東": PREFS[7:14], "中部": PREFS[14:23], "近畿": PREFS[23:30],
              "中国・四国": PREFS[30:39], "九州・沖縄": PREFS[39:47]}.items():
    for p in ps: BLOCK[p] = b
TOKYO_AREA = ["埼玉県", "千葉県", "東京都", "神奈川県"]

def outcome(df, y):
    if y == "tw": return df["tw"]
    if y == "f80": return df["f80"]
    if y == "f60": return df["f60_80"] + df["f80"]
    if y == "home": return df["home"]
    raise ValueError(y)

def decompose(D, status="有業者総数", y="tw", base="全国", prefs=PREFS):
    """対称型のシフト・シェア分解。差 = 構成効果 + 内部効果（産業ごとの率の差）。"""
    d = D[(D.status == status) & (D.cat != "総数")].copy()
    d["y"] = outcome(d, y)
    N = d[d.region == base].set_index("cat")
    sN = N["total"] / N["total"].sum(); rN = (N["y"] / N["total"]).fillna(0)
    rows = []
    for p in prefs:
        P = d[d.region == p].set_index("cat").reindex(N.index).fillna(0)
        sP = P["total"] / P["total"].sum()
        rP = (P["y"] / P["total"]).where(P["total"] > 0, rN)   # 0人の産業は全国の率で埋める（内部効果0）
        comp = ((sP - sN) * (rP + rN) / 2).sum()
        within = ((rP - rN) * (sP + sN) / 2).sum()
        lasp = ((sP - sN) * rN).sum()                       # 全国の率で重みづけた構成効果
        expected = (sP * rN).sum()                          # 構成だけを当てはめた率
        std = (sN * rP).sum()                               # 全国の構成にそろえた率（直接法）
        actual = (sP * rP).sum()
        rows.append(dict(region=p, block=BLOCK[p], employed=P["total"].sum(), actual=actual, national=(sN*rN).sum(),
                         gap=actual - (sN*rN).sum(), comp=comp, within=within, comp_lasp=lasp, expected=expected, standardized=std))
    return pd.DataFrame(rows), pd.DataFrame({"share_nat": sN, "rate_nat": rN, "employed_nat": N["total"], "y_nat": N["y"]})

def var_share(T, w=None):
    g = T["gap"]; c = T["comp"]
    if w is None:
        return float(np.cov(c, g)[0, 1] / np.var(g, ddof=1))
    w = w / w.sum(); gm = (w * g).sum(); cm = (w * c).sum()
    return float((w * (c - cm) * (g - gm)).sum() / (w * (g - gm) ** 2).sum())

res = {}
T, NAT = decompose(I)
T.to_csv(os.path.join(R, "decomp_industry_tw.csv"), index=False)
res["national_rate"] = float(T["national"].iloc[0])
res["n_pref"] = len(T)
res["gap_range"] = [float(T.gap.min()), float(T.gap.max())]
res["actual_range"] = [float(T.actual.min()), float(T.actual.max())]
res["var_share_comp_unweighted"] = var_share(T)
res["var_share_comp_weighted"] = var_share(T, T.employed)
res["corr_actual_expected"] = float(np.corrcoef(T.actual, T.expected)[0, 1])
res["sd_actual"] = float(T.actual.std()); res["sd_expected"] = float(T.expected.std()); res["sd_standardized"] = float(T.standardized.std())
res["max_min_actual"] = float(T.actual.max() / T.actual.min()); res["max_min_standardized"] = float(T.standardized.max() / T.standardized.min())
tk = T.set_index("region").loc["東京都"]
res["tokyo"] = dict(actual=float(tk.actual), gap=float(tk.gap), comp=float(tk.comp), within=float(tk.within), standardized=float(tk.standardized))
ta = T[T.region.isin(TOKYO_AREA)]
res["tokyo_area_gap_mean"] = float(ta.gap.mean()); res["tokyo_area_comp_share_mean"] = float((ta.comp / ta.gap).mean())
oth = T[~T.region.isin(TOKYO_AREA)]
res["others_gap_mean"] = float(oth.gap.mean()); res["others_comp_mean"] = float(oth.comp.mean()); res["others_within_mean"] = float(oth.within.mean())
res["n_pref_comp_larger_abs"] = int((T.comp.abs() > T.within.abs()).sum())

# 産業別（全国）
d = I[(I.status == "有業者総数") & (I.region == "全国") & (I.cat != "総数")].set_index("cat")
ind = pd.DataFrame({"employed": d.total, "tw_rate": d.tw / d.total, "f80_rate": d.f80 / d.total,
                    "f80_among_tw": d.f80 / d.tw, "home_among_tw": d.home / d.tw,
                    "share_of_tw": d.tw / d.tw.sum(), "share_of_employed": d.total / d.total.sum()})
# 東京圏とそれ以外の産業内の率
def area_rate(regs, y="tw"):
    x = I[(I.status == "有業者総数") & (I.region.isin(regs)) & (I.cat != "総数")].groupby("cat")[["total", "tw", "f80"]].sum()
    return x[y] / x["total"]
ind["tw_rate_tokyo_area"] = area_rate(TOKYO_AREA); ind["tw_rate_others"] = area_rate([p for p in PREFS if p not in TOKYO_AREA])
ind["ratio_tokyo_others"] = ind.tw_rate_tokyo_area / ind.tw_rate_others
ta_tot = I[(I.status == "有業者総数") & (I.region.isin(TOKYO_AREA)) & (I.cat != "総数")].groupby("cat")[["total", "tw"]].sum()
ind["tokyo_area_share_of_tw"] = ta_tot.tw / d.tw; ind["tokyo_area_share_of_employed"] = ta_tot.total / d.total
ind.sort_values("tw_rate", ascending=False).to_csv(os.path.join(R, "industry_national.csv"))
res["industry_top"] = ind.sort_values("tw_rate", ascending=False).head(5)[["tw_rate", "f80_rate", "f80_among_tw"]].round(4).reset_index().values.tolist()
res["industry_bottom"] = ind.sort_values("tw_rate").head(5)[["tw_rate"]].round(4).reset_index().values.tolist()
allT = I[(I.status == "有業者総数") & (I.cat == "総数")].set_index("region")
res["f80_among_tw_nat"] = float(allT.loc["全国", "f80"] / allT.loc["全国", "tw"])
res["tokyo_area_share_tw"] = float(allT.loc[TOKYO_AREA, "tw"].sum() / allT.loc["全国", "tw"])
res["tokyo_area_share_employed"] = float(allT.loc[TOKYO_AREA, "total"].sum() / allT.loc["全国", "total"])
res["tokyo_area_share_f80"] = float(allT.loc[TOKYO_AREA, "f80"].sum() / allT.loc["全国", "f80"])
# 東京圏の多さを、産業構成（全国の産業内の率×東京圏の構成）でどれだけ説明できるか
x = I[(I.status == "有業者総数") & (I.region.isin(TOKYO_AREA)) & (I.cat != "総数")].groupby("cat")[["total", "tw"]].sum()
o = I[(I.status == "有業者総数") & (I.region.isin([p for p in PREFS if p not in TOKYO_AREA])) & (I.cat != "総数")].groupby("cat")[["total", "tw"]].sum()
rN = NAT.rate_nat
def agg_rates(x): s = x.total / x.total.sum(); r = x.tw / x.total; return s, r
sA, rA = agg_rates(x); sO, rO = agg_rates(o)
gapAO = (sA * rA).sum() - (sO * rO).sum()
compAO = ((sA - sO) * (rA + rO) / 2).sum(); withinAO = ((rA - rO) * (sA + sO) / 2).sum()
res["tokyo_vs_others"] = dict(rate_tokyo_area=float((sA*rA).sum()), rate_others=float((sO*rO).sum()), gap=float(gapAO),
                              comp=float(compAO), within=float(withinAO), comp_share=float(compAO / gapAO))
# 内部効果がどの産業から来ているか（東京圏 vs その他）
contrib = ((rA - rO) * (sA + sO) / 2).sort_values(ascending=False)
contrib.to_csv(os.path.join(R, "tokyo_vs_others_within_by_industry.csv"), header=["within_contrib"])
res["within_contrib_top"] = [[k, round(float(v), 4)] for k, v in contrib.head(5).items()]
compc = ((sA - sO) * (rA + rO) / 2).sort_values(ascending=False)
res["comp_contrib_top"] = [[k, round(float(v), 4)] for k, v in compc.head(5).items()]

# 地方ブロック
blk = T.groupby("block").apply(lambda g: pd.Series(dict(gap=np.average(g.gap, weights=g.employed), comp=np.average(g.comp, weights=g.employed),
                                                        within=np.average(g.within, weights=g.employed), actual=np.average(g.actual, weights=g.employed))))
blk.to_csv(os.path.join(R, "decomp_block.csv"))

# 頑健性
rob = []
def add(name, T):
    rob.append(dict(spec=name, var_share_comp=var_share(T), var_share_comp_w=var_share(T, T.employed),
                    corr_actual_expected=float(np.corrcoef(T.actual, T.expected)[0, 1]),
                    tokyo_comp_share=float(T.set_index("region").loc["東京都", "comp"] / T.set_index("region").loc["東京都", "gap"]) if "東京都" in set(T.region) else np.nan,
                    n=len(T)))
add("主：有業者・産業・実施した", T)
add("雇用者（役員を除く）・産業", decompose(I, status="雇用者（役員を除く）")[0])
To, _ = decompose(O); To.to_csv(os.path.join(R, "decomp_occupation_tw.csv"), index=False); add("有業者・職業（産業の代わり）", To)
add("有業者・産業・頻度80%以上", decompose(I, y="f80")[0])
add("有業者・産業・頻度60%以上", decompose(I, y="f60")[0])
add("有業者・産業・自宅で実施", decompose(I, y="home")[0])
add("東京都を除く46道府県", T[T.region != "東京都"])
add("東京圏（1都3県）を除く43道府県", T[~T.region.isin(TOKYO_AREA)])
Tl = T.copy(); Tl["comp"] = Tl["comp_lasp"]; Tl["gap"] = Tl["actual"] - Tl["national"]; add("全国の率で重みづけた構成効果（非対称）", Tl)
RB = pd.DataFrame(rob); RB.to_csv(os.path.join(R, "robustness.csv"), index=False)
res["robustness"] = RB.round(3).values.tolist()
res["occ_vs_ind_corr_comp"] = float(np.corrcoef(T.comp, To.comp)[0, 1])
# 産業と職業の分解：職業のほうが構成で説明できる割合
json.dump(res, open(os.path.join(R, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(res, ensure_ascii=False, indent=1, default=float)[:6000])
