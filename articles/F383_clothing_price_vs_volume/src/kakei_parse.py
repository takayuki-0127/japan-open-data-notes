"""（F352 の同名ファイルに「消費支出」の行の読み出しを足したもの）
家計調査 詳細結果表（第4-6表・第4-3表）の品目の値を読み出す（旧い xls と新しい xlsx の両方）。"""
import re
import pandas as pd

AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
QUINT = ["平均", "Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ"]
S = lambda v, i, j: re.sub(r"[\s　]", "", str(v.iloc[i, j]))

def num(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return float("nan")

def _rows(v, codes, want_hh):
    """コード列を見つけ、(行番号, key) の一覧を返す。key は品目コード、または 'hh_size'"""
    cc = next(j for j in range(v.shape[1]) if (v.iloc[:, j].astype(str).str.strip() == "9.4.1").any())
    out = []
    for i in range(v.shape[0]):
        c = S(v, i, cc)
        if c in codes:
            out.append((i, c, S(v, i, cc + 1)))
        elif want_hh and any(S(v, i, j).startswith("世帯人員") for j in range(max(0, cc - 1), cc + 2)):
            out.append((i, "hh_size", "世帯人員"))
        elif want_hh and S(v, i, cc + 1) == "消費支出":
            out.append((i, "cons", "消費支出"))
        elif want_hh and any(S(v, i, j).startswith("世帯数分布") for j in range(max(0, cc - 1), cc + 2)):
            out.append((i, "hh_weight", "世帯数分布（1万分比）"))
    return out

def read_46(path, year, codes):
    """第4-6表：年齢階級ごとの 支出金額・購入頻度"""
    v = list(pd.read_excel(path, sheet_name=None, header=None).values())[0]
    recs = []
    if year <= 2019:
        hr = next(i for i in range(15) if S(v, i, 11) == "平均")
        cols = {S(v, hr, j): j for j in range(v.shape[1]) if S(v, hr, j) in AGES}
        get = lambda i, a: (num(v.iloc[i, cols[a]]), num(v.iloc[i, cols[a] - 1]))
    else:
        hr = next(i for i in range(15) if any(S(v, i, j) == "平均・支出金額" for j in range(v.shape[1])))
        cols = {S(v, hr, j): j for j in range(v.shape[1])}
        get = lambda i, a: (num(v.iloc[i, cols[f"{a}・支出金額"]]), num(v.iloc[i, cols[f"{a}・購入頻度"]]))
    seen = set()
    for i, c, name in _rows(v, codes, True):
        if c in seen:
            continue
        seen.add(c)
        for a in AGES:
            amt, freq = get(i, a)
            recs.append(dict(year=year, group=a, code=c, name=name, amount=amt, freq=freq))
    return recs

def read_43(path, year, codes):
    """第4-3表：年間収入五分位ごとの 支出金額・購入頻度（二人以上の世帯のシート）"""
    sh = pd.read_excel(path, sheet_name=None, header=None)
    names = list(sh)
    pick = lambda key: next(n for n in names if "二人" in n and key in n)
    out = {}
    for key in ("支出金額", "購入頻度"):
        v = sh[pick(key)]
        hr = next(i for i in range(15) if S(v, i, v.shape[1] - 1) in ("Ⅴ", "5", "5.0"))
        cols = {}
        for j in range(v.shape[1]):
            lab = S(v, hr, j)
            lab = {"平均": "平均", "1": "Ⅰ", "2": "Ⅱ", "3": "Ⅲ", "4": "Ⅳ", "5": "Ⅴ", "1.0": "Ⅰ", "2.0": "Ⅱ", "3.0": "Ⅲ", "4.0": "Ⅳ", "5.0": "Ⅴ"}.get(lab, lab)
            if lab in QUINT:
                cols[lab] = j
        assert list(cols) == QUINT, (path, cols)
        seen = set()
        for i, c, name in _rows(v, codes, key == "支出金額"):
            if c in seen:
                continue
            seen.add(c)
            for q in QUINT:
                out.setdefault((c, q), dict(year=year, group=q, code=c, name=name))[("amount" if key == "支出金額" else "freq")] = num(v.iloc[i, cols[q]])
    return list(out.values())
