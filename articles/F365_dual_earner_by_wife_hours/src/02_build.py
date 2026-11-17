"""02_build.py : 労働力調査 基本集計 第IV-7表（年により形が違う）から、夫が非農林業雇用者の列を取り出して
data/couples.csv を作る（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
SHEETS = {"1": "夫婦のいる世帯", "4": "夫婦と子供から成る世帯"}
ITEMS = ["総数", "雇用者_非農林業", "休業者", "週1～14時間", "週15～34時間", "週15～29時間", "週30～34時間", "週35時間以上",
         "月121～180時間", "月181～240時間", "月241時間以上", "完全失業者", "非労働力人口"]


def n(s):
    return "" if pd.isna(s) else re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s))).replace("~", "～")


def parse(path, year, base):
    xf = pd.ExcelFile(path)
    out = []
    for sh, hh in SHEETS.items():
        v = xf.parse(sh, header=None)
        assert hh.replace("世帯", "") in n(" ".join(str(x) for x in v.iloc[0:16, :].values.ravel())) or sh == "1", (path.name, sh)
        # 妻の項目の行（ラベルの列は年で違う）
        rows = {}
        n_emp = 0
        for i in range(16, len(v)):
            labs = [n(v.iat[i, j]).replace("(妻の就業状態)", "") for j in range(6, 15)]
            cand = [x.replace("妻の就業状態", "") for x in labs if x and not re.fullmatch(r"[\d.]+", x) and x not in ("全国",) and "年平均" not in x]
            cand = [x for x in cand if x]
            lab = cand[-1] if cand else ""
            if lab == "雇用者":
                n_emp += 1
                if n_emp == 2:
                    rows["雇用者_非農林業"] = i
            elif lab in ITEMS and lab not in rows:
                rows[lab] = i
        assert set(ITEMS) <= set(rows), (path.name, set(ITEMS) - set(rows))
        # 値の始まりの列：総数の行で、管理番号（1）の次の列
        i0 = rows["総数"]
        nums = [j for j in range(8, v.shape[1]) if re.fullmatch(r"\d+", n(v.iat[i0, j]))]
        col0 = next(j for j in nums if float(n(v.iat[i0, j])) > 1000)  # 総数×総数の欄（万世帯で1000を超える最初の数）
        col = col0 + 11  # 夫：非農林業の雇用者（項目12）
        hdr = " ".join(n(v.iat[r, col]) for r in range(5, 16))
        assert "雇用者" in hdr and "役員" not in hdr, (path.name, sh, hdr)
        tot = float(n(v.iat[i0, col0]))
        for k in ITEMS:
            out.append({"year": year, "base": base, "household": hh, "wife": k, "value": float(n(v.iat[rows[k], col])),
                        "all_couples": tot})
    return out


if __name__ == "__main__":
    rows = []
    for p in sorted(RAW.glob("iv7_*")):
        m = re.match(r"iv7_(\d{4})_(cur|old2010|old2015)", p.name)
        rows += parse(p, int(m.group(1)), {"cur": "2020年基準", "old2010": "2010年基準", "old2015": "2015年基準"}[m.group(2)])
    df = pd.DataFrame(rows).sort_values(["base", "household", "year", "wife"])
    df.to_csv(OUT / "couples.csv", index=False, float_format="%.0f")
    w = df[(df.household == "夫婦のいる世帯")].pivot_table(index=["base", "year"], columns="wife", values="value")
    w["hours_sum"] = w[["休業者", "週1～14時間", "週15～34時間", "週35時間以上"]].sum(axis=1)
    print(w[["雇用者_非農林業", "hours_sum", "週35時間以上", "非労働力人口", "完全失業者"]])
