# F231 予測の地平ごとの評価（03_分析.py の結果を読む）
import json, numpy as np, pandas as pd
np.random.seed(231)
m = pd.read_csv("results/forecasts_main.csv.gz")
r = pd.read_csv("results/forecasts_covid_imputed.csv.gz")
for d in (m, r):
    d["対象月"] = pd.PeriodIndex(d["対象月"], freq="M"); d["起点"] = pd.PeriodIndex(d["起点"], freq="M")
    d["ape"] = (d["予測"] / d["実績"] - 1).abs() * 100
    d["covid"] = (d["対象月"] >= pd.Period("2020-03", "M")) & (d["対象月"] <= pd.Period("2021-12", "M"))
MODELS = ["季節ナイーブ", "季節ナイーブ＋伸び", "ETS", "SARIMA", "LightGBM"]
out = {}

def table(d, mask=None):
    x = d if mask is None else d[mask]
    t = x.groupby(["モデル", "h"]).ape.mean().unstack(0)
    return t[[c for c in MODELS if c in t.columns]]

A = table(m, ~m.covid)                     # 主：コロナ期の月は採点しない
A.round(3).to_csv("results/A_mape_by_h.csv")
best = A.drop(columns="季節ナイーブ").min(axis=1); bestm = A.drop(columns="季節ナイーブ").idxmin(axis=1)
skill = 1 - best / A["季節ナイーブ"]
out["A"] = {"mape_h": {str(h): {k: round(v, 2) for k, v in A.loc[h].items()} for h in (1, 3, 6, 12, 18, 24)},
            "best_model_h": {str(h): bestm[h] for h in (1, 3, 6, 12, 18, 24)},
            "skill_vs_snaive_h": {str(h): round(skill[h], 3) for h in (1, 3, 6, 12, 18, 24)},
            "best_ape_le5_last_h": int(max([h for h in A.index if best[h] <= 5] or [0])),
            "best_ape_le3_last_h": int(max([h for h in A.index if best[h] <= 3] or [0])),
            "skill_pos_last_h": int(max([h for h in A.index if skill[h] > 0] or [0]))}
# 業態別
B = m[~m.covid].groupby(["業態", "モデル", "h"]).ape.mean().unstack(1)
rows = []
for k, g in B.groupby(level=0):
    g = g.droplevel(0); bb = g.drop(columns="季節ナイーブ").min(axis=1); sk = 1 - bb / g["季節ナイーブ"]
    rows.append({"業態": k, "h1_best": round(bb[1], 2), "h12_best": round(bb[12], 2), "h24_best": round(bb[24], 2),
                 "h1_snaive": round(g.loc[1, "季節ナイーブ"], 2), "h12_snaive": round(g.loc[12, "季節ナイーブ"], 2),
                 "skill_h1": round(sk[1], 3), "skill_h12": round(sk[12], 3), "skill_h24": round(sk[24], 3),
                 "skill_pos_last_h": int(max([h for h in sk.index if sk[h] > 0] or [0])),
                 "best_le5_last_h": int(max([h for h in bb.index if bb[h] <= 5] or [0]))})
Bt = pd.DataFrame(rows); Bt.to_csv("results/B_by_type.csv", index=False); out["B"] = rows
# 予算：12月の起点から翌年1〜12月の合計（=年間予算）と、2年目の合計
y = m[(m.起点.dt.month == 12) & (~m.covid)].copy()
y["年"] = np.where(y.h <= 12, "1年目", "2年目")
g = y.groupby(["起点", "業態", "モデル", "年"]).agg(n=("h", "size"), a=("実績", "sum"), p=("予測", "sum")).reset_index()
g = g[g.n == 12]; g["err"] = (g.p / g.a - 1) * 100
C = g.groupby(["モデル", "年"]).err.agg(lambda e: e.abs().mean()).unstack(1).round(2)
C.to_csv("results/C_annual_budget.csv"); out["C"] = C.to_dict()
out["C_n"] = int(g[g.モデル == "ETS"].shape[0])
# 区間（SARIMA 80%）の当たり
s = m[(m.モデル == "SARIMA") & (~m.covid)].copy(); s["in"] = (s.実績 >= s.下80) & (s.実績 <= s.上80)
cov = s.groupby("h")["in"].mean(); width = ((s.上80 - s.下80) / s.予測 * 100).groupby(s.h).median()  # 中央値（発散した区間が少数あるため）
pd.DataFrame({"当たり": cov.round(3), "幅_pct": width.round(2)}).to_csv("results/D_interval.csv")
out["D"] = {str(h): [round(cov[h], 3), round(width[h], 2)] for h in (1, 6, 12, 24)}
# 頑健性1：コロナ期も採点に入れる
R1 = table(m); out["R1_all_targets"] = {str(h): {k: round(v, 2) for k, v in R1.loc[h].items()} for h in (1, 12, 24)}
# 頑健性2：コロナ期をならした系列で学習（LightGBM なし）、採点はコロナ期以外
R2 = table(r, ~r.covid); out["R2_imputed"] = {str(h): {k: round(v, 2) for k, v in R2.loc[h].items()} for h in (1, 12, 24)}
# 頑健性3：起点の時期で分ける（コロナ前の起点〜2019-12／コロナ後の起点 2022-01〜）
pre = m[(m.起点 <= pd.Period("2018-02", "M")) & (~m.covid)]; post = m[m.起点 >= pd.Period("2022-01", "M")]
out["R3_pre"] = {str(h): {k: round(v, 2) for k, v in table(pre).loc[h].items()} for h in (1, 12, 24)}
out["R3_post"] = {str(h): {k: round(v, 2) for k, v in table(post).loc[h].items()} for h in (1, 12, 24) if h in table(post).index}
# 頑健性4：指標を変える（APE の中央値）
med = m[~m.covid].groupby(["モデル", "h"]).ape.median().unstack(0)
out["R4_median"] = {str(h): {k: round(v, 2) for k, v in med.loc[h].items()} for h in (1, 12, 24)}
# 頑健性5：起点のブートストラップで「いちばん良いモデル − 季節ナイーブ」の差の区間
def boot(h, model, B=2000):
    x = m[(~m.covid) & (m.h == h)]
    p = x.pivot_table(index=["起点", "業態"], columns="モデル", values="ape").dropna()
    ori = p.index.get_level_values(0).unique(); d = []
    rng = np.random.default_rng(231)
    for _ in range(B):
        s_ = rng.choice(ori, len(ori)); q = pd.concat([p.loc[o] for o in s_])
        d.append(q[model].mean() - q["季節ナイーブ"].mean())
    return [round(np.percentile(d, 2.5), 2), round(np.percentile(d, 97.5), 2)]
out["R5_boot"] = {str(h): {"model": bestm[h], "diff_ci": boot(h, bestm[h], 1000)} for h in (1, 6, 12, 24)}
out["n_origins"] = int(m.起点.nunique()); out["n_rows"] = int(len(m))
json.dump(out, open("results/main.json", "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:6000])
