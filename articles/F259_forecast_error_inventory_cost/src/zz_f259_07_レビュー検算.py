# F259 07 独立レビューで指摘された点の検算（後から足した）
import json, math, numpy as np, pandas as pd
from scipy.stats import norm
f = pd.read_csv("data/forecasts_scaled.csv.gz"); f["e"] = f["実績"] - f["予測"]
f["covid"] = f["対象月"].between("2020-03", "2021-12")
z = norm.ppf(0.9); out = {}
# (1)(2) 起点×h の外れの表（窓がコロナ期にかかる起点は、窓ごとに除く。results/B と同じ）
W = f[f.h <= 6].pivot_table(index=["業態", "モデル", "起点"], columns="h", values="e")
C = f[f.h <= 6].pivot_table(index=["業態", "モデル", "起点"], columns="h", values="covid").astype(bool)
def ok(H): return ~C[list(range(1, H + 1))].any(axis=1)
pairs = {}
for a, b in [(1, 2), (2, 3), (3, 4), (4, 5), (1, 3), (2, 4), (3, 5), (2, 5), (1, 5)]:
    x = W[ok(max(a, b))]
    pairs[f"h{a}-h{b}"] = round(float(np.median([np.corrcoef(g[a], g[b])[0, 1] for _, g in x.groupby(level=[0, 1])])), 3)
out["月どうしの外れの相関_中央値"] = pairs
rows = []
for (k, m), g0 in W.groupby(level=[0, 1]):
    g1 = g0[ok(1).loc[g0.index]]; s1 = math.sqrt((g1[1] ** 2).mean())
    for H in range(1, 7):
        e = g0[ok(H).loc[g0.index]][list(range(1, H + 1))].sum(axis=1)
        rows.append(dict(業態=k, モデル=m, H=H, 必要な倍率=np.quantile(e, 0.9) / (z * s1), RMSE倍=math.sqrt((e ** 2).mean()) / s1,
                         偏りを除いた倍率=e.std(ddof=0) / s1, 偏りを除いた必要な倍率=np.quantile(e - e.mean(), 0.9) / (z * s1),
                         平均の外れ=e.mean(), 起点間のSD=e.std(ddof=1), n=len(e)))
R = pd.DataFrame(rows); R.round(6).to_csv("results/G_review_multipliers.csv", index=False)
med = R.groupby("H")[["必要な倍率", "RMSE倍", "偏りを除いた倍率", "偏りを除いた必要な倍率", "平均の外れ"]].median()
out["倍率の中央値_H別"] = med.round(3).to_dict()
out["SARIMA_H別"] = R[R.モデル == "SARIMA"].groupby("H")[["必要な倍率", "平均の外れ"]].median().round(3).to_dict()
out["モデル別_H4_平均の外れ_と_起点間SD"] = R[R.H == 4].groupby("モデル")[["平均の外れ", "起点間のSD"]].median().round(2).to_dict()
# (3) シミュレーションの欠品なしの割合：月ごと・2か月の発注周期ごと
A = pd.read_csv("results/A_cost_main.csv"); q = A[A.p == 9]
out["欠品なしの月の割合"] = (1 - q.groupby(["決め方", "L"]).欠品月の割合.mean()).unstack().round(3).to_dict(orient="index")
lg = pd.read_csv("results/sim_log_p9.csv.gz"); lg["mi"] = lg.月.str[:4].astype(int) * 12 + lg.月.str[5:].astype(int) - 1
# 周期：発注の起点の翌月から2か月
lg["周期"] = lg.mi // 2   # 起点は奇数の月番号（12月・2月…）なので、その翌月と翌々月が同じ周期
cyc = lg.groupby(["業態", "モデル", "L", "決め方", "周期"]).agg(n=("売り逃し", "size"), lost=("売り逃し", "max")).reset_index()
cyc = cyc[cyc.n == 2]
out["欠品なしの周期の割合"] = (cyc.assign(ok=cyc.lost <= 1e-9).groupby(["決め方", "L"]).ok.mean()).unstack().round(3).to_dict(orient="index")
# (4) モデルの順位（決め方ごと、L=0〜3 平均）
rk = q.groupby(["決め方", "モデル"]).費用.mean().unstack()
out["モデル別費用と順位"] = {r: {m: [round(v, 2), int(rk.loc[r].rank()[m])] for m, v in rk.loc[r].items()} for r in rk.index}
# (5) 後から見た最良の倍率の分布、2か月持つ前提の差
k = q[q.決め方 == "後から見た最良の倍率"].倍率
out["最良倍率_中央値_四分位"] = [round(k.median(), 2), round(k.quantile(0.25), 2), round(k.quantile(0.75), 2)]
t = q.groupby(["決め方", "L"]).費用.mean().unstack()
out["2か月持つ前提_minus_分位点_L別"] = (t.loc["分位点（2か月持つ前提）"] - t.loc["合計の外れの分位点"]).round(3).to_dict()
# (6) H3：LightGBM を除く・ルートの式と分位点だけで比べる
tt = q.pivot_table(index=["業態", "L", "モデル"], columns="決め方", values="費用")
def ef(models, rules):
    x = tt.loc[tt.index.get_level_values(2).isin(models), rules]
    rule = (x.max(axis=1) - x.min(axis=1)).groupby(level=[0, 1]).mean().mean()
    mod = x.groupby(level=[0, 1]).agg(lambda s: s.max() - s.min()).mean(axis=1).mean()
    return round(float(rule), 2), round(float(mod), 2)
MO = ["季節ナイーブ", "季節ナイーブ＋伸び", "ETS", "SARIMA", "LightGBM"]
out["H3_幅_決め方vsモデル"] = {"3つの決め方・5モデル": ef(MO, ["なし", "ルートの式", "合計の外れの分位点"]),
                          "3つの決め方・LightGBM除く": ef(MO[:4], ["なし", "ルートの式", "合計の外れの分位点"]),
                          "ルートと分位点・5モデル": ef(MO, ["ルートの式", "合計の外れの分位点"]),
                          "ルートと分位点・LightGBM除く": ef(MO[:4], ["ルートの式", "合計の外れの分位点"])}
# (7) H2：24組の差（合計の外れの RMSE − 1か月先の MAPE）のブートストラップ
C = pd.read_csv("results/C_rank_corr.csv"); rng = np.random.default_rng(259); h2 = {}
for cr in ["合計の外れの分位点", "なし"]:
    p = C[C.費用の決め方 == cr].pivot_table(index=["業態", "L"], columns="指標", values="順位相関")
    d = (p["RMSE_合計"] - p["MAPE_1か月先"]).to_numpy()
    bs = [rng.choice(d, len(d)).mean() for _ in range(2000)]
    h2[cr] = dict(差の平均=round(d.mean(), 3), 区間95=[round(np.quantile(bs, 0.025), 3), round(np.quantile(bs, 0.975), 3)],
                  業態でまとめた差=(p["RMSE_合計"] - p["MAPE_1か月先"]).groupby(level=0).mean().round(2).to_dict())
out["H2_差のブートストラップ"] = h2
# (8) 6業態まとめた分位点の頑健性
E = pd.read_csv("results/E_robustness.csv"); pe = E[E.頑健性 == "6業態まとめて分位点"]
out["まとめた分位点"] = dict(費用=pe.groupby(["決め方", "L"]).費用.mean().unstack().loc["合計の外れの分位点"].round(2).to_dict(),
                       覆えた割合=pe.groupby(["決め方", "L"]).カバー率.mean().unstack().loc["合計の外れの分位点"].round(3).to_dict())
json.dump(out, open("results/G_review_checks.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
