"""問い直し（結果を見てから足した）：
調査産業計（一般労働者）では、総実労働時間の減りはほぼ全部が出勤日数の減りで、1日あたりの時間は変わらなかった。
これは産業をまたいで共通か。16産業それぞれで、2015→2025年の総時間の変化を「日数」と「1日あたり」に分ける。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
a = pd.read_csv(ROOT / "data" / "hours_annual_industry.csv")
NAMES = {"C": "鉱業", "D": "建設業", "E": "製造業", "F": "電気・ガス", "G": "情報通信", "H": "運輸・郵便", "I": "卸売・小売", "J": "金融・保険",
         "K": "不動産・物品賃貸", "L": "学術研究等", "M": "飲食サービス等", "N": "生活関連サービス等", "O": "教育・学習支援", "P": "医療・福祉",
         "Q": "複合サービス", "R": "その他のサービス"}
r3 = lambda x: round(float(x), 3)
rows = []
for i, nm in NAMES.items():
    g = a[(a.ind == i) & (a.type == 1)].set_index("year")
    tot = 100 * np.log(g.loc[2025, "total_hours"] / g.loc[2015, "total_hours"])
    days = 100 * np.log(g.loc[2025, "days"] / g.loc[2015, "days"])
    rows.append(dict(ind=i, name=nm, total_logpct=tot, days_logpct=days, perday_logpct=tot - days,
                     perday_2015=g.loc[2015, "total_hours"] / g.loc[2015, "days"], perday_2025=g.loc[2025, "total_hours"] / g.loc[2025, "days"]))
t = pd.DataFrame(rows); t.round(3).to_csv(RES / "requestion_by_industry.csv", index=False)
out = dict(n_industries=int(len(t)), n_total_down=int((t.total_logpct < 0).sum()), n_days_down=int((t.days_logpct < 0).sum()),
           n_perday_down=int((t.perday_logpct < 0).sum()),
           n_days_bigger_than_perday=int((t.days_logpct.abs() > t.perday_logpct.abs()).sum()),
           median_days_logpct=r3(t.days_logpct.median()), median_perday_logpct=r3(t.perday_logpct.median()))
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(t.round(2).to_string())
