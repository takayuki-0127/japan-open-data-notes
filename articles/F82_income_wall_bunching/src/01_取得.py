"""就業構造基本調査の2つの表を e-Stat から取り、CSV にして data/raw/ に置く。
- 2022年 第66表（statInfId 000040077332）：男女、配偶関係、年齢、所得、就業調整の有無、雇用形態別の非正規の職員・従業員
- 2017年 主要統計表 第7表（statInfId 000031735818）：年齢、所得、男女、配偶関係、就業調整の有無別の非正規の職員・従業員
e-Stat に直接つながらない環境では、ブラウザで Excel を開いて CSV で保存し、同じ名前で置いてください。"""
import io, pathlib, urllib.request
import pandas as pd
RAW = pathlib.Path(__file__).resolve().parents[1] / 'data' / 'raw'; RAW.mkdir(parents=True, exist_ok=True)
URL = 'https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0'
for sid, name in [('000040077332', 'shugyo2022_t66.csv'), ('000031735818', 'shugyo2017_t07.csv')]:
    b = urllib.request.urlopen(URL.format(sid), timeout=60).read()
    pd.read_excel(io.BytesIO(b), header=None, dtype=str).to_csv(RAW / name, index=False, header=False)
    print('saved', name)
