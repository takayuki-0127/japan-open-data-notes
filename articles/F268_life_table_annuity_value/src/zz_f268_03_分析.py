"""03 分析：65歳の年金現価 a65 の5年ごとの変化・年齢の分解・割引率との比較・将来推計人口の見通しとの比較・頑健性。"""
import json
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from common import (DATA, RES, SEXES, AGE_MAX, RATE_BASE, RATES, AGE_GROUPS, AGE_GROUP_LABELS,
                    qx_from_mx, survival_from, annuity_due, a_x_from_mx, e_x_from_mx)

RES.mkdir(exist_ok=True)
jmd = pd.read_csv(DATA / "jmd_mx.csv")
YEARS = sorted(jmd.year.unique())


def mx_vec(sex, year, src=None):
    d = (src if src is not None else jmd)
    v = d[(d.sex == sex) & (d.year == year)].sort_values("age").mx.to_numpy()
    assert len(v) == AGE_MAX + 2, (sex, year, len(v))
    return v


MX = {(s, y): mx_vec(s, y) for s in SEXES for y in YEARS}

# ---------- 1. 年ごとの a65 ----------
rows = []
for s in SEXES:
    for y in YEARS:
        r = {"sex": s, "year": y, "e65": e_x_from_mx(MX[(s, y)], 65)}
        for rate in RATES:
            r[f"a65_{rate*100:.1f}"] = a_x_from_mx(MX[(s, y)], 65, rate)
        rows.append(r)
a65 = pd.DataFrame(rows)
a65.to_csv(RES / "a65_by_year.csv", index=False)
col = f"a65_{RATE_BASE*100:.1f}"

# ---------- 2. 5年ごとの変化 ----------
d5 = []
for s in SEXES:
    t = a65[a65.sex == s].set_index("year")
    for y in YEARS:
        if y + 5 in t.index:
            r = {"sex": s, "start": y, "end": y + 5}
            for rate in RATES:
                c = f"a65_{rate*100:.1f}"
                r[f"d_{rate*100:.1f}"] = t.loc[y + 5, c] / t.loc[y, c] - 1
            r["d_e65"] = t.loc[y + 5, "e65"] - t.loc[y, "e65"]
            d5.append(r)
d5 = pd.DataFrame(d5)
d5.to_csv(RES / "delta5.csv", index=False)
dcol = f"d_{RATE_BASE*100:.1f}"


def d5_get(s, y0, c=dcol):
    return float(d5[(d5.sex == s) & (d5.start == y0)][c].iloc[0])


# 1990〜2019年の5年あたりの伸び（複利で年あたりにならして5年分に直す）と、重なりのある窓の平均
hist = {}
for s in SEXES:
    t = a65[a65.sex == s].set_index("year")[col]
    geo = (t[2019] / t[1990]) ** (5 / 29) - 1
    win = d5[(d5.sex == s) & (d5.start >= 1990) & (d5.end <= 2019)][dcol]
    geo10 = (t[2019] / t[2009]) ** (5 / 10) - 1
    hist[s] = {"geo_per5": geo, "geo_per5_2009_2019": geo10, "mean_windows": float(win.mean()), "min_windows": float(win.min()),
               "max_windows": float(win.max()), "n_windows": int(len(win))}


# ---------- 3. 年齢の分解 ----------
def group_idx(g):
    lo, hi = g
    return [a for a in range(lo, min(hi, AGE_MAX + 1) + 1)]  # 100（開いた階級）は 95以上に入る


def a65_of(mx, rate=RATE_BASE, start=65, tail="const"):
    return a_x_from_mx(mx, start, rate, tail)


def decompose(mx0, mx1, rate=RATE_BASE, start=65, groups=AGE_GROUPS):
    """年齢層ごとに死亡率を入れ替えて a65 の変化（比率の対数ではなく a65 の差）を分ける。
    若い順・高い順の2通りの順番で入れ替え、その平均を寄与とする（寄与の合計は全体の差に一致）。
    1つずつだけ入れ替えた場合の合計との差を交互作用の残りとして出す。"""
    base, end = a65_of(mx0, rate, start), a65_of(mx1, rate, start)
    gidx = [group_idx(g) for g in groups]
    contrib = {}
    for order in (list(range(len(groups))), list(range(len(groups)))[::-1]):
        cur = mx0.copy(); prev = base
        for gi in order:
            cur[gidx[gi]] = mx1[gidx[gi]]
            v = a65_of(cur, rate, start)
            contrib.setdefault(gi, []).append(v - prev)
            prev = v
    seq = {gi: np.mean(v) for gi, v in contrib.items()}
    one = {}
    for gi in range(len(groups)):
        f = mx0.copy(); f[gidx[gi]] = mx1[gidx[gi]]
        b = mx1.copy(); b[gidx[gi]] = mx0[gidx[gi]]
        one[gi] = 0.5 * ((a65_of(f, rate, start) - base) + (end - a65_of(b, rate, start)))
    total = end - base
    return total, seq, total - sum(one.values()), base


dec_rows = []
for s in SEXES:
    for (y0, y1) in [(1990, 1995), (1995, 2000), (2000, 2005), (2005, 2010), (2009, 2014), (2014, 2019), (2019, 2024)]:
        total, seq, resid, base = decompose(MX[(s, y0)].copy(), MX[(s, y1)].copy())
        for gi, lab in enumerate(AGE_GROUP_LABELS):
            dec_rows.append({"sex": s, "start": y0, "end": y1, "age_group": lab,
                             "contrib_a65": seq[gi], "contrib_pct_of_base": seq[gi] / base,
                             "share_of_total": seq[gi] / total if total != 0 else np.nan,
                             "total_a65": total, "total_pct": total / base, "interaction_resid_oneatatime": resid})
dec = pd.DataFrame(dec_rows)
dec.to_csv(RES / "decomposition.csv", index=False)


def share75(s, y0):
    t = dec[(dec.sex == s) & (dec.start == y0)]
    return float(t[t.age_group.isin(AGE_GROUP_LABELS[2:])].contrib_a65.sum() / t.total_a65.iloc[0])


# ---------- 4. 割引率との比較 ----------
rate_rows = []
for s in SEXES:
    for y in [2014, 2019, 2024]:
        a_b = a65_of(MX[(s, y)], RATE_BASE)
        for dr in [-0.005, -0.0025, +0.005]:
            rate_rows.append({"sex": s, "year": y, "rate_from": RATE_BASE, "rate_to": RATE_BASE + dr,
                              "pct_change": a65_of(MX[(s, y)], RATE_BASE + dr) / a_b - 1})
rate_df = pd.DataFrame(rate_rows)
rate_df.to_csv(RES / "rate_sensitivity.csv", index=False)


def rate_down05(s, y=2014):
    """2014年の生命表で割引率を0.5ポイント下げたときの a65 の変化"""
    return float(rate_df[(rate_df.sex == s) & (rate_df.year == y) & (np.isclose(rate_df.rate_to, RATE_BASE - 0.005))]["pct_change"].iloc[0])


# 生命表の5年の更新と同じ大きさになる割引率の下げ幅（2014年の表から）
equiv = {}
for s in SEXES:
    target = a65_of(MX[(s, 2019)], RATE_BASE)
    f = lambda r: a65_of(MX[(s, 2014)], r) - target
    r_eq = brentq(f, -0.02, RATE_BASE + 0.01)
    equiv[s] = RATE_BASE - r_eq

# ---------- 5. Lee–Carter で将来推計人口の平均寿命に合わせる ----------
LC_Y0, LC_Y1 = 1970, 2024


def fit_lc(s):
    ys = list(range(LC_Y0, LC_Y1 + 1))
    M = np.log(np.vstack([MX[(s, y)] for y in ys]).T)  # 年齢 × 年
    a = M.mean(axis=1)
    U, S, Vt = np.linalg.svd(M - a[:, None], full_matrices=False)
    b = U[:, 0] / U[:, 0].sum()
    k = Vt[0] * S[0] * U[:, 0].sum()
    # 2段目：各年の平均寿命に合うよう k を直す（Lee–Miller）
    k2 = []
    for j, y in enumerate(ys):
        e_obs = e_x_from_mx(MX[(s, y)], 0)
        g = lambda kk: e_x_from_mx(np.exp(a + b * kk), 0) - e_obs
        k2.append(brentq(g, k[j] - 200, k[j] + 200))
    return a, b, np.array(k2), ys


ipss = pd.read_csv(DATA / "raw" / "zaisei_kensho_r6_assumptions.csv")
targets = {}
for _, r in ipss[ipss.item.str.startswith("2070年の平均寿命")].iterrows():
    s = "男" if r["item"].endswith("男") else "女"
    targets[(r["case"], s)] = float(r["value"])

proj_rows, lc_save = [], {}
LC = {s: fit_lc(s) for s in SEXES}
for s in SEXES:
    a, b, k, ys = LC[s]
    k_last = k[-1]
    # 出発点は 2024 年の実際の死亡率（ジャンプオフ）：mx(t) = mx2024 × exp(b (k(t) − k2024))
    mx24 = MX[(s, 2024)]
    # 2070年の平均寿命に合う k を3つの仮定それぞれで求める
    k70s = {}
    for case in ["死亡中位", "死亡高位", "死亡低位"]:
        tgt = targets[(case, s)]
        g = lambda kk: e_x_from_mx(mx24 * np.exp(b * (kk - k_last)), 0) - tgt
        k70s[case] = brentq(g, k_last - 400, k_last + 100)
    # 中位は2045年の平均寿命（将来推計人口の中位）にも合わせ、2024→2045→2070年を折れ線でつなぐ。
    # 高位・低位は2045年の値を持っていないので、2045年までの k の動きが2070年までの動きに占める割合を中位と同じと置く。
    ie = pd.read_csv(DATA / "raw" / "ipss_e0_from_F86.csv").set_index("year")
    t45 = float(ie.loc[2045, f"e0_{s}"])
    g45 = lambda kk: e_x_from_mx(mx24 * np.exp(b * (kk - k_last)), 0) - t45
    k45_mid = brentq(g45, k_last - 400, k_last + 100)
    frac = (k45_mid - k_last) / (k70s["死亡中位"] - k_last)
    lc_save[s] = {"b": [float(v) for v in b], "k2024": float(k_last), "k2070": {c: float(v) for c, v in k70s.items()},
                  "k2045": {c: float(k_last + frac * (v - k_last)) for c, v in k70s.items()}, "frac_2045": float(frac)}
    for case in ["死亡中位", "死亡高位", "死亡低位"]:
        k70 = k70s[case]; k45 = k_last + frac * (k70 - k_last)
        for y in range(2024, 2071):
            if y <= 2045:
                kk = k_last + (k45 - k_last) * (y - 2024) / (2045 - 2024)
            else:
                kk = k45 + (k70 - k45) * (y - 2045) / (2070 - 2045)
            mx = mx24 * np.exp(b * (kk - k_last))
            proj_rows.append({"sex": s, "case": case, "year": y, "e0": e_x_from_mx(mx, 0), "e65": e_x_from_mx(mx, 65),
                              **{f"a65_{rr*100:.1f}": a65_of(mx, rr) for rr in RATES}})
proj = pd.DataFrame(proj_rows)
(RES / "lc_params.json").write_text(json.dumps(lc_save, ensure_ascii=False))
proj.to_csv(RES / "ipss_projection_a65.csv", index=False)

ipss_e = pd.read_csv(DATA / "raw" / "ipss_e0_from_F86.csv")
ipss_mid = ipss_e[ipss_e.note.astype(str).str.contains("2")].set_index("year")
proj_cmp = {}
for s in SEXES:
    t = a65[a65.sex == s].set_index("year")[col]
    p = proj[(proj.sex == s)]
    out = {}
    for case in ["死亡中位", "死亡高位", "死亡低位"]:
        pc = p[p.case == case].set_index("year")
        a2070 = pc.loc[2070, col]
        out[case] = {"a65_2070": a2070, "per5_2020_2070": (a2070 / t[2020]) ** (5 / 50) - 1,
                     "per5_2024_2070": (a2070 / t[2024]) ** (5 / 46) - 1,
                     "e65_2070": pc.loc[2070, "e65"], "e0_2045": pc.loc[2045, "e0"], "e65_2045": pc.loc[2045, "e65"]}
    out["ipss_mid_e65_2070"] = float(ipss_mid.loc[2070, f"e65_{s}"])
    out["ipss_mid_e65_2045"] = float(ipss_mid.loc[2045, f"e65_{s}"])
    out["ipss_mid_e0_2045"] = float(ipss_mid.loc[2045, f"e0_{s}"])
    proj_cmp[s] = out

# ---------- 6. 頑健性 ----------
rob = []
# R1 割引率
for s in SEXES:
    for rate in RATES:
        c = f"d_{rate*100:.1f}"
        rob.append({"check": "R1 割引率", "variant": f"{rate*100:.1f}%", "sex": s,
                    "d_2014_2019": d5_get(s, 2014, c), "d_2019_2024": d5_get(s, 2019, c)})

# R2 簡易生命表（厚生労働省）の qx で計算
mh = pd.read_csv(DATA / "mhlw_qx.csv")


def a65_mhlw(s, y, rate=RATE_BASE, start=65):
    t = mh[(mh.sex == s) & (mh.year == y)].sort_values("age")
    q = t.qx.to_numpy()[:105]  # 0..104 歳
    m_open = 1.0 / float(t[t.age == 105].ex.iloc[0])  # 105歳以上は定常人口から m = l/T = 1/e
    p = survival_from(q, start, open_m=m_open, tail="const")
    return annuity_due(p, rate)


mh_a = {}
for s in SEXES:
    for y in [2014, 2019, 2024]:
        mh_a[(s, y)] = a65_mhlw(s, y)
    rob.append({"check": "R2 簡易生命表（厚生労働省）", "variant": "qx を直接使う", "sex": s,
                "d_2014_2019": mh_a[(s, 2019)] / mh_a[(s, 2014)] - 1, "d_2019_2024": mh_a[(s, 2024)] / mh_a[(s, 2019)] - 1})

# R3 3年平均の死亡率（その年と前2年）
for s in SEXES:
    def mx3(y):
        return np.mean([MX[(s, yy)] for yy in (y - 2, y - 1, y)], axis=0)
    a = {y: a65_of(mx3(y)) for y in (2014, 2019, 2024)}
    rob.append({"check": "R3 3年平均の死亡率", "variant": "その年と前2年", "sex": s,
                "d_2014_2019": a[2019] / a[2014] - 1, "d_2019_2024": a[2024] / a[2019] - 1})

# R4 開いた階級の扱い
for s in SEXES:
    for tail, lab in [("cut", "100歳で打ち切る"), ("grow", "死亡率を年10%ずつ上げて延ばす")]:
        a = {y: a65_of(MX[(s, y)], tail=tail) for y in (2014, 2019, 2024)}
        rob.append({"check": "R4 100歳以上の扱い", "variant": lab, "sex": s,
                    "d_2014_2019": a[2019] / a[2014] - 1, "d_2019_2024": a[2024] / a[2019] - 1})

# R5 年金を始める年齢
for s in SEXES:
    for st in (60, 70):
        a = {y: a65_of(MX[(s, y)], start=st) for y in (2014, 2019, 2024)}
        rob.append({"check": "R5 始める年齢", "variant": f"{st}歳", "sex": s,
                    "d_2014_2019": a[2019] / a[2014] - 1, "d_2019_2024": a[2024] / a[2019] - 1})
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)

# 年齢の分解の頑健性：R2〜R5 の条件でも 75歳以上の割合を出す
share_rob = []
for s in SEXES:
    for rate in RATES:
        tot, seq, _, _ = decompose(MX[(s, 2014)].copy(), MX[(s, 2019)].copy(), rate=rate)
        share_rob.append({"sex": s, "variant": f"割引率 {rate*100:.1f}%", "share75": sum(seq[g] for g in range(2, 7)) / tot})
    m0 = np.mean([MX[(s, yy)] for yy in (2012, 2013, 2014)], axis=0)
    m1 = np.mean([MX[(s, yy)] for yy in (2017, 2018, 2019)], axis=0)
    tot, seq, _, _ = decompose(m0, m1)
    share_rob.append({"sex": s, "variant": "3年平均の死亡率", "share75": sum(seq[g] for g in range(2, 7)) / tot})
share_rob = pd.DataFrame(share_rob)
share_rob.to_csv(RES / "decomposition_robustness.csv", index=False)

# ---------- 7. 仮説の判定 ----------
H = {}
H["H1"] = {s: d5_get(s, 2014) for s in SEXES}
H["H1_verdict"] = "支持" if all(v >= 0.02 for v in H["H1"].values()) else "外れ"
H["H2"] = {s: {"d_2019_2024": d5_get(s, 2019), "ratio_to_2014_2019": d5_get(s, 2019) / d5_get(s, 2014)} for s in SEXES}
H["H2_verdict"] = "支持" if all(v["ratio_to_2014_2019"] < 0.5 for v in H["H2"].values()) else "外れ"
H["H3"] = {s: share75(s, 2014) for s in SEXES}
H["H3_verdict"] = "支持" if all(v >= 0.6 for v in H["H3"].values()) else "外れ"
H["H4"] = {s: {"rate_down_0.5pt": rate_down05(s), "table_update_2014_2019": d5_get(s, 2014),
               "equiv_rate_cut_pt": equiv[s] * 100} for s in SEXES}
H["H4_verdict"] = "支持" if all(v["rate_down_0.5pt"] > v["table_update_2014_2019"] for v in H["H4"].values()) else "外れ"
H["H5"] = {s: {"proj_mid_per5": proj_cmp[s]["死亡中位"]["per5_2020_2070"], "hist_per5_1990_2019": hist[s]["geo_per5"]} for s in SEXES}
H["H5_verdict"] = "支持" if all(v["proj_mid_per5"] < v["hist_per5_1990_2019"] for v in H["H5"].values()) else "外れ"

main = {
    "rate_base": RATE_BASE,
    "a65": {s: {str(y): float(a65[(a65.sex == s) & (a65.year == y)][col].iloc[0]) for y in (1990, 2014, 2019, 2020, 2024)} for s in SEXES},
    "e65": {s: {str(y): float(a65[(a65.sex == s) & (a65.year == y)].e65.iloc[0]) for y in (1990, 2014, 2019, 2020, 2024)} for s in SEXES},
    "hist_1990_2019": hist,
    "hypotheses": H,
    "equiv_rate_cut_pt": {s: equiv[s] * 100 for s in SEXES},
    "mhlw_a65": {f"{s}_{y}": v for (s, y), v in mh_a.items()},
    "projection": proj_cmp,
    "decomposition_interaction_resid": {f"{s}_{y0}": float(dec[(dec.sex == s) & (dec.start == y0)].interaction_resid_oneatatime.iloc[0]) for s in SEXES for y0 in (2014, 2019)},
}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=float))
print(json.dumps(main, ensure_ascii=False, indent=1, default=float))
