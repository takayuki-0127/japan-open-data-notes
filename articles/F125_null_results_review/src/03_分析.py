"""「見えなかった／言い切れない」の割合と、記事の種類・手法・分析の単位・検出力への言及との関係。"""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats
ROOT = pathlib.Path(__file__).resolve().parents[1]; RES = ROOT / "results"
df = pd.read_csv(ROOT / "data" / "articles.csv")
TYPE = {"E": "効果・関係の推定", "P": "予測", "D": "記述・測定・作法"}
df["type_ja"] = df.type.map(TYPE)
def share(g, col="broad"): return pd.Series({"記事数": len(g), "割合": round(g[col].mean(), 3), "本数": int(g[col].sum())})
out = {}
out["all"] = {"n": len(df), "N": int((df.outcome == "N").sum()), "U": int((df.outcome == "U").sum()), "Y": int((df.outcome == "Y").sum()),
              "broad_share": round(df.broad.mean(), 3), "strict_share": round(df.strict.mean(), 3)}
by_type = df.groupby("type_ja").apply(share); by_type.to_csv(RES / "by_type.csv")
by_fam = df.groupby("family").apply(share).sort_values("割合", ascending=False); by_fam.to_csv(RES / "by_family.csv")
E_ = df[df.type == "E"].copy()
E_["big"] = E_.unit.isin(["市区町村（約1,700）", "法人・地点など（1万以上）"]).astype(int)
by_unit = E_.groupby("unit").apply(share); by_unit.to_csv(RES / "by_unit_effect.csv")
tab = pd.crosstab(E_.big, E_.broad); odds, p = stats.fisher_exact(tab.values)
out["effect_unit"] = {"table": tab.to_dict(), "odds_ratio": round(float(odds), 2), "fisher_p": round(float(p), 3)}
tab2 = pd.crosstab(E_.big, E_.strict); o2, p2 = stats.fisher_exact(tab2.values)
out["effect_unit_strict"] = {"odds_ratio": round(float(o2), 2), "fisher_p": round(float(p2), 3)}
# 検出力への言及
pw = df.groupby("outcome").power.agg(["mean", "sum", "count"]).round(3); pw.to_csv(RES / "power_by_outcome.csv")
out["power_mention_E_null"] = {"N": round(E_[E_.outcome == "N"].power.mean(), 3), "Y": round(E_[E_.outcome == "Y"].power.mean(), 3)}
# 時期
df["half"] = np.where(df.num <= 60, "F01–F60", "F61–F120")
out["by_half"] = df.groupby(["half", "type"]).broad.mean().round(3).unstack().to_dict()
# 頑健性
rob = []
kappa = lambda a, b: (np.mean(a == b) - (a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))) / (1 - (a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())))
rob.append(["判定を README の結果欄のキーワードだけで行う", round(df.auto.mean(), 3), round(E_.auto.mean(), 3), f"手作業との一致 {np.mean(df.auto == df.broad):.0%}・κ={kappa(df.auto.values, df.broad.values):.2f}"])
rob.append(["厳しい定義（見えなかった だけ）", round(df.strict.mean(), 3), round(E_.strict.mean(), 3), f"単位の関係 OR={o2:.2f}, p={p2:.2f}"])
for h in ["F01–F60", "F61–F120"]:
    s = df[df.half == h]; rob.append([f"{h} だけ", round(s.broad.mean(), 3), round(s[s.type == 'E'].broad.mean(), 3), f"記事数 {len(s)}"])
s = df[~df.fid.isin(["F118", "F119", "F120"]) & (df.family != "統計の作法・集計")]
rob.append(["まとめ直し（F118〜F120）と「統計の作法」を除く", round(s.broad.mean(), 3), round(s[s.type == 'E'].broad.mean(), 3), f"記事数 {len(s)}"])
# 1件ずつ判定を反転させても E の割合がどこまで動くか（境界の判定の重み）
flip = [E_.drop(i).broad.mean() for i in E_.index]
rob.append(["効果の記事から1本ずつ外す（39通り）", round(df.broad.mean(), 3), f"{min(flip):.3f}〜{max(flip):.3f}", "1本の判定の影響"])
pd.DataFrame(rob, columns=["チェック", "全体の割合", "効果・関係の推定の割合", "メモ"]).to_csv(RES / "robustness.csv", index=False)
out["robustness"] = rob
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)); print(by_type); print(by_fam); print(by_unit)
