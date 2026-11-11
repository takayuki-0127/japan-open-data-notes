"""家計調査 年報 詳細結果表（第4-1表・第4-6表）の Excel を長い形に直す。
2019年以前の xls（4列ごとに見出し）と、2020年以降の xlsx（「区分・指標」の見出し）の両方に対応する。"""
import re
import pandas as pd

METRICS = ("購入頻度", "支出金額", "購入数量", "平均価格")


def _clean(s):
    s = str(s).replace("　", "").strip()
    s = re.sub(r"\((人|歳|％|円)\)$", "", s)
    return s


def parse(path, sheet=0):
    d = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    rows = []
    # 新しい形：行のどこかに「品目分類」という見出しがあり、その1行上が「区分・指標」
    hdr = [i for i in range(30) if any(str(v).strip() == "品目分類" for v in d.iloc[i].tolist())]
    if hdr:
        h = hdr[0]
        icol = [j for j, v in enumerate(d.iloc[h].tolist()) if str(v).strip() == "品目分類"][0]
        labs = d.iloc[h - 1].tolist()
        cols = []
        for j, l in enumerate(labs):
            l = str(l)
            if "・" in l and l.split("・")[-1] in METRICS:
                cols.append((j, l.rsplit("・", 1)[0], l.rsplit("・", 1)[1]))
        body = d.iloc[h + 1:]
    else:
        # 古い形：「支出金額」の行の3行上に区分名（平均・年齢・市の名前）がある
        mrow = [i for i in range(30) if any(str(v).strip() == "支出金額" for v in d.iloc[i].tolist())][0]
        grow = mrow - 3
        icol = None
        cols = []
        for j in range(d.shape[1]):
            if str(d.iat[mrow, j]).strip() == "支出金額":
                g = None
                for i in range(mrow - 1, max(mrow - 7, -1), -1):
                    v = d.iat[i, j]
                    if isinstance(v, str) and v.strip() and v.strip() not in METRICS:
                        g = v.strip()
                        break
                for k, m in ((j - 1, "購入頻度"), (j, "支出金額"), (j + 1, "購入数量"), (j + 2, "平均価格")):
                    cols.append((k, g, m))
        first = [i for i in range(mrow, mrow + 8) if any("世帯数分布" in str(v) for v in d.iloc[i, :10].tolist())][0]
        body = d.iloc[first:]
    for _, r in body.iterrows():
        if icol is None:
            # 古い形：品目名は8列目（大きい区分は7列目）、品目番号は5列目
            v8 = r.iloc[8] if pd.notna(r.iloc[8]) else r.iloc[7]
            item = _clean(v8)
        else:
            item = _clean(r.iloc[icol])
        if not item or item == "nan":
            continue
        for j, g, m in cols:
            v = r.iloc[j]
            try:
                v = float(str(v).replace(",", ""))
            except ValueError:
                v = None
            rows.append((int(r.iloc[5]) if pd.notna(r.iloc[5]) else None, item, g, m, v))
    out = pd.DataFrame(rows, columns=["no", "item", "group", "metric", "value"])
    # 区分名をそろえる（「22130 浜松市」→「浜松市」、「全　国」→「全国」）
    out["group"] = (out["group"].astype(str).str.replace(r"^\d{4,}\s+", "", regex=True)
                    .str.replace(r"[\s\u3000]", "", regex=True).replace({"全": "全国"}))
    return out
