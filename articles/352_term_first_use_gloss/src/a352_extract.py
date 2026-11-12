"""352 専門用語には、最初に一言の説明が付いているか（④ 振り返り R107）— 原稿で用語の初出を調べる

使い方: python a352_extract.py <記事の md があるフォルダ>
  50の用語それぞれについて、記事の本文で最初に出てくる所を探し、その場で説明が付いているかを機械で判定する。
  出すのは data/term_first_use.csv（記事の番号・用語・判定）だけで、本文は出さない。
  判定：paren＝直後のかっこで説明／swap＝ふつうの言葉が先で用語がかっこの中／toha＝「とは」「は、…です」「と呼ぶ」で説明／
        section＝「用語を先に」の節にある／next＝次の文がその用語の説明で始まる／none＝どれでもない
"""
import re, sys, os, csv
from mdlib import load, clean, folder_like
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
# (名前, 正規表現)。長い用語を先に探して印をつけ、短い用語（回帰・相関など）が中に入らないようにする
TERMS = [
    ("ロジスティック回帰", r"ロジスティック回帰"), ("ポアソン回帰", r"ポアソン回帰"), ("分位点回帰", r"分位点回帰"), ("回帰不連続", r"回帰不連続"), ("重回帰", r"重回帰"),
    ("差の差", r"(?<!誤)差の差"), ("合成コントロール", r"合成コントロール"), ("操作変数", r"操作変数"), ("傾向スコア", r"傾向スコア"), ("固定効果", r"固定効果"),
    ("交絡", r"交絡"), ("標準偏差", r"標準偏差"), ("標準誤差", r"標準誤差"), ("信頼区間", r"信頼区間"), ("p値", r"[pPｐ]\s?値"),
    ("有意", r"有意(?!義)"), ("相関係数", r"相関係数"), ("決定係数", r"決定係数|R²|R\^2"), ("残差", r"残差"), ("外れ値", r"外れ値"),
    ("中央値", r"中央値"), ("四分位", r"四分位"), ("分位点", r"分位点"), ("パーセンタイル", r"パーセンタイル"), ("対数", r"対数"),
    ("季節調整", r"季節調整"), ("移動平均", r"移動平均"), ("寄与度", r"寄与度"), ("弾力性", r"弾力性"), ("ジニ係数", r"ジニ係数"),
    ("多重共線性", r"多重共線性"), ("欠測", r"欠測"), ("ブートストラップ", r"ブートストラップ"), ("交差検証", r"交差検証|クロスバリデーション"), ("過学習", r"過学習"),
    ("正則化", r"正則化"), ("勾配ブースティング", r"勾配ブースティング"), ("ランダムフォレスト", r"ランダムフォレスト"), ("主成分分析", r"主成分分析"), ("クラスタリング", r"クラスタリング|クラスター分析"),
    ("ベイズ", r"ベイズ"), ("事後分布", r"事後分布"), ("自己相関", r"自己相関"), ("ARIMA", r"S?ARIMA"), ("状態空間", r"状態空間"),
    ("プラセボ", r"プラセボ"), ("RMSE", r"RMSE"), ("AUC", r"AUC"), ("頑健性", r"頑健性"), ("回帰", r"(?<!への)回帰"),
]
assert len(TERMS) == 50
HIRA = r"[ぁ-ん]"
def sent_bounds(text, a, b):
    s0 = max(text.rfind("。", 0, a), text.rfind("\n", 0, a)) + 1
    e = [x for x in (text.find("。", b), text.find("\n", b)) if x >= 0]
    return s0, (min(e) if e else len(text))
def judge(text, a, b, glossary, name=""):
    after = text[b:b + 90]; before = text[max(0, a - 40):a]
    # 1) 直後のかっこで説明：用語（…）。かっこの中にひらがながあり、数字で始まらず、「どうし・つき・のみ・だけ」で終わらない
    m = re.match(r"[」』]?[（(]([^）)]{4,})[）)]", after)
    if m:
        c = m.group(1)
        if re.search(HIRA, c) and not re.match(r"[0-9０-９pPｐ<＜±+\-−]", c) and not re.search(r"(どうし|つき|のみ|だけ)$", c):
            return "paren"
    # 2) ふつうの言葉が先で、用語がかっこの中：ばらつき（標準偏差）、誤差の大きさ（RMSE、…）。直前の8字に数字がある場合は値の注記とみなす
    if name != "対数" and re.search(r"[（(]$", before) and not re.search(r"[0-9０-９]", before[-9:-1]) and len(before.strip()) >= 3:
        if re.match(r"[^（()）]{0,6}[）)]", after) or re.match(r"[、，,]", after):
            return "swap"
    # 3) 文の中で説明：用語とは…／用語は、…です（数字のない文）／…を「用語」と呼ぶ
    s0, e1 = sent_bounds(text, a, b); rest = text[b:e1 + 1]
    if re.match(r"[」』]?(とは|というのは|と(呼び|呼ば|呼ん|いい|言い))", rest):
        return "toha"
    if re.match(r"[」』]?は、", rest) and not re.search(r"[0-9０-９]", rest) and re.search(r"(です|ます|こと|もの|方法|指標|ました)。?$", rest.strip()):
        return "toha"
    # 4) 「用語を先に」の節にある
    if glossary:
        return "section"
    # 5) 次の文が、その用語の説明で始まる（用語は、… ／ これは… ／ つまり…）
    nxt = text[e1 + 1:e1 + 90].lstrip(); n1 = re.split(r"[。\n]", nxt)[0]
    if re.match(r"これは|つまり|簡単に|かんたんに|言いかえ|要するに", nxt) or (re.match(re.escape(text[a:b]) + r"[」』]?(とは|は、)", nxt) and not re.search(r"[0-9０-９]", n1)):
        return "next"
    return "none"
def main(D):
    rows = []
    for i, title, lines in load(D):
        g = group_of(folder_like(i))
        if g is None:
            continue
        body = clean(lines, keep_heads=True)
        # 「用語を先に」などの節の中身
        gl, on = [], False
        for l in body:
            if l.startswith("#"):
                on = bool(re.search(r"用語", l)); continue
            if on:
                gl.append(l)
        gtext = "\n".join(gl)
        text = "\n".join(l for l in body if not l.startswith("#"))
        masked = text
        for name, pat in TERMS:
            m = re.search(pat, masked)
            if not m:
                continue
            n = len(re.findall(pat, masked))
            rows.append(dict(id=i, group=g, term=name, n=n, label=judge(text, m.start(), m.end(), bool(re.search(pat, gtext)), name)))
            masked = re.sub(pat, lambda mm: "■" * len(mm.group(0)), masked)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    with open(os.path.join(OUT, "data", "term_first_use.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "行（記事×用語）", len({r["id"] for r in rows}), "本")
if __name__ == "__main__":
    main(sys.argv[1])
