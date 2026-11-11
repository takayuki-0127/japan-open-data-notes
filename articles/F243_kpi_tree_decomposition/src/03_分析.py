"""F243 03 分析：売上の変化を KPI に分ける。
A 架空の会社（ひかり書店：架空）で、KPI ツリーの分け方・順番・チャネルの構成（ミックス）の効き方を確かめる
B 家計調査の食料130品目で、支出の変化を「値段」と「量」と「品目の構成」に分ける（方法を4つ比べる）
C 商業動態統計で、全店の前年比と既存店の前年比のずれ（店舗網の効果）を見る
"""
import itertools, json, math, os
import numpy as np, pandas as pd
B = os.path.join(os.path.dirname(__file__), "..")
R = f"{B}/results"; os.makedirs(R, exist_ok=True)
rng = np.random.default_rng(243)
out = {}

# ---------- A 架空の会社：ひかり書店（架空）----------
# チャネル：アプリ・Web。KPI：訪問数 × 構成比 × 購入率 × 1注文の点数 × 1点の単価
ch = pd.DataFrame({
    "チャネル": ["アプリ", "Web"],
    "訪問0": [20000, 180000], "訪問1": [60000, 140000],
    "購入率0": [0.20, 0.020], "購入率1": [0.18, 0.018],
    "点数0": [1.5, 1.2], "点数1": [1.5, 1.2],
    "単価0": [1500, 1400], "単価1": [1500, 1400]})
V0, V1 = ch["訪問0"].sum(), ch["訪問1"].sum()
X0 = {"訪問数": V0, "構成": (ch["訪問0"] / V0).values, "購入率": ch["購入率0"].values, "点数": ch["点数0"].values, "単価": ch["単価0"].values}
X1 = {"訪問数": V1, "構成": (ch["訪問1"] / V1).values, "購入率": ch["購入率1"].values, "点数": ch["点数1"].values, "単価": ch["単価1"].values}
FAC = list(X0)
def sales(X): return X["訪問数"] * np.sum(X["構成"] * X["購入率"] * X["点数"] * X["単価"])
def mixX(S): return {f: (X1[f] if f in S else X0[f]) for f in FAC}
S0, S1 = sales(X0), sales(X1)
conv0 = np.sum(X0["構成"] * X0["購入率"]); conv1 = np.sum(X1["構成"] * X1["購入率"])
# シャープレイ値（全部の順番の平均）と、順番ごとの寄与
orders = list(itertools.permutations(FAC))
contrib = {f: [] for f in FAC}
for o in orders:
    cur = set(); prev = S0
    for f in o:
        cur.add(f); v = sales(mixX(cur)); contrib[f].append(v - prev); prev = v
shap = {f: float(np.mean(contrib[f])) for f in FAC}
rngs = {f: (float(np.min(contrib[f])), float(np.max(contrib[f]))) for f in FAC}
# LMDI（チャネルごとの売上の積に分け、構成も1つの要因）
def L(a, b): return (a - b) / (math.log(a) - math.log(b)) if a != b else a
Sc0 = X0["訪問数"] * X0["構成"] * X0["購入率"] * X0["点数"] * X0["単価"]
Sc1 = X1["訪問数"] * X1["構成"] * X1["購入率"] * X1["点数"] * X1["単価"]
lm = {f: 0.0 for f in FAC}
for c in range(2):
    w = L(Sc1[c], Sc0[c])
    for f in FAC:
        a1 = X1[f] if f == "訪問数" else X1[f][c]; a0 = X0[f] if f == "訪問数" else X0[f][c]
        lm[f] += w * math.log(a1 / a0)
# 上だけで分けた素朴なツリー：売上 = 総訪問 × 全体の購入率 × 平均点数 × 平均単価
items0 = np.sum(X0["構成"] * X0["購入率"] * X0["点数"]) / conv0; items1 = np.sum(X1["構成"] * X1["購入率"] * X1["点数"]) / conv1
price0 = S0 / (V0 * conv0 * items0); price1 = S1 / (V1 * conv1 * items1)
naive0 = {"訪問数": V0, "全体の購入率": conv0, "平均点数": items0, "平均単価": price0}
naive1 = {"訪問数": V1, "全体の購入率": conv1, "平均点数": items1, "平均単価": price1}
NF = list(naive0)
nc = {f: [] for f in NF}
for o in itertools.permutations(NF):
    cur = {f: naive0[f] for f in NF}; prev = S0
    for f in o:
        cur[f] = naive1[f]; v = np.prod(list(cur.values())); nc[f].append(v - prev); prev = v
naive_shap = {f: float(np.mean(nc[f])) for f in NF}
out["A"] = {"売上0": S0, "売上1": S1, "伸び率": S1 / S0 - 1, "全体の購入率0": conv0, "全体の購入率1": conv1,
            "チャネル別の購入率の変化": (ch["購入率1"] / ch["購入率0"] - 1).tolist(),
            "シャープレイ": shap, "順番による幅": rngs, "LMDI": lm, "素朴なツリーのシャープレイ": naive_shap, "順番の数": len(orders)}
pd.DataFrame({"要因": FAC, "シャープレイ": [shap[f] for f in FAC], "LMDI": [lm[f] for f in FAC],
              "順番での最小": [rngs[f][0] for f in FAC], "順番での最大": [rngs[f][1] for f in FAC]}).to_csv(f"{R}/A_fictional_decomp.csv", index=False)
# A の頑健性：ランダムな2チャネルの変化で、全体の購入率の向きが両チャネルの向きと逆になる割合
N = 20000; flip = 0; bothdown = 0
for _ in range(N):
    cv0 = rng.uniform(0.005, 0.3, 2); cv1 = cv0 * np.exp(rng.normal(0, 0.15, 2))
    s0 = rng.dirichlet([1, 1]); s1 = rng.dirichlet([1, 1])
    t0, t1 = np.sum(s0 * cv0), np.sum(s1 * cv1)
    if np.all(cv1 < cv0):
        bothdown += 1
        if t1 > t0: flip += 1
    elif np.all(cv1 > cv0) and t1 < t0: flip += 1
out["A_シミュレーション"] = {"回数": N, "両方下がった回": bothdown, "全体の向きが逆になった割合": flip / N}

# ---------- B 家計調査：支出の変化を値段・量・構成に分ける ----------
k = pd.read_csv(f"{B}/data/kakei_items.csv")
k = k[k["group"] != "光熱"]  # 食料・飲料に絞る
def decomp(y0, y1, drop_break=True, drop_fresh=False):
    a = k[k.year == y0].set_index("code"); b = k[k.year == y1].set_index("code")
    idx = a.index.intersection(b.index)
    if drop_break:
        br = k[(k.year > y0) & (k.year <= y1) & (k["break"] == 1)]["code"].unique(); idx = idx.difference(br)
    if drop_fresh: idx = idx[(a.loc[idx, "fresh"] == 0).values]
    a, b = a.loc[idx], b.loc[idx]
    p0, q0, p1, q1 = a.price, a.q, b.price, b.q
    E0, E1 = p0 * q0, p1 * q1
    d = pd.DataFrame({"name": a.name, "group": a.group, "E0": E0, "E1": E1})
    d["価格_L"] = (p1 - p0) * q0; d["量_L"] = (q1 - q0) * p1           # 値段を先に動かす
    d["価格_P"] = (p1 - p0) * q1; d["量_P"] = (q1 - q0) * p0           # 量を先に動かす
    d["価格_S"] = (p1 - p0) * (q0 + q1) / 2; d["量_S"] = (q1 - q0) * (p0 + p1) / 2  # シャープレイ（中点）
    Lw = np.where(E1 != E0, (E1 - E0) / (np.log(E1) - np.log(E0)), E0)
    d["価格_LMDI"] = Lw * np.log(p1 / p0); d["量_LMDI"] = Lw * np.log(q1 / q0)
    return d
periods = [(2019, 2024), (2014, 2019), (2022, 2024), (2004, 2024)]
rowsP = []
for y0, y1 in periods:
    d = decomp(y0, y1)
    dE = (d.E1 - d.E0).sum()
    for m in ["L", "P", "S", "LMDI"]:
        rowsP.append({"期間": f"{y0}→{y1}", "方法": m, "品目数": len(d), "支出0": d.E0.sum(), "支出1": d.E1.sum(), "変化": dE,
                      "価格": d[f"価格_{m}"].sum(), "量": d[f"量_{m}"].sum(), "残り": dE - d[f"価格_{m}"].sum() - d[f"量_{m}"].sum()})
P = pd.DataFrame(rowsP); P.to_csv(f"{R}/B_total_by_method_period.csv", index=False)
main = decomp(2019, 2024)
G = main.groupby("group")[["E0", "E1", "価格_S", "量_S"]].sum(); G["変化"] = G.E1 - G.E0
G.sort_values("変化").to_csv(f"{R}/B_group_2019_2024.csv")
main.to_csv(f"{R}/B_items_2019_2024.csv")
# 品目の粒度を粗くすると：群を1品目とみなして（100g の群だけ）値段×量に分けると、構成の効果が値段に混ざる
mixrows = []
for (y0, y1) in [(2019, 2024), (2014, 2019), (2022, 2024)]:
    a = k[(k.year == y0) & (k.unit == "1g(100g)")].set_index("code"); b = k[(k.year == y1) & (k.unit == "1g(100g)")].set_index("code")
    idx = a.index.intersection(b.index)
    br = k[(k.year > y0) & (k.year <= y1) & (k["break"] == 1)]["code"].unique(); idx = idx.difference(br)
    a, b = a.loc[idx], b.loc[idx]
    for g, ia in a.groupby("group"):
        ib = b.loc[ia.index]
        Q0, Q1 = ia.q.sum(), ib.q.sum(); s0, s1 = ia.q / Q0, ib.q / Q1
        Pa0, Pa1 = (s0 * ia.price).sum(), (s1 * ib.price).sum()
        rate = ((s0 + s1) / 2 * (ib.price - ia.price)).sum(); mix = ((s1 - s0) * (ia.price + ib.price) / 2).sum()
        up = int((ib.price > ia.price).sum())
        mixrows.append({"期間": f"{y0}→{y1}", "群": g, "品目数": len(ia), "100gあたり平均価格0": Pa0, "100gあたり平均価格1": Pa1,
                        "変化": Pa1 - Pa0, "変化率": Pa1 / Pa0 - 1, "値段の効果": rate, "構成の効果": mix,
                        "値上がりした品目": up, "平均の向きと品目の多数派が逆": bool((Pa1 > Pa0) != (up > len(ia) / 2)),
                        "量の変化率（g）": Q1 / Q0 - 1})
MX = pd.DataFrame(mixrows); MX.to_csv(f"{R}/B_mix_rate_by_group.csv", index=False)
# 頑健性：生鮮を除く・区分の変更を含める
r_nofresh = decomp(2019, 2024, drop_fresh=True); r_br = decomp(2019, 2024, drop_break=False)
out["B"] = {"主の期間": "2019→2024", "品目数": int(len(main)), "支出0": float(main.E0.sum()), "支出1": float(main.E1.sum()),
            "変化": float((main.E1 - main.E0).sum()), "変化率": float(main.E1.sum() / main.E0.sum() - 1),
            "価格S": float(main["価格_S"].sum()), "量S": float(main["量_S"].sum()),
            "方法別": P.to_dict("records"),
            "生鮮を除く": {"品目数": int(len(r_nofresh)), "価格S": float(r_nofresh["価格_S"].sum()), "量S": float(r_nofresh["量_S"].sum()), "変化": float((r_nofresh.E1 - r_nofresh.E0).sum())},
            "区分の変更も含める": {"品目数": int(len(r_br)), "価格S": float(r_br["価格_S"].sum()), "量S": float(r_br["量_S"].sum())},
            "値段の寄与の大きい品目": main.assign(v=main["価格_S"]).nlargest(5, "v")[["name", "v"]].values.tolist(),
            "量の寄与の小さい品目": main.assign(v=main["量_S"]).nsmallest(5, "v")[["name", "v"]].values.tolist()}

# ---------- C 商業動態統計：全店と既存店 ----------
m = pd.read_csv(f"{B}/data/meti_yoy_all_vs_existing.csv"); m["年"] = m.ym.str[:4].astype(int)
crow = []
def era(y): return "1990年代" if y < 2000 else "2000年代" if y < 2010 else "2010年代" if y < 2020 else "2020年代"
m["時期"] = m["年"].map(era)
m = m[m["年"] >= 1990]
for (t, e), g in m.groupby(["業態", "時期"]):
    crow.append({"業態": t, "時期": e, "月数": len(g), "全店の平均": g["全店"].mean(), "既存店の平均": g["既存店"].mean(),
                 "差の平均": g["差（店舗網）"].mean(), "差の絶対値の平均": g["差（店舗網）"].abs().mean(),
                 "向きが逆の月の割合": float((np.sign(g["全店"]) != np.sign(g["既存店"])).mean()),
                 "相関": float(g[["全店", "既存店"]].corr().iloc[0, 1])})
for t, g in m.groupby("業態"):
    crow.append({"業態": t, "時期": "全期間", "月数": len(g), "全店の平均": g["全店"].mean(), "既存店の平均": g["既存店"].mean(),
                 "差の平均": g["差（店舗網）"].mean(), "差の絶対値の平均": g["差（店舗網）"].abs().mean(),
                 "向きが逆の月の割合": float((np.sign(g["全店"]) != np.sign(g["既存店"])).mean()),
                 "相関": float(g[["全店", "既存店"]].corr().iloc[0, 1])})
# 頑健性：全店の前年比を販売額の水準から計算しているため、調査の見直しなどで段差が出た月（差の絶対値が10ポイント超）を除く
for t, g in m.groupby("業態"):
    g2 = g[g["差（店舗網）"].abs() <= 10]
    crow.append({"業態": t, "時期": "全期間（段差の月を除く）", "月数": len(g2), "全店の平均": g2["全店"].mean(), "既存店の平均": g2["既存店"].mean(),
                 "差の平均": g2["差（店舗網）"].mean(), "差の絶対値の平均": g2["差（店舗網）"].abs().mean(),
                 "向きが逆の月の割合": float((np.sign(g2["全店"]) != np.sign(g2["既存店"])).mean()),
                 "相関": float(g2[["全店", "既存店"]].corr().iloc[0, 1])})
C = pd.DataFrame(crow); C.to_csv(f"{R}/C_all_vs_existing.csv", index=False)
big = m[m["差（店舗網）"].abs() > 10][["業態", "ym", "全店", "既存店"]]; big.to_csv(f"{R}/C_large_gap_months.csv", index=False)
out["C_段差の月"] = big.groupby("業態").ym.agg(["count", "min", "max"]).reset_index().to_dict("records")
out["C"] = C.to_dict("records")
json.dump(out, open(f"{R}/main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({"A": {k2: out["A"][k2] for k2 in ["売上0", "売上1", "伸び率", "全体の購入率0", "全体の購入率1", "シャープレイ", "順番による幅", "LMDI", "素朴なツリーのシャープレイ"]}, "Asim": out["A_シミュレーション"]}, ensure_ascii=False, default=float, indent=0))
print(P.round(0).to_string()); print(G.round(0).to_string()); print(MX.round(3).to_string()); print(C.round(2).to_string())
print(json.dumps({k2: out["B"][k2] for k2 in ["生鮮を除く", "区分の変更も含める", "値段の寄与の大きい品目", "量の寄与の小さい品目"]}, ensure_ascii=False, default=float))
