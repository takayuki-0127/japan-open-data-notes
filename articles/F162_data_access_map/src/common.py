"""共通：記事フォルダの読み込み、出どころ（作り手）と取得経路の辞書"""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"

# 統計の作り手（公表元）。行の中に名前・統計名・ドメインが出たら、その作り手の行とみなす
OWNERS = [
 ("総務省統計局", r"統計局|(?<!e-)stat\.go\.jp|国勢調査|労働力調査|家計調査|消費者物価|住宅・土地統計|就業構造基本調査|経済センサス|人口推計|住民基本台帳人口移動|社会・人口統計体系|統計でみる(市区町村|都道府県)|ssdsview|SSDSE|統計センター|nstac|小売物価|社会生活基本調査|全国家計構造調査|個人企業経済調査|科学技術研究調査|サービス産業動向|家計消費状況"),
 ("厚生労働省", r"厚生労働省|厚労省|mhlw\.go\.jp|人口動態|毎月勤労統計|賃金構造基本統計|一般職業紹介|国民生活基礎調査|医療施設|介護保険事業|NDB|患者調査|雇用動向|就労条件|最低賃金|生命表|衛生行政|福祉行政|社会福祉施設|保育所等関連"),
 ("内閣府", r"内閣府|cao\.go\.jp|国民経済計算|GDP 速報|GDP速報|四半期別GDP|県民経済計算|景気ウォッチャー|景気動向指数|消費動向調査|ESRI"),
 ("日本銀行", r"日本銀行|日銀|boj\.or\.jp|短観|企業物価|資金循環"),
 ("気象庁", r"気象庁|jma\.go\.jp|過去の気象データ|アメダス|AMeDAS"),
 ("国土交通省", r"国土交通省|国交省|mlit\.go\.jp|国土数値情報|地価公示|地価調査|不動産情報ライブラリ|reinfolib|建築着工|住宅着工|駅別乗降|旅客地域流動|鉄道輸送|自動車輸送|宿泊旅行統計|観光庁"),
 ("経済産業省", r"経済産業省|経産省|meti\.go\.jp|鉱工業|商業動態|資源エネルギー庁|enecho|FIT|固定価格買取|工業統計|特定サービス産業|電力調査統計|特許庁|jpo\.go\.jp|中小企業庁"),
 ("社人研", r"社人研|国立社会保障・人口問題研究所|ipss\.go\.jp|将来推計人口|出生動向基本調査"),
 ("環境省", r"環境省|env\.go\.jp|一般廃棄物|WBGT|暑さ指数|大気汚染物質"),
 ("国税庁", r"国税庁|法人番号|houjin-bangou|nta\.go\.jp|民間給与実態"),
 ("文部科学省", r"文部科学省|文科省|mext\.go\.jp|学校基本調査|学力・学習状況|全国学力|国立教育政策研究所|nier\.go\.jp|学校保健統計|子供の学習費"),
 ("警察庁・消防庁", r"警察庁|npa\.go\.jp|消防庁|fdma\.go\.jp|救急搬送|熱中症による救急|交通事故統計"),
 ("農林水産省", r"農林水産省|農水省|maff\.go\.jp|林野庁|農林業センサス|漁業・養殖業|作物統計|木材需給|森林資源"),
 ("財務省・税関", r"財務省|mof\.go\.jp|貿易統計|税関|customs\.go\.jp|国債金利|法人企業統計"),
 ("電力会社", r"東京電力|tepco|関西電力|kansai-td|エリア需給|電力需給実績|でんき予報|OCCTO|電力広域"),
 ("国立国会図書館", r"国立国会図書館|国会会議録|kokkai\.ndl|warp\.ndl"),
 ("感染症の機関", r"感染症|id-info|jihs|niid|IDWR"),
 ("国際機関・海外", r"IMF|国際通貨基金|世界銀行|World Bank|worldbank|Comtrade|OECD|FRED|stlouisfed|World Development"),
 ("地方自治体", r"metro\.tokyo|\.lg\.jp|都庁|オープンデータカタログ|(?<![閣省庁局])(都|道|府|県|市)「"),
 ("総務省（統計局以外）", r"soumu\.go\.jp|地方財政|決算カード|市町村別決算|ふるさと納税|ふるさと納税に関する現況|住民基本台帳に基づく人口|情報通信白書|通信利用動向|地方公営企業"),
 ("その他の公的機関", r"JNTO|日本政府観光局|日本郵便|japanpost|労働政策研究|\bJIL\b|jil\.go\.jp|デジタル庁|人事院|会計検査院"),
]
# 経路（取り方）。行の中の URL・data/raw のファイル名・言葉から判定する（1行に複数あってよい）
URL = r"https?://[^\s)）」>|`'\"]+"
RAWP = r"data/raw/[^\s)）|`'\"]+"
ROUTE_ORDER = ["API", "表ファイル", "一括ファイル", "Webページの表", "画面操作", "PDF", "手で転記", "_page"]
NOT_API = r"(API|appId|アプリケーションID)[^。]{0,40}(使わ|要る|必要|登録)"
def routes_of(t):
    r = set()
    urls = re.findall(URL, t); raws = re.findall(RAWP, t)
    for u in urls:
        ul = u.lower()
        if re.search(r"/api(/|\b)|^https?://api\.|comtradeapi|datamapper/api|getstats", ul): r.add("API")
        elif re.search(r"\.(xlsx?|csv|txt|tsv)(\?|$)|file-download|statinfid|stat-search/files", ul): r.add("表ファイル")
        elif re.search(r"\.(zip|shp|geojson|topojson|gml|kml)(\?|$)|nlftp\.mlit", ul): r.add("一括ファイル")
        elif re.search(r"\.pdf(\?|$)", ul): r.add("PDF")
        elif re.search(r"\.(php|asp|aspx|cgi)\?|view/|ssdsview", ul): r.add("Webページの表")
        elif re.search(r"\.(html?|asp|aspx|php)$|/$", ul): r.add("_page")
    for p in raws:
        pl = p.lower()
        if re.search(r"\.(xlsx?|csv|txt|tsv)(\.gz)?$", pl): r.add("表ファイル")
        elif re.search(r"\.(zip|shp|geojson|topojson|gpkg)$", pl): r.add("一括ファイル")
        elif pl.endswith(".pdf"): r.add("PDF")
        elif re.search(r"\.jsonl?(\.gz)?$", pl) and re.search(r"API|api", t): r.add("API")
    if re.search(r"\bAPI\b|検索用API", t) and not re.search(NOT_API, t): r.add("API")
    if re.search(r"Excel|エクセル|SheetJS|\.xlsx?\b|（XLSX?）|\bXLSX?\b|statInfId|file-download|stat-search/files", t): r.add("表ファイル")
    if re.search(r"[\w\-]+\.csv\b", t) and re.search(r"元の|元データ|ダウンロード|公開|取得", t): r.add("表ファイル")
    if re.search(r"CSV ?(ファイル|形式|で(ダウンロード|公開|取得))|ダウンロードした CSV|の CSV", t): r.add("表ファイル")
    if re.search(r"ZIP|\bzip|[\w\-]+\.zip\b|一括ダウンロード|全件データ|シェープ|国土数値情報", t): r.add("一括ファイル")
    if re.search(r"api_get_result|開発者ツール|コンソール|検索画面|ダウンロード画面|条件を(選|指定)|画面で一度|画面から|ブラウザで(実行|開)|ブラウザの(中|ページ)|ページ上で|ページ内で|dbview|データベース（DB）|in-page|IndexedDB|を選んで(ダウンロード|出力)|ブラウザで取得", t): r.add("画面操作")
    if re.search(r"read_html|ページの表|HTML の表|表示された表", t): r.add("Webページの表")
    if re.search(r"PDF", t): r.add("PDF")
    if re.search(r"書き写|転記|手入力|手で(入力|写)|図表の数値", t): r.add("手で転記")
    return sorted(r, key=ROUTE_ORDER.index)
REUSE = r"F\d{1,3}[^。]{0,40}(README|を参照|の加工|を加工|と同じ|で(作|整|取)っ|で取り込み済み|で作成|で取得|から作っ|から(写|整え|取り直)|を再利用|を使い回)|(F\d{1,3}|記事 ?\d{3}|\b\d{3}\b)( ?・ ?F?\d{1,3})*( ?の| ?で| ?と| ?から| ?を)(同じ|取得|整え|作っ|使っ|写|取り込|フォルダ|データ|表|特徴量|パネル|予測)|使い回|新しく(は)?(取得|取っ)|新しい(データの)?取得はな|新規の取得はな|取得済み|コピーして|写す|写した|再利用|同梱済み"
SECT = r"データ|取得|出典|再現|動かし方|Data|Source"

COUNT_LINE = r"\|\s*\d+\s*本\s*\||\d+本の記事"   # 記事の本数を数えた表（メタ記事）は出どころの記録ではない

def article_text(folder: Path):
    """README のデータ・出典・再現手順などの節と、src の取得用ファイル・data の説明を、行のリストで返す"""
    lines = []
    rd = folder / "README.md"
    if rd.exists():
        keep = False
        for l in rd.read_text(encoding="utf-8", errors="ignore").splitlines():
            if re.match(r"#{2,6} ", l):
                keep = bool(re.search(SECT, l))
                continue
            if (keep or re.match(r"\W{0,3}出典", l)) and l.strip() and not re.search(COUNT_LINE, l):
                lines.append(("README", l))
    src = folder / "src"
    if src.exists():
        for f in sorted(src.iterdir()):
            n = f.name
            if re.match(r"(0?1[_-]|fetch|get_|download|取得)", n) or n.endswith(".md"):
                for l in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if l.strip():
                        lines.append(("src/" + n, l))
    for f in sorted((folder / "data").rglob("*.md")) if (folder / "data").exists() else []:
        for l in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if l.strip():
                lines.append(("data/" + f.name, l))
    return lines
