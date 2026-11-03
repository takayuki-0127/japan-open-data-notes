"""各 README から頑健性の節を取り出し、確かめた項目（表の行・箇条書き）に分け、
種類を辞書で分類し、キーワードと数値（区間）で「変わったか」を自動で判定する。
自動判定は手作業の判定（data/hand_labels.csv）と比べるためのもの。"""
import pathlib, os
HERE = pathlib.Path(__file__).resolve().parent.parent
os.chdir(HERE)
os.makedirs('data/interim', exist_ok=True)

# ---- 1. 頑健性の節を取り出す
import re,glob,os,json
out={}
for p in sorted(glob.glob('data/raw/readmes/*.md'),key=lambda x:int(re.search(r'F(\d+)',x).group(1))):
    fid=os.path.basename(p)[:-3]; t=open(p).read(); L=t.split('\n')
    sec=[];on=False;lvl=0
    for l in L:
        m=re.match(r'^(#+)\s',l)
        if m:
            if on and len(m.group(1))<=lvl: on=False
            if '頑健' in l or '感度' in l: on=True; lvl=len(m.group(1)); sec.append(l); continue
        if on: sec.append(l)
    extra=[l for l in L if ('頑健' in l) and l not in sec]
    out[fid]={'sec':'\n'.join(sec).strip(),'extra':'\n'.join(extra).strip()}
json.dump(out,open('data/interim/rob_raw.json','w'),ensure_ascii=False,indent=0)
import statistics
s=[len(v['sec'])+len(v['extra']) for v in out.values()]
#print(len(out),sum(s),statistics.median(s),sum(1 for v in out.values() if not v['sec']))

# ---- 2. 項目に分ける
import re,json
R=json.load(open('data/interim/rob_raw.json'))
items=[]
def cells(l): return [c.strip() for c in l.strip().strip('|').split('|')]
for fid,v in R.items():
    sec=v['sec']; src='sec'
    lines=sec.split('\n')[1:] if sec else []
    got=[]
    hdr=None
    for l in lines:
        s=l.strip()
        if not s: continue
        if s.startswith('|'):
            c=cells(s)
            if set(''.join(c))<=set('-: '): continue
            if hdr is None: hdr=c; continue
            got.append(('row',c[0],s))
        elif re.match(r'^[-*・]\s|^\d+[.)．]\s',s):
            got.append(('bul',re.sub(r'^[-*・\d.)．]+\s*','',s),s))
        elif s.startswith('#'): hdr=None; continue
        else:
            for x in re.split(r'(?<=。)',s):
                if len(x.strip())>8: got.append(('txt',x.strip(),x.strip()))
    if not got:
        src='extra'
        for l in v['extra'].split('\n'):
            s=l.strip()
            if not s: continue
            if s.startswith('|'):
                c=cells(s); s2=c[-1] if len(c)>1 else c[0]
            else: s2=re.sub(r'^[-*・]\s*','',s)
            got.append(('ext',s2,s))
    for k,(kind,label,full) in enumerate(got):
        items.append(dict(fid=fid.split('_')[0],folder=fid,k=k,kind=kind,label=label[:200],text=full[:600],src=src))
json.dump(items,open('data/interim/items.json','w'),ensure_ascii=False)
import collections
#print(len(items),collections.Counter(i['kind'] for i in items))
c=None #(min(c.values()),max(c.values()),len(c))

# ---- 3. 種類と自動判定
import re,json,collections
I=json.load(open('data/interim/items.json'))
BASE=re.compile(r'^\**(基本|主設定|ベース|本文|基準|元の|既定|base\b)')
TYPES=[
 ('プラセボ・並べ替え',r'プラセボ|並べ替え|偽の|ランダムに選び|置換|でたらめ'),
 ('検証の分け方',r'検証|交差|ブロック|分割|fold|ホールドアウト|起点|テスト期間|評価用'),
 ('期間・時期',r'期間|\d{4}年|年度|年以降|年まで|〜\d{4}|学習\s*\d|コロナ|延長|前半|後半|年代|時期'),
 ('対象を絞る・除く',r'人以上|以上$|以上（|除く|除外|だけ|のみ|限る|以上の|未満|外す|抜く|サンプル|標本'),
 ('定義・指標',r'あたり|にそろえ|粗く|近似|移動平均|処置を|項目|系列|対照|賃金|世帯|支給|で見る|で数える|物差し|含める|含めない|考えない|まとめる|向き|出発点|定義|指標|にする|に変え|入れ替|代わりに|別の|原数値|名目|実質|当たり|割合で|で測|対数|基準|水準'),
 ('変数・調整',r'使わない|入れない|なし$|FE|引く|共変量|特徴量|変数|ダミー|トレンド|固定効果|コントロール|調整|入れる|加える|足す|抜いた'),
 ('モデル・推定法',r'ブートストラップ|LWZ|X-13|管理限界|UMAP|HDBSCAN|TF-IDF|SVD|STL|マッチング|GCN|Rational|Matern|MICE|補完|分解|組み替え|仮定|モデル|ARIMA|SARIMA|LightGBM|GBM|回帰|推定|手法|OLS|ポアソン|ロジット|ベイズ|事前分布|カーネル|線形|ランダムフォレスト|GMM|PPML|DEA|IPF|クラスタ|k-means|ウォード|分布の形|辞書|埋め込み'),
 ('設定値・パラメータ',r'h\s*=|キャリパー|最近傍|1対\d|葉|深さ|seasonal|robust=|上位\d|下位\d|次元|因子\d|因子[一二三2-9]つ|状態|自由度|×\s*\d|[+\-−]\d+\s*%|初期を|階級|分位|正規化|平均の取り|幾何|算術|t分布|足し算|最小|最大|数を|の数|閾値|しきい|次数|ラグ|窓|帯域|バンド幅|倍率|重み|長さ|区分|ハイパー|k\s*=|\d+通り|乱数|シード'),
 ('データ源・集計単位',r'データ|出典|調査|集計|単位|市区町村|都道府県|地域|境界|隣接|隣'),
]
SAME=r'同じ|変わらな|変わりませ|ほぼ同じ|維持|残っ|残り|保た|一致|揺るが|安定|どれでも|すべてで|いずれも|ほとんど変わら|大きく変わらな|向きは同じ'
WEAK=r'0をまた�|有意でな|有意ではな|はっきりしな|弱ま|縮ん|小さくな|半分|動く|動いた|ばらつ|幅が|揺れ|左右され|変わり得|依存'
CHG=r'逆に|逆転|反転|符号|消え|入れ替わ|変わった|変わる|崩れ|成り立たな|結論が変|順位が変|なくなる|なくなった'
NUM=re.compile(r'([+\-−–]?\d+(?:\.\d+)?)\s*[（(]\s*([+\-−–]?\d+(?:\.\d+)?)\s*[〜~～,，]\s*([+\-−–]?\d+(?:\.\d+)?)')
def f(x): return float(x.replace('−','-').replace('–','-'))
def num_ci(text):
    m=NUM.search(text); 
    return (f(m.group(1)),f(m.group(2)),f(m.group(3))) if m else None
def firstnum(cells):
    for c in cells:
        m=re.search(r'[+\-−–]?\d+(?:\.\d+)?',c.replace(',',''))
        if m: return f(m.group(0))
    return None
def ttype(label,mode):
    if re.search(r'どの設定|どれでも|すべての(チェック|設定|条件)|いずれの|どの仮定|どのチェック|どの組み合わせ|どの条件',label): return ['まとめ（複数のチェック）']
    out=[t for t,p in TYPES if re.search(p,label)]
    return out or ['その他']
def classify(mode='main'):
    res=[]
    byf=collections.defaultdict(list)
    for it in I: byf[it['fid']].append(it)
    for fid,its in byf.items():
        rows=[i for i in its if i['kind']=='row']
        base=next((i for i in rows if BASE.search(i['label'])),rows[0] if rows else None)
        bci=num_ci(base['text']) if base else None
        bnum=firstnum([c for c in base['text'].strip('|').split('|')[1:]]) if base else None
        for it in its:
            lab=it['label']; txt=it['text']
            isbase = it['kind']=='row' and (it is base)
            if isbase or (it['kind']=='row' and BASE.search(lab)): continue
            if it['kind'] in('txt','ext') and not re.search(SAME+'|'+WEAK+'|'+CHG,txt): continue  # prose w/o judgement: skip
            o=None
            if re.search(CHG,txt): o='変わった'
            elif re.search(WEAK,txt): o='弱まる・動いた'
            elif re.search(SAME,txt): o='変わらない'
            if mode!='text' and o is None and it['kind']=='row':
                ci=num_ci(txt)
                if ci and bci:
                    v,lo,hi=ci; bv,blo,bhi=bci
                    bsig=(blo>0 or bhi<0); sig=(lo>0 or hi<0)
                    if v*bv<0 and abs(v)>1e-9 and abs(bv)>1e-9 and (sig or bsig): o='変わった'
                    elif bsig!=sig: o='弱まる・動いた'
                    else: o='変わらない'
                else:
                    v=firstnum(txt.strip('|').split('|')[1:])
                    if v is not None and bnum not in (None,0):
                        r=v/bnum
                        if r<0 and mode!='strict': o='変わった'
                        elif r<0: o='弱まる・動いた'
                        elif abs(r-1)>0.5: o='弱まる・動いた'
                        else: o='変わらない'
            if o is None: o='判定できない'
            if mode=='strict' and o=='弱まる・動いた' and not re.search(r'0をまたぐ|有意で|はっきりしな|消え|逆',txt) and it['kind']!='row': o='変わらない'
            tt=ttype(lab if it['kind']=='row' else txt,mode)
            res.append(dict(fid=fid,kind=it['kind'],label=lab[:120],types=tt,primary=tt[0],outcome=o))
    return res
if True:
    for mode in ['main','text','strict']:
        r=classify(mode); c=collections.Counter(x['outcome'] for x in r)
        print(mode,len(r),c)
    for mode in ['main','text','strict']:
        json.dump(classify(mode),open(f'data/interim/coded_{mode}.json','w'),ensure_ascii=False)
    r=classify('main'); print(collections.Counter(x['primary'] for x in r))
