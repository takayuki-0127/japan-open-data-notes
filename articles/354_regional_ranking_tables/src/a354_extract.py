"""354 地域を比べた記事で、順位の表はどれだけ載せていたか（④ 振り返り R109）— 原稿で地域の単位と順位の書き方を数える

使い方: python a354_extract.py <記事の md があるフォルダ> [<japan-open-data-notes のルート>]
  記事ごとに、地域の単位（都道府県・市区町村）と、順位の言葉・地域の名前つきの上位／下位の文・順位の表や図の説明があるかを数える。
  出すのは data/ranking_counts.csv（記事ごとの数）だけで、本文も地域の名前も出さない
"""
import re, sys, os, csv
from mdlib import load, clean, sentences, folder_like
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
PREF = "北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄".split()
PREF_RE = re.compile("|".join(sorted(PREF, key=len, reverse=True)))
# 市区町村らしい名前（○○市・○○町・○○村・○○区）。「都市」「市場」「地区」「町村」などの言葉は除く
MUNI_RE = re.compile(r"(?<![一-龥])[一-龥ヶケぁ-んァ-ヶ]{1,6}?(?<!都)(?<!各)(?<!同)(?<!全)(?<!地)(?<!政令)(?<!特別)(?<!市)(?<!区)(?<!の)(市|町|村|区)(?![場内民部分町村区街長役立営域制外議])")
RANKW = r"順位|ランキング|[0-9０-９]+位|上位|下位|トップ|ワースト|最下位"
TOP = r"最も(高|多|大き|長|速|早)|いちばん(高|多|大き|長|速|早)|一番(高|多|大き|長)|最高(?!気温|裁|記録)|最大(?!余震|クラス|限|で[0-9０-９]|[0-9０-９])|最多|(?<![0-9０-９])1位|首位|トップ|上位[0-9０-９]*"
BOT = r"最も(低|少な|小さ|短|遅)|いちばん(低|少な|小さ|短|遅)|一番(低|少な|小さ|短)|最低(?!賃金|限|気温)|最小(?!二乗|限|検出|[0-9０-９])|最少|最下位|ワースト|下位[0-9０-９]*|47位|(?<!より)(低い|少ない|小さい|短い|遅い)(のは|ほうから|順)|下から[0-9０-９]+"
def main(D):
    rows = []
    for i, title, lines in load(D):
        g = group_of(folder_like(i))
        if g is None:
            continue
        raw = "\n".join(lines); body = clean(lines); text = title + "\n" + "\n".join(body)
        S = [title] + sentences(body)
        prefs = set(PREF_RE.findall(text))
        r = dict(id=i, group=g, n_sent=len(S), n_pref_names=len(prefs), w_pref=len(re.findall(r"都道府県|47都道府県|各県|県ごと|県別|県の差", text)), w_muni=len(re.findall(r"市区町村|市町村", text)),
                 n_muni_names=len(set(m.group(0) for m in MUNI_RE.finditer(text))))
        r["rank_word"] = len(re.findall(RANKW, text)); r["title_rank_word"] = int(bool(re.search(RANKW, title)))
        tp = bp = tm = bm = 0
        for s in S:
            hp = bool(PREF_RE.search(s)); hm = bool(MUNI_RE.search(s)); t = bool(re.search(TOP, s)); b = bool(re.search(BOT, s))
            tp += hp and t; bp += hp and b; tm += hm and t and not hp; bm += hm and b and not hp
        r.update(top_pref=tp, bottom_pref=bp, top_muni=tm, bottom_muni=bm)
        r["title_top_named"] = int(bool((PREF_RE.search(title) or MUNI_RE.search(title)) and re.search(TOP, title)))
        r["title_bottom_named"] = int(bool((PREF_RE.search(title) or MUNI_RE.search(title)) and re.search(BOT, title)))
        # 順位の表：表の行のうち、1列目か2列目が順位（1, 2, 3… や 1位）で、地域の名前がある行が5行以上
        tb = [l for l in raw.split("\n") if l.strip().startswith("|")]
        rk = [l for l in tb if re.match(r"\|\s*(\d{1,2}位?|[０-９]{1,2}位?)\s*\|", l) and (PREF_RE.search(l) or MUNI_RE.search(l))]
        r["rank_table_rows"] = len(rk); r["place_table_rows"] = sum(1 for l in tb if PREF_RE.search(l) or MUNI_RE.search(l))
        # 図の説明に、順位・上位下位・47都道府県を並べた、と書いてあるか
        cap = [l for l in raw.split("\n") if re.match(r"\s*(図\s*[0-9０-９]+|［図|!\[)", l)]
        r["fig_rank_caption"] = sum(1 for l in cap if re.search(RANKW + r"|47都道府県|都道府県別|高い順|低い順|多い順|少ない順|並べ", l))
        rows.append(r)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    with open(os.path.join(OUT, "data", "ranking_counts.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "本")
    if len(sys.argv) > 2:  # README の表に、順位つきで地域を並べた行があるか
        from common import readmes, dedup
        rr = []
        for folder, t in dedup(readmes(sys.argv[2])):
            tb = [l for l in t.split("\n") if l.strip().startswith("|")]
            rk = [l for l in tb if re.match(r"\|\s*(\d{1,2}位?)\s*\|", l) and (PREF_RE.search(l) or MUNI_RE.search(l))]
            head = [l for l in tb if re.search(r"\|\s*順位\s*\|", l)]
            rr.append(dict(folder=folder, group=group_of(folder), rank_rows=len(rk), rank_header=len(head), place_rows=sum(1 for l in tb if PREF_RE.search(l) or MUNI_RE.search(l))))
        with open(os.path.join(OUT, "data", "readme_rank_tables.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rr[0].keys())); w.writeheader(); w.writerows(rr)
        print(len(rr), "README")
if __name__ == "__main__":
    main(sys.argv[1])
