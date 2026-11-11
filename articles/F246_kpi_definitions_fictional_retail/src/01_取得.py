"""01 取得：このフォルダで使う公開データは、すでにリポジトリにある3つのファイルの写し（新しい取得はしない）。
- data/raw/sales_monthly_6types.csv : 経済産業省「商業動態統計」業態別販売額（F231 の data/ から。スーパーの月次の動きだけを使う）
- data/raw/calendar_daily.csv.gz     : 曜日・祝日・連休の日付表（F233 の data/ から。内閣府「国民の祝日」をもとに作成）
- data/raw/kakei_items.csv           : 総務省「家計調査」品目別の価格（F243 の data/ から。食品の値段の上がり方の目安だけを使う）
架空の会社「サンプルマート（架空）」の数字は、02_整形.py がこの3つの動きをもとに合成する。
"""
import pathlib, hashlib
R = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
for f in sorted(R.iterdir()):
    print(f.name, f.stat().st_size, hashlib.md5(f.read_bytes()).hexdigest())
