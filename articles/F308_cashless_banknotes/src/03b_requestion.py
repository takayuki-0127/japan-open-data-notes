"""問い直し（結果を見てから足した）：
銀行券は2023年をピークに減り始め、年の伸びはコールレートとよく一緒に動いていた（電子マネーの広がりとは一緒に動かない）。
では、減り始めたのはいつで、どの券種か。月末の券種別の前年同月比を2021〜2026年で追う。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
b = pd.read_csv(ROOT / "data" / "boj_monthly.csv")
b["ym"] = b.year * 12 + b.month - 1
b = b.set_index("ym").sort_index()
r3 = lambda x: round(float(x), 3)
out = {}
t = pd.DataFrame(index=b.index)
for c, nm in (("MACCV2", "total"), ("MACCV2@01", "y10000"), ("MACCV2@03", "y1000"), ("MACCV2@02", "y5000")):
    t[f"yoy_{nm}"] = 100 * (np.log(b[c]) - np.log(b[c].shift(12)))
t["call"] = b.STRACLUCON; t["year"] = b.year; t["month"] = b.month
t = t[t.year >= 2019]
t.round(4).to_csv(RES / "requestion_monthly_yoy.csv")
neg = t[(t.yoy_y10000 < 0)]
first = neg.index.min()
out["first_negative_yoy_10000"] = f"{first // 12}-{first % 12 + 1:02d}" if pd.notna(first) else None
negt = t[(t.yoy_total < 0)].index.min()
out["first_negative_yoy_total"] = f"{negt // 12}-{negt % 12 + 1:02d}" if pd.notna(negt) else None
last = t.index.max()
out["latest"] = dict(ym=f"{last // 12}-{last % 12 + 1:02d}", yoy_total=r3(t.loc[last, "yoy_total"]), yoy_10000=r3(t.loc[last, "yoy_y10000"]),
                     yoy_1000=r3(t.loc[last, "yoy_y1000"]), call=r3(t.loc[last, "call"]))
out["n_months_10000_negative_2024_2026"] = int((t[t.year >= 2024].yoy_y10000 < 0).sum())
out["n_months_2024_2026"] = int((t.year >= 2024).sum())
out["mean_yoy_1000_2024_2026"] = r3(t[t.year >= 2024].yoy_y1000.mean())
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
print(t[t.year >= 2023][["yoy_total", "yoy_y10000", "yoy_y1000", "call"]].round(2).to_string())
