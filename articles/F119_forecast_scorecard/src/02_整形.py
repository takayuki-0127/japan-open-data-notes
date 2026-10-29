"""02 整形：2026年10月の東京エリアの1時間値・日別値を、F22・F92 と同じ形で書き出す（関数は f119common.py）"""
from f119common import ROOT, oct_hourly, oct_daily

if __name__ == "__main__":
    h, d = oct_hourly(), oct_daily()
    h.to_csv(ROOT / "data" / "oct2026_hourly_tokyo.csv")
    d.to_csv(ROOT / "data" / "oct2026_daily_tokyo.csv", index=False)
    print(len(h), int(h.demand.isna().sum()), len(d), d.peak_mw.max())
