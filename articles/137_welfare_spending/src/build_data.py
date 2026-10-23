"""e-Stat から取った地方財政状況調査（市町村分）表7〜12 の抜き出しファイルを、市区町村×年度の表に整える。

data/raw/d137b_bundle.csv は、各表の CSV から必要な行だけを抜き出してつないだもの（形式は README）。
"""
import csv, collections, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "d137b_bundle.csv"
OUT = ROOT / "data" / "municipal_expenditure.csv"
MUNI = {"1", "2", "3", "4", "5", "8", "9"}  # 団体区分：6（一部事務組合）・7（広域連合）などを除く市区町村
KAN = ["議会費", "総務費・総額", "民生費・総額", "衛生費・総額", "労働費・総額", "農林水産業費・総額", "商工費",
       "土木費・総額", "消防費", "教育費・総額", "災害復旧費・総額", "公債費", "諸支出金・総額", "前年度繰上充用金"]
SUB = ["民生費・社会福祉費", "民生費・老人福祉費", "民生費・児童福祉費", "民生費・生活保護費", "民生費・災害救助費"]
FIN = ["国庫支出金", "都道府県支出金", "地方債", "一般財源等"]  # 民生費の財源（行名）


def main(src=SRC):
    hdr, rec = {}, collections.defaultdict(dict)
    with open(src, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            p = next(csv.reader([line.rstrip("\n")]))
            if line.startswith("#H,"):
                hdr[(p[1], p[2])] = [c.split(":", 1)[-1] for c in p[3:]]
                continue
            cols = hdr.get((p[0], p[1]))
            v = p[2:]
            if not cols or len(v) != len(cols) or v[5] not in MUNI:
                continue
            d = dict(zip(cols, v))
            key = (int(d["決算年度"]), d["団体コード "].strip().zfill(6))
            r = rec[key]
            r.update({"fiscal_year": key[0], "code": key[1], "pref": d["県名"], "name": d["団体名"], "kubun": d["団体区分"]})
            row = d["行名称"].strip()  # 行番号は表ごとに違うので行名で見る
            for c in cols[10:]:
                x = d[c].strip()
                val = float(x) if x not in ("", "-") else 0.0
                if row == "歳出合計" and (c in KAN or c in SUB):
                    r[c] = val
                elif row in FIN and c == "民生費・総額":
                    r["民生費財源・" + row] = val
    df = pd.DataFrame(rec.values())
    df = df[df[KAN].notna().all(axis=1)].copy()  # 表7〜12 がそろう年度だけ（2008年度は表10〜12 が取れていない）
    df["歳出合計"] = df[KAN].sum(axis=1)
    df = df.sort_values(["fiscal_year", "code"])
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(df.groupby("fiscal_year").size())


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else SRC)
