"""351 出典には、統計の名前・表の番号・取得日がそろっているか（④ 振り返り R106）— README から要素を拾う

使い方: python a351_extract.py <japan-open-data-notes のルート>
  articles/*/README.md を読み、「出典」の見出しの節（と README 全体）に要素があるかどうかを、記事ごとに 0/1 で
  data/source_elements.csv に出す。README の本文は出さない。
  初期の記事で同じ README の本文を共有しているものは、最初の1本だけを数える（common.dedup）
"""
import re, sys, os, csv
from common import readmes, group_of, dedup, section
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
DATE = r"\d{4}\s*[年/\-.]\s*\d{1,2}(\s*[月/\-.]\s*\d{1,2}\s*日?)?"
PAT = {
    # だれが出したか
    "publisher": r"省|庁|統計局|統計センター|日本銀行|日銀|協会|機構|研究所|委員会|連合会|財団|協議会|内閣府|OECD|World Bank|世界銀行|Kaggle|UCI|国連|取引所",
    # 統計・資料の名前（かぎかっこで書いたもの）
    "stat_name": r"「[^」]{2,60}」|『[^』]{2,60}』",
    # どの表か（表の番号、統計表の ID、系列のコード）
    "table_id": r"第\s*[0-9０-９]+[-‐–の]?[0-9０-９]*\s*表|(?<![図の])表\s*[0-9０-９]+[-‐–]?[0-9０-９]*(?![つ本枚個])|統計表\s*ID|statInfId|statsDataId|表番号|時系列コード|系列コード|Table\s*[0-9]+",
    "url": r"https?://",
    # URL の外に書いた 9〜12桁の番号（e-Stat の統計表の番号など）
    "long_id": r"(?<![0-9])[0-9]{9,12}(?![0-9])",
    # いつ取ったか
    "fetch_date": r"(取得|アクセス|ダウンロード|閲覧)(日|は|：|:|、|（|\(|\s){0,4}" + DATE + r"(?!\s*[〜～])(?![^\n。]{0,4}公表)|" + DATE + r"\s*(に|、|\s)?(取得|アクセス|ダウンロード|閲覧)",
    # どの年・期間の数字か
    "period": r"\d{4}\s*年?度?\s*[〜～–\-]\s*\d{4}|\d{4}\s*年度?(分|調査|版|平均|確報|確定)|(令和|平成|昭和)\s*[0-9０-９元]+\s*年",
    # 使い方の決まり（加工して作成、利用規約、ライセンス）
    "terms": r"利用規約|ライセンス|License|CC[ -]?BY|加工して作成|PDL",
}
def main(repo):
    rows = []
    for folder, t in dedup(readmes(repo)):
        secs = section(t, r"出典"); src = "\n".join(secs)
        r = dict(folder=folder, group=group_of(folder), has_section=int(bool(secs)), chars=len(src.strip()))
        nourl = lambda x: re.sub(r"https?://[^\s）)|]+", " ", x)
        for k, p in PAT.items():
            r[k] = int(bool(re.search(p, nourl(src) if k == "long_id" else src)))
        r["table_id"] = int(r["table_id"] or r.pop("long_id")); r.pop("long_id", None)
        r["url_estat_list"] = int(bool(re.search(r"e-stat\.go\.jp/[^\s）)]*toukei=", src)))
        r["url_top_only"] = int(bool(re.search(r"https?://[^/\s）)]+/?[\s）)]", src + " ")) and not re.search(r"https?://[^/\s）)]+/[^\s）)]{3,}", src))
        r["fetch_date_anywhere"] = int(bool(re.search(PAT["fetch_date"], t)))
        r["table_id_anywhere"] = int(bool(re.search(PAT["table_id"], t) or re.search(PAT["long_id"], nourl(t))))
        rows.append(r)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    with open(os.path.join(OUT, "data", "source_elements.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "README")
if __name__ == "__main__":
    main(sys.argv[1])
