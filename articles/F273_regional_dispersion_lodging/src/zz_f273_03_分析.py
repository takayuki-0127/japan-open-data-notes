"""03 分析：地方部の割合・集中の物差し・仮説 H1〜H5・頑健性"""
import json, pathlib
import numpy as np
import pandas as pd
R = pathlib.Path(__file__).resolve().parents[1]
cy = pd.read_csv(R / "data/pref_year.csv")
fy = pd.read_csv(R / "data/pref_fiscal_year.csv")
pop = pd.read_csv(R / "data/pref_population_ssdse_b.csv")

BIG8 = {11, 12, 13, 14, 23, 26, 27, 28}          # 観光庁の三大都市圏
BIG6 = {11, 12, 13, 14, 23, 27}                  # 京都・兵庫を地方部に入れる
TOKYO4 = {11, 12, 13, 14}                        # 首都圏1都3県だけ
HOK_OKI = {1, 47}

def norm(n):
    """都道府県名を「東京」「京都」「大阪」「青森」の形にそろえる"""
    n = n[:-1] if n.endswith("県") else n
    return n[:-1] if n in ("東京都", "京都府", "大阪府") else n

def gini(x, w=None):
    x = np.asarray(x, float)
    if w is None:
        w = np.ones_like(x)
    w = np.asarray(w, float)
    o = np.argsort(x)
    x, w = x[o], w[o]
    cw = np.cumsum(w) / w.sum()
    cxw = np.cumsum(x * w) / (x * w).sum()
    # 台形で面積を出す（重みつきローレンツ曲線）
    b = np.concatenate([[0], cw]); l = np.concatenate([[0], cxw])
    area = np.sum((b[1:] - b[:-1]) * (l[1:] + l[:-1]) / 2)
    return 1 - 2 * area

def hhi(x):
    s = np.asarray(x, float) / np.sum(x)
    return float(np.sum(s ** 2))

def theil(x):
    x = np.asarray(x, float); m = x.mean(); s = x / m
    s = s[s > 0]
    return float(np.mean(np.where(s > 0, s * np.log(s), 0)) * len(s) / len(x))

def top_share(x, k):
    x = np.sort(np.asarray(x, float))[::-1]
    return float(x[:k].sum() / x.sum())

def metrics(df, col, big=BIG8):
    loc = df[~df.code.isin(big)]
    out = {
        "total": float(df[col].sum()),
        "local": float(loc[col].sum()),
        "local_share": float(loc[col].sum() / df[col].sum()),
        "gini47": gini(df[col].values),
        "hhi47": hhi(df[col].values),
        "theil47": theil(df[col].values),
        "top5_47": top_share(df[col].values, 5),
        "top5_local": top_share(loc[col].values, 5),
        "gini_local": gini(loc[col].values),
    }
    return out

rows = []
for y, g in cy.groupby("year"):
    for col in ["foreign", "japanese", "total"]:
        m = metrics(g, col); m.update(year=int(y), who=col); rows.append(m)
M = pd.DataFrame(rows)
M.to_csv(R / "results/A_metrics_by_year.csv", index=False)

def get(who, y, k):
    return float(M[(M.who == who) & (M.year == y)][k].iloc[0])

res = {}
# --- 白書・審議会資料との照合 ---
wp = {2020: 38.3, 2021: 30.7, 2022: 26.0, 2023: 28.5, 2024: 30.9, 2025: 33.0}
res["whitepaper_check"] = {str(y): {"published": v, "mine": round(100 * get("foreign", y, "local_share"), 1)} for y, v in wp.items()}
res["whitepaper_check"]["2024_local_mil"] = {"published": 5086, "mine": round(get("foreign", 2024, "local") / 1e4)}
res["whitepaper_check"]["2025_local_mil"] = {"published_sokuhou": 5873, "mine_kakutei": round(get("foreign", 2025, "local") / 1e4)}
res["whitepaper_check"]["2025_total_mil"] = {"published_sokuhou": 17787, "mine_kakutei": round(get("foreign", 2025, "total") / 1e4)}

# --- H1 ---
s = {y: get("foreign", y, "local_share") for y in range(2011, 2026)}
peak_y = max(range(2011, 2020), key=lambda y: s[y])
res["H1"] = {"share_2025": s[2025], "share_2017": s[2017], "precovid_peak_year": peak_y,
             "verdict": "支持" if s[2025] < s[2017] else "外れ"}
# --- H2 ---
g23, g25 = get("foreign", 2023, "gini47"), get("foreign", 2025, "gini47")
dg = g25 - g23
res["H2"] = {"gini_2023": g23, "gini_2025": g25, "diff": dg,
             "local_share_2023": s[2023], "local_share_2025": s[2025],
             "verdict": "支持" if dg <= -0.005 else ("外れ（向きが言えない）" if abs(dg) < 0.005 else "外れ")}
# --- H3 ---
t19, t25 = get("foreign", 2019, "top5_local"), get("foreign", 2025, "top5_local")
res["H3"] = {"top5_local_2019": t19, "top5_local_2025": t25, "verdict": "支持" if t25 > t19 else "外れ"}
# --- H4 ---
j11, j25 = get("japanese", 2011, "local_share"), get("japanese", 2025, "local_share")
res["H4"] = {"jp_share_2011": j11, "jp_share_2025": j25, "diff_pt": 100 * (j25 - j11),
             "verdict": "支持" if 100 * (j11 - j25) >= 3 else "外れ"}
# --- H5 ---
def growth(y0, y1, big=True):
    a = cy[cy.year == y0]; b = cy[cy.year == y1]
    if big:
        return b[b.code.isin(BIG8)].foreign.sum() / a[a.code.isin(BIG8)].foreign.sum() - 1
    return b[~b.code.isin(BIG8)].foreign.sum() / a[~a.code.isin(BIG8)].foreign.sum() - 1
gl, gb = growth(2024, 2025, False), growth(2024, 2025, True)
avg1519 = float(np.mean([s[y] for y in range(2015, 2020)]))
res["H5"] = {"growth_local_2024_25": gl, "growth_big_2024_25": gb, "share_2025": s[2025], "avg_2015_19": avg1519,
             "verdict": "支持" if (gl > gb and s[2025] < avg1519) else "外れ"}

# --- 増加の分け方 ---
def decomp(y0, y1):
    T0, T1 = get("foreign", y0, "total"), get("foreign", y1, "total")
    s0, s1 = s[y0], s[y1]
    return {"local_increase_mil": (s1 * T1 - s0 * T0) / 1e4, "from_total_growth_mil": (T1 - T0) * s0 / 1e4,
            "from_share_change_mil": (s1 - s0) * T1 / 1e4}
res["decomp_2019_2025"] = decomp(2019, 2025)
res["decomp_2023_2025"] = decomp(2023, 2025)

# --- 2019→2025 の都道府県ごとの増え方（名前は結果ファイルにだけ） ---
a = cy[cy.year == 2019].set_index("code"); b = cy[cy.year == 2025].set_index("code")
gr = (b.foreign / a.foreign).rename("ratio").to_frame()
gr["local"] = ~gr.index.isin(BIG8)
gr["inc"] = b.foreign - a.foreign
gr.to_csv(R / "results/B_pref_growth_2019_2025.csv")
loc = gr[gr.local]
inc_pos = loc.inc.clip(lower=0)
res["pref_growth"] = {
    "n_local_above_2019": int((loc.ratio > 1).sum()), "n_local": int(len(loc)),
    "n_big_above_2019": int((gr[~gr.local].ratio > 1).sum()),
    "median_ratio_local": float(loc.ratio.median()), "median_ratio_big": float(gr[~gr.local].ratio.median()),
    "local_total_inc_mil": float(loc.inc.sum() / 1e4),
    "top5_local_share_of_local_increase": float(inc_pos.sort_values(ascending=False).iloc[:5].sum() / loc.inc.sum()),
}

# --- 頑健性 ---
rob = []
for y in [2017, 2019, 2023, 2024, 2025]:
    g = cy[cy.year == y]
    for nm, big in [("基本（8都府県）", BIG8), ("京都・兵庫を地方部に（6）", BIG6), ("首都圏1都3県だけ（4）", TOKYO4)]:
        rob.append({"check": "R1 三大都市圏の定義", "variant": nm, "year": y,
                    "value": float(g[~g.code.isin(big)].foreign.sum() / g.foreign.sum())})
    rob.append({"check": "R2 物差し", "variant": "HHI", "year": y, "value": hhi(g.foreign)})
    rob.append({"check": "R2 物差し", "variant": "タイル指数", "year": y, "value": theil(g.foreign.values)})
    rob.append({"check": "R2 物差し", "variant": "上位5都道府県の割合", "year": y, "value": top_share(g.foreign, 5)})
    py = min(y, 2023)
    p = pop[pop.fy == py].copy()
    gg = g.merge(cy[cy.year == y][["code"]], on="code")
    gg = gg.assign(pref_nm=gg.name.map(norm))
    p = p.assign(pref_nm=p.pref.map(norm))
    gg = gg.merge(p[["pref_nm", "pop"]], on="pref_nm", how="left")
    assert gg["pop"].notna().all(), gg[gg["pop"].isna()].name.tolist()
    rob.append({"check": "R3 人口1人あたり（人口で重みをつけたジニ）", "variant": f"人口は{py}年度", "year": y,
                "value": gini((gg.foreign / gg["pop"]).values, gg["pop"].values)})
    loc_ex = g[~g.code.isin(BIG8 | HOK_OKI)]
    rob.append({"check": "R4 北海道・沖縄を除いた地方部の割合", "variant": "37県÷全国", "year": y,
                "value": float(loc_ex.foreign.sum() / g.foreign.sum())})
for y in [2017, 2019, 2023, 2024]:
    g = fy[fy.fy == y]
    rob.append({"check": "R5 年度（4〜3月）", "variant": "地方部の割合", "year": y,
                "value": float(g[~g.code.isin(BIG8)].foreign.sum() / g.foreign.sum())})
    rob.append({"check": "R5 年度（4〜3月）", "variant": "ジニ係数", "year": y, "value": gini(g.foreign.values)})
RB = pd.DataFrame(rob)
RB.to_csv(R / "results/C_robustness.csv", index=False)

res["series"] = {w: {str(y): {k: round(get(w, y, k), 4) for k in ["local_share", "gini47", "hhi47", "top5_47", "top5_local", "gini_local"]}
                     for y in range(2011, 2026)} for w in ["foreign", "japanese"]}
(R / "results/main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
for k in ["whitepaper_check", "H1", "H2", "H3", "H4", "H5", "decomp_2019_2025", "decomp_2023_2025", "pref_growth"]:
    print(k, json.dumps(res[k], ensure_ascii=False))
print(RB.pivot_table(index=["check", "variant"], columns="year", values="value").round(3).to_string())
