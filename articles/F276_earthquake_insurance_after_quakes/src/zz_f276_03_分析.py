"""03 分析：PLAN.md の H1〜H4 と頑健性。"""
import json, pathlib, sys
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f276_common import PREF, CODE, ADJ, EVENTS
ROOT = pathlib.Path(__file__).resolve().parents[1]
PRO, RES = ROOT / "data" / "processed", ROOT / "results"
RES.mkdir(parents=True, exist_ok=True)
an = pd.read_csv(PRO / "annual_pref.csv")
mon = pd.read_csv(PRO / "monthly_pref.csv")
FUT = an[an.code > 0].pivot(index="year", columns="code", values="futai")
KAN = an[an.code > 0].pivot(index="year", columns="code", values="kanyu")
NEW = mon[mon.code > 0].pivot(index="ym", columns="code", values="new")
ALL = list(range(1, 48))
KMAX = 5

def groups(aff, adj_in_control=False):
    a = set(aff)
    adj = set(x for p in aff for x in ADJ[p]) - a
    ctrl = [c for c in ALL if c not in a and (adj_in_control or c not in adj)]
    return sorted(a), sorted(adj), ctrl

def uplift(S, p, ctrl, t0, trend=False):
    """U(k) = [S_p(t0+k)-base_p] - [S_c(t0+k)-base_c]"""
    out = {}
    base_y = t0 - 1
    if base_y not in S.index or pd.isna(S.at[base_y, p]):
        return out
    sc = S[ctrl].mean(axis=1)
    for k in range(0, KMAX + 1):
        y = t0 + k
        if y not in S.index or pd.isna(S.at[y, p]):
            break
        if trend:
            if (t0 - 3) not in S.index or pd.isna(S.at[t0 - 3, p]):
                return {}
            bp = S.at[base_y, p] + (k + 1) * (S.at[base_y, p] - S.at[t0 - 3, p]) / 2
            bc = sc[base_y] + (k + 1) * (sc[base_y] - sc[t0 - 3]) / 2
        else:
            bp, bc = S.at[base_y, p], sc[base_y]
        out[k] = (S.at[y, p] - bp) - (sc[y] - bc)
    return out

def overlap(code, eid):
    me = next(e for e in EVENTS if e[0] == eid)
    for e in EVENTS:
        if e[0] == eid or e[4] is None or me[4] is None:
            continue
        if code in [CODE[n] for n in e[3]] and abs(e[4] - me[4]) <= 5:
            return True
    return False

def annual_table(S, tkey=4, adj_in_control=False, trend=False, drop=None, role="aff"):
    rows = []
    for e in EVENTS:
        eid, name, ym, affn, t0f, t0c = e
        t0 = e[tkey]
        if t0 is None:
            continue
        aff = [CODE[n] for n in affn if not (drop and (eid, n) in drop)]
        a, adj, ctrl = groups(aff, adj_in_control)
        targets = a if role == "aff" else adj
        for p in targets:
            u = uplift(S, p, ctrl, t0, trend)
            if not u:
                continue
            r = dict(event=eid, name=name, pref=PREF[p - 1], code=p, role=role, t0=t0, base=S.at[t0 - 1, p],
                     overlap=overlap(p, eid))
            for k, v in u.items():
                r[f"U{k}"] = v
            ks = [k for k in (0, 1, 2) if k in u]
            r["peak"] = max(u[k] for k in ks) if ks else np.nan
            r["peak_k"] = max(ks, key=lambda k: u[k]) if ks else np.nan
            r["full_peak"] = len(ks) == 3
            r["retention"] = (u[5] / r["peak"]) if (5 in u and r["peak"] > 0) else np.nan
            rows.append(r)
    return pd.DataFrame(rows)

def verdicts(aff, adj):
    pk = aff[aff.full_peak]
    h1_share = (pk.peak >= 3).mean()
    ret = aff.dropna(subset=["retention"])
    h2_med = ret.retention.median()
    adjpk = adj[adj.full_peak]
    h3_ratio = adjpk.peak.median() / pk.peak.median() if len(adjpk) else np.nan
    return dict(n_peak=int(len(pk)), h1_share_ge3=float(h1_share), h1_n_ge3=int((pk.peak >= 3).sum()),
                peak_median=float(pk.peak.median()), n_ret=int(len(ret)), h2_retention_median=float(h2_med),
                adj_peak_median=float(adjpk.peak.median()) if len(adjpk) else None,
                h3_ratio=float(h3_ratio) if h3_ratio == h3_ratio else None)

main = {}
aff = annual_table(FUT); adj = annual_table(FUT, role="adj")
aff.to_csv(RES / "A_affected_uplift.csv", index=False); adj.to_csv(RES / "A_adjacent_uplift.csv", index=False)
main["base"] = verdicts(aff, adj)
# 追加の目安（計画にない）：山が3pt以上の組だけの残り方
big = aff[(aff.peak >= 3) & aff.retention.notna()]
main["base"]["retention_median_peak_ge3"] = float(big.retention.median()) if len(big) else None
main["base"]["n_retention_peak_ge3"] = int(len(big))

# 月の新契約
def ym_add(ym, k):
    y, m = map(int, ym.split("/")); t = y * 12 + (m - 1) + k
    return f"{t // 12:04d}/{t % 12 + 1:02d}"
mrows, mser = [], []
for e in EVENTS:
    eid, name, ym0, affn, t0f, t0c = e
    if ym_add(ym0, -12) not in NEW.index:
        continue
    aff_c = [CODE[n] for n in affn]
    a, adjc, ctrl = groups(aff_c)
    nc = NEW[ctrl].sum(axis=1)
    for p in a:
        ser = {}
        for k in range(-6, 25):
            ym = ym_add(ym0, k)
            if ym not in NEW.index:
                break
            b = ym_add(ym0, (k % 12) - 12) if k >= 0 else ym_add(ym, -12)  # 地震前の1年の同じ月を基準（k<0 は前年同月）
            if b not in NEW.index:
                continue
            ser[k] = (NEW.at[ym, p] / NEW.at[b, p]) / (nc[ym] / nc[b])
        post = {k: v for k, v in ser.items() if k >= 0}
        if not post:
            continue
        ks = [k for k in (0, 1, 2, 3) if k in post]
        pk_k = max(ks, key=lambda k: post[k]); pk = post[pk_k]
        hl = None
        if pk > 1:
            for k in sorted(post):
                if k > pk_k and post[k] - 1 < (pk - 1) / 2:
                    hl = k - pk_k; break
        last = max(post)
        mrows.append(dict(event=eid, name=name, pref=PREF[p - 1], ym0=ym0, peak=pk, peak_m=pk_k, half_life=hl,
                          months_obs=last, R12=post.get(12), R24=post.get(24),
                          pre_mean=np.mean([v for k, v in ser.items() if k < 0]) if any(k < 0 for k in ser) else None,
                          in_plan=eid in ("E2011", "E2016", "E2018", "E2019", "E2021", "E2024", "E2025")))
        for k, v in ser.items():
            mser.append(dict(event=eid, pref=PREF[p - 1], k=k, R=v))
M = pd.DataFrame(mrows); M.to_csv(RES / "B_monthly_peaks.csv", index=False)
pd.DataFrame(mser).to_csv(RES / "B_monthly_series.csv", index=False)
Mp = M[M.in_plan]
hl = Mp.half_life.dropna()
main["monthly"] = dict(n=int(len(Mp)), peak_median=float(Mp.peak.median()), share_peak_ge15=float((Mp.peak >= 1.5).mean()),
                       half_life_median=float(hl.median()) if len(hl) else None, n_halflife=int(len(hl)),
                       n_no_halflife=int(Mp.half_life.isna().sum()),
                       all_n=int(len(M)), all_peak_median=float(M.peak.median()),
                       all_half_life_median=float(M.half_life.dropna().median()))

# 頑健性
rob = {}
a1 = annual_table(FUT, trend=True); d1 = annual_table(FUT, trend=True, role="adj"); rob["R1_trend_base"] = verdicts(a1, d1)
a2 = annual_table(FUT, adj_in_control=True); d2 = annual_table(FUT, adj_in_control=True, role="adj"); rob["R2_control_all"] = verdicts(a2, d2)
a3 = aff[~aff.overlap]; d3 = adj; rob["R3_no_overlap"] = verdicts(a3, d3); rob["R3_no_overlap"]["pairs"] = a3[["event", "pref"]].values.tolist()
a4 = annual_table(KAN, tkey=5); d4 = annual_table(KAN, tkey=5, role="adj"); rob["R4_household_rate"] = verdicts(a4, d4)
a4.to_csv(RES / "C_household_uplift.csv", index=False)
drop = {("E2011", "長野"), ("E2011", "静岡")}
a5 = annual_table(FUT, drop=drop); d5 = annual_table(FUT, drop=drop, role="adj"); rob["R5_2011_no_nagano_shizuoka"] = verdicts(a5, d5)
main["robust"] = rob
main["H1"] = "支持" if main["base"]["h1_share_ge3"] > 0.5 else "外れ"
main["H2"] = "支持" if main["base"]["h2_retention_median"] >= 0.5 else "外れ"
main["H3"] = "支持" if (main["base"]["h3_ratio"] or 0) >= 1 / 3 else "外れ"
main["H4"] = "支持" if (main["monthly"]["peak_median"] >= 1.5 and (main["monthly"]["half_life_median"] or 99) <= 6) else "外れ"
nat = an[an.code == 0].set_index("year")
main["national"] = {int(y): dict(futai=nat.at[y, "futai"], kanyu=nat.at[y, "kanyu"]) for y in nat.index}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
pd.set_option("display.width", 220)
print(aff[["event", "pref", "base", "U0", "U1", "U2", "U3", "U4", "U5", "peak", "retention", "overlap"]].round(2).to_string())
print(adj.groupby("event")[["U0", "U1", "U2", "peak"]].median().round(2))
print(M[["event", "pref", "peak", "peak_m", "half_life", "months_obs", "R12", "R24", "pre_mean"]].round(2).to_string())
print(json.dumps({k: main[k] for k in ["base", "monthly", "H1", "H2", "H3", "H4"]}, ensure_ascii=False, indent=1, default=float))
for k, v in rob.items():
    print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "pairs"})

# ---- 結果を見た後に足したもの ----
# (a) 偶然の幅：地震のない県×年度で同じ「山」を計算（被災県・隣の県・その前後5年を除く）
rng = np.random.default_rng(276)
evpairs = set()
for e in EVENTS:
    if e[4] is None:
        continue
    for n in e[3]:
        p = CODE[n]
        for q in [p] + ADJ[p]:
            for y in range(e[4] - 5, e[4] + 6):
                evpairs.add((q, y))
pl = []
for p in ALL:
    for t0 in range(2003, 2024):
        if any((p, y) in evpairs for y in range(t0 - 1, t0 + 3)):
            continue
        ctrl = [c for c in ALL if c != p and c not in ADJ[p]]
        u = uplift(FUT, p, ctrl, t0)
        if all(k in u for k in (0, 1, 2)):
            pl.append(dict(code=p, t0=t0, peak=max(u[k] for k in (0, 1, 2)), U2=u[2]))
PL = pd.DataFrame(pl); PL.to_csv(RES / "D_placebo_peaks.csv", index=False)
q = PL.peak.quantile([0.5, 0.9, 0.95]).to_dict()
main["placebo"] = dict(n=int(len(PL)), median=q[0.5], p90=q[0.9], p95=q[0.95],
                       share_ge3=float((PL.peak >= 3).mean()),
                       events_above_p95=int((aff[aff.full_peak].peak > q[0.95]).sum()))
# (b) 問い直し：上がり幅は、地震の前の付帯率が低い県ほど大きいのか
x = aff[aff.full_peak].copy()
b = np.polyfit(x.base, x.peak, 1)
rho = x[["base", "peak"]].corr(method="spearman").iloc[0, 1]
x5 = aff.dropna(subset=["U5"])
b5 = np.polyfit(x5.base, x5.U5, 1)
# 残りの伸びしろで割った上がり幅
x["peak_rel"] = x.peak / (100 - x.base)
main["reask"] = dict(n=int(len(x)), slope_peak_per_10pt=float(b[0] * 10), spearman=float(rho),
                     slope_U5_per_10pt=float(b5[0] * 10), n5=int(len(x5)),
                     spearman_U5=float(x5[["base", "U5"]].corr(method="spearman").iloc[0, 1]),
                     peak_low_base_median=float(x[x.base < 50].peak.median()), n_low=int((x.base < 50).sum()),
                     peak_high_base_median=float(x[x.base >= 50].peak.median()), n_high=int((x.base >= 50).sum()),
                     peak_rel_median=float(x.peak_rel.median()))
x.to_csv(RES / "E_reask_base_vs_peak.csv", index=False)
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print("placebo", {k: round(v, 3) if isinstance(v, float) else v for k, v in main["placebo"].items()})
print("reask", {k: round(v, 3) if isinstance(v, float) else v for k, v in main["reask"].items()})
