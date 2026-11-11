"""README から「公的データで困ったこと」の手がかりになる行を取り出す。
使い方: python a241_01_extract.py <japan-open-data-notes を clone したフォルダ>
（2026-11-12 時点のコミット 996936a の README 501本で作成）
"""
import sys, re, csv, os
from common import readmes, group_of

CATS = {
    "定義・分類・数え方の変更": r"定義が変わ|定義の変更|定義変更|分類の変更|分類が変わ|数え方の変更|数え方が変わ|表の形が違|段差を|段差が|接続係数",
    "改訂（速報と確報・遡及）": r"改訂(され|後|前|で)|遡及(して|改訂|集計)|速報(値)?と確報|確報で|書き換わ|改定され",
    "欠測・秘匿・非公表": r"欠測|欠損|秘匿|非公表|公表されていない|空欄|欠けて",
    "PDFや資料からの手での転記": r"(PDF|画像)(だけ|から|の表|しか)|転記|書き起こ|手で写|手入力|目で読",
    "取れない・代わりのデータ": r"取れな|取得できな|入手できな|手に入らな|ダウンロードできな|見つからず|代わりに使|代用|代替データ|公開されていな",
    "市町村合併・境界の変更": r"市町村合併|市区町村合併|合併が続|合併前|合併後|境界(が|の)変|境域",
    "暦年と年度・時点のずれ": r"暦年(換算|に|と年度|の値)|年度と暦年|時点の違|時点がずれ|暦年 t",
    "丸め・桁": r"桁ずれ|丸め(の|で)(誤差|範囲|幅)|公表値の丸め|印刷(合計|された合計)|単位が(違|異な)",
}

repo = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
data = os.path.join(here, "..", "data")
idx, rows = [], []
for folder, text in readmes(repo):
    idx.append([folder, group_of(folder), len(text)])
    for ln in text.split("\n"):
        s = ln.strip()
        if not s or "http" in s or s.startswith("#"):
            continue  # リンクの行（出典の PDF など）と見出しは数えない
        for c, pat in CATS.items():
            if re.search(pat, s):
                rows.append([folder, group_of(folder), c, s[:240]])
with open(os.path.join(data, "readme_index.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["folder", "group", "n_chars"]); w.writerows(idx)
with open(os.path.join(data, "trouble_lines.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["folder", "group", "category", "line"]); w.writerows(rows)
print(len(idx), "READMEs,", len(rows), "matched lines")
