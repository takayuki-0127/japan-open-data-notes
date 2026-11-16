"""問い直し（結果を見てから足した）：
業種ごとに見ると、売場面積が伸びた業種ほど個人の店が減った、という関係はなかった（むしろ逆向き）。
では、個人の店の減少は「売場が広がった業種」と「売場も縮んだ業種」のどちらで起きたのか。
また、ほとんどの業種で、店の数に占める個人の店の割合は下がったのか（業種の中での入れ替わり）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
r3 = lambda x: round(float(x), 3)
p = pd.read_csv(RES / "industry_panel_1991r_2007.csv", dtype={"code": str}).set_index("code")
p["indiv_share0"] = 100 * p.i0 / (p.i0 + p.c0); p["indiv_share1"] = 100 * p.i1 / (p.i1 + p.c1)
p["share_change"] = p.indiv_share1 - p.indiv_share0
p["indiv_loss"] = p.i1 - p.i0
p["group"] = np.where(p.dx > 0, "売場面積が増えた業種", "売場面積が減った業種")
g = p.groupby("group").agg(n=("name", "size"), indiv_loss=("indiv_loss", "sum"), i0=("i0", "sum"))
g["share_of_loss"] = 100 * g.indiv_loss / g.indiv_loss.sum()
g.round(3).to_csv(RES / "requestion_loss_by_group.csv")
# 個人の割合の変化を「業種の中」と「業種の構成」に分ける
w0 = (p.i0 + p.c0) / (p.i0 + p.c0).sum(); w1 = (p.i1 + p.c1) / (p.i1 + p.c1).sum()
s0, s1 = p.indiv_share0, p.indiv_share1
total_change = float((w1 * s1).sum() - (w0 * s0).sum())
within = float((w0 * (s1 - s0)).sum()); between = float(((w1 - w0) * s1).sum())
p.round(3).to_csv(RES / "requestion_industry_detail.csv")
top = p.sort_values("indiv_loss").head(8)[["name", "i0", "i1", "indiv_loss", "dx", "share_change"]]
out = dict(loss_by_group={k: dict(n=int(r.n), indiv_loss=int(r.indiv_loss), share_of_loss=r3(r.share_of_loss)) for k, r in g.iterrows()},
           n_industries=int(len(p)), n_indiv_share_fell=int((p.share_change < 0).sum()),
           indiv_share_total=[r3((w0 * s0).sum()), r3((w1 * s1).sum())], indiv_share_change=r3(total_change), within=r3(within), between=r3(between),
           top_loss=[dict(code=c, name=r["name"], loss=int(r.indiv_loss), floor_dlog=r3(r.dx), share_change=r3(r.share_change)) for c, r in top.iterrows()])
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
