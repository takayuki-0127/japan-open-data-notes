# 気象庁「平年値（統計期間1991〜2020年）」のアメダスの月別平年値と地点一覧をダウンロードし、
# 気温（要素 0500=平均、0600=日最高の平均、0700=日最低の平均）だけを抜き出して data/raw/f74_jma_normals.txt を作る。
# 記事を作ったときは、この処理をブラウザのページ内（JSZip）で行い、同じ形式のファイルを保存した。
import io, zipfile, requests
from pathlib import Path
B = Path(__file__).resolve().parents[1]
U = 'https://ds.data.jma.go.jp/obd/stats/data/mdrr/normal/2020/data/'
st = zipfile.ZipFile(io.BytesIO(requests.get(U+'amedas_station_index.zip', timeout=120).content))
st_txt = st.read('amedas_station_index.csv').decode('shift_jis')
z = zipfile.ZipFile(io.BytesIO(requests.get(U+'normal_amedas_monthly.zip', timeout=300).content))
rows = []
for f in z.namelist():
    if not f.endswith('.csv'): continue
    for l in z.read(f).decode('shift_jis').splitlines():
        c = l.split(',')
        if len(c) >= 5 and c[2] in ('0500', '0600', '0700'):
            rows.append(','.join(x.strip() for x in c))
(B/'data/raw').mkdir(parents=True, exist_ok=True)
(B/'data/raw/f74_jma_normals.txt').write_text('##STATION\n'+st_txt+'\n##TEMP\n'+'\n'.join(rows), encoding='utf-8')
print(len(rows), 'rows')
