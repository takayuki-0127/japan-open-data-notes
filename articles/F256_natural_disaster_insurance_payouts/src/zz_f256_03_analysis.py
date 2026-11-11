"""03 分析：名目の保険金を、物価（建設工事費デフレーター）と住宅数で割り引く。

出力 results/
  top10_adjusted.csv       上位10事故：名目・実質・住宅1戸あたり・件数・1件あたり
  annual_fy.csv            2012〜2025年度：協会が調査した自然災害の年度合計
  events_adjusted.csv      2012〜2025年度の事故ごと（実質・1件あたり、種目別）
  robustness.csv           頑健性（物価のものさし・住宅数の補間・範囲・大きな事故を抜く・足切り）
  severity_by_peril.csv    災害の種類別 1件あたり実質保険金
  summary.json             本文で使う数字
"""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
P, R = ROOT / "data" / "processed", ROOT / "results"
R.mkdir(exist_ok=True)
ev = pd.read_csv(P / "events.csv")
top = pd.read_csv(P / "top10.csv")
pr = pd.read_csv(P / "deflator.csv").set_index("fy")
dw = pd.read_csv(P / "dwellings.csv")
T_SURVEY = dw.year.values + 0.75  # 調査は各年10月1日
D_SURVEY = dw.dwellings.values.astype(float)
SLOPE_LAST = (D_SURVEY[-1] - D_SURVEY[-2]) / 5.0
H_SURVEY = dw.households.values.astype(float)  # 頑健性：住宅数の代わりに世帯数（空き家を除いた分母）
H_SLOPE = (H_SURVEY[-1] - H_SURVEY[-2]) / 5.0

def tdate(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return y + (m - 0.5) / 12

def dwell(t, how="linear"):
    if how == "households":
        if t > T_SURVEY[-1]:
            return H_SURVEY[-1] + H_SLOPE * (t - T_SURVEY[-1])
        return float(np.interp(t, T_SURVEY, H_SURVEY))
    if how == "step":  # 直前の調査値のまま
        i = np.searchsorted(T_SURVEY, t, side="right") - 1
        return D_SURVEY[max(i, 0)]
    if t > T_SURVEY[-1]:  # 2023年10月より後は、2018→2023年の増え方で延ばす
        return D_SURVEY[-1] + SLOPE_LAST * (t - T_SURVEY[-1])
    return float(np.interp(t, T_SURVEY, D_SURVEY))

def adjust(df, amount_yen, fy, ym, deflator="defl_house", how="linear"):
    p = df[fy].map(pr[deflator]) if deflator != "none" else 100.0
    real = df[amount_yen] * 100.0 / p
    d = df[ym].map(lambda s: dwell(tdate(s), how))
    return real, d

# ---- 上位10事故 ----
top["nom_yen"] = top.tot_oku * 1e8
top["real_yen"], top["dwell"] = adjust(top, "nom_yen", "fy", "event_ym")
top["real_oku"] = top.real_yen / 1e8
top["yen_per_dwelling"] = top.real_yen / top.dwell
top["claims_per_1000"] = top.n / top.dwell * 1000
top["real_man_per_claim"] = top.real_yen / top.n / 1e4
top["era"] = np.where(top.fy <= 2004, "1991〜2004年", "2014年以降")
top["rank_real_pd"] = top.yen_per_dwelling.rank(ascending=False).astype(int)
top.to_csv(R / "top10_adjusted.csv", index=False)
print(top[["rank", "name", "fy", "tot_oku", "real_oku", "yen_per_dwelling", "claims_per_1000", "real_man_per_claim", "rank_real_pd"]].round(1).to_string())

# ---- 2012〜2025年度：事故ごと ----
nat = ev[ev.natural == 1].copy()
nat["all_yen"] = nat.all_k * 1e3
nat["real_yen"], nat["dwell"] = adjust(nat, "all_yen", "fy", "event_ym")
nat["real_oku"] = nat.real_yen / 1e8
nat["yen_per_dwelling"] = nat.real_yen / nat.dwell
nat["claims_per_1000"] = nat.all_n / nat.dwell * 1000
nat["real_man_per_claim"] = nat.real_yen / nat.all_n / 1e4
k = 100.0 / nat.fy.map(pr["defl_house"])
nat["real_man_fire"] = nat.fire_k * 1e3 * k / nat.fire_n / 1e4
nat["real_man_veh"] = nat.veh_k * 1e3 * k / nat.veh_n.replace(0, np.nan) / 1e4
nat["fire_share"] = (nat.fire_k + nat.misc_k + nat.marine_k) / nat.all_k
nat.to_csv(R / "events_adjusted.csv", index=False)

FY = range(2012, 2026)
def annual(df, col="real_yen", ncol="all_n", how="linear"):
    g = df.groupby("fy").agg(n_events=("file", "size"), claims=(ncol, "sum"), real_yen=(col, "sum"), dwell=("dwell", "mean"))
    g = g.reindex(FY).fillna({"n_events": 0, "claims": 0, "real_yen": 0})
    g["dwell"] = [dwell(f + 0.5, how) for f in g.index]  # 年度の真ん中（10月1日ごろ）の分母
    g["yen_per_dwelling"] = g.real_yen / g.dwell
    g["claims_per_1000"] = g.claims / g.dwell * 1000
    g["real_man_per_claim"] = g.real_yen / g.claims.replace(0, np.nan) / 1e4
    return g
ann = annual(nat)
ann.to_csv(R / "annual_fy.csv")
print(ann.round(1).to_string())

def ktau(s):
    t = stats.kendalltau(s.index, s.values)
    return round(float(t.statistic), 3), round(float(t.pvalue), 3)

def halves(s):
    a, b = s.loc[2012:2018].mean(), s.loc[2019:2025].mean()
    return round(float(a), 1), round(float(b), 1), round(float(b / a), 2)

summ = {}
summ["annual_tau_pd"] = ktau(ann.yen_per_dwelling)
summ["annual_halves_pd"] = halves(ann.yen_per_dwelling)
summ["annual_median_pd"] = (round(float(ann.yen_per_dwelling.loc[2012:2018].median()), 1), round(float(ann.yen_per_dwelling.loc[2019:2025].median()), 1))
summ["annual_tau_claims"] = ktau(ann.claims_per_1000)
summ["annual_tau_sev"] = ktau(ann.real_man_per_claim)
summ["annual_halves_claims"] = halves(ann.claims_per_1000)
summ["annual_halves_sev"] = halves(ann.real_man_per_claim)
summ["top2_share_of_14y"] = round(float(nat.nlargest(2, "real_yen").real_yen.sum() / nat.real_yen.sum()), 3)
summ["top3_share_of_14y"] = round(float(nat.nlargest(3, "real_yen").real_yen.sum() / nat.real_yen.sum()), 3)
summ["total_real_oku_14y"] = round(float(nat.real_yen.sum() / 1e8))

# 上位10の時代比較
g = top.groupby("era")
summ["top10_era"] = {e: dict(n=int(len(d)), mean_yen_pd=round(float(d.yen_per_dwelling.mean())), max_yen_pd=round(float(d.yen_per_dwelling.max())),
                             mean_claims_1000=round(float(d.claims_per_1000.mean()), 1), mean_real_man_claim=round(float(d.real_man_per_claim.mean()), 1))
                     for e, d in g}
summ["mireille"] = top[top.fy == 1991][["real_oku", "yen_per_dwelling", "claims_per_1000", "real_man_per_claim", "rank_real_pd"]].round(1).iloc[0].to_dict()
summ["jebi"] = top[top["rank"] == 1][["real_oku", "yen_per_dwelling", "claims_per_1000", "real_man_per_claim", "rank_real_pd"]].round(1).iloc[0].to_dict()
summ["hagibis"] = top[top["rank"] == 2][["real_oku", "yen_per_dwelling", "claims_per_1000", "real_man_per_claim", "rank_real_pd"]].round(1).iloc[0].to_dict()
d91, d18 = pr.loc[1991, "defl_house"], pr.loc[2018, "defl_house"]
summ["price_1991_to_2018"] = round(float(d18 / d91), 3)
summ["price_1991_to_2025"] = round(float(pr.loc[2025, "defl_house"] / d91), 3)
summ["cpi_1991_to_2025"] = round(float(pr.loc[2025, "cpi_all"] / pr.loc[1991, "cpi_all"]), 3)
summ["dwell_1991_to_2018"] = round(dwell(2018.7) / dwell(1991.7), 3)
summ["hh_1991_to_2018"] = round(dwell(2018.7, "households") / dwell(1991.7, "households"), 3)
# PLAN の H3：年度合計を「件数（住宅1,000戸あたり）」と「1件あたり実質」に分けた前後比と傾向
summ["H3_freq_halves_ratio"] = summ["annual_halves_claims"][2]
summ["H3_sev_halves_ratio"] = summ["annual_halves_sev"][2]

# 災害の種類別 1件あたり
sev = nat.groupby("peril").agg(events=("file", "size"), claims=("all_n", "sum"), real_oku=("real_oku", "sum"),
                               fire_n=("fire_n", "sum"), veh_n=("veh_n", "sum"))
sev["real_man_per_claim"] = sev.real_oku * 1e4 / sev.claims
sev = sev.sort_values("real_man_per_claim", ascending=False)
sev.to_csv(R / "severity_by_peril.csv")
print(sev.round(1).to_string())
summ["sev_by_peril"] = sev.real_man_per_claim.round(1).to_dict()

# 事故単位：1件あたり実質が時代とともに増えたか（風水害の種類をそろえて）
for per in ["台風", "大雨"]:
    d = nat[nat.peril == per]
    t = stats.kendalltau(d.event_ym.map(tdate), d.real_man_per_claim)
    summ[f"tau_sev_events_{per}"] = (round(float(t.statistic), 3), round(float(t.pvalue), 3), int(len(d)))

# ---- 頑健性 ----
rows = []
def era_ratio(deflator="defl_house", how="linear", scope="tot_oku"):
    t = top.copy(); t["nom_yen"] = t[scope] * 1e8
    t["real_yen"], t["dwell"] = adjust(t, "nom_yen", "fy", "event_ym", deflator, how)
    t["pd"] = t.real_yen / t.dwell
    old, new = t[t.fy <= 2004].pd, t[t.fy >= 2013].pd
    m91 = int(t.pd.rank(ascending=False)[t.fy == 1991].iloc[0])
    return round(float(new.mean() / old.mean()), 2), round(float(new.max() / old.max()), 2), m91
def ann_stats(deflator="defl_house", how="linear", drop_top=0, scope="all", thresh=0):
    d = ev[ev.natural == 1].copy()
    amt = {"all": d.all_k, "fire": d.fire_k + d.misc_k, "veh": d.veh_k}[scope] * 1e3
    d["amt"] = amt
    if thresh: d = d[d.all_k * 1e3 >= thresh * 1e8]
    d["real_yen"], d["dwell"] = adjust(d, "amt", "fy", "event_ym", deflator, how)
    if drop_top: d = d.drop(d.nlargest(drop_top, "real_yen").index)
    g = annual(d, how=how)
    tau, p = ktau(g.yen_per_dwelling)
    a, b, ratio = halves(g.yen_per_dwelling)
    return tau, p, a, b, ratio
base = dict(deflator="defl_house", how="linear")
variants = [("基準（住宅総合デフレーター・直線補間・全種目）", {}),
            ("物価：建設総合デフレーター", dict(deflator="defl_const")),
            ("物価：CPI総合", dict(deflator="cpi_all")),
            ("物価：CPI（持家の帰属家賃を除く総合）", dict(deflator="cpi_ex_rent")),
            ("物価：割り引かない（名目）", dict(deflator="none")),
            ("住宅数：直前の調査値のまま（階段）", dict(how="step")),
            ("分母：住宅数の代わりに世帯数（空き家を除く）", dict(how="households"))]
for lab, kw in variants:
    er = era_ratio(**kw); an = ann_stats(**kw)
    rows.append(dict(variant=lab, top10_new_over_old_mean=er[0], top10_new_over_old_max=er[1], mireille_rank_real_pd=er[2],
                     annual_tau=an[0], annual_p=an[1], fy12_18_mean_yen_pd=an[2], fy19_25_mean_yen_pd=an[3], halves_ratio=an[4]))
er = era_ratio(scope="fire_oku")
an = ann_stats(scope="fire")
rows.append(dict(variant="範囲：火災・新種だけ（自動車・海上を除く）", top10_new_over_old_mean=er[0], top10_new_over_old_max=er[1], mireille_rank_real_pd=er[2],
                 annual_tau=an[0], annual_p=an[1], fy12_18_mean_yen_pd=an[2], fy19_25_mean_yen_pd=an[3], halves_ratio=an[4]))
an = ann_stats(scope="veh")
rows.append(dict(variant="範囲：自動車（車両）だけ", annual_tau=an[0], annual_p=an[1], fy12_18_mean_yen_pd=an[2], fy19_25_mean_yen_pd=an[3], halves_ratio=an[4]))
for k_ in (1, 2):
    an = ann_stats(drop_top=k_)
    rows.append(dict(variant=f"大きな事故を抜く：14年間の上位{k_}事故を除く", annual_tau=an[0], annual_p=an[1], fy12_18_mean_yen_pd=an[2], fy19_25_mean_yen_pd=an[3], halves_ratio=an[4]))
an = ann_stats(thresh=100)
rows.append(dict(variant="足切り：名目100億円以上の事故だけ", annual_tau=an[0], annual_p=an[1], fy12_18_mean_yen_pd=an[2], fy19_25_mean_yen_pd=an[3], halves_ratio=an[4]))
rob = pd.DataFrame(rows)
rob.to_csv(R / "robustness.csv", index=False)
print(rob.to_string())
summ["robustness"] = rows
json.dump(summ, open(R / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in summ.items() if k != "robustness"}, ensure_ascii=False, default=float, indent=0))

# ---- 問い直し：大きな事故は「増えた」のか ----
# 協会の上位10事故は「記録の残るすべての事故のうち名目で大きい順の10件」。
# 10位は名目1,642億円。住宅1戸あたり実質がX円以上の事故は、名目に戻すと X×住宅数×物価/100。
# これが1991年以降のどの時点でも1,642億円を超えるXなら、その事故は必ず上位10に入っている（取りこぼしがない）。
def cutoff(deflator="defl_house", how="linear"):
    # 1991年4月〜2026年3月の毎月で、その月に起きた事故が名目1,642億円に届くのに必要な「住宅1戸あたり実質」を出し、最大をとる
    need = []
    for y in range(1991, 2026):
        for m in range(1, 13):
            fy = y - (m <= 3)
            if fy < 1991 or fy > 2025:
                continue
            t = y + (m - 0.5) / 12
            p = pr.loc[fy, deflator] / 100.0 if deflator != "none" else 1.0
            need.append(1642e8 / (p * dwell(t, how)))
    return max(need)

def big_events(deflator="defl_house", how="linear"):
    x = cutoff(deflator, how)
    t = top.copy(); t["nom_yen"] = t.tot_oku * 1e8
    t["real_yen"], t["dwell"] = adjust(t, "nom_yen", "fy", "event_ym", deflator, how)
    t["pd"] = t.real_yen / t.dwell
    big = t[t.pd >= x]
    a = int((big.fy <= 2012).sum()); b = int((big.fy >= 2013).sum())
    # 年数：FY1991〜2012 は22年、FY2013〜2025 は13年。件数の割合が年数の割合と同じという仮説の正確二項検定（片側）
    p = stats.binomtest(b, a + b, 13 / 35, alternative="greater").pvalue if a + b else np.nan
    return round(x), a, b, round(a / 22, 3), round(b / 13, 3), round(float(p), 3), list(big.sort_values("pd", ascending=False).name)

be = {}
for lab, kw in [("住宅総合デフレーター", {}), ("建設総合デフレーター", dict(deflator="defl_const")), ("CPI総合", dict(deflator="cpi_all")),
                ("割り引かない", dict(deflator="none")), ("住宅数を階段で", dict(how="step")), ("世帯数で割る", dict(how="households"))]:
    be[lab] = big_events(**kw)
    print(lab, be[lab])
summ["big_events"] = be
# 足切りを上げても同じか（基準の物価で、カットオフを1.5倍・2倍）
x0 = cutoff()
t = top.copy()
for mult in (1.5, 2.0):
    big = t[t.yen_per_dwelling >= x0 * mult]
    summ[f"big_events_x{mult}"] = (round(x0 * mult), int((big.fy <= 2012).sum()), int((big.fy >= 2013).sum()), list(big.name))
    print(mult, summ[f"big_events_x{mult}"])
json.dump(summ, open(R / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
