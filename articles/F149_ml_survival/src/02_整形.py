"""1法人1行の分析用データを作る。

- 対象: 株式会社(301)・合同会社(305)・その他の設立登記法人(399)。2015-11-01 以降に法人番号が指定された法人
- 結末: 閉鎖＝「清算の結了等」(01)＋「登記官による閉鎖」(21)。合併(11)は打ち切り（F79・F106 と同じ原因別ハザード）
- 打ち切り: 2026-09-30。時間は指定日からの年数
- 特徴量（すべて法人の登記上の属性と、所在市区町村の集計値。名前・番号・住所は使わない）
  kind(3) / area(東京23区・政令市・その他) / region(6) / pref(47) / cohort(指定年) / month(指定月) /
  dom(指定日の日にち) / dow(曜日) / muni_logn(市区町村の新規法人数の対数) / muni_llc(市区町村の合同会社の割合) /
  muni_other(その他法人の割合)
- 10万社の標本（seed 42）を data/sample100k.parquet に、残りの法人は「市区町村の閉鎖率」の計算にだけ使う
"""
import pandas as pd, numpy as np
from common import RAW, DATA, SEED

END = pd.Timestamp("2026-09-30")
d = pd.read_csv(RAW / "houjin_new_2015_2026.csv.gz", dtype=str)
d = d[d.kind.isin(["301", "305", "399"])].copy()
d["start"] = pd.to_datetime(d["assign"]); d = d[d.start < END]
d["stop"] = pd.to_datetime(d["close"]).fillna(END)
d["T"] = (d.stop - d.start).dt.days / 365.25
d = d[d["T"] >= 0].copy()
d["T"] = d["T"].clip(lower=0.5 / 365.25)
d["E"] = d.cause.isin(["01", "21"]).astype(int)
d["E01"] = d.cause.eq("01").astype(int)
d["kind"] = d.kind.map({"301": "株式会社", "305": "合同会社", "399": "その他法人"})
d["pref"] = pd.to_numeric(d.pref, errors="coerce")
d = d[d.pref.between(1, 47)].copy(); d["pref"] = d.pref.astype(int)
reg = {**{p: "北海道・東北" for p in range(1, 8)}, **{p: "関東" for p in range(8, 15)},
       **{p: "中部" for p in range(15, 24)}, **{p: "近畿" for p in range(24, 31)},
       **{p: "中国・四国" for p in range(31, 40)}, **{p: "九州・沖縄" for p in range(40, 48)}}
d["region"] = d.pref.map(reg)
c = pd.to_numeric(d.city, errors="coerce").fillna(0).astype(int)
d["area"] = np.where((d.pref == 13) & c.between(101, 123), "東京23区", np.where(c.between(100, 199), "政令市", "その他"))
d["muni"] = d.pref * 1000 + np.where((d.pref != 13) & c.between(100, 199), (c // 10) * 10, c)
d["cohort"] = d.start.dt.year + (d.start.dt.dayofyear - 1) / 365.25
d["month"] = d.start.dt.month; d["dom"] = d.start.dt.day; d["dow"] = d.start.dt.dayofweek
g = d.groupby("muni")
d["muni_logn"] = np.log(g.kind.transform("size"))
d["muni_llc"] = g.kind.transform(lambda s: (s == "合同会社").mean())
d["muni_other"] = g.kind.transform(lambda s: (s == "その他法人").mean())
cols = ["kind", "area", "region", "pref", "muni", "cohort", "month", "dom", "dow", "muni_logn", "muni_llc", "muni_other", "T", "E", "E01"]
d = d[cols].reset_index(drop=True)
rng = np.random.default_rng(SEED)
idx = rng.permutation(len(d))
s = d.iloc[idx[:100_000]].reset_index(drop=True)
rest = d.iloc[idx[100_000:]].reset_index(drop=True)
s.to_parquet(DATA / "sample100k.parquet", index=False)
# 標本の外の法人で、市区町村ごとの「閉鎖件数÷リスク年」（目的変数の漏れを避けるため標本は使わない）
m = rest.groupby("muni").agg(ev=("E", "sum"), ry=("T", "sum")).reset_index()
tot = rest.E.sum() / rest["T"].sum()
m["muni_rate"] = (m.ev + 5 * tot) / (m.ry + 5)    # 小さい市区町村は全体の率へ縮める（事前の重み＝5リスク年）
m[["muni", "muni_rate"]].to_parquet(DATA / "muni_rate_outside.parquet", index=False)
# 全件の要約
pd.DataFrame({"n_all": [len(d)], "events_all": [d.E.sum()], "n_sample": [len(s)], "events_sample": [s.E.sum()],
              "riskyears_sample": [s["T"].sum()], "n_rest": [len(rest)]}).to_csv(DATA / "summary.csv", index=False)
print(len(d), d.E.sum(), s.E.sum(), round(s["T"].sum()), d.muni.nunique())
