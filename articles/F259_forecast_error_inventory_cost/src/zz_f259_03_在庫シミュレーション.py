# F259 03 在庫シミュレーション
# 架空の小売チェーン「あおばストア（架空）」：6業態の需要（2017〜2019年の月平均＝100）を、
# F231 の予測（5モデル、起点は2か月ごと）で、2か月ごとに発注する（R=2）。
# リードタイム L＝0〜3か月、発注点補充方式（L+R か月の予測の合計＋安全在庫まで補充）、売れ残りは繰り越す。
# 費用は例として置いた比（実在の費用ではない）：在庫1単位1か月 h=1、売り逃し1単位 p（主は9）。
import json, math, numpy as np, pandas as pd
from scipy.stats import norm, spearmanr

R = 2; LS = [0, 1, 2, 3]; H_COST = 1.0; PS = [4, 9, 19]; P_MAIN = 9
TYPES = ["百貨店", "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "家電大型専門店"]
MODELS = ["季節ナイーブ", "季節ナイーブ＋伸び", "ETS", "SARIMA", "LightGBM"]
RULES = ["なし", "ルートの式", "合計の外れの分位点", "偏りだけ直す", "分位点（2か月持つ前提）"]
# 「偏りだけ直す」と「分位点（2か月持つ前提）」は、最初の結果を見た後に足した問い（計画にはない）
Q2 = "分位点（2か月持つ前提）"   # 安全在庫は次の発注まで R=2 か月持つので、目標を α=p/(p+R·h) にする
K_GRID = np.round(np.arange(-2.0, 8.01, 0.1), 2)                       # 後から見た最良の一定倍率（目安）

def mi(ym): y, m = map(int, ym.split("-")); return y * 12 + m - 1
def ym(i): return f"{i // 12}-{i % 12 + 1:02d}"
COV0, COV1 = mi("2020-03"), mi("2021-12")

d = pd.read_csv("data/demand_scaled.csv"); f = pd.read_csv("data/forecasts_scaled.csv.gz")
D = {k: dict(zip(g.ym.map(mi), g["需要"])) for k, g in d.groupby("業態")}
F = {}
for (k, mo, o), g in f.groupby(["業態", "モデル", "起点"]):
    F[(k, mo, mi(o))] = g.sort_values("h")["予測"].to_numpy()
ORIGINS = sorted({mi(o) for o in f["起点"].unique()})

def touches_covid(o, H): return not (o + H < COV0 or o + 1 > COV1)
def cum_err(k, mo, o, H): return sum(D[k][o + j] for j in range(1, H + 1)) - F[(k, mo, o)][:H].sum()

# 外れの表（全起点・H=1..6）
E = {}
for k in TYPES:
    for mo in MODELS:
        for o in ORIGINS:
            for H in range(1, 7): E[(k, mo, o, H)] = cum_err(k, mo, o, H)

from functools import lru_cache
@lru_cache(maxsize=None)
def pool(k, mo, o, H, covid_ok, pooled):
    ks = TYPES if pooled else [k]
    return np.array([E[(kk, mo, oo, H)] for kk in ks for oo in ORIGINS
                     if oo + H <= o and (covid_ok or not touches_covid(oo, H))])

def ss_value(rule, k, mo, o, L, alpha, cfg, kmult=None):
    H = L + R
    if rule == "なし": return 0.0
    if rule in ("ルートの式", "倍率"):
        e1 = pool(k, mo, o, 1, cfg["covid_ok"], cfg["pooled"])
        if len(e1) < cfg["min_n"]: raise ValueError("history")
        s1 = math.sqrt((e1 ** 2).mean())
        return (norm.ppf(alpha) if rule == "ルートの式" else kmult) * s1 * math.sqrt(H)
    e = pool(k, mo, o, H, cfg["covid_ok"], cfg["pooled"])
    if len(e) < cfg["min_n"]: raise ValueError("history")
    if rule == Q2: return float(np.quantile(e, alpha * 0 + cfg["p"] / (cfg["p"] + R * H_COST)))
    return float(np.quantile(e, alpha)) if rule == "合計の外れの分位点" else float(e.mean())

def segments(cfg):
    if cfg["covid_ok"]: return [(mi(cfg["start_pre"]), mi("2024-10"))]
    return [(mi(cfg["start_pre"]), mi("2020-02")), (mi("2021-12"), mi("2024-10"))]

def simulate(k, mo, L, p, rule, cfg, kmult=None, log=None):
    cfg = dict(cfg, p=p); alpha = p / (p + H_COST); H = L + R
    out = dict(hold=0.0, short=0.0, months=0, so_months=0, demand=0.0, lost=0.0)
    for s0, s1 in segments(cfg):
        # 始めの状態：ふだんの回り方と同じにする（直前の発注がまだ届いていない分を「途中」に置く）
        f0 = F[(k, mo, s0)]; ss0 = ss_value(rule, k, mo, s0, L, alpha, cfg, kmult); pipe = {}
        if L >= 2: onhand = ss0 + f0[:L - 2].sum(); pipe[s0 + L - 1] = f0[L - 2:L].sum()
        else: onhand = ss0 + f0[:L].sum()
        onhand = max(onhand, 0.0) if not cfg["backorder"] else onhand
        S = f0[:H].sum() + ss0; o0 = max(0.0, S - (onhand + sum(pipe.values()))); pipe[s0 + L + 1] = pipe.get(s0 + L + 1, 0.0) + o0
        for t in range(s0 + 1, s1 + 1):
            onhand += pipe.pop(t, 0.0); dem = D[k][t]
            if cfg["backorder"]:
                onhand -= dem; short = max(-onhand, 0.0); lost = short
            else:
                sales = min(max(onhand, 0.0), dem); lost = dem - sales; onhand -= sales; short = lost
            hold = H_COST * max(onhand, 0.0)
            out["hold"] += hold; out["short"] += p * short; out["months"] += 1
            out["so_months"] += lost > 1e-9; out["demand"] += dem; out["lost"] += lost
            order = 0.0; S = np.nan
            if t in ORIGINS_SET and t < s1:
                S = F[(k, mo, t)][:H].sum() + ss_value(rule, k, mo, t, L, alpha, cfg, kmult)
                order = max(0.0, S - (onhand + sum(pipe.values())))
                pipe[t + L + 1] = pipe.get(t + L + 1, 0.0) + order
            if log is not None:
                log.append((k, mo, L, rule, ym(t), round(dem, 6), round(onhand, 6), round(lost, 6), round(order, 6)))
    out["cost"] = out["hold"] + out["short"]; return out

ORIGINS_SET = set(ORIGINS)

def order_origins(cfg):
    return [o for s0, s1 in segments(cfg) for o in ORIGINS if s0 <= o < s1]

def coverage(k, mo, L, p, rule, cfg, part=None):
    cfg = dict(cfg, p=p); alpha = p / (p + H_COST); H = L + R; hit = []
    for o in order_origins(cfg):
        if touches_covid(o, H) and not cfg["covid_ok"]: continue
        if part == "前" and o >= COV0: continue
        if part == "後" and o < COV0: continue
        hit.append(E[(k, mo, o, H)] <= ss_value(rule, k, mo, o, L, alpha, cfg))
    return float(np.mean(hit))

def run(cfg, ps, rules, with_k=False, log=None):
    rows = []
    for k in TYPES:
        for mo in MODELS:
            for L in LS:
                for p in ps:
                    for r in rules:
                        o = simulate(k, mo, L, p, r, cfg, log=log if (p == P_MAIN and log is not None) else None)
                        rows.append(dict(業態=k, モデル=mo, L=L, p=p, 決め方=r, 費用=o["cost"] / o["months"],
                                         在庫費=o["hold"] / o["months"], 欠品費=o["short"] / o["months"],
                                         欠品月の割合=o["so_months"] / o["months"], 売り逃し率=o["lost"] / o["demand"],
                                         カバー率=coverage(k, mo, L, p, r, cfg)))
                    if with_k:
                        best = min(((simulate(k, mo, L, p, "倍率", cfg, kmult=km)["cost"], km) for km in K_GRID))
                        o = simulate(k, mo, L, p, "倍率", cfg, kmult=best[1])
                        rows.append(dict(業態=k, モデル=mo, L=L, p=p, 決め方="後から見た最良の倍率", 費用=o["cost"] / o["months"],
                                         在庫費=o["hold"] / o["months"], 欠品費=o["short"] / o["months"],
                                         欠品月の割合=o["so_months"] / o["months"], 売り逃し率=o["lost"] / o["demand"],
                                         カバー率=np.nan, 倍率=best[1]))
    return pd.DataFrame(rows)

BASE = dict(covid_ok=False, pooled=False, backorder=False, min_n=8, start_pre="2018-08")
log = []
A = run(BASE, PS, RULES, with_k=True, log=log)
A.round(6).to_csv("results/A_cost_main.csv", index=False)
pd.DataFrame(log, columns=["業態", "モデル", "L", "決め方", "月", "需要", "月末在庫", "売り逃し", "発注量"]).to_csv(
    "results/sim_log_p9.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})

# ---- H1：必要な安全在庫は √(L+R) より速く増えるか
rowsN = []
for k in TYPES:
    for mo in MODELS:
        e1 = np.array([E[(k, mo, o, 1)] for o in ORIGINS if not touches_covid(o, 1)]); s1 = math.sqrt((e1 ** 2).mean())
        for H in range(1, 7):
            e = np.array([E[(k, mo, o, H)] for o in ORIGINS if not touches_covid(o, H)])
            q = np.quantile(e, 0.9)
            rowsN.append(dict(業態=k, モデル=mo, H=H, RMSE倍=math.sqrt((e ** 2).mean()) / s1,
                              必要な倍率=q / (norm.ppf(0.9) * s1), 平均の外れ=e.mean()))
N = pd.DataFrame(rowsN); N.round(6).to_csv("results/B_needed_ss_by_H.csv", index=False)
# 隣の月どうしの外れの相関（同じ起点の h と h+1）
ac = []
for k in TYPES:
    for mo in MODELS:
        x = np.array([[D[k][o + 1] - F[(k, mo, o)][0], D[k][o + 2] - F[(k, mo, o)][1]] for o in ORIGINS if not touches_covid(o, 2)])
        ac.append(np.corrcoef(x[:, 0], x[:, 1])[0, 1])

# ---- H2：どの指標が費用の順位と合うか（業態×L の中で5モデルを並べる）
rowsM = []
for k in TYPES:
    for mo in MODELS:
        for L in LS:
            H = L + R; oo = [o for o in order_origins(BASE) if not touches_covid(o, H)]
            e1 = np.array([E[(k, mo, o, 1)] for o in oo]); a1 = np.array([D[k][o + 1] for o in oo])
            eH = np.array([E[(k, mo, o, H)] for o in oo]); al = P_MAIN / (P_MAIN + 1)
            ss = np.array([ss_value("合計の外れの分位点", k, mo, o, L, al, dict(BASE, p=P_MAIN)) for o in oo]); u = eH - ss
            rowsM.append(dict(業態=k, モデル=mo, L=L, MAPE_1か月先=np.mean(np.abs(e1) / a1) * 100,
                              RMSE_1か月先=math.sqrt((e1 ** 2).mean()), RMSE_合計=math.sqrt((eH ** 2).mean()),
                              偏り_合計=abs(eH.mean()), ピンボール損失=np.mean(np.maximum(al * u, (al - 1) * u))))
M = pd.DataFrame(rowsM)
c9 = A[(A.p == P_MAIN)].pivot_table(index=["業態", "モデル", "L"], columns="決め方", values="費用").reset_index()
M = M.merge(c9, on=["業態", "モデル", "L"]); M.round(6).to_csv("results/C_metrics_vs_cost.csv", index=False)
MET = ["MAPE_1か月先", "RMSE_1か月先", "RMSE_合計", "偏り_合計", "ピンボール損失"]
rho = []
for (k, L), g in M.groupby(["業態", "L"]):
    for cr in ["合計の外れの分位点", "なし"]:
        for m in MET: rho.append(dict(業態=k, L=L, 費用の決め方=cr, 指標=m, 順位相関=spearmanr(g[m], g[cr]).statistic))
RHO = pd.DataFrame(rho); RHO.round(6).to_csv("results/C_rank_corr.csv", index=False)

# ---- H3：決め方の差とモデルの差
def effects(df):
    g = df[df.決め方.isin(["なし", "ルートの式", "合計の外れの分位点"])]
    t = g.groupby(["業態", "L", "モデル", "決め方"]).費用.mean().unstack("決め方")
    rule_eff = (t.max(axis=1) - t.min(axis=1)).groupby(level=[0, 1]).mean()            # 同じモデルで決め方を変えた幅
    t2 = g.groupby(["業態", "L", "決め方", "モデル"]).費用.mean().unstack("モデル")
    model_eff = (t2.max(axis=1) - t2.min(axis=1)).groupby(level=[0, 1]).mean()         # 同じ決め方でモデルを変えた幅
    return float(rule_eff.mean()), float(model_eff.mean()), int((rule_eff > model_eff).sum()), len(rule_eff)

def summ(df, p=P_MAIN):
    g = df[df.p == p]; t = g.groupby(["決め方", "L"]).費用.mean().unstack()
    cov = g.groupby(["決め方", "L"]).カバー率.mean().unstack()
    return t, cov

t9, cov9 = summ(A)
t9.round(3).to_csv("results/D_cost_by_rule_L_p9.csv"); cov9.round(4).to_csv("results/D_coverage_by_rule_L_p9.csv")
byp = A.groupby(["p", "決め方", "L"]).費用.mean().unstack(); byp.round(3).to_csv("results/D_cost_by_p_rule_L.csv")
bym = A[A.p == P_MAIN].groupby(["モデル", "決め方"]).費用.mean().unstack(); bym.round(3).to_csv("results/D_cost_by_model_rule_p9.csv")
re, me, nwin, ng = effects(A[A.p == P_MAIN])

# ---- 頑健性
ROB = {}
def rob_summary(name, df, p=P_MAIN):
    t, cov = summ(df, p); r_, m_, w_, n_ = effects(df[df.p == p])
    sq, qu = t.loc["ルートの式"], t.loc["合計の外れの分位点"]
    ROB[name] = dict(ルートの式_費用=sq.round(2).to_dict(), 分位点_費用=qu.round(2).to_dict(),
                     ルートの式_カバー率=cov.loc["ルートの式"].round(3).to_dict(), 分位点_カバー率=cov.loc["合計の外れの分位点"].round(3).to_dict(),
                     決め方の幅=round(r_, 2), モデルの幅=round(m_, 2), 決め方の方が大きい組=f"{w_}/{n_}")
rob_summary("主（p=9・売り逃し・業態ごと・コロナ期を除く・8個から）", A)
rob_summary("p=4", A, 4); rob_summary("p=19", A, 19)
RB = []
for name, cfg in [("バックオーダー", dict(BASE, backorder=True)), ("6業態まとめて分位点", dict(BASE, pooled=True)),
                  ("コロナ期も含めて1本", dict(BASE, covid_ok=True)), ("外れが12個たまってから", dict(BASE, min_n=12, start_pre="2019-04"))]:
    df = run(cfg, [P_MAIN], RULES); df["頑健性"] = name; RB.append(df); rob_summary(name, df)
pd.concat(RB).round(6).to_csv("results/E_robustness.csv", index=False)

# コロナ前・後に分けたカバー率（p=9）
CP = []
for part in ["前", "後"]:
    for r in ["ルートの式", "合計の外れの分位点"]:
        for L in LS:
            CP.append(dict(区間=part, 決め方=r, L=L, カバー率=np.mean([coverage(k, mo, L, P_MAIN, r, BASE, part) for k in TYPES for mo in MODELS])))
CP = pd.DataFrame(CP); CP.round(4).to_csv("results/D_coverage_pre_post.csv", index=False)

# ---- 要約
q = A[A.p == P_MAIN]
sq_cov = cov9.loc["ルートの式"]; qu_cov = cov9.loc["合計の外れの分位点"]
best_k = q[q.決め方 == "後から見た最良の倍率"].groupby("L").倍率.median()
nb = N[N.H.isin([2, 3, 4, 5])].groupby("H")[["必要な倍率", "RMSE倍"]].median()
rho_mean = RHO.groupby(["費用の決め方", "指標"]).順位相関.mean().unstack(0)
val = bym["合計の外れの分位点"]
main = dict(
    目標カバー率=round(P_MAIN / (P_MAIN + 1), 3),
    ルートの式_カバー率=sq_cov.round(3).to_dict(), 分位点_カバー率=qu_cov.round(3).to_dict(),
    偏りだけ_カバー率=cov9.loc["偏りだけ直す"].round(3).to_dict(),
    費用_p9=t9.round(2).to_dict(orient="index"),
    最良倍率の中央値_L別=best_k.round(2).to_dict(), z=round(norm.ppf(0.9), 3),
    必要な倍率_H別の中央値=nb["必要な倍率"].round(3).to_dict(), RMSE倍_H別の中央値=nb["RMSE倍"].round(3).to_dict(),
    sqrtH={H: round(math.sqrt(H), 3) for H in [2, 3, 4, 5]},
    隣の月の外れの相関_中央値=round(float(np.median(ac)), 3), 隣の月の外れの相関_範囲=[round(min(ac), 3), round(max(ac), 3)],
    順位相関の平均=rho_mean.round(3).to_dict(),
    決め方の幅=round(re, 2), モデルの幅=round(me, 2), 決め方の方が大きい組=f"{nwin}/{ng}",
    モデル別費用_分位点=val.round(2).to_dict(),
    カバー率_前後=CP.pivot_table(index=["区間", "決め方"], columns="L", values="カバー率").round(3).reset_index().to_dict(orient="records"),
    頑健性=ROB)
json.dump(main, open("results/main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
