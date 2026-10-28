"""1法人1行のデータを作り、区分化指数モデル（ポアソン）用に「グループ×種別×地域区分×設立年×経過年」に集計する。

- 対象: 株式会社(301)・合同会社(305)・その他の設立登記法人(399)、2015-11-01 以降に法人番号が指定された法人
- 結末: 閉鎖＝「清算の結了等」(01)＋「登記官による閉鎖」(21)。合併(11)は打ち切りとして扱う（原因別ハザード）
- 打ち切り: 2026-09-30
- 経過年を1年刻み（0〜10年、11区間）に分け、各区間の事象数と観察年数（リスク年）を集計
- グループ: 都道府県（47）、市区町村（都道府県＋市区町村コード）、地方（6）
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
d = d[d["T"] >= 0]
d["T"] = d["T"].clip(lower=0.5 / 365.25)   # 指定日と同じ日の閉鎖（64件）に半日分の観察を与える
d["ev_all"] = d.cause.isin(["01", "21"]).astype(int)      # 閉鎖（基本）
d["ev_01"] = d.cause.eq("01").astype(int)                  # 清算の結了等だけ
d["ev_mg"] = d.cause.eq("11").astype(int)                  # 合併（参考）
d["kindj"] = d.kind.map({"301": "株式会社", "305": "合同会社", "399": "その他法人"})
d["prefn"] = pd.to_numeric(d.pref, errors="coerce")
d = d[d.prefn.between(1, 47)].copy()
d["prefn"] = d.prefn.astype(int)
reg = {**{p: "北海道・東北" for p in range(1, 8)}, **{p: "関東" for p in range(8, 15)},
       **{p: "中部" for p in range(15, 24)}, **{p: "近畿" for p in range(24, 31)},
       **{p: "中国・四国" for p in range(31, 40)}, **{p: "九州・沖縄" for p in range(40, 48)}}
d["region"] = d.prefn.map(reg)
c = pd.to_numeric(d.city, errors="coerce")
d["area"] = np.where((d.prefn == 13) & c.between(101, 123), "東京23区",
             np.where(c.between(100, 199), "政令市", "その他の市町村"))
# 市区町村：政令市の区は市にまとめる（区コード 101-199 → 市の単位。東京23区は区ごと）
cc = c.fillna(0).astype(int)
city_unit = np.where((d.prefn != 13) & cc.between(100, 199), (cc // 10) * 10, cc)
d["muni"] = d.prefn * 1000 + city_unit
d["cohort"] = d.start.dt.year
d[["kindj", "prefn", "region", "area", "muni", "cohort", "T", "ev_all", "ev_01", "ev_mg"]].to_parquet(DATA / "firms.parquet", index=False)
print("法人数", len(d), "閉鎖", d.ev_all.sum(), "うち清算の結了等", d.ev_01.sum(), "市区町村の数", d.muni.nunique())

# 経過年ごとに分割して集計
K = 11
rows = []
T = d["T"].to_numpy()
for k in range(K):
    expo = np.clip(T - k, 0, 1)
    m = expo > 0
    ev = (T > k) & (T <= k + 1)
    rows.append(pd.DataFrame({"muni": d.muni.values[m], "prefn": d.prefn.values[m], "kindj": d.kindj.values[m],
                              "area": d.area.values[m], "cohort": d.cohort.values[m], "k": k, "expo": expo[m],
                              "ev_all": (d.ev_all.values * ev)[m], "ev_01": (d.ev_01.values * ev)[m],
                              "ev_mg": (d.ev_mg.values * ev)[m]}))
p = pd.concat(rows)
agg = p.groupby(["muni", "prefn", "kindj", "area", "cohort", "k"], as_index=False)[["expo", "ev_all", "ev_01", "ev_mg"]].sum()
agg.to_parquet(DATA / "pe_cells.parquet", index=False)
print("セル数", len(agg), "リスク年", round(agg.expo.sum()), "閉鎖", agg.ev_all.sum())
