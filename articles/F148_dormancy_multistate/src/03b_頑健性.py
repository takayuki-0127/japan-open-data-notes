"""頑健性: 状態の定義・法人の種類・期間・復活の扱いを変えて、主な数字がどう動くか。"""
import pandas as pd, numpy as np, importlib.util
from common import DATA, RES
spec = importlib.util.spec_from_file_location("a", "03_分析.py")
old = pd.read_parquet(DATA / "old_cells.parquet"); new = pd.read_parquet(DATA / "new_cells.parquet")
rows = []
def share(df, mmax=132, route3_filter=None, merge31=True):
    ev = df[(df.route > 0) & (df.m <= mmax)].copy()
    if route3_filter is not None:
        ev.loc[(ev.route == 3) & ~route3_filter(ev), "route"] = 9   # 1月以外の登記官閉鎖は別扱い
    if not merge31:
        ev.loc[ev.cause == "31", "route"] = 8
    tot = ev.groupby("route").n.sum()
    N = df.n.sum()
    return tot.get(3, 0) / tot[tot.index.isin([1, 2, 3])].sum(), tot.get(3, 0) / N, tot.get(1, 0) / N
kk = old[old.kindj == "株式会社"]
cases = [
    ("基本（2015年10月〜2026年10月、すべての種別）", old, {}),
    ("株式会社だけ", kk, {}),
    ("有限会社だけ", old[old.kindj == "有限会社"], {}),
    ("一般社団・NPOなどだけ", old[old.kindj == "一般社団・NPOなど"], {}),
    ("2024年12月まで（2025・26年の大きな整理を除く）", old, {"mmax": 110}),
    ("2016年3月〜2024年12月（最初の整理も除く）", old[(old.m < 0) | (old.m >= 5)], {"mmax": 110}),
    ("登記官による閉鎖を1月の分だけにする", old, {"route3_filter": lambda e: (e.m + 9) % 12 == 0}),
    ("「その他の清算の結了等」(31)を清算に入れない", old, {"merge31": False}),
]
for name, df, kw in cases:
    a, b, c = share(df, **kw)
    rows.append({"設定": name, "閉鎖のうち登記官による閉鎖の割合": a, "登記官による閉鎖（法人数に対する割合）": b, "清算の結了など（同）": c})
# 地域ごと（株式会社）
for ar, g in kk.groupby("area"):
    a, b, c = share(g); rows.append({"設定": f"株式会社・{ar}", "閉鎖のうち登記官による閉鎖の割合": a, "登記官による閉鎖（法人数に対する割合）": b, "清算の結了など（同）": c})
rb = pd.DataFrame(rows); rb.to_csv(RES / "robustness_old.csv", index=False, encoding="utf-8-sig"); print(rb.round(4).to_string())

# new: 設立年・AJ と 1−KM の差・地域
from ms import aj_new
nrow = []
for name, df in [("株式会社（基本）", new[new.kindj == "株式会社"]),
                 ("株式会社・2015〜2019年の設立", new[(new.kindj == "株式会社") & (new.cohort <= 2019)]),
                 ("株式会社・2020年以降の設立", new[(new.kindj == "株式会社") & (new.cohort >= 2020)]),
                 ("合同会社", new[new.kindj == "合同会社"]),
                 ("一般社団・NPOなど", new[new.kindj == "一般社団・NPOなど"])]:
    cur, ar = aj_new(df)
    r5 = cur[cur.age_m == 60].iloc[0]
    rr = {"設定": name, "5年_清算": r5["清算の結了など"], "5年_合併": r5["合併"], "5年_登記官閉鎖": r5["登記官による閉鎖"],
          "5年_1-KM清算と AJ の差（ポイント）": (r5["1-KM_清算だけ"] - r5["清算の結了など"]) * 100}
    a6 = df[(df.route == 3)]
    rr["登記官閉鎖のうち設立5年目（60〜71か月）の割合"] = a6[(a6.age >= 60) & (a6.age < 72)].n.sum() / max(a6.n.sum(), 1)
    nrow.append(rr)
nb = pd.DataFrame(nrow); nb.to_csv(RES / "robustness_new.csv", index=False, encoding="utf-8-sig"); print(nb.round(4).to_string())
