"""02 整形：事故ごとの損害を「2025年度の建設費・住宅数に直した億円」にそろえる。
A：協会が個別に調べた34事故（2012〜2025年度、14年）
B：取りこぼしのない大きな事故（1991〜2025年度、35年。住宅1戸あたり実質が F256 の足切り以上）"""
import pandas as pd
from zz_f260_common import RAW, P, to_2025, cutoff
P.mkdir(parents=True, exist_ok=True)
ev = pd.read_csv(RAW / "f256_events_adjusted.csv")
top = pd.read_csv(RAW / "f256_top10.csv")
rows = []
for d in ("defl_house", "cpi_all"):
    for _, r in ev.iterrows():
        loss, per = to_2025(r.all_k * 1e3, int(r.fy), r.event_ym, d)
        rows.append(dict(src="A", deflator=d, name=r.title, event_ym=r.event_ym, fy=int(r.fy), peril=r.peril, nom_oku=r.all_k * 1e3 / 1e8, yen_per_dwelling=per, loss_2025_oku=loss))
    for _, r in top.iterrows():
        loss, per = to_2025(r.tot_oku * 1e8, int(r.fy), r.event_ym, d)
        rows.append(dict(src="top10", deflator=d, name=r["name"], event_ym=r.event_ym, fy=int(r.fy), peril="台風" if "台風" in r["name"] else ("雪" if "雪" in r["name"] else "大雨"), nom_oku=float(r.tot_oku), yen_per_dwelling=per, loss_2025_oku=loss))
df = pd.DataFrame(rows)
df.to_csv(P / "events_2025scale_all.csv", index=False)
A = df[df.src == "A"].copy()
A.to_csv(P / "dataset_A.csv", index=False)
# B：2012年度より前は上位10表から、2012年度以降は個別の調査（A）から。足切りは物価のものさしごとに計算
B = []
for d in ("defl_house", "cpi_all"):
    c = cutoff(d)
    b = pd.concat([df[(df.src == "top10") & (df.deflator == d) & (df.fy < 2012)], df[(df.src == "A") & (df.deflator == d)]])
    b = b[b.yen_per_dwelling >= c].copy(); b["cutoff_yen_pd"] = c
    B.append(b)
B = pd.concat(B); B.to_csv(P / "dataset_B.csv", index=False)
print(B[["deflator", "name", "fy", "yen_per_dwelling", "loss_2025_oku", "cutoff_yen_pd"]].round(1).to_string())
print(A[A.deflator == "defl_house"].sort_values("loss_2025_oku", ascending=False)[["name", "loss_2025_oku"]].head(26).round(1).to_string())
