"""F281 06 レビュー対応（独立レビューの指摘を受けて結果を見た後に足した確かめ）

1. H4：「届いた割合（実績÷目標）」と「目標の高さ（目標÷基準）」はどちらにも目標が入るので、両者が無関係でも負の相関が出る。
   - 目標の高さと実際の伸び（実績÷基準）の順位相関と、並べ替え検定の p 値（両側）
   - 実際の伸びが目標の高さと無関係なとき（伸びを品目・計画の間で並べ替える）に、届いた割合との順位相関がどこに出るか
2. H2：不足の分母を、品目のプラスの分の合計（160kcal）ではなく国産熱量の不足全体（210kcal）にしたとき
3. R3（畜産物を一律の扱い）での飼料自給率の分（kcal）
4. 6 の問い直し：国産熱量を「自給率（整数）× 総供給熱量」で近似した丸めが、5年ごとの変化に与える幅（自給率を ±0.5 の一様で1万回ずらす）
5. 参考：計画の14品目にあった飼料作物を、飼料作物の収穫量（TDN、年）で足した場合
出力：results/G_review.json、results/G_h4_growth.csv
"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, P = ROOT / "results", ROOT / "data" / "processed"
rng = np.random.default_rng(281)
C = pd.read_csv(RES / "C_production_achievement.csv")
C["growth"] = C.actual / C.base
C["growth_avg3"] = C.actual_avg3 / C.base
C.to_csv(RES / "G_h4_growth.csv", index=False)


def rho_growth(df, col="growth", nperm=20000):
    r = spearmanr(df.ambition, df[col]).correlation
    g = df[col].to_numpy()
    perm = np.array([spearmanr(df.ambition, rng.permutation(g)).correlation for _ in range(nperm)])
    return float(r), float((np.sum(np.abs(perm) >= abs(r)) + 1) / (nperm + 1)), int(len(df))


def null_achieve(df, nperm=20000):
    """伸びが目標の高さと無関係なとき（伸びを並べ替える）の、目標の高さと届いた割合の順位相関の分布"""
    amb, g = df.ambition.to_numpy(), df.growth.to_numpy()
    obs = spearmanr(amb, g / amb).correlation
    perm = np.array([spearmanr(amb, rng.permutation(g) / amb).correlation for _ in range(nperm)])
    return {"observed": float(obs), "null_mean": float(perm.mean()), "null_q025": float(np.quantile(perm, 0.025)),
            "null_q975": float(np.quantile(perm, 0.975)), "p_one_sided_le_observed": float((np.sum(perm <= obs) + 1) / (nperm + 1))}


out = {}
r, p, n = rho_growth(C)
out["H4_growth"] = {"spearman_ambition_growth": r, "p_two_sided": p, "n": n, "null_for_achieve": null_achieve(C),
                    "median_growth_ambition_le1": float(C[C.ambition <= 1.0].growth.median()),
                    "median_growth_ambition_ge11": float(C[C.ambition >= 1.1].growth.median()),
                    "n_ambition_le1": int((C.ambition <= 1.0).sum()), "n_ambition_ge11": int((C.ambition >= 1.1).sum())}
rob = {}
for tag, sub, col in [("R1 3年度平均", C, "growth_avg3"), ("R5 魚介類を除く", C[C.item != "魚介類"], "growth"),
                      ("R5 牛肉・豚肉を除く", C[~C.item.isin(["牛肉", "豚肉"])], "growth"), ("R5 2010年計画を除く", C[C.plan != "H22"], "growth")]:
    r_, p_, n_ = rho_growth(sub, col=col, nperm=5000)
    rob[tag] = {"spearman": r_, "p_two_sided": p_, "n": n_}
out["H4_growth_robustness"] = rob

# 参考：飼料作物を足す（計画の値は万TDNトン、収穫量は千TDNトン→万）
harvest = {2010: 362.5, 2015: 380.3, 2020: 361.7, 2025: 344.6}
feedrows = [("H12", 394, 508, 2010), ("H17", 352, 524, 2015), ("H22", 435, 527, 2020), ("H27", 350, 501, 2025)]
F = pd.DataFrame([{"plan": pl, "item": "飼料作物", "base": b, "target": t, "actual": harvest[y], "target_fy": y} for pl, b, t, y in feedrows])
F["ambition"], F["achieve"], F["growth"] = F.target / F.base, F.actual / F.target, F.actual / F.base
C2 = pd.concat([C, F], ignore_index=True)
r2, p2, n2 = rho_growth(C2, nperm=5000)
out["H4_with_feed_crop_reference"] = {"rows": F.round(3).to_dict("records"), "spearman_ambition_achieve": float(spearmanr(C2.ambition, C2.achieve).correlation),
                                      "spearman_ambition_growth": r2, "p_two_sided": p2, "n": n2, "reached": int((C2.achieve >= 1).sum())}

# H2 の分母を 210kcal に
A = pd.read_csv(RES / "A_h27_items.csv", index_col=0)
LIVE = ["生乳", "牛肉", "豚肉", "鶏肉", "鶏卵"]
tot = float(A.shortfall_kcal.sum())
out["H2_denominator_total"] = {"total_shortfall_kcal": tot, "share_livestock_fish": float(A.loc[LIVE + ["魚介類"], "shortfall_kcal"].sum() / tot),
                               "share_rice": float(A.loc["米", "shortfall_kcal"] / tot), "share_livestock": float(A.loc[LIVE, "shortfall_kcal"].sum() / tot),
                               "share_fish": float(A.loc["魚介類", "shortfall_kcal"] / tot)}

# R3 の飼料の分は 03 の最後で results/G_r3_feed.json に書く（ここでは読むだけ）
out["R3_feed"] = json.loads((RES / "G_r3_feed.json").read_text())

# 6 の丸めの幅：自給率（整数）を ±0.5 の一様でずらす（2024・2025年度の国産熱量は公表値なので動かさない）
Fn = pd.read_csv(RES / "F_n_changes.csv", index_col=0)
ssr_, S_ = Fn.ssr.to_numpy(), Fn.S.to_numpy()
fixed = Fn.index.isin([2024, 2025])
sims, maxes, half = [], [], []
base_N = Fn.N.to_numpy()
for _ in range(10000):
    N = np.where(fixed, base_N, (ssr_ + rng.uniform(-0.5, 0.5, len(ssr_))) / 100 * S_)
    c = (N[5:] / N[:-5] - 1) * 100
    sims.append(c)
sims = np.array(sims)
orig = Fn.N_chg5.dropna().to_numpy()
dev = sims - orig
out["reask_rounding"] = {"n_windows": int(sims.shape[1]), "median_abs_q975_dev_pt": float(np.median(np.quantile(np.abs(dev), 0.975, axis=0))),
                         "max_abs_q975_dev_pt": float(np.max(np.quantile(np.abs(dev), 0.975, axis=0))),
                         "max_window_q975": float(np.quantile(sims.max(axis=1), 0.975)), "share_sims_any_window_ge_17_5": float((sims.max(axis=1) >= 17.5).mean()),
                         "note": "1965〜2023年度の国産熱量は、自給率（整数）×総供給熱量の近似（2024・2025年度だけ公表値）"}
(RES / "G_review.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
