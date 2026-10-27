"""内閣府 経済社会総合研究所「県民経済計算」の各基準年の表から、1人当たり県民所得と総人口を取得する。
（この記事のデータは 2026-10-28 にブラウザのページ内で同じ URL から取得した。data/raw/kenmin_raw.json）
令和5年度版（2011〜2023年度）は石川・奈良・徳島・香川・宮崎の5県が未公表だったため、
その5県は令和4年度版（tables/2022/soukatu7.xlsx）の値で補った（data/raw/v2022_missing5.csv）。"""
import io, json, pathlib, requests, pandas as pd
H = pathlib.Path(__file__).resolve().parents[1]
BASE = 'https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/'
FILES = {'v2023': 'tables/2023/soukatu7.xlsx', 'v2018': 'tables/2018/soukatu7.xlsx', 'h26': 'tables/h26/soukatu9.xls',
         'h21': 'tables/h20/soukatu9_1.xls', 'h15': 'tables/h15/soukatu6.xls', 's50': 'tables/s50/50soukatu7.xls',
         's30': 'tables/s30/30soukatu5_sankou.xls',
         'pop2023': 'tables/2023/soukatu9.xlsx', 'pop2018': 'tables/2018/soukatu9.xlsx', 'poph26': 'tables/h26/soukatu11.xls',
         'poph21': 'tables/h20/soukatu11_1.xls', 'poph15': 'tables/h15/soukatu8.xls', 'pops50': 'tables/s50/50soukatu9.xls'}
out = {}
for k, f in FILES.items():
    b = requests.get(BASE + f, timeout=60).content
    df = pd.read_excel(io.BytesIO(b), sheet_name=0, header=None)
    out[k] = df.astype(object).where(df.notna(), None).values.tolist()
(H/'data/raw').mkdir(parents=True, exist_ok=True)
json.dump(out, open(H/'data/raw/kenmin_raw.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
print('saved', len(out))
