"""data/raw の Excel から、分析用の表を作る（オフライン）。
出力：
  data/hw_monthly.csv   職業（求人の中分類）× 月 の求人数・求職者数
  data/wage_occ.csv     賃金の職種（小分類）× 年 の所定内給与・労働者数など（男女計・企業規模計）
  data/panel_group.csv  対応づけた職業グループ × 年 の賃金と求人倍率
"""
import pathlib, re
import numpy as np
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"

def clean(s):
    s = str(s).replace("　", "").replace("\n", "").replace(" ", "").strip()
    return s.replace("男女計", "", 1) if s.startswith("男女計") else s

# ---------- 求人（一般職業紹介状況 表21） ----------
SHEETS = {  # シートの位置 -> (指標, 範囲)
    0: ("new_openings", "all"), 1: ("active_openings", "all"), 2: ("new_seekers", "all"), 3: ("active_seekers", "all"),
    7: ("new_openings", "ft"), 8: ("active_openings", "ft"), 9: ("new_seekers", "ft"), 10: ("active_seekers", "ft"),
}
wb = openpyxl.load_workbook(RAW / "hw_t21_occupation_2022apr_.xlsx", read_only=True, data_only=True)
recs = []
for idx, (var, scope) in SHEETS.items():
    rows = list(wb.worksheets[idx].iter_rows(values_only=True))
    yrow, mrow = rows[1], rows[3]
    cols = []
    for j in range(len(yrow)):
        y, m = yrow[j], mrow[j]
        if y and m and str(m).endswith("月"):
            cols.append((j, int(str(y).replace("年", "")), int(str(m).replace("月", ""))))
    for r in rows[5:]:
        if r[0] is None or str(r[0]).startswith("（注"):
            continue
        name = clean(r[0])
        for j, y, m in cols:
            v = r[j]
            if v is None or v == "" or v == "-":
                continue
            recs.append((name, scope, var, y, m, float(v)))
hw = pd.DataFrame(recs, columns=["hw_item", "scope", "var", "year", "month", "value"])
hw = hw.pivot_table(index=["hw_item", "scope", "year", "month"], columns="var", values="value", aggfunc="first").reset_index()
hw = hw.sort_values(["scope", "hw_item", "year", "month"]).reset_index(drop=True)
hw.to_csv(DATA / "hw_monthly.csv", index=False)

# ---------- 賃金（賃金構造基本統計調査 職種 第1表、男女計・企業規模計） ----------
recs = []
for y in (2022, 2023, 2024, 2025):
    ws = openpyxl.load_workbook(RAW / f"wage_occ_t1_{y}.xlsx", read_only=True, data_only=True).worksheets[0]
    started = False
    for r in ws.iter_rows(values_only=True):
        lab = r[1]
        if lab is None:
            continue
        raw = str(lab).replace("　", "").strip()
        if raw.startswith("男女計"):
            started = True
        elif started and (raw.startswith("男") or raw.startswith("女")) and not raw.startswith("男女計"):
            break  # 男の表が始まったら終わり
        if not started or not isinstance(r[8], (int, float)):
            continue
        recs.append(dict(year=y, wage_item=clean(lab), age=r[3], tenure=r[4], hours=r[5], overtime=r[6],
                         regular_pay=r[7], scheduled_pay=r[8], bonus=r[9], workers10=r[10]))
wg = pd.DataFrame(recs)
wg.to_csv(DATA / "wage_occ.csv", index=False)

# ---------- 対応づけ ----------
mp = pd.read_csv(DATA / "occupation_map.csv")
miss_w = sorted(set(mp.loc[mp.source == "wage", "item"]) - set(wg.wage_item))
miss_h = sorted(set(mp.loc[mp.source == "hw", "item"]) - set(hw.hw_item))
assert not miss_w, miss_w
assert not miss_h, miss_h

# 賃金：グループごとに労働者数の重みつき平均（年ごと）
w = wg.merge(mp[mp.source == "wage"].rename(columns={"item": "wage_item"}), on="wage_item")
w["hourly"] = w.scheduled_pay / w.hours
def wavg(g):
    wt = g.workers10
    return pd.Series({
        "workers": float(wt.sum() * 10),
        "scheduled_pay": float(np.average(g.scheduled_pay, weights=wt)),
        "hourly": float(np.average(g.scheduled_pay, weights=wt) / np.average(g.hours, weights=wt)),
        "age": float(np.average(g.age, weights=wt)),
        "tenure": float(np.average(g.tenure, weights=wt)),
        "n_items": int(len(g)),
    })
wgrp = w.groupby(["group_id", "group_name", "year"], sort=True)[["scheduled_pay", "hours", "age", "tenure", "workers10"]].apply(wavg).reset_index()

# 求人：グループごとに件数を足す
h = hw.merge(mp[mp.source == "hw"].rename(columns={"item": "hw_item"}), on="hw_item")
hg = h.groupby(["group_id", "scope", "year", "month"], sort=True)[["active_openings", "active_seekers", "new_openings", "new_seekers"]].sum().reset_index()
hg["ym"] = hg.year * 12 + hg.month - 1

def window_ratio(scope, start_ym, end_ym, num="active_openings", den="active_seekers"):
    s = hg[(hg.scope == scope) & (hg.ym >= start_ym) & (hg.ym <= end_ym)]
    n_months = s.groupby("group_id").size()
    agg = s.groupby("group_id")[[num, den]].sum()
    out = agg[num] / agg[den]
    out[n_months < (end_ym - start_ym + 1)] = np.nan
    return out

ym = lambda y, m: y * 12 + m - 1
rows = []
for g in sorted(mp.group_id.unique()):
    rows.append({"group_id": g})
pan = pd.DataFrame(rows).set_index("group_id")
for scope in ("all", "ft"):
    pan[f"ratio_fy2022_{scope}"] = window_ratio(scope, ym(2022, 4), ym(2023, 3))
    pan[f"newratio_fy2022_{scope}"] = window_ratio(scope, ym(2022, 4), ym(2023, 3), "new_openings", "new_seekers")
    for y in (2023, 2024, 2025):  # その年の6月までの12か月
        pan[f"ratio_jun{y}_{scope}"] = window_ratio(scope, ym(y - 1, 7), ym(y, 6))
    pan[f"openings_fy2022_{scope}"] = hg[(hg.scope == scope) & (hg.ym >= ym(2022, 4)) & (hg.ym <= ym(2023, 3))].groupby("group_id").active_openings.sum() / 12
    pan[f"seekers_fy2022_{scope}"] = hg[(hg.scope == scope) & (hg.ym >= ym(2022, 4)) & (hg.ym <= ym(2023, 3))].groupby("group_id").active_seekers.sum() / 12
pan = pan.reset_index()

wide = wgrp.pivot(index=["group_id", "group_name"], columns="year", values=["scheduled_pay", "hourly", "age", "tenure", "workers"])
wide.columns = [f"{a}_{b}" for a, b in wide.columns]
wide = wide.reset_index()
out = wide.merge(pan, on="group_id").sort_values("group_id").reset_index(drop=True)
out.to_csv(DATA / "panel_group.csv", index=False, float_format="%.6f")
print("groups", len(out), "hw rows", len(hw), "wage rows", len(wg))
