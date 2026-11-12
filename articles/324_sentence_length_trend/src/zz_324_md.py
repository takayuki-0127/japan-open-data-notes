"""324 自分の文章は、読みやすくなったのか（④ 振り返り R104）— 原稿を数える

使い方: python zz_324_md.py <記事の md があるフォルダ> <出力の csv>
  ファイル名が「番号_」「F番号_」「T番号_」で始まる md を1本ずつ読み、文の統計だけを出す（本文そのものは出さない）。
  本文の文：題名・見出し・表・図の行・コード・出典・URL を除き、「。」「？」「！」で区切る。箇条書きは1項目を1つの段落として数える。5字未満は除く
"""
import re,sys,os,csv,statistics as st
D=sys.argv[1]; out=sys.argv[2]
rows=[]
for fn in sorted(os.listdir(D)):
    m=re.match(r'(F\d+|T\d+|\d{2,3})_.*\.md$',fn)
    if not m: continue
    t=open(os.path.join(D,fn),encoding='utf-8',errors='replace').read()
    lines=t.split('\n')
    title=''
    for i,l in enumerate(lines):
        if l.startswith('# '): title=l[2:].strip(); lines=lines[i+1:]; break
    body=[]; incode=False
    for l in lines:
        if l.strip().startswith('```'): incode=not incode; continue
        if incode: continue
        s=l.strip()
        if not s: body.append(''); continue
        if s.startswith('（note 下書き') or s.startswith('|') or s.startswith('［図') or s.startswith('![') or s.startswith('#') or s.startswith('<'): body.append(''); continue
        s=re.sub(r'https?://\S+','',s); s=re.sub(r'^[-・*]\s*','',s); s=re.sub(r'[*`]','',s)
        if s.startswith('出典') : body.append(''); continue
        body.append(s)
    paras=[]; cur=[]
    for s in body:
        if s=='':
            if cur: paras.append(cur); cur=[]
        else: cur.append(s)
    if cur: paras.append(cur)
    sents=[]; spp=[]
    for p in paras:
        n=0
        for s in p:
            for x in re.split(r'(?<=[。！？?])',s):
                x=x.strip()
                if len(x)>=5: sents.append(x); n+=1
        if n: spp.append(n)
    if len(sents)<5: continue
    L=[len(x) for x in sents]; txt=''.join(sents)
    NP=[len(re.sub(r'（[^（）]*）','',x)) for x in sents]; par=sum('（' in x for x in sents)/len(sents); sui=sum('推測' in x for x in sents)/len(sents)
    kan=len(re.findall(r'[一-鿿]',txt)); kata=len(re.findall(r'[゠-ヿ]',txt)); num=len(re.findall(r'[0-9０-９]',txt))
    comma=sum(x.count('、') for x in sents)
    rows.append([m.group(1),title,len(sents),st.median(L),round(st.mean(L),2),round(sum(l>60 for l in L)/len(L),4),round(sum(l>80 for l in L)/len(L),4),max(L),round(kan/len(txt),4),round(kata/len(txt),4),round(num/len(txt),4),round(comma/len(sents),3),st.median(spp),round(st.mean(spp),2),len(txt),int(os.path.getmtime(os.path.join(D,fn))),st.median(NP),round(par,4),round(sum(l>=100 for l in L)/len(L),4),round(sui,4)])
with open(out,'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow('id,title,n_sent,med_len,mean_len,share_gt60,share_gt80,max_len,kanji,katakana,digit,commas_per_sent,med_sent_per_para,mean_sent_per_para,chars,mtime,med_len_nopar,share_paren,share_ge100,share_suisoku'.split(',')); w.writerows(rows)
print(len(rows))
