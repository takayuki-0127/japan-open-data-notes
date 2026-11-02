"""README の「データ」「出典」から元データ（統計の系列）を名寄せし、記事どうしの再利用をつなぐ"""
import re, json, os, csv
D = os.path.join(os.path.dirname(__file__), '..', 'data')
rows = json.load(open(os.path.join(D, 'readme_sections.json'), encoding='utf-8'))
# 元データの名寄せ（細かい区分）。粗い区分は2つめの値
DICT = [
 ('国勢調査', r'国勢調査', '人口'), ('人口動態統計', r'人口動態', '人口'), ('住民基本台帳人口移動報告', r'人口移動報告', '人口'),
 ('人口推計', r'人口推計(?!.*将来)', '人口'), ('将来推計人口（社人研）', r'将来推計人口', '人口'),
 ('人口統計資料集（社人研）', r'人口統計資料集', '人口'), ('日本版死亡データベース', r'死亡データベース|JMD', '人口'),
 ('生命表', r'生命表', '人口'),
 ('社会・人口統計体系', r'社会・人口統計体系|統計でみる市区町村|統計でみる都道府県', '地域統計'), ('SSDSE', r'SSDSE', '地域統計'),
 ('労働力調査', r'労働力調査', '労働'), ('地域別最低賃金', r'最低賃金', '労働'), ('賃金構造基本統計調査', r'賃金構造', '労働'),
 ('毎月勤労統計調査', r'毎月勤労', '労働'), ('一般職業紹介状況', r'職業紹介|職業安定業務', '労働'),
 ('新規学卒就職者の離職状況', r'離職状況', '労働'), ('就業構造基本調査', r'就業構造基本', '労働'),
 ('消費者物価指数', r'消費者物価', '物価・家計'), ('家計調査', r'家計調査', '物価・家計'), ('小売物価統計調査', r'小売物価', '物価・家計'),
 ('消費動向調査', r'消費動向調査', '物価・家計'), ('国民生活基礎調査', r'国民生活基礎調査', '物価・家計'),
 ('四半期別GDP速報', r'GDP速報|四半期別GDP|国民経済計算|GDP', '景気・マクロ'), ('県民経済計算', r'県民経済計算', '景気・マクロ'),
 ('景気動向指数・景気基準日付', r'景気動向指数|景気基準日付', '景気・マクロ'), ('景気ウォッチャー調査', r'景気ウォッチャー', '景気・マクロ'),
 ('日本銀行 時系列統計', r'日本銀行|日銀', '景気・マクロ'), ('財務省 国債金利', r'国債金利', '景気・マクロ'),
 ('鉱工業指数', r'鉱工業指数', '景気・マクロ'), ('産業連関表', r'産業連関', '景気・マクロ'), ('年次経済報告（経済白書）', r'年次経済', '景気・マクロ'),
 ('経済センサス', r'経済センサス', '産業・企業'), ('法人番号（国税庁）', r'法人番号', '産業・企業'), ('商業統計', r'商業統計', '産業・企業'),
 ('市町村税課税状況等の調', r'市町村税課税', '産業・企業'),
 ('宿泊旅行統計調査', r'宿泊旅行統計', '観光・エネルギー'), ('訪日外客・インバウンド消費', r'インバウンド|訪日外客', '観光・エネルギー'),
 ('電力 エリア需給実績', r'エリア(の)?需給', '観光・エネルギー'), ('石油製品の価格・統計', r'石油製品|資源・エネルギー統計', '観光・エネルギー'),
 ('気象庁 過去の気象データ', r'気象庁|アメダス|過去の気象', '地理・気象'), ('地価公示', r'地価公示', '地理・気象'),
 ('国土数値情報（行政区域）', r'行政区域|japan-topography', '地理・気象'), ('国土数値情報（駅・DID・消防署）', r'駅別乗降|人口集中地区|消防署', '地理・気象'),
 ('立地適正化計画の作成状況', r'立地適正化', '地理・気象'), ('OpenStreetMap・OSRM', r'OSRM|OpenStreetMap', '地理・気象'),
 ('地域保健・健康増進事業報告', r'地域保健', '健康・教育・行政'), ('感染症発生動向調査', r'感染症発生動向|IDWR', '健康・教育・行政'),
 ('全国学力・学習状況調査', r'学力・学習状況', '健康・教育・行政'), ('救急救助の現況', r'救急救助', '健康・教育・行政'),
 ('医療費（医療費の地域差分析など）', r'医療費の地域差|医療費', '健康・教育・行政'), ('保育所等関連状況', r'保育所等|待機児童', '健康・教育・行政'),
 ('国会会議録', r'国会会議録', 'テキスト'), ('e-Stat 統計表の一覧', r'統計データを探す|ファイル）一覧', 'テキスト'),
]
num = {r['article']: r['num'] for r in rows}
def match(text):
    out = []
    for name, pat, grp in DICT:
        if re.search(pat, text): out.append((name, grp))
    return out
edges, edges_src, reuse = [], [], []
for r in rows:
    a = r['article']
    for nm, g in match(r['data_sec'] + '\n' + r['src_sec']): edges.append((a, nm, g))
    for nm, g in match(r['src_sec']): edges_src.append((a, nm, g))
    # 記事どうしの再利用：コードが別記事のフォルダを読む（厳しめ）／README のデータ・出典で別記事に触れる（ゆるめ）
    code_refs = set(int(x) for x in re.findall(r'\bF(\d{1,3})_[A-Za-z]', r['code']))
    txt = '\n'.join(l for l in (r['data_sec'] + '\n' + r['src_sec']).split('\n') if not re.match(r'\s*-\s*関連', l))
    txt_refs = set(int(x) for x in re.findall(r'(?<![0-9A-Za-z])F(\d{1,3})(?![0-9])', txt))
    for k in sorted((code_refs | txt_refs) - {r['num']}):
        if k > 120 or k not in num.values(): continue
        reuse.append((f'F{k:02d}' if k < 100 else f'F{k}', a, int(k in code_refs), int(k in txt_refs)))
W = lambda fn, hdr, rs: csv.writer(open(os.path.join(D, fn), 'w', newline='', encoding='utf-8')).writerows([hdr] + sorted(set(rs)))
W('article_dataset.csv', ['article', 'dataset', 'group'], edges)
W('article_dataset_srconly.csv', ['article', 'dataset', 'group'], edges_src)
W('article_reuse.csv', ['from_article', 'to_article', 'in_code', 'in_readme'], reuse)
art = [(r['article'], r['num'], r['title'], r['data_bytes'], r["data_files"]) for r in rows]
W('articles.csv', ['article', 'num', 'title', 'data_bytes', 'data_files'], art)
# 再利用でつまずいた記述：別記事の番号と「ずれ・違い」系の語が同じ文にあるもの
TROUBLE = r'(違|ずれ|合わな|改定|改訂|基準|合併|定義|取り直|取得し直|足りな|そろえ|つなぎ|延長|欠け|不足|変更|置き換)'
iss = []
for r in rows:
    body = r['data_sec'] + '\n' + r['src_sec'] + '\n' + r['issue_sec']
    for s in re.split(r'(?<=[。\n])', body):
        refs = [int(x) for x in re.findall(r'(?<![0-9A-Za-z])F(\d{1,3})(?![0-9])', s) if int(x) != r['num']]
        if refs and re.search(TROUBLE, s) and not re.match(r'\s*-\s*関連', s):
            iss.append((r['article'], ','.join(f'F{x:02d}' for x in sorted(set(refs))), s.strip()[:220]))
W('reuse_issue_sentences.csv', ['article', 'refs', 'sentence'], iss)
unmatched = [r['article'] for r in rows if not match(r['data_sec'] + '\n' + r['src_sec'])]
json.dump({'unmatched_articles': unmatched}, open(os.path.join(D, 'unmatched.json'), 'w'), ensure_ascii=False)
print(len(set(edges)), len(set(edges_src)), len(set(reuse)), len(iss), 'unmatched', unmatched)
