"""01 取得：このリポジトリの別の記事で取得済みの生データを、GitHub から取り直して data/raw/ に置く。

- 消費者物価指数（2020年基準、中分類、全国・月次・原数値）… F12 が e-Stat から取得した cpi.csv
- 景気動向指数の個別系列ほか（月次）… F13/F18 が内閣府の景気動向指数の Excel から作った monthly_levels.csv
- 家計調査（二人以上の世帯、小分類の1世帯あたり支出額・月次）… F11 が e-Stat の長期時系列表から作った kakei_monthly_long.csv（30品目だけ抜き出す）
元の統計の出典は README を参照。
"""
from pathlib import Path
import io, urllib.request
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
ITEMS = ['米', 'パン', '麺類', '生鮮魚介', '生鮮肉', '牛乳', '卵', '生鮮野菜', '生鮮果物', '菓子類', '主食的調理食品', '酒類', '一般外食',
         '電気代', 'ガス代', '上下水道料', '家事用耐久財', '冷暖房用器具', '洋服', '医薬品', '保健医療サービス', '自動車等購入',
         '自動車等維持', '通信', '授業料等', '教養娯楽用耐久財', '宿泊料', 'パック旅行費', '理美容サービス', 'たばこ']


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "cpi_chuubunrui.csv").write_bytes(get("F12_stats_pipeline/data/raw/cpi.csv"))
    (RAW / "ci_monthly_levels.csv").write_bytes(get("F18_nowcast_dfm/data/monthly_levels.csv"))
    k = pd.read_csv(io.BytesIO(get("F11_tax_hike_event/data/kakei_monthly_long.csv")))
    k[k.item.isin(ITEMS)][["date", "no", "item", "amount"]].to_csv(RAW / "kakei_items.csv", index=False)
    print("ok")


if __name__ == "__main__":
    main()
