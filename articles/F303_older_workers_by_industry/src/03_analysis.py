"""H1〜H4 と頑健性（オフライン）。医療・福祉、公務、分類不能は除く（事前に決めた）。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "employed_age_industry.csv")
COLS = [1, 5, 8, 9, 10, 35, 36, 42, 51, 58, 59, 62, 67, 71, 75, 82, 85]  # 対象の17産業（大分類、農業・林業はまとめる）
SHORT = {1: "農業・林業", 5: "漁業", 8: "鉱業", 9: "建設業", 10: "製造業", 35: "電気・ガス・水道", 36: "情報通信業", 42: "運輸・郵便",
         51: "卸売・小売", 58: "金融・保険", 59: "不動産・物品賃貸", 62: "学術研究・専門技術", 67: "宿泊・飲食", 71: "生活関連・娯楽",
         75: "教育・学習支援", 82: "複合サービス", 85: "サービス業（他に分類されない）"}
r3 = lambda x: round(float(x), 3)

def table(year, ages):
    x = d[(d.year == year) & d.col.isin(COLS)]
    tot = x[x.age == "総数"].set_index("col").employed_10k
    old = x[x.age.isin(ages)].groupby("col").employed_10k.sum()
    return tot.reindex(COLS), old.reindex(COLS)

def decompose(a, b, ages=("60～64歳", "65歳以上"), base="start"):
    Na, Oa = table(a, ages); Nb, Ob = table(b, ages)
    sa, sb = Oa / Na, Ob / Nb
    if base == "start":
        scale = (Nb - Na) * sa; share = Na * (sb - sa); inter = (Nb - Na) * (sb - sa)
    else:
        scale = (Nb - Na) * sb; share = Nb * (sb - sa); inter = -(Nb - Na) * (sb - sa)
    t = pd.DataFrame({"industry": [SHORT[c] for c in COLS], "N_start": Na.values, "N_end": Nb.values, "old_start": Oa.values, "old_end": Ob.values,
                      "share_start_pct": (100 * sa).values, "share_end_pct": (100 * sb).values, "d_old": (Ob - Oa).values,
                      "scale": scale.values, "within_share": share.values, "interaction": inter.values}, index=COLS)
    tot = dict(period=f"{a}-{b}", ages="+".join(ages), base=base, d_old_total=r3(t.d_old.sum()), scale_total=r3(t.scale.sum()),
               within_share_total=r3(t.within_share.sum()), interaction_total=r3(t.interaction.sum()))
    top = t.sort_values("d_old", ascending=False)
    tot["top3"] = top.industry.head(3).tolist()
    tot["top3_share_of_increase"] = r3(top.d_old.head(3).sum() / t.d_old.sum()) if t.d_old.sum() != 0 else None
    tot["n_ind_old_increase"] = int((t.d_old > 0).sum())
    pos = t.d_old[t.d_old > 0]
    tot["top3_share_of_gross_increase"] = r3(top.d_old.head(3).sum() / pos.sum()) if pos.sum() > 0 else None
    tot["gross_increase"] = r3(pos.sum()); tot["gross_decrease"] = r3(t.d_old[t.d_old < 0].sum())
    rho, p = stats.spearmanr(np.log(t.N_end / t.N_start), t.share_end_pct - t.share_start_pct)
    tot["spearman_growth_vs_dshare"] = r3(rho); tot["spearman_p"] = r3(p)
    return tot, t

out = {}
main, t = decompose(2018, 2025)
t.round(3).to_csv(RES / "decomp_2018_2025.csv", index_label="col")
out["main"] = main
out["H1_verdict"] = "支持" if main["within_share_total"] > main["scale_total"] else "外れ"
out["H2_verdict"] = "支持" if (main["top3_share_of_increase"] or 0) >= 0.5 else "外れ"
out["H3_verdict"] = "支持" if (main["spearman_growth_vs_dshare"] < 0 and main["spearman_p"] < 0.10) else "外れ"
m65, _ = decompose(2018, 2025, ages=("65歳以上",))
m6064, _ = decompose(2018, 2025, ages=("60～64歳",))
out["d_65p"] = m65["d_old_total"]; out["d_60_64"] = m6064["d_old_total"]
out["share_65p_of_increase"] = r3(m65["d_old_total"] / main["d_old_total"])
out["H4_verdict"] = "支持" if out["share_65p_of_increase"] >= 0.8 else "外れ"
# 全体（参考：除いた産業を含む全就業者）
x = d[(d.col == 0)]
allv = {y: float(x[(x.year == y) & x.age.isin(["60～64歳", "65歳以上"])].employed_10k.sum()) for y in (2013, 2018, 2025)}
out["all_industries_60p"] = allv
out["all_industries_60p_change_2018_2025"] = allv[2025] - allv[2018]
out["target_total_N_2018_2025"] = [r3(t.N_start.sum()), r3(t.N_end.sum())]
out["target_share_60p_2018_2025"] = [r3(100 * t.old_start.sum() / t.N_start.sum()), r3(100 * t.old_end.sum() / t.N_end.sum())]
# 年ごとの60歳以上の割合（対象産業計）
ys = []
for y in sorted(d.year.unique()):
    N, O = table(y, ("60～64歳", "65歳以上"))
    ys.append(dict(year=int(y), N=float(N.sum()), old=float(O.sum()), share_pct=r3(100 * O.sum() / N.sum())))
pd.DataFrame(ys).to_csv(RES / "target_share_by_year.csv", index=False)
# 頑健性
rob = [main | {"spec": "主 2018→2025"},
       decompose(2013, 2025)[0] | {"spec": "R1 2013→2025（基準の違う年をまたぐ）"},
       decompose(2019, 2025)[0] | {"spec": "R2 2019→2025"},
       m65 | {"spec": "R3 65歳以上だけ"},
       decompose(2018, 2025, base="end")[0] | {"spec": "R4 割合を2025年に固定"}]
rob_df = pd.DataFrame(rob); rob_df.to_csv(RES / "robustness.csv", index=False)
out["robustness"] = rob
# R5 製造業の中分類：60歳以上の割合の変化の向き
mf = d[(d.level == 3) & (d.col > 10) & (d.col < 35) & d.year.isin([2018, 2025])]
mt = mf[mf.age == "総数"].pivot(index="industry", columns="year", values="employed_10k")
mo = mf[mf.age.isin(["60～64歳", "65歳以上"])].groupby(["industry", "year"]).employed_10k.sum().unstack()
ms = (100 * mo / mt).dropna()
ms["d_share"] = ms[2025] - ms[2018]
ms.round(3).to_csv(RES / "manufacturing_sub.csv")
out["mfg_sub_n"] = int(len(ms)); out["mfg_sub_n_share_up"] = int((ms.d_share > 0).sum())
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "robustness"}, ensure_ascii=False, indent=0))
print(rob_df[["spec", "d_old_total", "scale_total", "within_share_total", "interaction_total", "top3", "top3_share_of_increase", "spearman_growth_vs_dshare", "spearman_p"]].to_string())
print(t.sort_values("d_old").round(2).to_string())
