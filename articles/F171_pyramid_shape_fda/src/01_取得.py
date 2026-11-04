"""01 取得：国勢調査の不詳補完値（年齢各歳・男女・市区町村）を CSV にまとめる。

使う表（e-Stat、どちらも Excel）
- 令和2年国勢調査 参考表：不詳補完結果
  「男女，年齢（各歳），国籍総数か日本人別人口，平均年齢及び年齢中位数－全国，都道府県，市区町村」
  statInfId=000032144436（2020年）
- 同 平成27年国勢調査に関する不詳補完結果（遡及集計） 同じ表 statInfId=000032144424（2015年）

e-Stat の Excel は大きく（各16MB前後）、作成時はブラウザ上で読み込んで国籍総数の行だけを
data/census_age_single_2015_2020.csv に書き出した。手元で作り直すときは、上の2ファイルを
data/raw/ に w2020.xlsx・w2015.xlsx の名前で置いてこのスクリプトを実行する
（https://www.e-stat.go.jp/stat-search/file-download?statInfId=<id>&fileKind=0）。
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "census_age_single_2015_2020.csv"

if OUT.exists() and not (RAW / "w2020.xlsx").exists():
    print("data/census_age_single_2015_2020.csv をそのまま使います")
else:
    rows = []
    for y in (2020, 2015):
        a = pd.read_excel(RAW / f"w{y}.xlsx", header=None, dtype=object).fillna("")
        hr = a.index[a.apply(lambda r: r.astype(str).str.startswith("001_0歳").any(), axis=1)][0]
        lab = a.index[(a.index > hr) & a.apply(lambda r: r.astype(str).str.contains("地域識別コード").any(), axis=1)][0]
        h = list(a.loc[hr])
        i0, i1 = h.index("000_総数"), h.index("101_100歳以上")
        for _, r in a.loc[lab + 1:].iterrows():
            if r[0] != "0_国籍総数":
                continue
            cn = str(r[4])
            vals = [0 if v in ("-", "") else int(v) for v in r[i0:i1 + 1]]
            rows.append([y, str(r[2]), str(r[1]).split("_")[0], cn[:5], cn[6:], *vals])
    cols = ["year", "level", "sex", "code", "name"] + [f"{i:03d}" for i in range(0, 102)]
    pd.DataFrame(rows, columns=cols).to_csv(OUT, index=False)
    print("wrote", OUT)
