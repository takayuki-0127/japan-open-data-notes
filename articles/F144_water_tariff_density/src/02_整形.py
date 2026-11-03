"""02 整形：地方公営企業年鑑（23）の事業別データを、1事業=1行の表にする。
入力: data/raw/f144_water_nenkan.json（01_取得 で作成。R06=令和6年度, R01=令和元年度）
      data/raw/SSDSE-A-2026.csv（市区町村の面積。市町村営の事業だけ突き合わせる）
出力: data/water_R06.csv, data/water_R01.csv
"""
import json, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
raw = json.load(open(ROOT / "data/raw/f144_water_nenkan.json", encoding="utf-8"))

# 行番号（R06・R01 とも同じ並びであることを 01 で確認済み）
ROWS = {
    "keiei": 3, "jigyo": 4, "pref": 5, "name": 6, "keitai": 8,
    "pop_admin": 16, "pop_served": 18,
    "intake_cap": 23, "cap_surface": 25, "cap_dam": 26, "cap_bulk": 27,
    "pipe_km1000": 29, "pipe_old": 30, "plants": 32,
    "intake": 35, "revenue_water_day": 37,
    "annual_dist": 39, "annual_rev_water": 43,
    "fee_basic": 47, "fee_excess": 48, "fee10": 49, "fee_system": 51,
    "yushu_rate": 67, "util_rate": 69,
    "supply_price": 76, "supply_cost": 77,
    "c_labor": 79, "c_interest": 81, "c_depr": 87, "c_power": 88, "c_repair": 91,
    "c_chem": 93, "c_contract": 95, "c_bulk": 96, "c_total": 100,
}

def num(x):
    if x in ("", "-", None):
        return np.nan
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return np.nan

ssd = pd.read_csv(ROOT / "data/raw/SSDSE-A-2026.csv", encoding="cp932", header=None, skiprows=3)
ssd = ssd[[1, 2, 36, 37]]
ssd.columns = ["pref", "name", "area_total", "area_hab"]
ssd["area_total"] = pd.to_numeric(ssd["area_total"], errors="coerce") / 100  # ha→km2
ssd["area_hab"] = pd.to_numeric(ssd["area_hab"], errors="coerce") / 100

for yr, d in raw.items():
    labels = d["labels"]
    assert "10m３当たり料金" in labels[ROWS["fee10"]], labels[ROWS["fee10"]]
    assert "給水原価" in labels[ROWS["supply_cost"]]
    assert "導送配水管延長" in labels[ROWS["pipe_km1000"]]
    recs = []
    for e in d["ents"]:
        r = {k: e[i] for k, i in ROWS.items()}
        for k in ROWS:
            if k not in ("keiei", "jigyo", "pref", "name", "keitai"):
                r[k] = num(r[k])
        r["keiei"] = str(r["keiei"]).strip()
        r["jigyo"] = str(r["jigyo"]).strip()
        r["pref"] = str(r["pref"]).strip()
        r["name"] = str(r["name"]).strip() or r["pref"]
        r["keitai"] = str(r["keitai"]).strip()
        recs.append(r)
    df = pd.DataFrame(recs)
    df["year"] = yr
    # 水源の割合（取水能力ベース）。地下水・その他 = 残り
    cap = df["intake_cap"]
    for c in ["cap_surface", "cap_dam", "cap_bulk"]:
        df[c] = df[c].fillna(0)
    df["sh_surface"] = df["cap_surface"] / cap
    df["sh_dam"] = df["cap_dam"] / cap
    df["sh_bulk"] = df["cap_bulk"] / cap
    df["sh_ground"] = (1 - df[["sh_surface", "sh_dam", "sh_bulk"]].sum(axis=1)).clip(lower=0)
    df["pipe_km"] = df["pipe_km1000"]  # 千m = km
    df["dens_pipe"] = df["pop_served"] / df["pipe_km"]  # 管路1kmあたり給水人口
    df["old_pipe_sh"] = df["pipe_old"] / df["pipe_km1000"]
    # 市町村営は市区町村の面積と突き合わせる
    m = df.merge(ssd, on=["pref", "name"], how="left")
    m.loc[~m["keiei"].isin(["市営", "町村営", "指定都市営"]), ["area_total", "area_hab"]] = np.nan
    m["dens_hab"] = m["pop_served"] / m["area_hab"]
    m.to_csv(ROOT / f"data/water_{yr}.csv", index=False, encoding="utf-8")
    print(yr, len(m), "末端上水道:", (m["keitai"] == "1").sum(),
          "面積一致:", m["area_hab"].notna().sum())
