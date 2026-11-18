"""問い直し（結果を見てから足した）：大学・大学院に限ると、出身国の構成はどう違うのか。
JASSO の国別の表は「高等教育機関」（専修学校などを含む）と「日本語教育機関」までしか分かれていないので、
学校基本調査（2025年度）の国籍別 外国人学生数（大学の学部など＋大学院）と並べる。
学校基本調査の外国人学生には「留学」以外の在留資格の人も入る点に注意。"""
import json
import pandas as pd
from common import ROOT, FOCUS

D, R = ROOT / "data", ROOT / "results"
g = pd.read_csv(D / "gakko_2025_univ_grad.csv").set_index("country")
comp = pd.read_csv(R / "composition_by_type.csv")
c25 = comp[comp.year == 2025].set_index("country")
gt = int(g.n.sum())
rows = []
for c in FOCUS:
    rows.append({"country": c, "gakko_univ_grad_n": int(g.n[c]), "gakko_univ_grad_share": round(100 * g.n[c] / gt, 1),
                 "gakko_univ_n": int(g.univ[c]), "gakko_grad_n": int(g.grad[c]),
                 "jasso_he_n": int(c25.he_n[c]), "jasso_he_share": float(c25.he_share[c]),
                 "jasso_jls_n": int(c25.jls_n[c]), "jasso_jls_share": float(c25.jls_share[c]),
                 "gakko_over_jasso_he": round(g.n[c] / c25.he_n[c], 3)})
t = pd.DataFrame(rows)
t.to_csv(R / "requestion_univ_grad.csv", index=False)
q = {"gakko_total_univ_grad": gt, "gakko_univ": int(g.univ.sum()), "gakko_grad": int(g.grad.sum()),
     "rows": t.to_dict(orient="records")}
# 大学・大学院の外国人学生に占める中国の割合と、ネパールの割合
q["china_share_univ_grad"] = float(t.set_index("country").gakko_univ_grad_share["中国"])
q["nepal_share_univ_grad"] = float(t.set_index("country").gakko_univ_grad_share["ネパール"])
json.dump(q, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True,
          default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(t.to_string()); print(gt)
