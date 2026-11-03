"""集計表（周辺表）だけから「それらしい個票」を合成し、元の多重クロス表と元の分析（F139）をどこまで再現できるかを比べる。

本当の表：就業構造基本調査 第52表を整形した 6変数の多重クロス表
  男女(2)×年齢(7)×雇用形態(4)×本業の所得(6)×本業の就業時間(4)×副業の有無(2) = 2,688 セル
合成の方法（どれも「公表されている程度の小さな表」だけを使う）
  S0 独立          : 1変数の表 6枚
  S1 BN（木）       : 2変数の表 5枚（相互情報量の最大全域木＝Chow–Liu）
  S2 IPF 副業の星形 : 「副業×各属性」5枚＋「男女×年齢」1枚
  S3 IPF 2変数すべて: 2変数の表 15枚
  S4 BN（親2つ）    : 3変数までの表（BIC で構造を選ぶ。親は2つまで）
  S5 IPF 2変数＋副業を含む3変数: 2変数の表 15枚＋「副業×2属性」の3変数の表 10枚
  S6 IPF 3変数すべて: 3変数の表 20枚（上限の目安）
合成した「個票」は、合成した同時分布から多項分布で引いたセルの件数として持つ（個人の記録は作らない・公開しない）。
件数は本当の推計人口÷100（F139 と同じ仮定：1標本あたり約100人分）。各方法 R 回引き直す。

入力: data/side_job_long.csv
出力: results/*.csv, results/summary.json
"""
import json, itertools, sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"; OUT.mkdir(exist_ok=True)
SEED = 147
R = int(sys.argv[1]) if len(sys.argv) > 1 else 20

df0 = pd.read_csv(ROOT / "data" / "side_job_long.csv")

def inc_group(s):
    c = int(s.split("_")[0])
    return {1: "1_100万円未満", 2: "1_100万円未満", 3: "2_100〜199万円", 4: "2_100〜199万円", 5: "3_200〜299万円", 6: "3_200〜299万円",
            7: "4_300〜499万円", 8: "4_300〜499万円", 9: "5_500〜699万円", 10: "5_500〜699万円"}.get(c, "6_700万円以上")

VARS = ["sex", "age", "emp", "inc", "hours", "side"]
JP = {"sex": "男女", "age": "年齢", "emp": "雇用形態", "inc": "所得", "hours": "就業時間", "side": "副業"}

def true_table(year, inc16=False):
    d = df0[(df0.year == year) & (df0.hours != "総数")].copy()
    d["inc"] = d.income if inc16 else d.income.map(inc_group)
    g = d.groupby(VARS).n.sum()
    levels = [sorted(d[v].unique()) for v in VARS]
    idx = pd.MultiIndex.from_product(levels, names=VARS)
    arr = g.reindex(idx, fill_value=0).values.reshape([len(l) for l in levels]).astype(float)
    return arr, levels

# ---------------- 合成の方法 ----------------
def margin(P, axes):
    other = tuple(i for i in range(P.ndim) if i not in axes)
    return P.sum(axis=other, keepdims=True)

ROUND = {"unit": None, "total": None}
def src_margin(P, axes):
    """合成する側が見る周辺表。ROUND が指定されていれば、人数に戻して unit 人単位に丸めた表（公表値の丸めをまねる）"""
    m = margin(P, axes)
    if ROUND["unit"]:
        u, t = ROUND["unit"], ROUND["total"]
        m = np.round(m * t / u) * u / t
    return m

def ipf(P_true, margins, iters=2000, tol=1e-12):
    Q = np.full(P_true.shape, 1.0 / P_true.size)
    targets = [(ax, src_margin(P_true, ax)) for ax in margins]
    if ROUND["unit"]:
        iters = 300  # 丸めた表どうしは少し食い違うので、完全には収束しない
    for it in range(iters):
        mx = 0.0
        for ax, tg in targets:
            cur = margin(Q, ax)
            with np.errstate(divide="ignore", invalid="ignore"):
                f = np.where(cur > 0, tg / cur, 0.0)
            Q = Q * f
            mx = max(mx, float(np.abs(cur - tg).max()))
        if mx < tol:
            break
    return Q / Q.sum(), it + 1

def mutual_info(P, a, b):
    pab = src_margin(P, (a, b)); pa = pab.sum(axis=b, keepdims=True); pb = pab.sum(axis=a, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(pab > 0, pab * np.log(pab / (pa * pb)), 0.0)
    return float(t.sum())

def chow_liu(P):
    G = nx.Graph()
    for a, b in itertools.combinations(range(P.ndim), 2):
        G.add_edge(a, b, weight=mutual_info(P, a, b))
    T = nx.maximum_spanning_tree(G)
    edges = [tuple(sorted(e)) for e in T.edges()]
    Q, _ = ipf(P, edges)  # 木の辺の2変数表に合わせた IPF は、木の BN と同じ分布になる
    return Q, edges

def bn_family_score(C, child, parents, N):
    axes = tuple(sorted((child,) + tuple(parents)))
    cnt = src_margin(C / N, axes) * N
    par = cnt.sum(axis=child, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        ll = np.where(cnt > 0, cnt * np.log(cnt / np.broadcast_to(par, cnt.shape)), 0.0).sum()
    r = C.shape[child]; q = int(np.prod([C.shape[p] for p in parents])) if parents else 1
    return ll - 0.5 * np.log(N) * (r - 1) * q

def bn_learn(P, N, maxp=2, penalty="bic"):
    """周辺表（3変数まで）だけで計算できる BIC で、親2つまでの DAG を山登りで選ぶ"""
    C = P * N
    k = P.ndim
    parents = {i: () for i in range(k)}
    def fam(i, ps):
        s = bn_family_score(C, i, ps, N)
        if penalty == "aic":  # AIC は罰則を log(N)/2 → 1 に置き換える
            r = C.shape[i]; q = int(np.prod([C.shape[p] for p in ps])) if ps else 1
            s += 0.5 * np.log(N) * (r - 1) * q - (r - 1) * q
        return s
    score = {i: fam(i, ()) for i in range(k)}
    def acyclic(par):
        G = nx.DiGraph(); G.add_nodes_from(range(k))
        for c, ps in par.items():
            for p in ps: G.add_edge(p, c)
        return nx.is_directed_acyclic_graph(G)
    while True:
        best = (0.0, None)
        for c in range(k):
            for p in range(k):
                if p == c: continue
                ps = parents[c]
                if p in ps:  # 削除
                    new = tuple(x for x in ps if x != p)
                    d = fam(c, new) - score[c]
                    if d > best[0] + 1e-9: best = (d, ("del", c, p, new))
                    # 向きを逆に
                    if len(parents[p]) < maxp:
                        par2 = dict(parents); par2[c] = new; par2[p] = tuple(sorted(parents[p] + (c,)))
                        if acyclic(par2):
                            d2 = d + fam(p, par2[p]) - score[p]
                            if d2 > best[0] + 1e-9: best = (d2, ("rev", c, p, new))
                elif len(ps) < maxp:
                    new = tuple(sorted(ps + (p,)))
                    par2 = dict(parents); par2[c] = new
                    if acyclic(par2):
                        d = fam(c, new) - score[c]
                        if d > best[0] + 1e-9: best = (d, ("add", c, p, new))
        if best[1] is None:
            break
        op, c, p, new = best[1]
        parents[c] = new; score[c] = fam(c, new)
        if op == "rev":
            parents[p] = tuple(sorted(parents[p] + (c,))); score[p] = fam(p, parents[p])
    # 同時分布 = Π P(x_i | 親)
    Q = np.ones(P.shape)
    for i in range(k):
        ps = parents[i]
        fa = src_margin(P, tuple(sorted((i,) + ps)))
        pa = fa.sum(axis=i, keepdims=True) if ps else np.ones([1] * k) * fa.sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            cond = np.where(pa > 0, fa / pa, 0.0)
        Q = Q * cond
    Q = Q / Q.sum()
    return Q, parents

def methods(P, N, bn_penalty="bic"):
    k = P.ndim
    side = VARS.index("side"); sex = VARS.index("sex"); age = VARS.index("age")
    one = [(i,) for i in range(k)]
    two = list(itertools.combinations(range(k), 2))
    three = list(itertools.combinations(range(k), 3))
    star = [tuple(sorted((i, side))) for i in range(k) if i != side] + [(sex, age)]
    out = {}
    out["S0 独立"] = (ipf(P, one)[0], len(one), sum(P.shape))
    Qt, edges = chow_liu(P)
    out["S1 BN（木）"] = (Qt, len(edges), int(sum(P.shape[a] * P.shape[b] for a, b in edges)))
    out["S2 IPF 副業の星形"] = (ipf(P, star)[0], len(star), int(sum(P.shape[a] * P.shape[b] for a, b in star)))
    out["S3 IPF 2変数すべて"] = (ipf(P, two)[0], len(two), int(sum(P.shape[a] * P.shape[b] for a, b in two)))
    Qb, parents = bn_learn(P, N, penalty=bn_penalty)
    fams = [tuple(sorted((i,) + ps)) for i, ps in parents.items() if ps]
    out["S4 BN（親2つ）"] = (Qb, len(fams), int(sum(np.prod([P.shape[a] for a in f]) for f in fams)))
    side3 = [f for f in three if side in f]
    sel = two + side3
    out["S5 IPF 2変数＋副業を含む3変数"] = (ipf(P, sel)[0], len(sel), int(sum(np.prod([P.shape[a] for a in f]) for f in sel)))
    out["S6 IPF 3変数すべて"] = (ipf(P, three)[0], len(three), int(sum(np.prod([P.shape[a] for a in f]) for f in three)))
    info = {"chow_liu_edges": [[VARS[a], VARS[b]] for a, b in edges],
            "bn_parents": {VARS[i]: [VARS[p] for p in ps] for i, ps in parents.items()}}
    return out, info

# ---------------- 評価 ----------------
def tvd(P, Q): return 0.5 * float(np.abs(P - Q).sum())
def hell(P, Q): return float(np.sqrt(0.5 * ((np.sqrt(P) - np.sqrt(Q)) ** 2).sum()))
def avg_marg_tvd(P, Q, order):
    return float(np.mean([tvd(margin(P, ax), margin(Q, ax)) for ax in itertools.combinations(range(P.ndim), order)]))

def to_long(C, levels):
    idx = pd.MultiIndex.from_product(levels, names=VARS)
    return pd.DataFrame({"n": C.ravel()}, index=idx).reset_index()

def wide(d, keys):
    g = d.groupby(keys + ["side"]).n.sum().unstack("side").fillna(0)
    for c in ("副業あり", "副業なし"):
        if c not in g: g[c] = 0.0
    g["N"] = g["副業あり"] + g["副業なし"]
    g = g[g.N > 0].reset_index()
    g["p"] = g["副業あり"] / g.N
    return g

FACT = {"sex": "C(sex, Treatment('男'))", "age": "C(age, Treatment('35〜44歳'))", "emp": "C(emp, Treatment('正規'))"}
def inc_term(levels_inc):
    ref = "4_300〜499万円" if "4_300〜499万円" in levels_inc else sorted(levels_inc)[len(levels_inc) // 2]
    return f"C(inc, Treatment('{ref}'))"

def analysis(C_long, w_scale):
    """F139 の主な分析を、件数の表 C_long に当てはめる。w_scale は件数を標本の人数に直す割り算の数"""
    res = {}
    INC = inc_term(C_long.inc.unique())
    REF = " + ".join(list(FACT.values()) + [INC])
    g = wide(C_long, ["sex", "age", "emp", "inc"])
    fit = lambda gg, rhs: smf.glm("p ~ " + rhs, data=gg, family=sm.families.Binomial(), var_weights=gg.N / w_scale).fit()
    m0 = fit(g, "1"); m_emp = fit(g, FACT["emp"]); m1 = fit(g, REF)
    m2 = fit(g, REF + f" + {FACT['age']}:{FACT['emp']}")
    res["dev_emp"] = 1 - m_emp.deviance / m0.deviance
    res["dev_main"] = 1 - m1.deviance / m0.deviance
    res["dev_ageemp"] = 1 - m2.deviance / m0.deviance
    ci = m1.conf_int()
    coefs = {}
    for name in m1.params.index:
        if name == "Intercept": continue
        coefs[name] = (float(m1.params[name]), float(ci.loc[name, 0]), float(ci.loc[name, 1]))
    res["coefs"] = coefs
    # 粗い女性のオッズ比
    gs = wide(C_long, ["sex"]).set_index("sex").p
    res["crude_female_OR"] = float((gs["女"] / (1 - gs["女"])) / (gs["男"] / (1 - gs["男"])))
    res["adj_female_OR"] = float(np.exp(m1.params[[n for n in m1.params.index if "sex" in n][0]]))
    # 年齢×雇用形態の率（正規の 15〜24歳 と 75歳以上）
    ae = wide(C_long, ["emp", "age"]).set_index(["emp", "age"]).p
    res["reg_young"] = float(ae.get(("正規", "15〜24歳"), np.nan)); res["reg_old"] = float(ae.get(("正規", "75歳以上"), np.nan))
    res["irr_young"] = float(ae.get(("非正規", "15〜24歳"), np.nan)); res["irr_old"] = float(ae.get(("非正規", "75歳以上"), np.nan))
    # 就業時間のオッズ比（主効果＋就業時間）
    gh = wide(C_long, ["sex", "age", "emp", "inc", "hours"])
    mh = fit(gh, REF + " + C(hours, Treatment('200日以上・週35〜59時間'))")
    for name in mh.params.index:
        if "hours" in name:
            c = mh.conf_int().loc[name]
            res["coefs"][name] = (float(mh.params[name]), float(c[0]), float(c[1]))
    res["rate"] = float(C_long[C_long.side == "副業あり"].n.sum() / C_long.n.sum())
    return res

def overlap(a, b):
    """Karr ほか（2006）の信頼区間の重なり。a, b は (est, lo, hi)"""
    lo, hi = max(a[1], b[1]), min(a[2], b[2])
    if hi <= lo: return 0.0
    return 0.5 * ((hi - lo) / (a[2] - a[1]) + (hi - lo) / (b[2] - b[1]))

def compare(true_res, syn_res):
    keys = [k for k in true_res["coefs"] if k in syn_res["coefs"]]
    d = np.array([abs(syn_res["coefs"][k][0] - true_res["coefs"][k][0]) for k in keys])
    ov = np.array([overlap(true_res["coefs"][k], syn_res["coefs"][k]) for k in keys])
    sign = np.mean([np.sign(syn_res["coefs"][k][0]) == np.sign(true_res["coefs"][k][0]) for k in keys])
    return dict(mean_abs_logOR=float(d.mean()), max_abs_logOR=float(d.max()), ci_overlap=float(ov.mean()),
                ci_overlap_min=float(ov.min()), share_overlap_gt0=float((ov > 0).mean()), sign_agree=float(sign))

def run(year=2022, inc16=False, scale=100.0, R=R, bn_penalty="bic", round_margins=None, tag="主"):
    P_cnt, levels = true_table(year, inc16)
    total = P_cnt.sum()
    N = int(round(total / scale))
    ROUND["unit"] = round_margins; ROUND["total"] = total  # 合成側が見る周辺表だけを丸める
    P = P_cnt / total; Psrc = P
    true_long = to_long(P_cnt, levels)
    true_res = analysis(true_long, scale)
    meths, info = methods(Psrc, N, bn_penalty)
    ROUND["unit"] = None
    rng = np.random.default_rng(SEED)
    rows, raw = [], []
    for name, (Q, ntab, ncell) in meths.items():
        pop = dict(method=name, tag=tag, year=year, n_tables=ntab, n_cells=ncell,
                   tvd_pop=tvd(P, Q), hell_pop=hell(P, Q), m3_pop=avg_marg_tvd(P, Q, 3), m4_pop=avg_marg_tvd(P, Q, 4))
        pop_res = analysis(to_long(Q * N, levels), 1.0)  # 引き直す前の合成分布そのもの
        cp = compare(true_res, pop_res)
        pop.update({f"pop_{k}": v for k, v in cp.items()})
        reps = []
        for r in range(R):
            C = rng.multinomial(N, Q.ravel()).reshape(Q.shape).astype(float)
            Pc = C / C.sum()
            sres = analysis(to_long(C, levels), 1.0)
            cmp_ = compare(true_res, sres)
            rec = dict(rep=r, tvd=tvd(P, Pc), hell=hell(P, Pc), m3=avg_marg_tvd(P, Pc, 3), m4=avg_marg_tvd(P, Pc, 4),
                       dev_emp=sres["dev_emp"], dev_main=sres["dev_main"], dev_ageemp=sres["dev_ageemp"],
                       crude_f=sres["crude_female_OR"], adj_f=sres["adj_female_OR"],
                       reg_young=sres["reg_young"], reg_old=sres["reg_old"], irr_young=sres["irr_young"], irr_old=sres["irr_old"],
                       rate=sres["rate"], **cmp_)
            reps.append(rec)
            for k, v in sres["coefs"].items():
                raw.append(dict(method=name, tag=tag, rep=r, term=k, est=v[0], lo=v[1], hi=v[2]))
        rp = pd.DataFrame(reps)
        for c in rp.columns:
            if c == "rep": continue
            pop[c] = float(rp[c].mean()); pop[c + "_sd"] = float(rp[c].std())
        rows.append(pop)
    # 本当の表から引き直したとき（同じ N の標本のぶれ）＝ 再現の「天井」
    reps = []
    for r in range(R):
        C = rng.multinomial(N, P.ravel()).reshape(P.shape).astype(float)
        sres = analysis(to_long(C, levels), 1.0)
        cmp_ = compare(true_res, sres)
        reps.append(dict(tvd=tvd(P, C / C.sum()), hell=hell(P, C / C.sum()), m3=avg_marg_tvd(P, C / C.sum(), 3),
                         m4=avg_marg_tvd(P, C / C.sum(), 4), dev_emp=sres["dev_emp"], dev_main=sres["dev_main"],
                         dev_ageemp=sres["dev_ageemp"], crude_f=sres["crude_female_OR"], adj_f=sres["adj_female_OR"],
                         reg_young=sres["reg_young"], reg_old=sres["reg_old"], irr_young=sres["irr_young"], irr_old=sres["irr_old"],
                         rate=sres["rate"], **cmp_))
        for k, v in sres["coefs"].items():
            raw.append(dict(method="本当の表から引き直し", tag=tag, rep=r, term=k, est=v[0], lo=v[1], hi=v[2]))
    rp = pd.DataFrame(reps)
    ceil = dict(method="本当の表から引き直し", tag=tag, year=year, n_tables=1, n_cells=int(P.size), tvd_pop=0.0, hell_pop=0.0, m3_pop=0.0, m4_pop=0.0)
    for c in rp.columns:
        ceil[c] = float(rp[c].mean()); ceil[c + "_sd"] = float(rp[c].std())
    rows.append(ceil)
    truth = dict(method="本当の表", tag=tag, year=year, dev_emp=true_res["dev_emp"], dev_main=true_res["dev_main"],
                 dev_ageemp=true_res["dev_ageemp"], crude_f=true_res["crude_female_OR"], adj_f=true_res["adj_female_OR"],
                 reg_young=true_res["reg_young"], reg_old=true_res["reg_old"], irr_young=true_res["irr_young"],
                 irr_old=true_res["irr_old"], rate=true_res["rate"])
    rows.append(truth)
    for k, v in true_res["coefs"].items():
        raw.append(dict(method="本当の表", tag=tag, rep=-1, term=k, est=v[0], lo=v[1], hi=v[2]))
    return pd.DataFrame(rows), pd.DataFrame(raw), info, N

if __name__ == "__main__":
    allrows, allraw, infos = [], [], {}
    specs = [
        dict(tag="主（2022・所得6区分）"),
        dict(tag="2017年", year=2017),
        dict(tag="所得16区分", inc16=True),
        dict(tag="標本1/10（N÷10）", scale=1000.0),
        dict(tag="BN の構造を AIC で選ぶ", bn_penalty="aic"),
        dict(tag="周辺表を1千人単位に丸める", round_margins=1000.0),
    ]
    for sp in specs:
        tag = sp.pop("tag")
        rr = R if tag.startswith("主") else max(5, R // 2)
        rows, raw, info, N = run(R=rr, tag=tag, **sp)
        info["N"] = N
        infos[tag] = info
        allrows.append(rows); allraw.append(raw)
        print(tag, "N=", N, flush=True)
        print(rows[["method", "n_tables", "n_cells", "tvd_pop", "tvd", "m3", "mean_abs_logOR", "ci_overlap", "dev_emp", "dev_ageemp", "adj_f"]].round(4).to_string(), flush=True)
    res = pd.concat(allrows); raw = pd.concat(allraw)
    res.to_csv(OUT / "method_comparison.csv", index=False)
    # 係数は主の分析だけ、各方法の平均で保存
    rm = raw[raw.tag.str.startswith("主")].groupby(["method", "term"])[["est", "lo", "hi"]].mean().reset_index()
    rm.to_csv(OUT / "coefficients_main.csv", index=False)
    json.dump(dict(infos=infos, R_main=R, seed=SEED), open(OUT / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
