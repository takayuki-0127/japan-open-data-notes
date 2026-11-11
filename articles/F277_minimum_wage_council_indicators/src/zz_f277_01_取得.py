"""F277 01 取得
- 日本銀行 短観（中小企業・全産業の業況判断DI・雇用人員判断DI）は API で取得（なければ取りに行く）。
- それ以外は、公表資料から写した小さな CSV を data/raw に置いている（出典は README と各 CSV）。
  * t4_rate.csv：賃金改定状況調査 第4表（産業計・男女計・ランク計）。各年の目安小委員会の議事録・資料から転記
  * jil_mw_weighted_avg.csv：地域別最低賃金の全国加重平均額（JILPT「早わかり グラフでみる長期労働統計」図3 の Excel から転記）
  * jil_springwage.csv：主要企業の春季賃上げ率（JILPT 図2、厚生労働省「民間主要企業春季賃上げ要求・妥結状況」）
  * cpi_ex_imputed_rent_monthly.csv：消費者物価指数 2020年基準 長期時系列の「持家の帰属家賃を除く総合」（F209 で e-Stat から取得した品目別ファイルの列を抜き出し）
  * mw_add_on_over_meyasu_2016_2025.csv：目安を上回った額（都道府県別、令和8年 第1回目安小委「主要統計資料」p.49 から転記）
- 最後に各ファイルの md5 を MANIFEST.json に書く。
"""
import os, json, hashlib, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
BOJ = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=CO"
       "&startDate=200201&endDate=202604&code=TK99F0000601GCQ03000,TK99F0000608GCQ03000")
p = os.path.join(RAW, "boj_tankan_sme.json")
if not os.path.exists(p):
    open(p, "wb").write(urllib.request.urlopen(BOJ, timeout=60).read())
man = {}
for f in sorted(os.listdir(RAW)):
    man[f] = hashlib.md5(open(os.path.join(RAW, f), "rb").read()).hexdigest()
man["_boj_api"] = BOJ
json.dump(man, open(os.path.join(RAW, "..", "MANIFEST.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(man, ensure_ascii=False, indent=1))
