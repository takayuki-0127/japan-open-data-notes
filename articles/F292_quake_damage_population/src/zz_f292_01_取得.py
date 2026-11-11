"""01 取得：一次資料の記録（md5 マニフェスト）。
取得はブラウザで手動（内閣府・社人研のサイトから）。PDF はリポジトリに含めず、md5 だけ残す。
- 内閣府 南海トラフ巨大地震 最大クラス地震における被害想定（2025年3月）
  saidai_01.pdf（被害の概要）/ saidai_02.pdf（都府県別の詳細）/ sanko_gaiyo.pdf（被害想定手法の概要）
  → pdftotext -layout でテキスト化したものを data/raw に置く
- 社人研 日本の地域別将来推計人口 2013年推計・2018年推計・2023年推計（都道府県別・年齢4区分）を f292_pop.csv に整理
"""
import hashlib, json, sys, pathlib
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PDF_MD5 = {  # 取得時に記録（PDF本体は data/raw に置かない）
    "f292_saidai_01.pdf": "f2e357036a1bd7fca1a52c79a19ede4e",
    "f292_saidai_02.pdf": "25193c8970c2339e219c8136e3363faf",
    "f292_sanko_gaiyo.pdf": "c5bbab77512e58a35109f28110914715",
}
URLS = {
    "f292_saidai_01.pdf": "https://www.bousai.go.jp/jishin/nankai/taisaku_wg_02/pdf/saidai_01.pdf",
    "f292_saidai_02.pdf": "https://www.bousai.go.jp/jishin/nankai/taisaku_wg_02/pdf/saidai_02.pdf",
    "f292_sanko_gaiyo.pdf": "https://www.bousai.go.jp/jishin/nankai/taisaku_wg_02/pdf/sanko_gaiyo.pdf",
}
man = {"pdf": {k: {"md5": v, "url": URLS[k]} for k, v in PDF_MD5.items()},
       "pop_source": "https://www.ipss.go.jp/pp-shicyoson/j/shicyoson23/t-page.asp（2018・2013年推計も同サイト）",
       "raw": {}}
for f in sorted((out / "data/raw").glob("f292_*")):
    man["raw"][f.name] = {"md5": hashlib.md5(f.read_bytes()).hexdigest(), "bytes": f.stat().st_size}
(out / "data/raw/MANIFEST.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n")
print(json.dumps(man["raw"], ensure_ascii=False))
