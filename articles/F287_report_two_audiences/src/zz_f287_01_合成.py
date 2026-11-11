"""01 合成：みどり堂（架空）の店×部門×月の数字を作る（種287、12店）。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from zz_f287_common import gen
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)
df = gen(287, 12)
df.round(6).to_csv(os.path.join(OUT, "midorido_monthly.csv"), index=False)
print(df.shape, df.sales.sum().round(1))
