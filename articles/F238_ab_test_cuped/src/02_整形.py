"""02 整形：F196 の frame.csv から、模擬テストに使う市区町村の指標を作る。
y_ は SSDSE-A-2026（今の値）、x_ は SSDSE-A-2021（前の値）。前回の人口が0の町と、避難指示区域が設定された福島県の12市町村（2015年の値が極端になる。F180・F197 と同じ）は除く。
除く前の全市区町村も geo_metrics_all.csv に残す（頑健性で使う）。"""
from pathlib import Path
import numpy as np
import pandas as pd
D = Path(__file__).resolve().parents[1] / "data"
d = pd.read_csv(D / "geo_frame_src.csv", dtype={"area_code": str})
EVAC = {"07211", "07212", "07308", "07541", "07542", "07543", "07544", "07545", "07546", "07547", "07548", "07564"}
d = d[(d.y_pop > 0) & (d.x_pop > 0)].copy()
out = pd.DataFrame({"area_code": d.area_code, "pref": d.pref})
out["birth_rate"] = d.y_births / d.y_pop * 1000
out["birth_rate_pre"] = d.x_births / d.x_pop * 1000
out["emp_ratio"] = d.y_employees / d.y_pop
out["emp_ratio_pre"] = d.x_employees / d.x_pop
out["aging"] = d.y_aging_mean
out["aging_pre"] = d.x_aging_mean
out["births"] = d.y_births
out["births_pre"] = d.x_births
out["log_emp_ratio"] = np.log(out.emp_ratio)
out["log_emp_ratio_pre"] = np.log(out.emp_ratio_pre)
out.to_csv(D / "geo_metrics_all.csv", index=False)
main = out[~out.area_code.str[1:].isin(EVAC)]
main.to_csv(D / "geo_metrics.csv", index=False)
print(len(out), "all /", len(main), "main")
