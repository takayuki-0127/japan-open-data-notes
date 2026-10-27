"""1法人1行の生存時間データを作る。

- 対象: 株式会社(301)・合同会社(305)・その他の設立登記法人(399: 一般社団・NPO法人など)
- 開始: 法人番号の指定日（新しく設立された法人では設立登記の日とほぼ同じ）
- 終了（イベント）: 登記記録の閉鎖のうち「清算の結了等」(01) と「登記官による閉鎖」(21)
- 打ち切り: 2026-09-30 時点で閉鎖されていない／合併による解散(11)・他の管轄への本店移転(31)はその日で打ち切り
"""
import pandas as pd, numpy as np
from common import RAW, DATA

END = pd.Timestamp("2026-09-30")
d = pd.read_csv(RAW / "houjin_new_2015_2026.csv.gz", dtype=str)
d = d[d.kind.isin(["301", "305", "399"])].copy()
d["start"] = pd.to_datetime(d["assign"])
d["stop"] = pd.to_datetime(d["close"]).fillna(END)
d = d[d.start < END]
d["T"] = (d.stop - d.start).dt.days / 365.25
d = d[d["T"] >= 0]
d["E"] = d.cause.isin(["01", "21"]).astype(int)
d["E_merge"] = d.cause.isin(["01", "21", "11"]).astype(int)   # 頑健性: 合併も「消えた」に含める
d["kindj"] = d.kind.map({"301": "株式会社", "305": "合同会社", "399": "その他（一般社団・NPOなど）"})
d["cohort"] = d.start.dt.year
reg = {**{p: "北海道・東北" for p in range(1, 8)}, **{p: "関東" for p in range(8, 15)},
       **{p: "中部" for p in range(15, 24)}, **{p: "近畿" for p in range(24, 31)},
       **{p: "中国・四国" for p in range(31, 40)}, **{p: "九州・沖縄" for p in range(40, 48)}}
d["prefn"] = pd.to_numeric(d.pref, errors="coerce")
d = d[d.prefn.between(1, 47)]
d["region"] = d.prefn.astype(int).map(reg)
c = pd.to_numeric(d.city, errors="coerce")
d["area"] = np.where((d.prefn == 13) & c.between(101, 123), "東京23区",
             np.where(c.between(100, 199), "政令市", "その他の市町村"))
cols = ["kindj", "prefn", "region", "area", "cohort", "start", "T", "E", "E_merge", "cause"]
d[cols].to_parquet(DATA / "survival.parquet", index=False)
print(len(d), d.E.mean().round(4), d.groupby("kindj").size().to_dict())
