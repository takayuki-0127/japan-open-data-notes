"""03 分析：世帯数の変化の分解、都道府県の増減、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
D = pd.read_csv(ROOT / "data" / "households.csv")
YEARS = [1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]
REGION = {"北海道・東北": range(1, 8), "関東": range(8, 15), "中部": range(15, 24), "近畿": range(24, 31),
          "中国": range(31, 36), "四国": range(36, 40), "九州・沖縄": range(40, 48)}
def r(x, n=1): return float(round(float(x), n))

def decomp(h0, p0, h1, p1, sym=True):
    k0, k1 = h0 / p0, h1 / p1
    if sym:
        pop = (p1 - p0) * (k0 + k1) / 2; size = (p0 + p1) / 2 * (k1 - k0)
    else:  # 始めの年の世帯の大きさを固定
        pop = (p1 - p0) * k0; size = p1 * (k1 - k0)
    return pop, size

M = {}
# ---- 全国
n = D[D.pref == 0].set_index("year")
rows = []
for a, b in zip(YEARS[:-1], YEARS[1:]):
    h0, p0, h1, p1 = n.loc[a, "gen_h"], n.loc[a, "gen_p"], n.loc[b, "gen_h"], n.loc[b, "gen_p"]
    pop, size = decomp(h0, p0, h1, p1)
    rows.append({"期間": f"{a}→{b}", "世帯数の変化": int(h1 - h0), "人員の変化": int(p1 - p0),
                 "人口の効果": int(round(pop)), "人数の効果": int(round(size)),
                 "1世帯あたり人員_始": r(p0 / h0, 3), "1世帯あたり人員_終": r(p1 / h1, 3)})
NT = pd.DataFrame(rows); NT.to_csv(RES / "national_decomposition.csv", index=False)
last = NT.iloc[-1]; prev = NT.iloc[-2]; t1015 = NT[NT["期間"] == "2010→2015"].iloc[0]
M["全国"] = {"一般世帯数_2020": int(n.loc[2020, "gen_h"]), "一般世帯数_2025": int(n.loc[2025, "gen_h"]),
            "一般世帯人員_2020": int(n.loc[2020, "gen_p"]), "一般世帯人員_2025": int(n.loc[2025, "gen_p"]),
            "1世帯あたり人員_2020": r(n.loc[2020, "gen_p"] / n.loc[2020, "gen_h"], 3),
            "1世帯あたり人員_2025": r(n.loc[2025, "gen_p"] / n.loc[2025, "gen_h"], 3),
            "2020_2025": {k: (int(v) if isinstance(v, (int, np.integer)) else v) for k, v in last.items()},
            "2015_2020": {k: (int(v) if isinstance(v, (int, np.integer)) else v) for k, v in prev.items()},
            "2010_2015": {k: (int(v) if isinstance(v, (int, np.integer)) else v) for k, v in t1015.items()}}
M["H1"] = {"世帯数の変化_2020_2025": int(last["世帯数の変化"]), "判定": ("支持" if last["世帯数の変化"] > 0 else "外れ") + "（参考：数字を見たあとに置いた仮説）"}
M["H3"] = {"人数の効果_2010_2015": int(t1015["人数の効果"]), "人数の効果_2015_2020": int(prev["人数の効果"]),
           "人数の効果_2020_2025": int(last["人数の効果"]),
           "判定": "支持" if last["人数の効果"] < t1015["人数の効果"] else "外れ"}

# ---- 都道府県
P = D[D.pref > 0].pivot(index="pref", columns="year", values=["gen_h", "gen_p"])
names = D[(D.pref > 0) & (D.year == 2025)].set_index("pref")["name"]
pref = pd.DataFrame({"県": names})
for a, b in [(2010, 2015), (2015, 2020), (2020, 2025)]:
    pref[f"世帯変化率_{a}_{b}_%"] = ((P["gen_h"][b] / P["gen_h"][a] - 1) * 100).round(3)
    pref[f"人員変化率_{a}_{b}_%"] = ((P["gen_p"][b] / P["gen_p"][a] - 1) * 100).round(3)
pref.index.name = "pref"; pref.to_csv(RES / "pref_changes.csv")
dec = {f"{a}_{b}": int((P["gen_h"][b] < P["gen_h"][a]).sum()) for a, b in [(2005, 2010), (2010, 2015), (2015, 2020), (2020, 2025)]}
M["H2"] = {"世帯が減った県の数": dec, "判定": "支持" if (dec["2020_2025"] >= 20 and dec["2020_2025"] > dec["2015_2020"]) else "外れ"}
M["H2"]["人員が減った県の数_2020_2025"] = int((P["gen_p"][2025] < P["gen_p"][2020]).sum())
M["H2"]["世帯が増えた県_2020_2025"] = [names[p] for p in P.index if P["gen_h"][2025][p] > P["gen_h"][2020][p]]

def corr(a, b, drop=()):
    q = pref.drop(index=list(drop))
    x = q[f"人員変化率_{a}_{b}_%"]; y = q[f"世帯変化率_{a}_{b}_%"]
    pr = stats.pearsonr(x, y)[0]; lr = stats.linregress(x, y)
    return pr, lr.slope, lr.intercept, -lr.intercept / lr.slope
pr, sl, ic, x0 = corr(2020, 2025)
M["H4"] = {"相関_r": r(pr, 3), "傾き": r(sl, 3), "切片_%": r(ic, 2), "世帯が増減ゼロになる人員の変化率_%": r(x0, 2),
           "判定": "支持" if pr >= 0.8 else "外れ"}
for a, b in [(2010, 2015), (2015, 2020)]:
    p2, s2, i2, x2 = corr(a, b)
    M[f"参考_{a}_{b}"] = {"相関_r": r(p2, 3), "切片_%": r(i2, 2), "世帯が増減ゼロになる人員の変化率_%": r(x2, 2)}

# 地方別（北から南）
reg = []
for nm, rg in REGION.items():
    rg = list(rg)
    for a, b in [(2015, 2020), (2020, 2025)]:
        h0, h1 = P["gen_h"][a][rg].sum(), P["gen_h"][b][rg].sum()
        p0, p1 = P["gen_p"][a][rg].sum(), P["gen_p"][b][rg].sum()
        pop, size = decomp(h0, p0, h1, p1)
        reg.append({"地方": nm, "期間": f"{a}→{b}", "世帯数の変化": int(h1 - h0), "人口の効果": int(round(pop)), "人数の効果": int(round(size)),
                    "世帯が減った県の数": int((P["gen_h"][b][rg] < P["gen_h"][a][rg]).sum()), "県の数": len(rg)})
RG = pd.DataFrame(reg); RG.to_csv(RES / "by_region.csv", index=False)
M["地方別_2020_2025"] = {row["地方"]: {"世帯数の変化": row["世帯数の変化"], "世帯が減った県の数": row["世帯が減った県の数"], "県の数": row["県の数"]}
                        for row in reg if row["期間"] == "2020→2025"}

# ---- 頑健性
rob = []
# 1 施設等の世帯を含む総数（2020年まで）：2015→2020年の減った県の数
dt = D[D.pref > 0].pivot(index="pref", columns="year", values="total_h")
rob.append(("H2", "施設等の世帯を含む総数（2015→2020年）", "世帯が減った県の数", int((dt[2020] < dt[2015]).sum()),
            "（参考：2025年は総数なし）"))
# 2 始めの年の大きさを固定する分け方
_, s_a = decomp(n.loc[2020, "gen_h"], n.loc[2020, "gen_p"], n.loc[2025, "gen_h"], n.loc[2025, "gen_p"], sym=False)
_, s_b = decomp(n.loc[2010, "gen_h"], n.loc[2010, "gen_p"], n.loc[2015, "gen_h"], n.loc[2015, "gen_p"], sym=False)
rob.append(("H3", "始めの年の大きさを固定", "人数の効果 2010→15／2020→25", f"{int(round(s_b)):,}／{int(round(s_a)):,}", "支持" if s_a < s_b else "外れ"))
# 3 2015→2020年の相関
p3 = M["参考_2015_2020"]["相関_r"]
rob.append(("H4", "2015→2020年", "相関 r", p3, "支持" if p3 >= 0.8 else "外れ"))
# 4 東京都を除く
p4, *_ = corr(2020, 2025, drop=(13,))
rob.append(("H4", "東京都を除く（2020→2025年）", "相関 r", r(p4, 3), "支持" if p4 >= 0.8 else "外れ"))
# 5 スピアマン
sp = stats.spearmanr(pref["人員変化率_2020_2025_%"], pref["世帯変化率_2020_2025_%"])[0]
rob.append(("H4", "スピアマンの順位相関", "rho", r(sp, 3), "支持" if sp >= 0.8 else "外れ"))
R = pd.DataFrame(rob, columns=["仮説", "変えたこと", "指標", "値", "判定"]); R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {f"{a}|{b}": {"指標": c, "値": v, "判定": j} for a, b, c, v, j in rob}

# ---- 問い直し（結果を見てから足した）：世帯が減った県は「人口の減りが速い」のか「世帯の小さくなり方が遅い」のか
sz = lambda y: P["gen_p"][y] / P["gen_h"][y]
q = pd.DataFrame({"県": names, "人員変化率_%": (P["gen_p"][2025] / P["gen_p"][2020] - 1) * 100,
                  "1世帯あたり人員の変化率_%": (sz(2025) / sz(2020) - 1) * 100,
                  "世帯変化率_%": (P["gen_h"][2025] / P["gen_h"][2020] - 1) * 100})
q["世帯が減った"] = q["世帯変化率_%"] < 0
q.round(3).to_csv(RES / "requestion_pref_2020_2025.csv")
g = q.groupby("世帯が減った")[["人員変化率_%", "1世帯あたり人員の変化率_%", "世帯変化率_%"]].mean()
M["問い直し"] = {"減った県の平均": {k: r(v, 2) for k, v in g.loc[True].items()},
               "増えた県の平均": {k: r(v, 2) for k, v in g.loc[False].items()},
               "全国_人員変化率_%": r((n.loc[2025, "gen_p"] / n.loc[2020, "gen_p"] - 1) * 100, 2),
               "全国_1世帯あたり人員の変化率_%": r(((n.loc[2025, "gen_p"] / n.loc[2025, "gen_h"]) / (n.loc[2020, "gen_p"] / n.loc[2020, "gen_h"]) - 1) * 100, 2),
               "1世帯あたり人員の変化率_県の範囲_%": [r(q["1世帯あたり人員の変化率_%"].min(), 2), r(q["1世帯あたり人員の変化率_%"].max(), 2)],
               "人員変化率_県の範囲_%": [r(q["人員変化率_%"].min(), 2), r(q["人員変化率_%"].max(), 2)]}
cs = stats.pearsonr(q["人員変化率_%"], q["1世帯あたり人員の変化率_%"])[0]
M["問い直し"]["人員の変化率と1世帯あたり人員の変化率の相関_r"] = r(cs, 3)

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1, default=float)
print(json.dumps(M, ensure_ascii=False, indent=1, default=float))
print(NT.to_string())
