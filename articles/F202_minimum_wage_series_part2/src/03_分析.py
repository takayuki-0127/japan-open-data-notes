"""F202 分析
1. 年収の壁と最低賃金の重なり（時間に直す・20時間の線・県の就業調整の割合）
2. 全国一律にしたときのシナリオ（前提を振った幅）
3. 言えること・言えないこと（検出力・外挿の範囲）
"""
import json
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import RAW, DATA, RES, SEED

rng = np.random.default_rng(SEED)
out = {}

# ---------------------------------------------------------------- 1. 年収の壁を時間に直す
nat = pd.read_csv(DATA / "mw_national.csv")
WALLS = {"106万円（月8.8万円）": 1_056_000, "130万円": 1_300_000}
for name, w in WALLS.items():
    nat[f"h_week_{w}"] = w / nat["mw_wavg"] / 52
nat.to_csv(RES / "wall_hours_national.csv", index=False)
def hrow(y):
    r = nat[nat.year == y].iloc[0]
    return {"mw": r.mw_wavg, "h106": round(r[f"h_week_1056000"], 2), "h130": round(r[f"h_week_1300000"], 2)}
out["wall_hours"] = {y: hrow(y) for y in (2005, 2012, 2017, 2022, 2025, 2026)}

# 20時間の線：週20時間×52週÷12か月で月8.8万円になる時給
H20 = 20 * 52 / 12
MW_20LINE = 88_000 / H20
out["mw_20h_line"] = round(MW_20LINE, 1)
long = pd.read_csv(DATA / "mw_pref_long.csv")
cnt = (long["mw"] >= MW_20LINE).groupby(long["year"]).sum().astype(int).rename("n_pref_over_20hline")
cnt.to_csv(RES / "pref_over_20h_line.csv")
out["n_pref_over_20hline"] = {int(k): int(v) for k, v in cnt.items() if k >= 2019}
# 月8.8万円に届く週の時間（県、2026年度）
l26 = long[long.year == 2026].copy()
l26["h_week_for_88k"] = 88_000 / l26["mw"] / (52 / 12)
l26["h_week_under130"] = 1_300_000 / l26["mw"] / 52
l26.to_csv(RES / "pref_hours_2026.csv", index=False)
out["pref_hours_2026"] = {"h88k_min": round(l26.h_week_for_88k.min(), 1), "h88k_max": round(l26.h_week_for_88k.max(), 1),
                          "h130_min": round(l26.h_week_under130.min(), 1), "h130_max": round(l26.h_week_under130.max(), 1)}

# F82：有配偶の女性の集積の大きさ b
f82 = pd.read_csv(RAW / "f82_bunching_main.csv")
f82r = pd.read_csv(RAW / "f82_robustness.csv")
mw_w = f82[f82.key.str.contains("有配偶の女性")].copy()
out["f82_b_married_women"] = {k[:4]: round(v, 2) for k, v in zip(mw_w.key, mw_w.b)}
rb = f82r[~f82r.spec.str.contains("100万円刻み")].pivot(index="spec", columns="year", values="b")
out["f82_b_drop_range"] = [round((rb[2017] - rb[2022]).min(), 2), round((rb[2017] - rb[2022]).max(), 2)]

# 県の就業調整の割合（非正規の女性）と最低賃金
pa = pd.read_csv(DATA / "panel_adjust.csv")
nat_sh = pd.read_csv(DATA / "adjust_national.csv")
out["adjust_national"] = {f"{r.year}_{r.sex}": round(r.share_adj, 2) for r in nat_sh.itertuples()}

def wls(y, x, w):
    X = sm.add_constant(x)
    m = sm.WLS(y, X, weights=w).fit(cov_type="HC1")
    return m

def perm_p(y, x, w, n=10000):
    b0 = wls(y, x, w).params.iloc[1]
    xs = np.asarray(x)
    cnt = 0
    for _ in range(n):
        b = wls(y, rng.permutation(xs), w).params.iloc[1]
        cnt += abs(b) >= abs(b0)
    return (cnt + 1) / (n + 1)

rows = []
def add(label, sex, kind, y, x, w, scale, unit, perm=True):
    m = wls(y, x, w)
    b, se = m.params.iloc[1] * scale, m.bse.iloc[1] * scale
    rows.append({"spec": label, "sex": sex, "kind": kind, "coef": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se,
                 "p": m.pvalues.iloc[1], "p_perm": perm_p(y, x, w, 4000) if perm else np.nan,
                 "n": len(y), "unit": unit, "corr": np.corrcoef(x, y)[0, 1]})

for sex in ("F", "M"):
    d22 = pa[(pa.year == 2022) & (pa.sex == sex)]
    # 断面：最低賃金が10%高い県で、就業調整の割合は何ポイント違うか
    add("断面2022・最低賃金の額", sex, "level", d22.share_adj, d22.lmw, d22.tot_all, np.log(1.1), "pt / 最低賃金+10%")
    if sex == "F":
        add("断面2022・25〜54歳", sex, "level", d22.share_adj_25_54, d22.lmw, d22.tot_25_54, np.log(1.1), "pt / 最低賃金+10%")
        dd = d22[d22.code != 13]
        add("断面2022・東京を除く", sex, "level", dd.share_adj, dd.lmw, dd.tot_all, np.log(1.1), "pt / 最低賃金+10%")
        add("断面2022・カイツ指標", sex, "level", d22.share_adj, d22.kaitz, d22.tot_all, 0.05, "pt / カイツ+0.05", perm=False)
    # 変化：2017→2022 の最低賃金の上がり方と、就業調整の割合の変化
    a = pa[(pa.year == 2017) & (pa.sex == sex)].set_index("code")
    b_ = pa[(pa.year == 2022) & (pa.sex == sex)].set_index("code")
    dy = b_.share_adj - a.share_adj
    dx = b_.lmw - a.lmw
    w = (a.tot_all + b_.tot_all) / 2
    add("変化2017→22・最低賃金の上がり方", sex, "change", dy, dx, w, 0.01, "pt / 上がり方+1%")
    if sex == "F":
        dy2 = b_.share_adj_25_54 - a.share_adj_25_54
        add("変化2017→22・25〜54歳", sex, "change", dy2, dx, (a.tot_25_54 + b_.tot_25_54) / 2, 0.01, "pt / 上がり方+1%")
        keep = dx.index != 13
        add("変化2017→22・東京を除く", sex, "change", dy[keep], dx[keep], w[keep], 0.01, "pt / 上がり方+1%")
        out["dlmw_range_pct"] = [round(100 * dx.min(), 1), round(100 * dx.max(), 1), round(100 * dx.std(), 2)]
        out["dshare_F"] = {"mean": round(dy.mean(), 2), "min": round(dy.min(), 2), "max": round(dy.max(), 2),
                           "n_down": int((dy < 0).sum())}
adj = pd.DataFrame(rows)
adj.to_csv(RES / "adjust_vs_mw.csv", index=False)
out["adjust_vs_mw"] = adj.round(3).to_dict(orient="records")

# ---------------------------------------------------------------- 2. 全国一律のシナリオ
sc = pd.read_csv(DATA / "scenario_base.csv")
pw = pd.read_csv(RAW / "f201_panel_wage.csv")
kaitz_obs_max = float(pw.kaitz.max())
kaitz_obs_p99 = float(pw.kaitz.quantile(0.99))
# 2026年度のカイツ指標の見込み：2025年の値×（2026年度÷2025年度の最低賃金）÷（1＋時給の伸び）
g = pw[pw.year == 2025].dlw.median() / 100
sc["kaitz2026"] = sc.kaitz2025 * sc.mw2026 / sc.mw2025 / (1 + g)
out["wage_growth_assumed_pct"] = round(100 * g, 2)
LEVELS = {"全国加重平均（1,177円）にそろえる": 1177, "いちばん高い県（1,280円）にそろえる": 1280, "1,500円にそろえる": 1500}
# 雇用の弾力性（最低賃金1%あたりの就業者の%変化）。F201 の per10 を、就業率の平均で弾力性に直した値
mc = pd.read_csv(RAW / "f201_method_comparison.csv")
main = mc[(mc.outcome == "emp_rate") & (mc["sample"] == "2008–25（2020–22除く）") &
          (~mc.note.str.contains("72組", na=False)) & (~mc.method.str.contains("合成", na=False) | mc.note.str.contains("並べ替え", na=False))]
ratio = (main.elast / main.per10).median()   # per10（pt）→ 弾力性
E = {
    "方法の幅の上端（0）": 0.0,
    "方法の幅の中ほど（−0.04）": float(main.elast.median()),
    "方法の幅の下端（−0.18）": float(main.elast.min()),
    "前編が渡した端（−0.35）": -0.35,
}
_lo, _hi = float(main.lo.min() * ratio), float(main.hi.max() * ratio)
E[f"95%区間の下端（{_lo:+.2f}）".replace("-", "−")] = _lo
E[f"95%区間の上端（{_hi:+.2f}）".replace("-", "−")] = _hi
out["elasticities"] = {k: round(v, 3) for k, v in E.items()}
srows, prow = [], []
emp_total = sc.emp.sum()
for lname, L in LEVELS.items():
    new = np.maximum(sc.mw2026, L)
    pct = np.log(new / sc.mw2026)
    kz = sc.kaitz2026 * new / sc.mw2026
    for c, p, k in zip(sc.code, pct, kz):
        prow.append({"level": lname, "code": c, "pct_up": 100 * (np.exp(p) - 1), "kaitz_new": k})
    base = {"level": lname, "L": L, "n_raised": int((new > sc.mw2026).sum()),
            "wavg_up_pct": float(100 * np.average(np.exp(pct) - 1, weights=sc.emp)),
            "max_up_pct": float(100 * (np.exp(pct.max()) - 1)),
            "n_kaitz_over_obsmax": int((kz > kaitz_obs_max).sum()),
            "emp_share_kaitz_over_obsmax": float(100 * sc.emp[kz > kaitz_obs_max].sum() / emp_total)}
    for ename, e in E.items():
        d = (sc.emp * e * pct).sum()            # 千人
        # 感度：観測されたカイツ指標の最大を超える分だけ、効き方を2倍にする
        over = np.clip(np.log(kz / np.maximum(sc.kaitz2026, kaitz_obs_max)), 0, None)
        d2 = (sc.emp * e * (pct + over)).sum()
        srows.append({**base, "elast_name": ename, "elast": e, "d_emp_10k": d / 10, "d_emp_pct": 100 * d / emp_total,
                      "d_emp_10k_nonlinear": d2 / 10})
scen = pd.DataFrame(srows)
scen.to_csv(RES / "scenario_uniform.csv", index=False)
pd.DataFrame(prow).to_csv(RES / "scenario_pref_increase.csv", index=False)
out["kaitz_obs_max"] = round(kaitz_obs_max, 3)
out["kaitz_obs_p99"] = round(kaitz_obs_p99, 3)
summ = {}
for lname in LEVELS:
    s = scen[scen.level == lname]
    mainband = s[s.elast_name.str.contains("方法の幅")]
    summ[lname] = {
        "n_raised": int(s.n_raised.iloc[0]), "wavg_up_pct": round(s.wavg_up_pct.iloc[0], 1), "max_up_pct": round(s.max_up_pct.iloc[0], 1),
        "main_band_10k": [round(mainband.d_emp_10k.min(), 1), round(mainband.d_emp_10k.max(), 1)],
        "wide_band_10k": [round(s.d_emp_10k.min(), 1), round(s.d_emp_10k.max(), 1)],
        "nonlinear_low_10k": round(s.d_emp_10k_nonlinear.min(), 1),
        "n_kaitz_over_obsmax": int(s.n_kaitz_over_obsmax.iloc[0]),
        "emp_share_kaitz_over_obsmax": round(s.emp_share_kaitz_over_obsmax.iloc[0], 1),
    }
out["scenario_summary"] = summ
out["emp_total_10k"] = round(emp_total / 10, 1)

# 頑健性：基準の年度を2025年度にする（2026年度の値が確定済みか不安な場合）
rob = []
for lname, L in LEVELS.items():
    for basecol in ("mw2025", "mw2026"):
        new = np.maximum(sc[basecol], L)
        pct = np.log(new / sc[basecol])
        for ename in ("方法の幅の下端（−0.18）", "前編が渡した端（−0.35）"):
            rob.append({"level": lname, "base": basecol, "elast_name": ename,
                        "d_emp_10k": float((sc.emp * E[ename] * pct).sum() / 10)})
rob = pd.DataFrame(rob)
rob.to_csv(RES / "scenario_robust_base_year.csv", index=False)
out["scenario_robust_base_year"] = rob.round(1).to_dict(orient="records")

# ---------------------------------------------------------------- 3. 言えること・言えないこと
fj = json.load(open(RAW / "f201_for_F202.json", encoding="utf-8"))
mde = pd.DataFrame(fj["mde"])
out["mde80_per10"] = [round(mde.mde80.min(), 2), round(mde.mde80.max(), 2)]
out["mde80_elast"] = [round(mde.mde80.min() * ratio, 3), round(mde.mde80.max() * ratio, 3)]
# 1,500円のときに「見分けられる最小の差」を人数に直すと
s15 = scen[(scen.level == "1,500円にそろえる")].iloc[0]
pct15 = np.log(np.maximum(sc.mw2026, 1500) / sc.mw2026)
out["mde_people_at1500_10k"] = round(float((sc.emp * (mde.mde80.min() * ratio) * pct15).sum() / 10), 1)

json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:6000])
