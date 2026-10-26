"""02 整形：3つの統計から月次の98系列を作り、前月からの変化にそろえる → data/changes.csv, data/series_list.csv"""
from pathlib import Path
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).parent))
from detect import to_change

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
START, END = "2005-01-01", "2026-08-01"

CPI = ['穀類', '魚介類', '肉類', '乳卵類', '野菜・海藻', '果物', '油脂・調味料', '菓子類', '調理食品', '飲料', '酒類', '外食',
       '家賃', '設備修繕・維持', '電気代', 'ガス代', '他の光熱', '上下水道料', '家庭用耐久財', '室内装備品', '寝具類', '家事雑貨',
       '家事用消耗品', '家事サービス', '和服', '洋服', 'シャツ・セーター・下着類', '履物類', '他の被服', '被服関連サービス',
       '医薬品・健康保持用摂取品', '保健医療用品・器具', '保健医療サービス', '交通', '自動車等関係費', '通信', '授業料等',
       '教科書・学習参考教材', '補習教育', '教養娯楽用耐久財', '教養娯楽用品', '書籍・他の印刷物', '教養娯楽サービス',
       '理美容サービス', '理美容用品', '身の回り用品', 'たばこ', '他の諸雑費']
RATE_CI = {'小売販売額（前年比）', '卸売販売額（前年比）', 'マネーストック（前年比）', '長期金利', '完全失業率', '有効求人倍率'}


def main():
    cols, meta = {}, []
    # 消費者物価指数（2020年基準、原数値）
    c = pd.read_csv(RAW / "cpi_chuubunrui.csv", header=None, dtype=str)
    head = c.iloc[0].tolist()
    body = c[c[0].str.fullmatch(r"\d{6}", na=False)]
    idx = pd.to_datetime(body[0], format="%Y%m")
    for name in CPI:
        j = head.index(name)
        s = pd.Series(pd.to_numeric(body[j], errors="coerce").values, index=idx)
        key = f"物価:{name}"
        cols[key] = to_change(s, "log")
        meta.append((key, "消費者物価指数", name, "対数差"))
    # 景気動向指数の個別系列ほか（F18 と同じ、季節調整済みの系列を含む）
    ci = pd.read_csv(RAW / "ci_monthly_levels.csv", parse_dates=["month"]).set_index("month")
    for name in ci.columns:
        kind = "diff" if name in RATE_CI else "log"
        key = f"景気:{name}"
        cols[key] = to_change(ci[name], kind)
        meta.append((key, "景気動向指数の個別系列", name, "差" if kind == "diff" else "対数差"))
    # 家計調査（二人以上の世帯、1世帯あたり支出額・名目）
    k = pd.read_csv(RAW / "kakei_items.csv")
    k["date"] = pd.to_datetime(k["date"])
    for name, g in k.groupby("item", sort=False):
        s = g.set_index("date")["amount"]
        key = f"家計:{name}"
        cols[key] = to_change(s, "log")
        meta.append((key, "家計調査", name, "対数差"))
    df = pd.DataFrame(cols).loc[START:END]
    df.index.name = "month"
    df.to_csv(ROOT / "data" / "changes.csv", float_format="%.5f")
    pd.DataFrame(meta, columns=["key", "source", "name", "transform"]).to_csv(ROOT / "data" / "series_list.csv", index=False)
    print(df.shape, "欠測の多い系列:", df.isna().sum().sort_values().tail(3).to_dict())


if __name__ == "__main__":
    main()
