"""問い直し（結果を見てから足した）：
60歳以上の増加はおもに「産業の中で60歳以上の割合が上がった」分だった。では、60歳をまたいで同じ産業で働き続ける人は増えたのか。
5年前に55〜59歳だった人数に対する、今の60〜64歳の人数の比（同じ生まれ年の集まりを産業ごとに追う近似）を、
2013→2018年と2020→2025年で比べる。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "employed_age_industry.csv")
COLS = [1, 5, 8, 9, 10, 35, 36, 42, 51, 58, 59, 62, 67, 71, 75, 82, 85]
SHORT = {1: "農業・林業", 5: "漁業", 8: "鉱業", 9: "建設業", 10: "製造業", 35: "電気・ガス・水道", 36: "情報通信業", 42: "運輸・郵便",
         51: "卸売・小売", 58: "金融・保険", 59: "不動産・物品賃貸", 62: "学術研究・専門技術", 67: "宿泊・飲食", 71: "生活関連・娯楽",
         75: "教育・学習支援", 82: "複合サービス", 85: "サービス業（他に分類されない）"}
r3 = lambda x: round(float(x), 3)
def get(y, age):
    return d[(d.year == y) & (d.age == age) & d.col.isin(COLS)].set_index("col").employed_10k.reindex(COLS)
rows = []
for a, b in ((2013, 2018), (2020, 2025)):
    s55, s60 = get(a, "55～59歳"), get(b, "60～64歳")
    for c in COLS:
        rows.append(dict(period=f"{a}-{b}", col=c, industry=SHORT[c], age55_59_start=s55[c], age60_64_end=s60[c],
                         ratio=s60[c] / s55[c] if s55[c] > 0 else np.nan))
    rows.append(dict(period=f"{a}-{b}", col=0, industry="対象17産業の計", age55_59_start=s55.sum(), age60_64_end=s60.sum(), ratio=s60.sum() / s55.sum()))
r = pd.DataFrame(rows)
r.round(4).to_csv(RES / "requestion_cohort.csv", index=False)
w = r.pivot(index="industry", columns="period", values="ratio")
w["change"] = w["2020-2025"] - w["2013-2018"]
big = r[(r.period == "2013-2018") & (r.age55_59_start >= 10) & (r.col != 0)].industry.tolist()  # 55〜59歳が10万人以上の産業
wb = w.loc[[i for i in w.index if i in big]]
out = dict(total_2013_2018=r3(w.loc["対象17産業の計", "2013-2018"]), total_2020_2025=r3(w.loc["対象17産業の計", "2020-2025"]),
           n_big=int(len(wb)), n_big_ratio_up=int((wb.change > 0).sum()),
           by_industry_big={i: [r3(wb.loc[i, "2013-2018"]), r3(wb.loc[i, "2020-2025"])] for i in wb.index})
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
