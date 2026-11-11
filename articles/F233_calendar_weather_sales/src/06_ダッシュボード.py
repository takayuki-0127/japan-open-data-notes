"""06 ダッシュボード（HTML 1枚・外部ライブラリなし）を作り、画面の画像を残す"""
import pandas as pd, json
from pathlib import Path
B = Path(__file__).resolve().parents[1]; R = B/'results'
c = pd.read_csv(R/'C_monthly_contrib.csv'); c = c[c.ym>='2023-06'].round(2)
f = pd.read_csv(R/'G_calendar_effect_2026_2027.csv').round(2)
co = pd.read_csv(R/'A_coef_main.csv').round(2)
data = dict(hist=c.to_dict('records'), fut=f[['ym','業態','カレンダー寄与','d_n_sat','d_n_sun','d_n_hol_wd','d_n_renkyu','d_n_days']].to_dict('records'),
            coef=co[['業態','変数','係数','lo','hi']].to_dict('records'))
html = open(B/'dashboard/template.html', encoding='utf-8').read().replace('/*DATA*/', 'const DATA='+json.dumps(data, ensure_ascii=False)+';')
(B/'dashboard/index.html').write_text(html, encoding='utf-8'); print('ok', len(html))
