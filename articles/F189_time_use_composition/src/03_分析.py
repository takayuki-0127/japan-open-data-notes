# F189 生活時間の組成データ分析（社会生活基本調査 1976〜2021）
import json, os
import numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data"); R = os.path.join(ROOT, "results"); os.makedirs(R, exist_ok=True)
rng = np.random.default_rng(189)

age = pd.read_csv(os.path.join(D, "time_use_by_age_1976_2021.csv"))
day = pd.read_csv(os.path.join(D, "time_use_by_day_1976_2021.csv"))
day["activity"] = day.activity.str.replace("･", "・")
age = age[~age.activity.str.contains("次活動")]

A20 = ["睡眠", "身の回りの用事", "食事", "通勤・通学", "仕事", "学業", "家事", "介護・看護", "育児", "買い物",
       "移動(通勤・通学を除く)", "テレビ・ラジオ・新聞・雑誌", "休養・くつろぎ", "学習・自己啓発・訓練(学業以外)",
       "趣味・娯楽", "スポーツ", "ボランティア活動・社会参加活動", "交際・付き合い", "受診・療養", "その他"]
G8 = {"睡眠": ["睡眠"], "身の回り・食事": ["身の回りの用事", "食事", "受診・療養"],
      "仕事・通勤": ["仕事", "通勤・通学"], "学業・学習": ["学業", "学習・自己啓発・訓練(学業以外)"],
      "家事関連": ["家事", "介護・看護", "育児", "買い物"], "テレビ等": ["テレビ・ラジオ・新聞・雑誌"],
      "休養・くつろぎ": ["休養・くつろぎ"],
      "趣味・交際など": ["移動(通勤・通学を除く)", "趣味・娯楽", "スポーツ", "ボランティア活動・社会参加活動", "交際・付き合い", "その他"]}
G4 = {"睡眠": ["睡眠"], "身の回り・食事": ["身の回りの用事", "食事"],
      "仕事・家事など(2次活動)": ["通勤・通学", "仕事", "学業", "家事", "介護・看護", "育児", "買い物"],
      "自由時間(3次活動)": ["移動(通勤・通学を除く)", "テレビ・ラジオ・新聞・雑誌", "休養・くつろぎ", "学習・自己啓発・訓練(学業以外)",
                       "趣味・娯楽", "スポーツ", "ボランティア活動・社会参加活動", "交際・付き合い", "受診・療養", "その他"]}
GROUPS = {"G4": G4, "G8": G8, "G20": {a: [a] for a in A20}}
YEARS = [1996, 2001, 2006, 2011, 2016, 2021]
AGES = ["10～14歳", "15～19歳", "20～24歳", "25～29歳", "30～39歳", "40～49歳", "50～59歳", "60～64歳", "65～69歳", "70歳以上"]


def vec(df, acts=A20):
    s = df.set_index("activity").value.reindex(acts)
    return s.astype(float).values


def group(v, G, acts=A20):
    idx = {a: i for i, a in enumerate(acts)}
    return np.array([sum(v[idx[a]] for a in G[g]) for g in G])


def clr(x, z=0.5):
    x = np.where(x <= 0, z, x).astype(float)
    l = np.log(x)
    return l - l.mean()


def adist(x, y, z=0.5):
    return float(np.sqrt(((clr(x, z) - clr(y, z)) ** 2).sum()))


def sel(sex="総数", grp="総数", ag="計", year=None):
    q = age[(age.sex == sex) & (age.group == grp) & (age.age == ag)]
    if year is not None: q = q[q.year == year]
    return q


out = {}
# ---------- A. 全体（10歳以上）2001→2021 ----------
rowsA = []
for gk, G in GROUPS.items():
    x1, x2 = group(vec(sel(year=2001)), G), group(vec(sel(year=2021)), G)
    c = clr(x2) - clr(x1)
    for i, g in enumerate(G):
        rowsA.append(dict(grouping=gk, part=g, min2001=x1[i], min2021=x2[i], diff_min=x2[i] - x1[i],
                          diff_pt=100 * (x2[i] / x2.sum() - x1[i] / x1.sum()), log_ratio=np.log(max(x2[i], .5) / max(x1[i], .5)),
                          clr_change=c[i]))
A = pd.DataFrame(rowsA); A.to_csv(os.path.join(R, "A_change_2001_2021.csv"), index=False)
a20 = A[A.grouping == "G20"]
rho = spearmanr(a20.diff_min.abs(), a20.clr_change.abs()).correlation
out["A"] = dict(dist_G8=adist(group(vec(sel(year=2001)), G8), group(vec(sel(year=2021)), G8)),
                dist_G20=adist(vec(sel(year=2001)), vec(sel(year=2021))),
                rank_rho_abs_min_vs_clr=rho,
                top_min=a20.reindex(a20.diff_min.abs().sort_values(ascending=False).index)[["part", "diff_min", "log_ratio"]].head(5).values.tolist(),
                top_clr=a20.reindex(a20.clr_change.abs().sort_values(ascending=False).index)[["part", "diff_min", "log_ratio"]].head(5).values.tolist())
# 寄与：Aitchison 距離の2乗を部分に分ける（clr 差の2乗の割合）
for gk in ["G8", "G20"]:
    s = A[A.grouping == gk].copy(); s["share_sq"] = s.clr_change ** 2 / (s.clr_change ** 2).sum()
    out["A"]["share_" + gk] = s.sort_values("share_sq", ascending=False)[["part", "share_sq"]].values.tolist()

# ---------- B. 5年ごとの動きの大きさ ----------
rowsB = []
for sex in ["総数", "男", "女"]:
    for gk in ["G4", "G8", "G20"]:
        G = GROUPS[gk]
        for y1, y2 in zip(YEARS[:-1], YEARS[1:]):
            rowsB.append(dict(sex=sex, grouping=gk, period=f"{y1}-{y2}",
                              dist=adist(group(vec(sel(sex=sex, year=y1)), G), group(vec(sel(sex=sex, year=y2)), G))))
B = pd.DataFrame(rowsB); B.to_csv(os.path.join(R, "B_step_distance.csv"), index=False)
out["B"] = B[B.sex == "総数"].pivot(index="period", columns="grouping", values="dist").round(3).to_dict()

# 長い期間（15歳以上・週全体、1次/2次/3次と睡眠）1976〜2021
dd = day[(day.sex == "総数") & (day.group == "総数") & (day.day == "週全体")]
long = []
for y in sorted(dd.year.unique()):
    q = dd[dd.year == y].set_index("activity").value.astype(float)
    sl = q["睡眠"]; p1 = q["１次活動"] - sl
    long.append(dict(year=y, 睡眠=sl, 身の回り食事=p1, 二次活動=q["２次活動"], 三次活動=q["３次活動"]))
L = pd.DataFrame(long); L.to_csv(os.path.join(R, "B_long_G4_1976_2021.csv"), index=False)
Lv = L[["睡眠", "身の回り食事", "二次活動", "三次活動"]].values
out["B_long"] = dict(steps={f"{int(L.year[i])}-{int(L.year[i+1])}": adist(Lv[i], Lv[i + 1]) for i in range(len(L) - 1)},
                     first_last=L.iloc[[0, -1]].to_dict("records"))

# ---------- C. 男女×年齢 ----------
rowsC = []
for sex in ["男", "女"]:
    for ag in AGES:
        x1, x2 = vec(sel(sex=sex, ag=ag, year=2001)), vec(sel(sex=sex, ag=ag, year=2021))
        g1, g2 = group(x1, G8), group(x2, G8)
        c = clr(g2) - clr(g1)
        r = dict(sex=sex, age=ag, dist_G8=adist(g1, g2), dist_G20=adist(x1, x2))
        for i, g in enumerate(G8): r["clr_" + g] = c[i]; r["min2001_" + g] = g1[i]; r["min2021_" + g] = g2[i]
        rowsC.append(r)
C = pd.DataFrame(rowsC); C.to_csv(os.path.join(R, "C_sex_age_2001_2021.csv"), index=False)
out["C"] = dict(dist_range=[C.dist_G8.min(), C.dist_G8.max()],
                top=C.sort_values("dist_G8", ascending=False)[["sex", "age", "dist_G8"]].head(4).values.tolist(),
                bottom=C.sort_values("dist_G8")[["sex", "age", "dist_G8"]].head(3).values.tolist(),
                rest_up_all=bool((C["clr_休養・くつろぎ"] > 0).all()),
                rest_min_change=[C["min2021_休養・くつろぎ"].sub(C["min2001_休養・くつろぎ"]).min(), C["min2021_休養・くつろぎ"].sub(C["min2001_休養・くつろぎ"]).max()],
                tv_down=int((C["clr_テレビ等"] < 0).sum()))
# テレビは若い世代ほど減ったか
tv = C[["sex", "age", "min2001_テレビ等", "min2021_テレビ等", "clr_テレビ等"]]
out["C"]["tv"] = tv.values.tolist()

# ---------- D. 高齢化の分け方（人口推計の年齢構成で重みづけ） ----------
POP = pd.read_csv(os.path.join(D, "population_by_age_2001_2020.csv"))
def popw(y):  # 2021年は2020年10月1日の人口で代用
    q = POP[POP.year == (2020 if y == 2021 else y)].set_index("age").pop_thousand.reindex(AGES).values.astype(float)
    return q / q.sum()
def agemat(y, sex="総数"):
    return np.column_stack([vec(sel(sex=sex, ag=ag, year=y)) for ag in AGES])
rowsD = []
for y in [2001, 2006, 2011, 2016, 2021]:
    w = popw(y); M = agemat(y); t = vec(sel(year=y)); fit = M @ w
    rowsD.append(dict(year=y, max_abs_resid_min=float(np.abs(fit - t).max()), w65plus=float(w[-2:].sum()), w10_29=float(w[:4].sum())))
Dw = pd.DataFrame(rowsD); Dw.to_csv(os.path.join(R, "D_weights_fit.csv"), index=False)
def decompose(y1, y2, G=G8):
    w1, w2, M1, M2 = popw(y1), popw(y2), agemat(y1), agemat(y2)
    g = lambda v: group(v, G)
    f1, f2, cfa, cfb = M1 @ w1, M2 @ w2, M1 @ w2, M2 @ w1
    tot = clr(g(f2)) - clr(g(f1))
    ea = 0.5 * ((clr(g(cfa)) - clr(g(f1))) + (clr(g(f2)) - clr(g(cfb))))
    ma = 0.5 * ((g(cfa) - g(f1)) + (g(f2) - g(cfb)))
    return tot, ea, tot - ea, g(f2) - g(f1), ma
tot, ea, eb, mt, ma = decompose(2001, 2021)
D2 = pd.DataFrame([dict(part=p, total=tot[i], age_structure=ea[i], within_age=eb[i], min_total=mt[i], min_age=ma[i]) for i, p in enumerate(G8)])
D2.to_csv(os.path.join(R, "D_aging_decomposition.csv"), index=False)
tot16, ea16, _, mt16, ma16 = decompose(2001, 2016)
out["D"] = dict(fit=Dw.round(3).values.tolist(), dist_total=float(np.sqrt((tot ** 2).sum())), dist_age=float(np.sqrt((ea ** 2).sum())),
                dist_within=float(np.sqrt((eb ** 2).sum())), share_age_proj=float((ea @ tot) / (tot @ tot)),
                table=D2.round(3).values.tolist(), min_age_2001_2016=dict(zip(G8, np.round(ma16, 1))), min_tot_2001_2016=dict(zip(G8, np.round(mt16, 1))))

# ---------- E. 男女の差 ----------
rowsE = []
for grp, ag in [("総数", "計"), ("有業者", "計"), ("総数", "30～39歳"), ("総数", "40～49歳")]:
    for y in YEARS:
        m, f = vec(sel("男", grp, ag, y)), vec(sel("女", grp, ag, y))
        gm, gf = group(m, G8), group(f, G8)
        i_h, i_w = list(G8).index("家事関連"), list(G8).index("仕事・通勤")
        bal = lambda v: np.log(v[i_h] / v[i_w])
        rowsE.append(dict(group=grp, age=ag, year=y, dist_G8=adist(gm, gf), dist_G20=adist(m, f), dist_G4=adist(group(m, G4), group(f, G4)),
                          male_house=gm[i_h], female_house=gf[i_h], male_work=gm[i_w], female_work=gf[i_w],
                          bal_male=bal(gm), bal_female=bal(gf)))
E = pd.DataFrame(rowsE); E.to_csv(os.path.join(R, "E_gender_gap.csv"), index=False)
e0 = E[(E.group == "総数") & (E.age == "計")]
out["E"] = dict(dist=e0[["year", "dist_G8", "dist_G20", "dist_G4"]].round(3).values.tolist(),
                house=e0[["year", "male_house", "female_house", "male_work", "female_work"]].values.tolist(),
                worker=E[(E.group == "有業者")][["year", "dist_G8"]].round(3).values.tolist(),
                age30=E[(E.age == "30～39歳")][["year", "dist_G8"]].round(3).values.tolist())

# ---------- F. 曜日 ----------
rowsF = []
d15 = day[(day.group == "総数")]
for sex in ["総数", "男", "女"]:
    for dy in ["平日", "土曜日", "日曜日"]:
        q1 = d15[(d15.sex == sex) & (d15.day == dy) & (d15.year == 2001)]
        q2 = d15[(d15.sex == sex) & (d15.day == dy) & (d15.year == 2021)]
        x1, x2 = group(vec(q1), G8), group(vec(q2), G8)
        c = clr(x2) - clr(x1)
        r = dict(sex=sex, day=dy, dist_G8=adist(x1, x2))
        for i, gname in enumerate(G8): r["clr_" + gname] = c[i]; r["d_" + gname] = x2[i] - x1[i]
        rowsF.append(r)
F = pd.DataFrame(rowsF); F.to_csv(os.path.join(R, "F_weekday_2001_2021.csv"), index=False)
out["F"] = F[F.sex == "総数"][["day", "dist_G8", "d_休養・くつろぎ", "d_趣味・交際など", "d_仕事・通勤", "clr_趣味・交際など"]].round(3).values.tolist()

# ---------- G. 頑健性 ----------
rowsG = []
for z in [0.1, 0.5, 1.0, 2.0]:
    for gk in ["G4", "G8", "G20"]:
        G = GROUPS[gk]
        x96, x01, x16, x21 = [group(vec(sel(year=y)), G) for y in [1996, 2001, 2016, 2021]]
        rowsG.append(dict(zero=z, grouping=gk, d01_21=adist(x01, x21, z), d01_16=adist(x01, x16, z), d16_21=adist(x16, x21, z),
                          d96_01=adist(x96, x01, z),
                          share_last5=adist(x16, x21, z) / adist(x01, x21, z)))
Gr = pd.DataFrame(rowsG); Gr.to_csv(os.path.join(R, "G_robustness.csv"), index=False)
out["G"] = Gr.round(3).values.tolist()
# 5年ごと距離の偶然の幅：丸め（±0.5分）だけで出る距離
sims = []
x = vec(sel(year=2021))
for _ in range(2000):
    e = rng.uniform(-0.5, 0.5, size=(2, len(x)))
    sims.append(adist(group(np.maximum(x + e[0], 0.01), G8), group(np.maximum(x + e[1], 0.01), G8)))
out["G_round_95"] = float(np.quantile(sims, 0.95))
# 割合のまま（パーセントポイント）と log 比の順位の比較：G8, G20
for gk in ["G8", "G20"]:
    s = A[A.grouping == gk]
    out["G_rank_" + gk] = dict(pt_top=s.reindex(s.diff_pt.abs().sort_values(ascending=False).index).part.head(3).tolist(),
                               clr_top=s.reindex(s.clr_change.abs().sort_values(ascending=False).index).part.head(3).tolist(),
                               rho=spearmanr(s.diff_pt.abs(), s.clr_change.abs()).correlation)

json.dump(out, open(os.path.join(R, "summary.json"), "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:9000])

# ---------- H. コロナ前（2001→2016）でも同じ形か ----------
rowsH = []
for sex in ["男", "女"]:
    for ag in AGES:
        g1, g2, g3 = [group(vec(sel(sex=sex, ag=ag, year=y)), G8) for y in [2001, 2016, 2021]]
        rowsH.append(dict(sex=sex, age=ag, d01_16=adist(g1, g2), d16_21=adist(g2, g3), d01_21=adist(g1, g3),
                          tv2001=g1[5], tv2016=g2[5], tv2021=g3[5], rest2001=g1[6], rest2016=g2[6], rest2021=g3[6]))
H = pd.DataFrame(rowsH); H.to_csv(os.path.join(R, "H_pre_covid_by_age.csv"), index=False)
young = H[H.age.isin(["15～19歳", "20～24歳", "25～29歳"])]; old = H[H.age.isin(["65～69歳", "70歳以上"])]
out["H"] = dict(young_d01_16=young.d01_16.mean(), young_d16_21=young.d16_21.mean(), old_d01_16=old.d01_16.mean(), old_d16_21=old.d16_21.mean(),
                rho_age_order=spearmanr(H.d01_16, H.d01_21).correlation,
                tv_young=young[["sex", "age", "tv2001", "tv2016", "tv2021"]].values.tolist())
# 年齢別の0の扱い：G20 で0がある年齢の距離を置き換え値で比べる
rowsZ = []
for z in [0.1, 0.5, 1.0, 2.0]:
    ds = [adist(vec(sel(sex=s, ag=a, year=2001)), vec(sel(sex=s, ag=a, year=2021)), z) for s in ["男", "女"] for a in AGES]
    rowsZ.append(dict(zero=z, mean_G20=np.mean(ds), max_G20=np.max(ds),
                      order_rho_vs_05=None))
Zr = pd.DataFrame(rowsZ)
base = [adist(vec(sel(sex=s, ag=a, year=2001)), vec(sel(sex=s, ag=a, year=2021)), 0.5) for s in ["男", "女"] for a in AGES]
for i, z in enumerate([0.1, 0.5, 1.0, 2.0]):
    ds = [adist(vec(sel(sex=s, ag=a, year=2001)), vec(sel(sex=s, ag=a, year=2021)), z) for s in ["男", "女"] for a in AGES]
    Zr.loc[i, "order_rho_vs_05"] = spearmanr(ds, base).correlation
Zr.to_csv(os.path.join(R, "G_zero_by_age_G20.csv"), index=False)
nz = int(sum((vec(sel(sex=s, ag=a, year=y)) == 0).sum() for s in ["男", "女"] for a in AGES for y in [2001, 2021]))
out["G_zero_age"] = dict(n_zero_cells=nz, table=Zr.round(3).values.tolist())
json.dump(out, open(os.path.join(R, "summary.json"), "w"), ensure_ascii=False, indent=1, default=float)
print("H", json.dumps(out["H"], ensure_ascii=False, default=float)); print("Z", out["G_zero_age"])
