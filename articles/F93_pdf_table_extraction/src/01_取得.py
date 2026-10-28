"""PDF の取得の記録と確認。
4つの PDF は Chrome のページ上で fetch して保存した（このコンテナから官公庁のサイトに直接つながらないため）。
  T1 学歴別   https://www.mhlw.go.jp/content/11800000/001318985.pdf
  T2 産業別   https://www.mhlw.go.jp/content/11800000/001319024.pdf （大学）
  T3 規模別   https://www.mhlw.go.jp/content/11800000/001319018.pdf （大学）
  T4 段差     https://www.stat.go.jp/data/roudou/pdf/10.pdf （3ページ目の（参考１））
正解の表は、F07・F66 で同じ PDF から作り、検算を通した CSV（data/raw/*.csv）を使う。
ここではファイルの存在とハッシュ、ページ数を確かめるだけ。"""
import hashlib, pypdf
from common import *
SHA = {"mhlw_education.pdf": "3d21fb0a", "mhlw_industry_univ.pdf": "91bc1526", "mhlw_size_univ.pdf": "2af2a3d2", "stat_lfs_method.pdf": "e4566454"}
for f, h in SHA.items():
    b = (RAW / f).read_bytes()
    got = hashlib.sha256(b).hexdigest()[:8]
    print(f, len(b), "bytes", len(pypdf.PdfReader(RAW / f).pages), "pages", "sha256", got, "OK" if got == h else "（公表元で差し替えられた可能性）")
