# F206 data/ を作る：F205（F157 の予測）と F22（需要・気温）から必要な列だけ切り出す
# リポジトリの articles/ の下で実行する想定（../F205_.../data と ../F22_.../data を読む）
import os, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)) + '/..'; A = H + '/..'
cols = ['ts', 'actual', '毎週', '毎月', '固定（開始前に1回）', '1週間前の同じ時刻']
for a in ['tokyo', 'kansai']:
    x = pd.read_csv(f'{A}/F205_power_forecast_practice_part1/data/f157_pred_{a}_2025_26.csv.gz')
    x[cols].to_csv(f'{H}/data/area_pred_{a}_2025_26.csv.gz', index=False, compression='gzip')
    h = pd.read_csv(f'{A}/F22_power_demand_forecast/data/hourly_{a}.csv')
    h = h[h.ts >= '2024-04-01']
    h[['ts', 'demand', 'temp_mean', 'temp_max', 'temp_min', 'humid_mean', 'precip_mm', 'holiday']].to_csv(
        f'{H}/data/hourly_{a}_2024_26.csv.gz', index=False, compression='gzip')
print('ok')
