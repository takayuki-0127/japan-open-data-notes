# 04 SQL 検算：架空のECサイトの A/B テスト（シミュレーション）を SQLite に入れ、04_集計.sql と Python の結果を比べる
import json, math, sqlite3, numpy as np, pandas as pd
from pathlib import Path
from scipy import stats
R = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(20261112)
n = 31234                                   # 基準5%・+10% を検出力80%で見つけるのに必要な1群の人数（03 の結果）
arm = np.repeat(["A", "B"], n)
p = np.where(arm == "A", .05, .055)
conv = (rng.random(2 * n) < p).astype(int)
spend = np.where(conv == 1, np.round(rng.lognormal(math.log(6000), .8, 2 * n)), 0.0)
df = pd.DataFrame({"user_id": np.arange(2 * n), "arm": arm, "converted": conv, "spend": spend})
df.to_csv(R / "data" / "sim_ab_events.csv.gz", index=False, compression="gzip")
con = sqlite3.connect(":memory:"); con.create_function("SQRT", 1, math.sqrt)
df.to_sql("ab_events", con, index=False)
sql = open(R / "src" / "04_集計.sql").read()
s = pd.read_sql(sql, con).iloc[0]
a, b = df[df.arm == "A"], df[df.arm == "B"]
ra, rb = a.converted.mean(), b.converted.mean(); pp = df.converted.mean()
zz = (rb - ra) / math.sqrt(pp * (1 - pp) * (2 / n))
out = {"sql": s.to_dict(), "python": {"rate_a": ra, "rate_b": rb, "z_stat": zz, "p_value": 2 * (1 - stats.norm.cdf(abs(zz)))},
       "max_abs_diff": float(max(abs(s.rate_a - ra), abs(s.rate_b - rb), abs(s.z_stat - zz)))}
json.dump(out, open(R / "results" / "G_sql_check.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
