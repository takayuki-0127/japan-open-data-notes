"""03 分析：日本人の減少と外国人の増加、要素の分解、地域別、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
METRO = [11, 12, 13, 14, 21, 23, 24, 26, 27, 28, 29]
CHIHO = [p for p in range(1, 48) if p not in METRO]
NOT_TK = [p for p in range(1, 48) if p not in (11, 12, 13, 14)]
PREF = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
        "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
        "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
        "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
REGION = {"北海道・東北": range(1, 8), "関東": range(8, 15), "中部": range(15, 24), "近畿": range(24, 31),
          "中国": range(31, 36), "四国": range(36, 40), "九州・沖縄": range(40, 48)}
S = pd.read_csv(ROOT / "data" / "stock.csv")
Fl = pd.read_csv(ROOT / "data" / "flows.csv")
def r(x, n=1): return float(round(float(x), n))

def comps(years):
    q = Fl[Fl.year.isin(years)].groupby(["pref", "nat", "item"], sort=True).persons.sum().unstack("item")
    c = pd.DataFrame({"自然": q["出生"] - q["死亡"], "県間": q["県間転入"] - q["県間転出"], "国外": q["入国"] - q["出国"]})
    c["計"] = c.sum(axis=1)
    return c.unstack("nat")  # 列：(要素, 国籍)

def offset(c, prefs):
    j = c.loc[prefs, ("計", "日本人")].sum(); f = c.loc[prefs, ("計", "外国人")].sum()
    return j, f, (f / -j * 100 if j < 0 else np.nan)

M = {}
# ---- 全国の人口（第5表）
nat = S[S.pref == 0].set_index("year")
nat_tab = pd.DataFrame({"日本人_千人": nat.japanese_k, "外国人_千人": nat.foreign_k, "総人口_千人": nat.total_k})
nat_tab["日本人の前年差"] = nat_tab["日本人_千人"].diff(); nat_tab["外国人の前年差"] = nat_tab["外国人_千人"].diff()
nat_tab["埋め合わせ率_%"] = (nat_tab["外国人の前年差"] / -nat_tab["日本人の前年差"] * 100).round(1)
nat_tab.index.name = "year"; nat_tab.to_csv(RES / "national_stock.csv")
def stock_off(y0, y1, prefs=None):
    q = S if prefs is None else S[S.pref.isin(prefs)]
    q = q[q.pref == 0] if prefs is None else q
    a = q[q.year == y0][["japanese_k", "foreign_k"]].sum(); b = q[q.year == y1][["japanese_k", "foreign_k"]].sum()
    dj, df = b.japanese_k - a.japanese_k, b.foreign_k - a.foreign_k
    return dj, df, df / -dj * 100
dj, df, o = stock_off(2019, 2024)
M["H1"] = {"日本人の変化_千人_2019_2024": r(dj, 0), "外国人の変化_千人_2019_2024": r(df, 0), "埋め合わせ率_%": r(o),
           "判定": ("支持" if o >= 20 else "外れ") + "（参考：数字を見たあとに置いた仮説）"}
dj2, df2, o2 = stock_off(2014, 2019)
M["全国_2014_2019"] = {"日本人の変化_千人": r(dj2, 0), "外国人の変化_千人": r(df2, 0), "埋め合わせ率_%": r(o2)}
dj3, df3, o3 = stock_off(2010, 2024)
M["全国_2010_2024"] = {"日本人の変化_千人": r(dj3, 0), "外国人の変化_千人": r(df3, 0), "埋め合わせ率_%": r(o3)}
M["全国_年ごとの埋め合わせ率_%"] = {int(y): (None if pd.isna(v) else float(v)) for y, v in nat_tab["埋め合わせ率_%"].items()}
M["全国_外国人_千人"] = {"2010": r(nat.foreign_k[2010], 0), "2019": r(nat.foreign_k[2019], 0), "2024": r(nat.foreign_k[2024], 0)}

# ---- 要素（2021〜24年）
C = comps([2021, 2022, 2023, 2024])
C0 = comps([2016, 2017, 2018, 2019])
out = C.copy(); out.columns = [f"{a}_{b}" for a, b in out.columns]; out.index.name = "pref"
out.insert(0, "県", ["全国" if p == 0 else PREF[p - 1] for p in out.index])
out.to_csv(RES / "components_2021_2024.csv")
jn, fn, on = offset(C, [0]); jn0, fn0, on0 = offset(C0, [0])
M["全国_要素"] = {"日本人_2021_2024": int(jn), "外国人_2021_2024": int(fn), "埋め合わせ率_2021_2024_%": r(on),
                 "日本人_2016_2019": int(jn0), "外国人_2016_2019": int(fn0), "埋め合わせ率_2016_2019_%": r(on0),
                 "注": "2020年10月〜2024年9月（2015年10月〜2019年9月）の出生・死亡・県間・国外の合計。国勢調査による水準の切り替えを含まない（レビューで追加）"}
jm, fm, om = offset(C, METRO); jc, fc, oc = offset(C, CHIHO)
M["H2"] = {"三大都市圏_日本人": int(jm), "三大都市圏_外国人": int(fm), "三大都市圏_埋め合わせ率_%": r(om),
           "地方圏_日本人": int(jc), "地方圏_外国人": int(fc), "地方圏_埋め合わせ率_%": r(oc),
           "判定": "支持" if om > oc else "外れ"}
intl_pos = int((C.loc[CHIHO, ("国外", "外国人")] > 0).sum()); inter_neg = int((C.loc[CHIHO, ("県間", "外国人")] < 0).sum())
M["H3"] = {"地方圏_外国人の国外が正の県数": intl_pos, "地方圏_外国人の県間が負の県数": inter_neg, "県数": 36,
           "地方圏_外国人_国外": int(C.loc[CHIHO, ("国外", "外国人")].sum()), "地方圏_外国人_県間": int(C.loc[CHIHO, ("県間", "外国人")].sum()),
           "地方圏_外国人_自然": int(C.loc[CHIHO, ("自然", "外国人")].sum()),
           "三大都市圏_外国人_県間": int(C.loc[METRO, ("県間", "外国人")].sum()),
           "判定": "支持" if (intl_pos == 36 and inter_neg >= 19) else "外れ"}
M["H3"]["地方圏_県間の流出_÷_国外の流入_%"] = r(-M["H3"]["地方圏_外国人_県間"] / M["H3"]["地方圏_外国人_国外"] * 100)
fz = C.loc[0]
share_intl = fz[("国外", "外国人")] / fz[("計", "外国人")] * 100
M["H4"] = {"全国_外国人_計": int(fz[("計", "外国人")]), "全国_外国人_国外": int(fz[("国外", "外国人")]),
           "全国_外国人_自然": int(fz[("自然", "外国人")]), "国外の割合_%": r(share_intl),
           "全国_日本人_計": int(fz[("計", "日本人")]), "全国_日本人_自然": int(fz[("自然", "日本人")]),
           "全国_日本人_国外": int(fz[("国外", "日本人")]),
           "要素の埋め合わせ率_全国_%": r(fz[("計", "外国人")] / -fz[("計", "日本人")] * 100),
           "判定": "支持" if share_intl >= 80 else "外れ"}
# 第5表の変化と要素の合計の差（2020→2024、全国）
st = S[S.pref == 0].set_index("year")
M["H4"]["第5表_外国人の変化_2020_2024_千人"] = r(st.foreign_k[2024] - st.foreign_k[2020], 0)
M["H4"]["第5表_日本人の変化_2020_2024_千人"] = r(st.japanese_k[2024] - st.japanese_k[2020], 0)

# 地方別（北から南）
reg = []
for name, rg in REGION.items():
    j, f, o = offset(C, list(rg))
    reg.append((name, int(j), int(f), r(o), int(C.loc[list(rg), ("国外", "外国人")].sum()), int(C.loc[list(rg), ("県間", "外国人")].sum())))
RG = pd.DataFrame(reg, columns=["地方", "日本人_計", "外国人_計", "埋め合わせ率_%", "外国人_国外", "外国人_県間"])
RG.to_csv(RES / "by_region_2021_2024.csv", index=False)
M["地方別_2021_2024"] = {row.地方: {"埋め合わせ率_%": row._4} for row in RG.itertuples()}
# 県別の埋め合わせ率（北から南）
pp = pd.DataFrame({"県": [PREF[p - 1] for p in range(1, 48)],
                   "日本人_計": C.loc[1:47, ("計", "日本人")].values, "外国人_計": C.loc[1:47, ("計", "外国人")].values},
                  index=range(1, 48))
pp["埋め合わせ率_%"] = np.where(pp["日本人_計"] < 0, pp["外国人_計"] / -pp["日本人_計"] * 100, np.nan).round(1)
pp["総数_計"] = pp["日本人_計"] + pp["外国人_計"]
pp.index.name = "pref"; pp.to_csv(RES / "pref_offset_2021_2024.csv")
M["県別"] = {"日本人が減った県数": int((pp["日本人_計"] < 0).sum()),
            "外国人が増えた県数": int((pp["外国人_計"] > 0).sum()),
            "日本人は減り総数は増えた県": [pp.loc[p, "県"] for p in pp.index if pp.loc[p, "日本人_計"] < 0 and pp.loc[p, "総数_計"] > 0],
            "埋め合わせ率_中央値_%": r(pp["埋め合わせ率_%"].median()),
            "埋め合わせ率_最小_%": r(pp["埋め合わせ率_%"].min()), "埋め合わせ率_最大_%": r(pp["埋め合わせ率_%"].max()),
            "地方圏の埋め合わせ率_中央値_%": r(pp.loc[CHIHO, "埋め合わせ率_%"].median()),
            "三大都市圏の埋め合わせ率_中央値_%": r(pp.loc[METRO, "埋め合わせ率_%"].median())}

# ---- 頑健性
rob = []
j0m, f0m, o0m = offset(C0, METRO); j0c, f0c, o0c = offset(C0, CHIHO)
rob.append(("H2", "コロナ前（2016〜19年）", "三大都市圏／地方圏 %", f"{r(o0m)}／{r(o0c)}", "支持" if o0m > o0c else "外れ"))
sm = stock_off(2020, 2024, METRO); sc = stock_off(2020, 2024, CHIHO)
rob.append(("H2", "第5表の人口の変化（2020→24年）", "三大都市圏／地方圏 %", f"{r(sm[2])}／{r(sc[2])}", "支持" if sm[2] > sc[2] else "外れ"))
C24 = comps([2024])
a24, b24 = offset(C24, METRO)[2], offset(C24, CHIHO)[2]
rob.append(("H2", "2024年だけ", "三大都市圏／地方圏 %", f"{r(a24)}／{r(b24)}", "支持" if a24 > b24 else "外れ"))
NM = [p for p in range(1, 48) if p not in NOT_TK]
a43, b43 = offset(C, [11, 12, 13, 14])[2], offset(C, NOT_TK)[2]
rob.append(("H2", "東京圏と、東京圏以外の43道府県", "東京圏／43道府県 %", f"{r(a43)}／{r(b43)}", "支持" if a43 > b43 else "外れ"))
ip0 = int((C0.loc[CHIHO, ("国外", "外国人")] > 0).sum()); in0 = int((C0.loc[CHIHO, ("県間", "外国人")] < 0).sum())
rob.append(("H3", "コロナ前（2016〜19年）", "国外が正の県数／県間が負の県数（36中）", f"{ip0}／{in0}", "支持" if ip0 == 36 and in0 >= 19 else "外れ"))
ip24 = int((C24.loc[CHIHO, ("国外", "外国人")] > 0).sum()); in24 = int((C24.loc[CHIHO, ("県間", "外国人")] < 0).sum())
rob.append(("H3", "2024年だけ", "国外が正の県数／県間が負の県数（36中）", f"{ip24}／{in24}", "支持" if ip24 == 36 and in24 >= 19 else "外れ"))
s0 = C0.loc[0, ("国外", "外国人")] / C0.loc[0, ("計", "外国人")] * 100
rob.append(("H4", "コロナ前（2016〜19年）", "国外の割合 %", r(s0), "支持" if s0 >= 80 else "外れ"))
s24 = C24.loc[0, ("国外", "外国人")] / C24.loc[0, ("計", "外国人")] * 100
rob.append(("H4", "2024年だけ", "国外の割合 %", r(s24), "支持" if s24 >= 80 else "外れ"))
R = pd.DataFrame(rob, columns=["仮説", "変えたこと", "指標", "値", "判定"])
R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {f"{a}|{b}": {"指標": c, "値": v, "判定": j} for a, b, c, v, j in rob}
M["コロナ前_2016_2019"] = {"三大都市圏_埋め合わせ率_%": r(o0m), "地方圏_埋め合わせ率_%": r(o0c),
                          "全国_外国人_計": int(C0.loc[0, ("計", "外国人")]), "全国_日本人_計": int(C0.loc[0, ("計", "日本人")])}

# ---- 問い直し：地方圏の外国人の県間の流出は、どこへ向かったか（三大都市圏の県間の受け入れとの対応）と、
#      地方圏の日本人の減少のうち、県間の流出と自然減のどちらが大きいか（外国人が埋めているのは何か）
q = {}
for lab, cc in [("2021_2024", C), ("2016_2019", C0)]:
    q[lab] = {"地方圏_日本人_自然": int(cc.loc[CHIHO, ("自然", "日本人")].sum()),
              "地方圏_日本人_県間": int(cc.loc[CHIHO, ("県間", "日本人")].sum()),
              "地方圏_日本人_国外": int(cc.loc[CHIHO, ("国外", "日本人")].sum()),
              "地方圏_外国人_国外": int(cc.loc[CHIHO, ("国外", "外国人")].sum()),
              "地方圏_外国人_県間": int(cc.loc[CHIHO, ("県間", "外国人")].sum()),
              "地方圏_外国人_自然": int(cc.loc[CHIHO, ("自然", "外国人")].sum()),
              "東京圏_外国人_県間": int(cc.loc[[11, 12, 13, 14], ("県間", "外国人")].sum()),
              "名古屋大阪圏_外国人_県間": int(cc.loc[[21, 23, 24, 26, 27, 28, 29], ("県間", "外国人")].sum())}
    q[lab]["地方圏_外国人の国外流入_÷_日本人の県間流出_%"] = r(q[lab]["地方圏_外国人_国外"] / -q[lab]["地方圏_日本人_県間"] * 100)
    q[lab]["地方圏_外国人の計_÷_日本人の自然減_%"] = r((q[lab]["地方圏_外国人_国外"] + q[lab]["地方圏_外国人_県間"] + q[lab]["地方圏_外国人_自然"]) / -q[lab]["地方圏_日本人_自然"] * 100)
M["問い直し"] = q
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps(M, ensure_ascii=False, indent=1))
