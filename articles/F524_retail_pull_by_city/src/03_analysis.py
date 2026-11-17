"""主な分析：小売吸引力指数（人口1人あたり小売販売額の全国比）の分布、人口規模別・都市圏の中心と周辺・県庁所在市、2014→2021年の変化。仮説と頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "muni.csv", dtype={"code": str})
CAP = {"北海道": "札幌市", "青森県": "青森市", "岩手県": "盛岡市", "宮城県": "仙台市", "秋田県": "秋田市", "山形県": "山形市", "福島県": "福島市",
       "茨城県": "水戸市", "栃木県": "宇都宮市", "群馬県": "前橋市", "埼玉県": "さいたま市", "千葉県": "千葉市", "東京都": "特別区部", "神奈川県": "横浜市",
       "新潟県": "新潟市", "富山県": "富山市", "石川県": "金沢市", "福井県": "福井市", "山梨県": "甲府市", "長野県": "長野市", "岐阜県": "岐阜市",
       "静岡県": "静岡市", "愛知県": "名古屋市", "三重県": "津市", "滋賀県": "大津市", "京都府": "京都市", "大阪府": "大阪市", "兵庫県": "神戸市",
       "奈良県": "奈良市", "和歌山県": "和歌山市", "鳥取県": "鳥取市", "島根県": "松江市", "岡山県": "岡山市", "広島県": "広島市", "山口県": "山口市",
       "徳島県": "徳島市", "香川県": "高松市", "愛媛県": "松山市", "高知県": "高知市", "福岡県": "福岡市", "佐賀県": "佐賀市", "長崎県": "長崎市",
       "熊本県": "熊本市", "大分県": "大分市", "宮崎県": "宮崎市", "鹿児島県": "鹿児島市", "沖縄県": "那覇市"}
BINS = [0, 5000, 10000, 30000, 100000, 300000, 1e9]
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]


def index(df, s, p):
    ok = df[s].notna()
    nat = df.loc[ok, s].sum() / df.loc[ok, p].sum()
    return df[s] / df[p] / nat


def merge_wards(df):
    k = df[df.kind == "ku"]
    row = {"code": "13100", "pref": "東京都", "name": "特別区部", "kind": "seirei", "role": "中心市",
           **{c: k[c].sum(min_count=1) for c in ["sales2014", "sales2021", "store2014", "store2021", "pop2015", "pop2020"]}}
    return pd.concat([df[df.kind != "ku"], pd.DataFrame([row])], ignore_index=True)


def r(x, k=2):
    return round(float(x), k)


d["idx2014"] = index(d, "sales2014", "pop2015")
d["idx2021"] = index(d, "sales2021", "pop2020")
d["idx2021_p15"] = index(d, "sales2021", "pop2015")
for y in (2014, 2021):  # 店舗の販売額（無店舗小売業を除く。無店舗の秘匿は0とみなす）
    d[f"store{y}"] = d[f"sales{y}"] - d[f"nonstore{y}"].fillna(0)
d["idx_store2014"] = index(d, "store2014", "pop2015")
d["idx_store2021"] = index(d, "store2021", "pop2020")
d["size"] = pd.cut(d.pop2020, BINS, right=False, labels=LABELS).astype(str)
d.to_csv(R / "index_by_municipality.csv", index=False, float_format="%.4f")
m = merge_wards(d)  # 東京23区をまとめた表（県庁所在市の比較に使う）
m["idx2014"] = index(m, "sales2014", "pop2015"); m["idx2021"] = index(m, "sales2021", "pop2020")
m["idx_store2014"] = index(m, "store2014", "pop2015"); m["idx_store2021"] = index(m, "store2021", "pop2020")
m["is_cap"] = [CAP.get(p) == n for p, n in zip(m.pref, m.name)]
cap = m[m.is_cap].copy()
assert len(cap) == 47, len(cap)
cap["chg"] = cap.idx2021 - cap.idx2014
cap["chg_store"] = cap.idx_store2021 - cap.idx_store2014
cap = cap.sort_values("code")
cap.to_csv(R / "capitals.csv", index=False, float_format="%.4f")

v = d[d.idx2021.notna()]
sz = v.groupby("size").agg(n=("idx2021", "size"), median=("idx2021", "median"), q1=("idx2021", lambda s: s.quantile(.25)), q3=("idx2021", lambda s: s.quantile(.75)),
                           over1_pct=("idx2021", lambda s: 100 * (s > 1).mean())).reindex(LABELS).round(3)
sz.to_csv(R / "by_size_2021.csv")
rl = v.groupby("role").agg(n=("idx2021", "size"), median=("idx2021", "median"), over1_pct=("idx2021", lambda s: 100 * (s > 1).mean())).round(3)
rl.to_csv(R / "by_role_2021.csv")
both = d[d.idx2014.notna() & d.idx2021.notna()]
over1 = 100 * (v.idx2021 > 1).mean()
small_med = float(sz.loc["5千人未満", "median"])
hyp = {
    "H1": {"capital_median_2021": r(cap.idx2021.median(), 3), "verdict": "支持" if cap.idx2021.median() >= 1.2 else "外れ"},
    "H2": {"over1_pct_2021": r(over1, 1), "n": int(len(v)), "verdict": "支持" if over1 < 40 else "外れ"},
    "H3": {"n_capital_down": int((cap.chg < 0).sum()), "verdict": "支持" if (cap.chg < 0).sum() > 23.5 else "外れ"},
    "H4": {"small_median_2021": r(small_med, 3), "verdict": "支持" if small_med < 0.6 else "外れ"},
}
mv = m[m.idx2021.notna()]
rob = [
    {"check": "本線：指数が1を超える市区町村の割合（2021年）", "value": r(over1, 1)},
    {"check": "東京23区を1つにまとめた場合", "value": r(100 * (mv.idx2021 > 1).mean(), 1)},
    {"check": "2021年の販売額を2015年の人口で割った場合", "value": r(100 * (d.idx2021_p15.dropna() > 1).mean(), 1)},
    {"check": "2014年と2021年の両方にある団体だけ（2021年）", "value": r(100 * (both.idx2021 > 1).mean(), 1)},
    {"check": "2014年（同じ定義）", "value": r(100 * (d.idx2014.dropna() > 1).mean(), 1)},
    {"check": "県庁所在市の中央値：本線（2021年）", "value": r(cap.idx2021.median(), 3)},
    {"check": "県庁所在市：人口で重みをつけた値（2021年）", "value": r(cap.sales2021.sum() / cap.pop2020.sum() / (mv.sales2021.sum() / mv.pop2020.sum()), 3)},
    {"check": "県庁所在市：指数が下がった数（両年とも値のある47市）", "value": int((cap.chg < 0).sum())},
    {"check": "県庁所在市の中央値（2014年）", "value": r(cap.idx2014.median(), 3)},
    {"check": "店舗の販売額だけ（無店舗小売業を除く）：県庁所在市の中央値（2021年）", "value": r(cap.idx_store2021.median(), 3)},
    {"check": "店舗の販売額だけ：県庁所在市で指数が下がった数", "value": int((cap.chg_store < 0).sum())},
    {"check": "店舗の販売額だけ：指数が1を超える市区町村の割合（2021年）", "value": r(100 * (d.idx_store2021.dropna() > 1).mean(), 1)},
    {"check": "人口で重みをつけた、都市圏の中心市の値（2021年）", "value": r(v[v.role == "中心市"].sales2021.sum() / v[v.role == "中心市"].pop2020.sum() / (v.sales2021.sum() / v.pop2020.sum()), 3)},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
main = {"n_2021": int(len(v)), "n_missing_2021": int(d.idx2021.isna().sum()), "n_missing_2014": int(d.idx2014.isna().sum()),
        "national_per_capita_man_yen": {"2014": r(d.sales2014.sum() / d.loc[d.sales2014.notna(), "pop2015"].sum() * 100, 1),
                                        "2021": r(d.sales2021.sum() / d.loc[d.sales2021.notna(), "pop2020"].sum() * 100, 1)},
        "over1_pct_2021": r(over1, 1), "over1_n_2021": int((v.idx2021 > 1).sum()), "median_all_2021": r(v.idx2021.median(), 3),
        "capital_median": {"2014": r(cap.idx2014.median(), 3), "2021": r(cap.idx2021.median(), 3)},
        "capital_min_max_2021": [r(cap.idx2021.min(), 3), r(cap.idx2021.max(), 3)], "capital_over1_2021": int((cap.idx2021 > 1).sum()),
        "capital_down": int((cap.chg < 0).sum()), "capital_chg_median": r(cap.chg.median(), 3),
        "role_median_2021": {k: float(v_) for k, v_ in rl["median"].items()}, "role_over1_2021": {k: float(v_) for k, v_ in rl.over1_pct.items()},
        "size_median_2021": {k: float(v_) for k, v_ in sz["median"].items()}, "size_over1_2021": {k: float(v_) for k, v_ in sz.over1_pct.items()},
        "hypotheses": hyp}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=1)); print(pd.DataFrame(rob).to_string()); print(sz); print(rl)
print(cap[["pref", "name", "idx2014", "idx2021", "chg"]].round(3).to_string())
