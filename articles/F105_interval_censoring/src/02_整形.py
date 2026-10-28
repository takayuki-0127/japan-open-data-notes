"""1法人1行のデータを作る（F28 と同じ定義）。
- 開始: 法人番号の指定日
- イベント: 閉鎖（「清算の結了等」01 ＋「登記官による閉鎖」21）
- 打ち切り: 合併による解散(11)・本店移転(31) はその日、残っている法人は 2026-09-30
"""
import pandas as pd, numpy as np
from common import RAW, DATA

END = pd.Timestamp("2026-09-30")
d = pd.read_csv(RAW / "houjin_new_2015_2026.csv.gz", dtype=str)
d = d[d.kind.isin(["301", "305", "399"])].copy()
d["start"] = pd.to_datetime(d["assign"])
d = d[d.start < END]
d["stop"] = pd.to_datetime(d["close"]).fillna(END)
d = d[d.stop >= d.start]
d["event"] = d.cause.isin(["01", "21"]).astype(int)
d["kindj"] = d.kind.map({"301": "株式会社", "305": "合同会社", "399": "その他の法人"})
d["prefn"] = pd.to_numeric(d.pref, errors="coerce")
d = d[d.prefn.between(1, 47)]
c = pd.to_numeric(d.city, errors="coerce")
d["area"] = np.where((d.prefn == 13) & c.between(101, 123), "東京23区",
             np.where(c.between(100, 199), "政令市", "その他の市町村"))
out = pd.DataFrame({
    "s": (d.start - pd.Timestamp("2015-01-01")).dt.days.values,   # 開始（2015-01-01 からの日数）
    "e": (d.stop - pd.Timestamp("2015-01-01")).dt.days.values,    # 閉鎖・打ち切りの日
    "event": d.event.values, "kindj": d.kindj.values, "area": d.area.values})
out.to_parquet(DATA / "firms.parquet", index=False)
print(len(out), out.event.sum())
