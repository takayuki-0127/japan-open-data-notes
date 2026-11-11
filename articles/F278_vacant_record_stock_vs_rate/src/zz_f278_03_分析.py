"""03 分析：空き家の増加を住宅数と空き家率に分ける・記録の数え方・標本誤差・都道府県・種類・問い直し"""
import json, math, pathlib
import numpy as np
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1]
O = R / "results"; O.mkdir(exist_ok=True)
nat = pd.read_csv(R / "data/national_long.csv")
pref = pd.read_csv(R / "data/pref_long.csv")
res = {}

# 全国の系列：1958〜1968は沖縄を含まない、1973年からは含む
inc = nat[nat.basis == "incl_okinawa"].set_index("year")
exc = nat[nat.basis == "excl_okinawa"].set_index("year")
ser = pd.concat([exc.loc[[1958, 1963, 1968]], inc]).copy()
ser["rate"] = ser.vacant / ser.stock
YEARS = list(ser.index)


def pair(y0, y1):
    """y0→y1 の (S0,V0,S1,V1)。1968→1973 は両方とも沖縄を含まない値"""
    if y0 == 1968 and y1 == 1973:
        a, b = exc.loc[1968], exc.loc[1973]
    else:
        a, b = ser.loc[y0], ser.loc[y1]
    return a.stock, a.vacant, b.stock, b.vacant


def decomp(S0, V0, S1, V1, how="mid"):
    r0, r1 = V0 / S0, V1 / S1
    if how == "mid": st, rt = (S1 - S0) * (r0 + r1) / 2, (S0 + S1) / 2 * (r1 - r0)
    elif how == "base": st, rt = (S1 - S0) * r0, S1 * (r1 - r0)   # 住宅の分を前の率で
    else: st, rt = (S1 - S0) * r1, S0 * (r1 - r0)                 # 住宅の分を後の率で
    assert abs(st + rt - (V1 - V0)) < 1
    return st, rt


# A. 各回の分解と記録
rows = []
for y0, y1 in zip(YEARS[:-1], YEARS[1:]):
    S0, V0, S1, V1 = pair(y0, y1)
    st, rt = decomp(S0, V0, S1, V1)
    prev = ser.loc[:y0]
    if y1 == 1973:  # 沖縄を含まない値どうしで記録を判定
        cnt_rec, rate_rec = exc.loc[1973].vacant > prev.vacant.max(), exc.loc[1973].vacant / exc.loc[1973].stock > prev.rate.max()
        rate_prev_max = prev.rate.max(); r1v = exc.loc[1973].vacant / exc.loc[1973].stock
    else:
        cnt_rec, rate_rec = ser.loc[y1].vacant > prev.vacant.max(), ser.loc[y1].rate > prev.rate.max()
        rate_prev_max = prev.rate.max(); r1v = ser.loc[y1].rate
    # 問い直し：率が前回のままでも「過去最多」になったか（前回の率×今回の住宅数 > それまでの最多）
    const_rate_count = S1 * (V0 / S0)
    rows.append(dict(y0=y0, y1=y1, dV=V1 - V0, stock_part=st, rate_part=rt, stock_share=st / (V1 - V0),
                     r0=V0 / S0, r1=V1 / S1, dS_pct=S1 / S0 - 1, count_record=bool(cnt_rec), rate_record=bool(rate_rec),
                     const_rate_record=bool(const_rate_count > prev.vacant.max())))
A = pd.DataFrame(rows)
A.to_csv(O / "A_decomp_records.csv", index=False)
res["stock_1973_excl"] = float(exc.loc[1973].stock)
res["const_rate_margin_pct"] = [float(100 * (pair(a, b)[2] * pair(a, b)[1] / pair(a, b)[0] / ser.loc[:a].vacant.max() - 1)) for a, b in zip(YEARS[:-1], YEARS[1:])]
res["national_series"] = {int(y): dict(stock=float(ser.loc[y].stock), vacant=float(ser.loc[y].vacant), rate=float(ser.loc[y].rate)) for y in YEARS}
res["records"] = dict(n=len(A), count_records=int(A.count_record.sum()), rate_records=int(A.rate_record.sum()),
                      rate_record_years=[int(y) for y in A[A.rate_record].y1], rate_nonrecord_years=[int(y) for y in A[~A.rate_record].y1],
                      count_record_years=[int(y) for y in A[A.count_record].y1],
                      const_rate_records=int(A.const_rate_record.sum()), const_rate_nonrecord_years=[int(y) for y in A[~A.const_rate_record].y1])
res["records_1973on"] = dict(n=int((A.y1 >= 1978).sum()), count=int(A[A.y1 >= 1978].count_record.sum()), rate=int(A[A.y1 >= 1978].rate_record.sum()))
res["stock_share_all"] = dict(total_dV=float(A.dV.sum()), total_stock=float(A.stock_part.sum()), share=float(A.stock_part.sum() / A.dV.sum()),
                              share_1973on=float(A[A.y0 >= 1973].stock_part.sum() / A[A.y0 >= 1973].dV.sum()))

# B. 2018→2023：H1 と分け方の頑健性
S0, V0, S1, V1 = pair(2018, 2023)
B = {}
for how in ["mid", "base", "end"]:
    st, rt = decomp(S0, V0, S1, V1, how)
    B[how] = dict(stock_part=st, rate_part=rt, stock_share=st / (V1 - V0))
res["h1_2018_2023"] = dict(dV=V1 - V0, dS=S1 - S0, r2018=V0 / S0, r2023=V1 / S1, **{k: v for k, v in B.items()})
res["H1"] = "支持" if B["mid"]["stock_share"] >= 0.5 else "外れ"

# C. 標本誤差（主要項目別標準誤差率、%）
CV = {2018: dict(vacant=0.57, vac_other=0.52, vac_rent=0.62), 2023: dict(vacant=0.35, vac_other=0.36, vac_rent=0.47)}
CV_S = {"main": 0.09, "zero": 0.0}   # 2018年の総数の標準誤差率は読み取りに不安があるので、2023年の値（0.09%）を両年に使う
Cres = []
for item in ["vacant", "vac_other", "vac_rent"]:
    v0, v1 = inc.loc[2018, item], inc.loc[2023, item]
    s0, s1 = inc.loc[2018].stock, inc.loc[2023].stock
    for cvs_name, cvs in CV_S.items():
        for rho in [0.0, 0.3, 0.5]:
            se_v0, se_v1 = v0 * CV[2018][item] / 100, v1 * CV[2023][item] / 100
            sd_dv = math.sqrt(se_v0**2 + se_v1**2 - 2 * rho * se_v0 * se_v1)
            r0, r1 = v0 / s0, v1 / s1
            se_r0 = r0 * math.sqrt((CV[2018][item] / 100) ** 2 + (cvs / 100) ** 2)
            se_r1 = r1 * math.sqrt((CV[2023][item] / 100) ** 2 + (cvs / 100) ** 2)
            sd_dr = math.sqrt(se_r0**2 + se_r1**2 - 2 * rho * se_r0 * se_r1)
            Cres.append(dict(item=item, cv_stock=cvs_name, rho=rho, dV=v1 - v0, se_dV=sd_dv, z_dV=(v1 - v0) / sd_dv,
                             r2018=r0, r2023=r1, dr_pt=100 * (r1 - r0), se_dr_pt=100 * sd_dr, z_dr=(r1 - r0) / sd_dr))
C = pd.DataFrame(Cres); C.to_csv(O / "C_sampling_error.csv", index=False)
main = C[(C.item == "vacant") & (C.cv_stock == "main") & (C.rho == 0)].iloc[0]
res["H3"] = dict(z_count=main.z_dV, z_rate=main.z_dr, dr_pt=main.dr_pt, se_dr_pt=main.se_dr_pt,
                 z_rate_range=[float(C[C.item == "vacant"].z_dr.min()), float(C[C.item == "vacant"].z_dr.max())],
                 verdict="支持" if main.z_dr >= 1.96 else "外れ")


# C2. 2018年の総数の標準誤差率（読み取れない）を変えたときの z（2023年は0.09%、相関0）
v0, v1 = inc.loc[2018].vacant, inc.loc[2023].vacant; s0, s1 = inc.loc[2018].stock, inc.loc[2023].stock
r0, r1 = v0 / s0, v1 / s1


def z_for(cv18):
    se0 = r0 * math.sqrt(0.0057**2 + (cv18 / 100) ** 2); se1 = r1 * math.sqrt(0.0035**2 + 0.0009**2)
    return (r1 - r0) / math.sqrt(se0**2 + se1**2)


sens = {f"{c:.2f}": z_for(c) for c in [0.0, 0.09, 0.2, 0.4, 0.6, 0.8]}
lo, hi = 0.09, 2.0
for _ in range(60):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if z_for(mid) >= 1.96 else (lo, mid)
res["h3_cvS2018_sensitivity"] = dict(z=sens, breakeven_cv_pct=lo)

# D. 都道府県：2023年の記録（それより前のすべての回と比べる）
D = []
for c, g in pref.groupby("code"):
    g = g.set_index("year").sort_index()
    g = g[g.vacant.notna() & g.stock.notna()]
    g["rate"] = g.vacant / g.stock
    prev, cur = g.loc[:2018], g.loc[2023]
    p18 = g.loc[2018]
    rec = dict(code=c, count_rec=cur.vacant > prev.vacant.max(), rate_rec=cur.rate > prev.rate.max(),
               count_rec5=cur.vacant >= 1.05 * prev.vacant.max(), rate_rec5=cur.rate >= 1.05 * prev.rate.max(),
               count_up=cur.vacant > p18.vacant, rate_up=cur.rate > p18.rate, stock_up=cur.stock > p18.stock,
               const_rate_rec=cur.stock * p18.rate > prev.vacant.max(),
               dV=cur.vacant - p18.vacant)
    st, rt = decomp(p18.stock, p18.vacant, cur.stock, cur.vacant)
    rec.update(stock_part=st, rate_part=rt)
    # その他の空き家の率
    if pd.notna(cur.vac_other):
        go = g[g.vac_other.notna()]
        ro = go.vac_other / go.stock
        rec.update(other_rate_rec=ro.loc[2023] > ro.loc[:2018].max(), other_rate_up=ro.loc[2023] > ro.loc[2018],
                   other_count_rec=go.loc[2023].vac_other > go.loc[:2018].vac_other.max())
    D.append(rec)
D = pd.DataFrame(D); D.to_csv(O / "D_pref_records_2023.csv", index=False)
res["H4"] = dict(n=len(D), count_rec=int(D.count_rec.sum()), rate_rec=int(D.rate_rec.sum()), diff=int(D.count_rec.sum() - D.rate_rec.sum()),
                 count_rec5=int(D.count_rec5.sum()), rate_rec5=int(D.rate_rec5.sum()),
                 count_up=int(D.count_up.sum()), rate_up=int(D.rate_up.sum()), stock_up=int(D.stock_up.sum()),
                 const_rate_rec=int(D.const_rate_rec.sum()),
                 other_rate_rec=int(D.other_rate_rec.sum()), other_rate_up=int(D.other_rate_up.sum()), other_count_rec=int(D.other_count_rec.sum()),
                 stock_share_pref_sum=float(D.stock_part.sum() / D.dV.sum()),
                 n_rate_part_negative=int((D.rate_part < 0).sum()))
res["H4"]["verdict"] = "支持" if res["H4"]["diff"] >= 10 else "外れ"

# E. 種類別（全国、1983年から）
E = []
for y in [1983, 1988, 1993, 1998, 2003, 2008, 2013, 2018, 2023]:
    r = inc.loc[y]
    rent_sale = r.vac_rent + (r.vac_sale if pd.notna(r.vac_sale) else 0)
    E.append(dict(year=y, stock=r.stock, total=r.vacant / r.stock, other=r.vac_other / r.stock, rent_sale=rent_sale / r.stock,
                  rent=r.vac_rent / r.stock if y >= 2003 else np.nan, second=r.vac_second / r.stock,
                  other_n=r.vac_other, rent_sale_n=rent_sale, second_n=r.vac_second))
E = pd.DataFrame(E); E.to_csv(O / "E_types_national.csv", index=False)
e18, e23 = E.set_index("year").loc[2018], E.set_index("year").loc[2023]
res["H5"] = dict(d_total_pt=100 * (e23.total - e18.total), d_other_pt=100 * (e23.other - e18.other), d_rent_sale_pt=100 * (e23.rent_sale - e18.rent_sale),
                 d_rent_pt=100 * (e23.rent - e18.rent), d_second_pt=100 * (e23.second - e18.second),
                 other_dV=float(inc.loc[2023].vac_other - inc.loc[2018].vac_other), total_dV=float(V1 - V0))
res["H5"]["verdict"] = "支持" if res["H5"]["d_other_pt"] > res["H5"]["d_total_pt"] else "外れ"
so = decomp(inc.loc[2018].stock, inc.loc[2018].vac_other, inc.loc[2023].stock, inc.loc[2023].vac_other)
res["other_decomp_2018_2023"] = dict(stock_part=so[0], rate_part=so[1], stock_share=so[0] / sum(so))
# その他の空き家の率の記録（1988〜2023年の8回）
oth = E.set_index("year").other
res["other_rate_records"] = [int(y) for y in oth.index[1:] if oth.loc[y] > oth.loc[:y].iloc[:-1].max()]

# H2
r = res["records"]
res["H2"] = "支持" if (r["count_records"] == 13 and r["rate_records"] <= 10) else "外れ"
json.dump(res, open(O / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(A.to_string()); print(json.dumps({k: res[k] for k in ["records", "records_1973on", "stock_share_all", "h1_2018_2023", "H1", "H2", "H3", "H4", "H5", "other_decomp_2018_2023", "other_rate_records"]}, ensure_ascii=False, indent=1, default=float))
print(C.round(3).to_string()); print(E.round(4).to_string())
