"""競合リスク用の1法人1行のデータを作る。

- 対象: 株式会社(301)・合同会社(305)・その他の設立登記法人(399)、2015-11-01 以降に法人番号が指定された法人
- 開始: 法人番号の指定日
- 結末（cause）:
    1 = 閉鎖（「清算の結了等」01 ＋「登記官による閉鎖」21）
    2 = 合併による解散（11）
    0 = 打ち切り（2026-09-30 時点で登記が残っている）
  ※ 他の管轄への本店移転(31)はこの3種別には出てこない（0件）
- 打ち切りの時刻は全員「2026-09-30 − 指定日」で分かっている（管理上の打ち切りだけ）。
"""
import pandas as pd, numpy as np
from common import RAW, DATA

END = pd.Timestamp("2026-09-30")
d = pd.read_csv(RAW / "houjin_new_2015_2026.csv.gz", dtype=str)
d = d[d.kind.isin(["301", "305", "399"])].copy()
d["start"] = pd.to_datetime(d["assign"])
d = d[d.start < END]
d["stop"] = pd.to_datetime(d["close"]).fillna(END)
d["T"] = (d.stop - d.start).dt.days / 365.25
d["C"] = (END - d.start).dt.days / 365.25          # 打ち切りの時刻（全員わかっている）
d = d[d["T"] >= 0]
d["cause3"] = np.select([d.cause.isin(["01", "21"]), d.cause.eq("11")], [1, 2], 0)
d["cause21"] = d.cause.eq("21").astype(int)
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
cols = ["kindj", "prefn", "region", "area", "cohort", "T", "C", "cause3", "cause21", "cause"]
d[cols].to_parquet(DATA / "cr.parquet", index=False)
print(len(d), d.cause3.value_counts().to_dict())
print(pd.crosstab(d.kindj, d.cause3))
