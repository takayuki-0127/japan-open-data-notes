"""F267 01 取得
日本フランチャイズチェーン協会「コンビニエンスストア統計調査」の月次の時系列表（PDF 2つ）は、
https://www.jfa-fc.or.jp/particle/320.html からブラウザで取得して data/raw/ に置いた
（このサイトはスクリプトからの直接取得を受け付けないため）。
  - jfa_cvs_monthly_2005_2016.pdf  (https://www.jfa-fc.or.jp/folder/1/img/20230120114232.pdf)
  - jfa_cvs_monthly_2017_2025.pdf  (https://www.jfa-fc.or.jp/folder/1/img/20260120121230.pdf)
商業動態統計（コンビニ販売額）は F231、消費者物価指数は F209 のデータの写し。
このスクリプトはファイルがそろっているかと大きさだけを確かめる。
"""
import hashlib, pathlib, sys
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
need = ["jfa_cvs_monthly_2005_2016.pdf", "jfa_cvs_monthly_2017_2025.pdf",
        "meti_sales_monthly_6types.csv", "cpi_gs_monthly.csv", "cpi_gs_meta.csv"]
ok = True
for n in need:
    p = RAW / n
    if not p.exists():
        print("missing", n); ok = False; continue
    print(n, p.stat().st_size, hashlib.md5(p.read_bytes()).hexdigest())
sys.exit(0 if ok else 1)
