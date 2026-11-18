"""問い直し（結果を見てから足した）：2023年度に戻りきっていないのは、定期（通勤・通学）と定期外のどちらか。
そろう事業者の人キロを定期・定期外に分け、2019年度＝100 で見る（全体と、第三セクター・中小民鉄別）。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
b = pd.read_csv(R / "panel_balanced.csv")
rows = []
for lab, t in [("全体", b), ("第三セクター", b[b.third_sector == 1]), ("中小民鉄", b[b.third_sector == 0])]:
    g = t.groupby("fy", sort=True)[["pk_pass", "pk_nonpass"]].sum()
    for fy in g.index:
        rows.append({"group": lab, "fy": int(fy), "pass_idx_2019": round(g.loc[fy, "pk_pass"] / g.loc[2019, "pk_pass"] * 100, 2),
                     "nonpass_idx_2019": round(g.loc[fy, "pk_nonpass"] / g.loc[2019, "pk_nonpass"] * 100, 2),
                     "pass_idx_2012": round(g.loc[fy, "pk_pass"] / g.loc[2012, "pk_pass"] * 100, 2),
                     "nonpass_idx_2012": round(g.loc[fy, "pk_nonpass"] / g.loc[2012, "pk_nonpass"] * 100, 2)})
d = pd.DataFrame(rows)
d.to_csv(R / "requestion_pass_nonpass.csv", index=False, encoding="utf-8")
m = json.load(open(R / "main.json", encoding="utf-8"))
x = d.set_index(["group", "fy"])
m["requestion"] = {g: {"pass_2023_vs_2019": float(x.loc[(g, 2023), "pass_idx_2019"]), "nonpass_2023_vs_2019": float(x.loc[(g, 2023), "nonpass_idx_2019"]),
                       "pass_2020_vs_2019": float(x.loc[(g, 2020), "pass_idx_2019"]), "nonpass_2020_vs_2019": float(x.loc[(g, 2020), "nonpass_idx_2019"]),
                       "pass_2019_vs_2012": float(x.loc[(g, 2019), "pass_idx_2012"]), "nonpass_2019_vs_2012": float(x.loc[(g, 2019), "nonpass_idx_2012"])}
                   for g in ["全体", "第三セクター", "中小民鉄"]}
t = b[(b.third_sector == 1) & (b.key != "北越急行")].groupby("fy")["pk_nonpass"].sum()
m["requestion"]["third_nonpass_2019_vs_2012_ex_hokuetsu"] = round(float(t[2019] / t[2012] * 100), 1)
json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(m["requestion"], ensure_ascii=False, indent=1))
