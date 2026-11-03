"""件数の表を、分析で使う形にそろえる。

状態（多状態モデル）
  0 活動（登記が残っている）
  1 清算の結了など（閉鎖の事由 01「清算の結了等」・31「その他の清算の結了等」）
  2 合併による解散（11）
  3 登記官による閉鎖（21）。解散したまま一定期間がたった登記記録や、休眠会社のみなし解散のあとの記録を、登記官が閉じるもの
  3→0 登記記録の復活（最新の処理区分が 22 の法人。あとで別の変更があった法人は数えられないので下限）
時間の単位は月。制度開始時にあった法人（old）は 2015年10月を起点にした暦の月、
新しく設立された法人（new）は法人番号の指定からの月数（2026年10月で打ち切り）。
"""
import pandas as pd, numpy as np
from common import RAW, DATA

END = pd.Period("2026-10", "M"); START_OLD = pd.Period("2015-10", "M")
KIND = {"301": "株式会社", "302": "有限会社", "305": "合同会社", "303": "合名・合資会社", "304": "合名・合資会社",
        "399": "一般社団・NPOなど"}
ROUTE = {"01": 1, "31": 1, "11": 2, "21": 3}

c = pd.read_csv(RAW / "cells_20261030.csv.gz", dtype=str, keep_default_na=False)
c["n"] = c.n.astype(int)
c = c[c.kind.isin(KIND)].copy()
c["kindj"] = c.kind.map(KIND)
c["route"] = c.cause.map(ROUTE).fillna(0).astype(int)
c["close_p"] = pd.PeriodIndex(c.close_ym.replace("", None), freq="M") if False else c.close_ym.apply(lambda s: pd.Period(s, "M") if s else pd.NaT)

old = c[c.group == "old"].copy()
old = old[(old.route == 0) | (old.close_p >= START_OLD)]          # 2015年10月より前の閉鎖は除く
old["m"] = old.close_p.apply(lambda p: (p - START_OLD).n if p is not pd.NaT else -1)
old.loc[old.route == 0, "m"] = -1
old[["kindj", "pref", "area", "route", "cause", "m", "n"]].to_parquet(DATA / "old_cells.parquet", index=False)

new = c[(c.group == "new") & c.kind.isin(["301", "305", "399"])].copy()
new["a"] = new.assign_ym.apply(lambda s: pd.Period(s, "M"))
new = new[new.a < END]
new["age"] = np.where(new.route > 0, new.close_p.apply(lambda p: p.ordinal if p is not pd.NaT else 0) - new.a.apply(lambda p: p.ordinal), -1)
new["cens"] = new.a.apply(lambda p: (END - p).n)
new["cohort"] = new.a.apply(lambda p: p.year)
new[["kindj", "pref", "area", "route", "cause", "cohort", "age", "cens", "n"]].to_parquet(DATA / "new_cells.parquet", index=False)

r = pd.read_csv(RAW / "revival_20261030.csv.gz", dtype=str, keep_default_na=False); r["n"] = r.n.astype(int)
r = r[r.kind.isin(KIND)].copy(); r["kindj"] = r.kind.map(KIND)
r["m"] = r.revive_ym.apply(lambda s: (pd.Period(s, "M") - START_OLD).n)
r.to_parquet(DATA / "revival.parquet", index=False)
print("old", old.n.sum(), old.groupby("route").n.sum().to_dict())
print("new", new.n.sum(), new.groupby("route").n.sum().to_dict())
print("revival", r.n.sum())
