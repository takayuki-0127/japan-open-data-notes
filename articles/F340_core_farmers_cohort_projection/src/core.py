"""共通の関数：データの読み込み、コーホート変化率、1期先の推計、指標。"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
d = pd.read_csv(ROOT / "data" / "core_workers_by_age.csv")
AGES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
        "65-69", "70-74", "75-79", "80-84", "85+"]
MID = np.array([17.5 + 5 * k for k in range(14)] + [87.5])
REGIONS = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]

# 系列：(年, 基準)。2025年の表の2020年の再掲は照合だけに使う
SER = {2005: "販売農家", 2010: "販売農家", 2020: "個人経営体", 2025: "個人経営体"}


def vec(year, basis, level="全国", name="全国", sex="計"):
    src = "2025年センサス" if year == 2025 else "累年統計"
    q = d[(d.year == year) & (d.basis == basis) & (d.level == level) & (d.name == name) & (d.sex == sex) & (d.source == src)]
    q = q.set_index("age").reindex(AGES)["n"].astype(float).values
    return q


def ccr(n0, n1):
    r = np.full(15, np.nan)
    r[1:14] = n1[1:14] / n0[0:13]
    r[14] = n1[14] / (n0[13] + n0[14])
    return r


def step(n, r):
    out = np.empty(15)
    out[0] = n[0]                     # 15〜19歳は横ばい
    out[1:14] = n[0:13] * r[1:14]
    out[14] = (n[13] + n[14]) * r[14]
    return out


def metrics(n):
    tot = n.sum()
    return {"total": float(tot), "share65_pct": float(100 * n[10:].sum() / tot), "under50": float(n[:7].sum()),
            "under50_share_pct": float(100 * n[:7].sum() / tot), "mean_age": float((n * MID).sum() / tot)}


# 期間ごとの変化率（2015年は、前の期間の終わりは販売農家、後の期間の始まりは個人経営体）
PERIODS = {"2005-10": ((2005, "販売農家"), (2010, "販売農家")), "2010-15": ((2010, "販売農家"), (2015, "販売農家")),
           "2015-20": ((2015, "個人経営体"), (2020, "個人経営体")), "2020-25": ((2020, "個人経営体"), (2025, "個人経営体"))}


def rates(level="全国", name="全国", sex="計"):
    out = {}
    for k, ((y0, b0), (y1, b1)) in PERIODS.items():
        out[k] = ccr(vec(y0, b0, level, name, sex), vec(y1, b1, level, name, sex))
    avg = np.full(15, np.nan)
    avg[1:] = np.vstack([out[k][1:] for k in PERIODS]).mean(axis=0)
    out["平均"] = avg
    return out


