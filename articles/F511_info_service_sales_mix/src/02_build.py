"""Excel の「年・実数」「年・伸び率」「年度・実数」「年度・伸び率」から、長い表を作る。
data/annual.csv：period_type（年・年度）、year、item、value（百万円）、growth（調整済み前年比、%）。"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "tokusabi_info_service_long.xls"
ITEMS = {
    "売上高|合計": "total", "ソフトウェア開発、プログラム作成|合計": "software_total",
    "ソフトウェア開発、プログラム作成|受注ソフトウェア": "custom",
    "ソフトウェア開発、プログラム作成|受注ソフトウェアのうちシステムインテグレーション(SI)": "custom_si",
    "ソフトウェア開発、プログラム作成|ソフトウェアプロダクツ": "products",
    "ソフトウェア開発、プログラム作成|ソフトウェアプロダクツのうちゲームソフト": "products_game",
    "計算事務等情報処理|計算事務等情報処理": "processing", "計算事務等情報処理|オンライン": "processing_online",
    "計算事務等情報処理|オフライン": "processing_offline", "キーパンチ等データ書き込み|キーパンチ等データ書き込み": "keypunch",
    "システム等管理運営受託|システム等管理運営受託": "sys_mgmt", "情報提供、各種調査、その他|情報提供、各種調査、その他": "info_other",
}


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def read(sheet):
    d = pd.read_excel(RAW, sheet_name=sheet, header=None)
    keys = [f"{d.iloc[1, j]}|{d.iloc[2, j]}" for j in range(d.shape[1])]
    cols = {ITEMS[k]: j for j, k in enumerate(keys) if k in ITEMS}
    assert len(cols) == len(ITEMS), cols
    out = []
    for i in range(len(d)):
        m = re.fullmatch(r"(\d{4})年度?", str(d.iloc[i, 1]).strip())
        if not m:
            continue
        for it, j in cols.items():
            out.append((int(m.group(1)), it, num(d.iloc[i, j])))
    return pd.DataFrame(out, columns=["year", "item", "v"])


def main():
    parts = []
    for ptype, a, g in [("年", "年・実数", "年・伸び率"), ("年度", "年度・実数", "年度・伸び率")]:
        x = read(a).rename(columns={"v": "value"})
        y = read(g).rename(columns={"v": "growth"})
        z = x.merge(y, on=["year", "item"], how="left")
        z.insert(0, "period_type", ptype)
        parts.append(z)
    out = pd.concat(parts, ignore_index=True).sort_values(["period_type", "item", "year"]).reset_index(drop=True)
    out.to_csv(ROOT / "data" / "annual.csv", index=False)


if __name__ == "__main__":
    main()
