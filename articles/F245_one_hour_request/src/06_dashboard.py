import json, os
B=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R=json.load(open(f'{B}/results/main.json'))
c=R['C_comparisons']; g=R['C_gap_vs_chain']
rows=''.join(f"<tr><td>{k}</td><td>{v:+.1f}%</td><td>{g[k]:+.1f}pt</td></tr>" for k,v in c.items())
items=sorted(R['B_item_contrib'].items(),key=lambda x:-x[1])
irows=''.join(f"<tr><td>{k}</td><td>{v:+.2f}pt</td><td>{R['B_item_growth'][k]:+.1f}%</td></tr>" for k,v in items)
h=f"""<!doctype html><html lang="ja"><meta charset="utf-8"><title>8月の売上：1枚の答え（あおばドラッグ・架空）</title>
<style>body{{font-family:'Noto Sans CJK JP',sans-serif;margin:24px;color:#1f2933;background:#fff;width:1180px}}h1{{font-size:24px;margin:0 0 4px}}.sub{{color:#52606d;font-size:13px;margin-bottom:16px}}
.grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}.card{{border:1px solid #d9e2ec;border-radius:10px;padding:14px}}.k{{font-size:13px;color:#52606d}}.v{{font-size:30px;font-weight:700}}
.ans{{background:#f0f4f8;border-left:5px solid #2f6fb3;padding:12px 16px;margin:14px 0;font-size:15px;line-height:1.7}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #e4e7eb;padding:5px 6px;text-align:left}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.warn{{font-size:13px;color:#7b4f00;background:#fff8e6;padding:10px 14px;border-radius:8px;margin-top:12px;line-height:1.6}}</style>
<h1>8月の売上は「うちだけ」悪いのか：1枚の答え</h1><div class="sub">あおばドラッグ（架空の会社）本部向け／作成：依頼から1時間の枠で／業界の数字は経済産業省「商業動態統計」（ドラッグストア、全店ベース）。チェーンの数字は依頼文の架空の値</div>
<div class="grid"><div class="card"><div class="k">あおばドラッグ 8月 前年同月比（架空）</div><div class="v">{-1.0:+.1f}%</div></div>
<div class="card"><div class="k">業界 8月 前年同月比（全国／関東）</div><div class="v">{R['A_industry_aug_yoy']:+.1f}% ／ {R['A_region_aug_yoy']['関東']:+.1f}%</div></div>
<div class="card"><div class="k">業界の2026年の着地（見込み、前年比）</div><div class="v">{R['D_landing_main']:+.1f}%</div><div class="k">モデル・期間の幅 {R['D_landing']['SARIMA']['min']:+.1f}〜{R['D_landing']['季節ナイーブ']['max']:+.1f}%</div></div></div>
<div class="ans"><b>答え（いま言えること）</b>：業界は8月も伸びていて（全国 {R['A_industry_aug_yoy']:+.1f}%）、カレンダーと天気の影響はほぼ打ち消し合っている（{R['C_calendar']:+.2f}／{R['C_weather']:+.2f}pt）。品目の構成を合わせても、業界より <b>3〜4ポイント低い</b>。ただし業界の数字は店が増えた分を含む「全店」で、うちの既存店と同じ土俵ではない。<b>「うちだけ悪い」と言い切るには、既存店どうしで比べる必要がある</b>。</div>
<div class="two"><div class="card"><b>比べ方を変えた業界の8月</b><table><tr><th>比べ方</th><th>業界</th><th>うち−業界</th></tr>{rows}</table></div>
<div class="card"><b>業界の伸びの内訳（品目別の寄与）</b><table><tr><th>品目</th><th>寄与</th><th>伸び率</th></tr>{irows}</table></div></div>
<div class="warn">言えないこと：業界は全店ベース（新店の分を含む）／チェーンの数字は1社1か月で揺れが大きい（地域どうしの8月の前年比の標準偏差は年により2〜7ポイント）／品目構成は仮置き。<br>もう1日あれば：既存店の前年比、店舗別・品目別の内訳、客数×客単価の分解（F243）、来月以降の予測（F231）。</div></html>"""
open(f'{B}/dashboard/one_page_answer.html','w').write(h)
# 図6：HTML を撮影
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':1230,'height':900},device_scale_factor=1)
        pg.goto(f'file://{B}/dashboard/one_page_answer.html'); pg.wait_for_timeout(500); pg.screenshot(path=f'{B}/figures/fig6_one_page_answer.png',full_page=True); b.close()
except ImportError: print('playwright なし：図6は手で撮影')
