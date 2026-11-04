import pymupdf,re,sys,json,collections
PREF="北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄".split()
W=sys.argv[1]
out={}
def rows(doc):
    global BK
    for p in doc:
        ws=p.get_text("words")
        g=collections.defaultdict(list)
        for w in ws: g[round((w[1]+w[3])/2/BK)].append(w)
        for k in sorted(g):
            yield " ".join(w[4] for w in sorted(g[k],key=lambda w:w[0]))
for y in range(2005,2027):
  res={}
  for BK in (3,5,2,7):
    doc=pymupdf.open(f"{W}/pdf/{y}.pdf")
    for line in rows(doc):
        s=line.replace("　"," ")
        z=re.sub(r"(?<=[^\x00-\x7f]) +(?=[^\x00-\x7f])","",s)
        for pf in PREF:
            m=re.search(r"(?:^|[\s\d])"+pf+r"(?:都|道|府|県)?(?=\s|\d|$)",z)
            if not m: continue
            if pf=="京都" and "東京都" in z: continue
            nums=re.findall(r"\d{1,3}(?:,\d{3})+|\d+\.\d+",z[m.end():])
            ints=[int(n.replace(",","")) for n in nums if "," in n]; decs=[float(n) for n in nums if "." in n]
            if len(ints)>=2 and decs:
                r=decs[0]; a,b=ints[0],ints[1]
                if abs(a/b-r)<0.002: cars,hh=a,b
                elif abs(b/a-r)<0.002: cars,hh=b,a
                else: continue
                res.setdefault(pf,(cars,hh,r))
  out[y]=res
  print(y,len(res),[p for p in PREF if p not in res][:5])
json.dump(out,open(f"{W}/an/pref_raw.json","w"),ensure_ascii=False)
