"""data/raw の Excel から、分析に使う表（data/*.csv）を作る。"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data")

PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉",
         "東京", "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重",
         "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島",
         "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
REGION = {}
for r, ps in [("北海道", ["北海道"]), ("東北", PREFS[1:7]), ("関東", PREFS[7:14]), ("中部", PREFS[14:23]),
              ("近畿", PREFS[23:30]), ("中国", PREFS[30:35]), ("四国", PREFS[35:39]), ("九州・沖縄", PREFS[39:])]:
    for p in ps:
        REGION[p] = r


def norm(v):
    """都道府県名をそろえる（「青森県」→「青森」）。合わなければ None。"""
    if not isinstance(v, str):
        return None
    s = v.replace(" ", "").replace("　", "")
    if s == "北海道":
        return s
    for suf in ("県", "府", "都"):
        if s.endswith(suf) and s[:-1] in PREFS:
            return s[:-1]
    return s if s in PREFS else None


def pref_cols(path, sheet, name_col, cols):
    """シートから、都道府県の行の指定の列を取る。cols は {出す名前: 列番号}。"""
    d = pd.read_excel(path, sheet_name=sheet, header=None)
    rows = {}
    for _, r in d.iterrows():
        p = norm(r.iloc[name_col])
        if p is None or p in rows:
            continue
        rows[p] = {k: float(r.iloc[c]) for k, c in cols.items()}
    assert len(rows) == 47, (path, sheet, len(rows))
    return pd.DataFrame.from_dict(rows, orient="index").loc[PREFS]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def national():
    """全国の年ごとの表：園数・在園者数（国公私立）・就園率。"""
    k = pd.read_excel(os.path.join(RAW, "gk_000031852314.xlsx"), header=None)
    e = pd.read_excel(os.path.join(RAW, "gk_000031852315.xlsx"), header=None)
    s = pd.read_excel(os.path.join(RAW, "gk_000031852304.xlsx"), header=None)

    def table(d, prefix):
        out = {}
        for _, r in d.iterrows():
            y = num(r.iloc[1])
            if not (1940 < y < 2100) or int(y) in out:
                continue
            out[int(y)] = {f"{prefix}_en": num(r.iloc[2]), f"{prefix}_en_pub": num(r.iloc[4]),
                           f"{prefix}_en_pri": num(r.iloc[5]), f"{prefix}_ji": num(r.iloc[6]),
                           f"{prefix}_ji_pub": num(r.iloc[8]), f"{prefix}_ji_pri": num(r.iloc[9])}
        return pd.DataFrame.from_dict(out, orient="index")

    kt, et = table(k, "kg"), table(e, "ke")
    rate = {}
    for _, r in s.iterrows():
        y = num(r.iloc[1])
        if 1940 < y < 2100 and int(y) not in rate:
            rate[int(y)] = {"kg_rate": num(r.iloc[2]), "ke_rate": num(r.iloc[3])}
    rt = pd.DataFrame.from_dict(rate, orient="index")
    n = kt.join(et, how="left").join(rt, how="left")
    n.index.name = "year"
    n = n.sort_index()
    n["ke_rate"] = n["ke_rate"].fillna(0.0).where(n.index >= 2015, 0.0)
    for c in [c for c in n.columns if c.startswith("ke_") and c != "ke_rate"]:
        n[c] = n[c].where(n.index >= 2015, 0.0)
    return n


def prefectural():
    g = lambda f: os.path.join(RAW, f)
    k14 = pref_cols(g("k11_2014.xls"), 0, 2, {"kg2014": 5})
    k14_5 = pref_cols(g("k11_2014.xls"), 1, 2, {"kg2014_5": 5})
    k15 = pref_cols(g("k11_2015.xlsx"), 0, 2, {"kg2015": 5})
    k15_5 = pref_cols(g("k11_2015.xlsx"), 1, 2, {"kg2015_5": 5})
    k25 = pref_cols(g("k11_2025.xlsx"), 0, 1, {"kg2025": 2, "kg2025_5": 18})
    ke25 = pref_cols(g("ke30_2025.xlsx"), 0, 1, {"ke2025_all": 2, "ke2025_3": 14, "ke2025_4": 23, "ke2025_5": 32})
    out = pd.concat([k14, k14_5, k15, k15_5, k25, ke25], axis=1)
    for y in (2023, 2024, 2025):
        c = pref_cols(g(f"ke39_{y}.xlsx"), 0, 0, {f"ke{y}_35": 1, f"ke{y}_35_n1": 2, f"ke{y}_35_n2": 3,
                                                   f"ke{y}_5": 22, f"ke{y}_5_n1": 23, f"ke{y}_5_n2": 24})
        if y == 2025:
            c = c.drop(columns=["ke2025_5"])
        out = pd.concat([out, c], axis=1)
    k17 = pref_cols(g("k17_2025.xlsx"), 0, 0, {"kg2025_35": 1, "kg2025_35_n1": 2, "kg2025_35_n2": 3,
                                               "kg2025_5b": 25, "kg2025_5_n1": 26, "kg2025_5_n2": 27})
    out = pd.concat([out, k17], axis=1)
    # 公立・私立のこども園（3〜5歳・1号）
    for sh, lab in ((2, "pub"), (3, "pri")):
        c = pref_cols(g("ke39_2025.xlsx"), sh, 0, {f"ke2025_35_{lab}": 1, f"ke2025_35_n1_{lab}": 2})
        out = pd.concat([out, c], axis=1)
    out.insert(0, "region", [REGION[p] for p in out.index])
    out.index.name = "pref"
    # 中の検算：同じ数を別の表から取ったものが一致するか
    assert (out["kg2025_5"] == out["kg2025_5b"]).all()
    assert (out["ke2025_3"] + out["ke2025_4"] + out["ke2025_5"] == out["ke2025_35"]).all()
    assert (out["kg2025_35"] == out["kg2025"]).all()
    return out.drop(columns=["kg2025_5b"])


if __name__ == "__main__":
    n = national()
    n.to_csv(os.path.join(OUT, "national.csv"), float_format="%.4f")
    p = prefectural()
    p.astype({c: "int64" for c in p.columns if c != "region"}).to_csv(os.path.join(OUT, "prefecture.csv"))
    print("national", n.shape, "prefecture", p.shape)
