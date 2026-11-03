"""03 分析：規模の遷移（マルコフ連鎖）・増減の内訳・予測の検証・シフトシェア。
乱数は使わない（決定的な計算のみ）。結果は results/ に出す。"""
import json, csv, re, pathlib
import numpy as np, pandas as pd
from scipy.optimize import minimize

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
t = pd.read_csv(ROOT / "data/transitions_long.csv")
stock = pd.read_csv(ROOT / "data/stock_2020_2025.csv")

H9 = ["<1", "1-3", "3-5", "5-10", "10-20", "20-30", "30-50", "50-100", "100+"]
H5 = ["<1", "1-3", "3-5", "5-10", "10+"]
M9 = {"none": "<1", "lt0.3": "<1", "0.3-1": "<1", "0.3-0.5": "<1", "0.5-1": "<1",
      "1-3": "1-3", "1-1.5": "1-3", "1.5-2": "1-3", "2-2.5": "1-3", "2.5-3": "1-3", "2-3": "1-3",
      "3-5": "3-5", "3-4": "3-5", "4-5": "3-5",
      "5-10": "5-10", "5-7.5": "5-10", "7.5-10": "5-10",
      "10-20": "10-20", "10-15": "10-20", "15-20": "10-20",
      "20-30": "20-30", "20-25": "20-30", "25-30": "20-30",
      "30-50": "30-50", "30-40": "30-50", "40-50": "30-50",
      "50-100": "50-100", "100+": "100+", "100-150": "100+", "150+": "100+",
      "15+": "10+", "50+": "10+"}
SPECIAL = {"exit", "unlinked_out", "exit_or_unlinked", "entry", "unlinked_in"}


def h5(c):
    if c in SPECIAL:
        return c
    m = M9[c]
    return m if m in H5 else "10+"


def h9(c):
    return c if c in SPECIAL else M9[c]


def nat(period):
    """全国の表（2005-2010 は 北海道＋都府県）"""
    if period == "2005-2010":
        g = t[(t.period == period) & t.area.isin(["北海道", "都府県"])].copy()
    else:
        g = t[(t.period == period) & (t.level == "全国")].copy()
    if period == "2005-2010":
        g["to"] = g["to"].replace({"exit_or_unlinked": "exit"})
    return g


def matrix(g, mapper, cls, exit_def="exit+unlinked"):
    """from×to の件数表 → 遷移確率（行＝前回の規模、列＝今回の規模＋退出）"""
    g = g.copy()
    g["f"] = g["from"].map(mapper); g["t"] = g["to"].map(mapper)
    c = g.groupby(["f", "t"]).n.sum().unstack(fill_value=0)
    cont = c.reindex(index=cls, columns=cls, fill_value=0)
    ex = c.reindex(index=cls).get("exit", pd.Series(0, index=cls)).fillna(0)
    un = c.reindex(index=cls).get("unlinked_out", pd.Series(0, index=cls)).fillna(0)
    if exit_def == "exit+unlinked":
        out = ex + un; denom = cont.sum(1) + out
    else:  # 接続不可を分母から除く（＝接続不可を、つながった経営体と同じ割合で振り分けるのと同じ）
        out = ex; denom = cont.sum(1) + out
    P = cont.div(denom, axis=0)
    P["exit"] = out / denom
    ent = c.reindex(columns=cls).loc[[x for x in ["entry", "unlinked_in"] if x in c.index]].sum()
    entry_only = c.reindex(columns=cls).loc[["entry"]].sum() if "entry" in c.index else ent * 0
    return P, cont, ent, entry_only, cont.sum(1) + ex + un


def updown(P, cls):
    k = len(cls); A = P[cls].values
    up = np.array([A[i, i + 1:].sum() for i in range(k)])
    dn = np.array([A[i, :i].sum() for i in range(k)])
    st = np.diag(A)
    return pd.DataFrame({"stay": st, "up": up, "down": dn, "exit": P["exit"].values}, index=cls)


res = {}
# ---------- A. 全国の遷移確率 ----------
tabs = []
for per in ["2005-2010", "2010-2015", "2015-2020"]:
    g = nat(per)
    for nm, mp, cls in (("H5", h5, H5), ("H9", h9, H9)):
        if per == "2005-2010" and nm == "H9":
            continue
        for ed in ("exit+unlinked", "exit_only"):
            if per == "2005-2010" and ed == "exit_only":
                continue
            P, cont, ent, ent0, n0 = matrix(g, mp, cls, ed)
            ud = updown(P, cls); ud["n_start"] = n0.values
            ud["period"] = per; ud["classes"] = nm; ud["exit_def"] = ed
            tabs.append(ud.reset_index().rename(columns={"index": "size"}))
            if nm == "H9" and ed == "exit+unlinked":
                P.round(4).to_csv(RES / f"transition_matrix_{per}.csv")
ud_all = pd.concat(tabs)
ud_all.to_csv(RES / "stay_up_down_exit.csv", index=False)

main = ud_all[(ud_all.period == "2015-2020") & (ud_all.classes == "H9") & (ud_all.exit_def == "exit+unlinked")].set_index("size")
res["main_2015_2020"] = main[["stay", "up", "down", "exit"]].round(4).to_dict()
# 全体の退出率
g = nat("2015-2020"); P, cont, ent, ent0, n0 = matrix(g, h9, H9)
res["overall_exit_2015_2020"] = float((P["exit"] * n0).sum() / n0.sum())
res["n2015"] = int(n0.sum()); res["n2020"] = int(cont.values.sum() + ent.sum())

# ---------- B. 大きい層の増え方の内訳（2015→2020） ----------
def decomp(per, thr_idx):
    g = nat(per); g = g.copy(); g["f"] = g["from"].map(h9); g["t"] = g["to"].map(h9)
    big = H9[thr_idx:]; small = H9[:thr_idx]
    tb = g[g.t.isin(big)]
    stay_big = tb[tb.f.isin(big)].n.sum()
    from_small = tb[tb.f.isin(small)].n.sum()
    ent_new = tb[tb.f == "entry"].n.sum(); ent_unl = tb[tb.f == "unlinked_in"].n.sum()
    fb = g[g.f.isin(big)]
    to_small = fb[fb.t.isin(small)].n.sum(); ex = fb[fb.t == "exit"].n.sum(); un = fb[fb.t == "unlinked_out"].n.sum()
    start = fb.n.sum(); end = stay_big + from_small + ent_new + ent_unl
    return dict(threshold=H9[thr_idx], start=int(start), end=int(end), stay=int(stay_big), from_smaller=int(from_small),
                entry=int(ent_new), unlinked_in=int(ent_unl), to_smaller=int(to_small), exit=int(ex), unlinked_out=int(un))

dec = []
for per in ["2010-2015", "2015-2020"]:
    for k in range(4, 9):
        r = decomp(per, k); r["period"] = per; dec.append(r)
dec = pd.DataFrame(dec); dec.to_csv(RES / "large_class_decomposition.csv", index=False)
res["decomp_2015_2020"] = dec[dec.period == "2015-2020"].to_dict("records")

# 規模ごとの「やめた数」と「上に移った数」（2015→2020、退出＝退出＋接続不可）
gg = nat("2015-2020").copy(); gg["f"] = gg["from"].map(h9); gg["t"] = gg["to"].map(h9)
flows = []
for i, c in enumerate(H9):
    x = gg[gg.f == c]
    flows.append(dict(size=c, n=int(x.n.sum()), exit=int(x[x.t.isin(["exit", "unlinked_out"])].n.sum()),
                      up=int(x[x.t.isin(H9[i + 1:])].n.sum()), up2=int(x[x.t.isin(H9[i + 2:])].n.sum())))
flows = pd.DataFrame(flows); flows["exit_per_up"] = flows.exit / flows.up
flows.to_csv(RES / "exit_vs_up_2015_2020.csv", index=False)
res["exit_vs_up"] = flows.round(3).to_dict("records")

# 経営耕地面積に占める大きい層の割合（2020・2025、総括編）
d = json.load(open(ROOT / "data/raw/f132_census_transitions.json", encoding="utf-8"))
R = list(csv.reader(d["2025_area__Ⅱ11"].splitlines()))
CLA = ["total", "lt0.3", "0.3-0.5", "0.5-1", "1-1.5", "1.5-2", "2-3", "3-5", "5-10", "10-20", "20-30", "30-50", "50-100", "100-150", "150+"]
def num(x):
    x = x.replace(",", "").strip()
    return 0.0 if x in ("", "-") else float(x)
for r in R:
    if len(r) > 30 and r[2].strip() == "(1)":
        a25 = dict(zip(CLA, map(num, r[3:18]))); a20 = dict(zip(CLA, map(num, r[18:33])))
area = []
for y, a in (("2020", a20), ("2025", a25)):
    s = pd.Series({k: v for k, v in a.items() if k != "total"}).groupby(lambda k: M9[k]).sum().reindex(H9)
    area.append(dict(year=y, total=a["total"], share_10plus=float(s[H9[4:]].sum() / a["total"]),
                     share_50plus=float(s[H9[7:]].sum() / a["total"]), share_lt3=float(s[H9[:2]].sum() / a["total"])))
res["area_share"] = area
pd.DataFrame(area).to_csv(RES / "area_share.csv", index=False)

# ---------- C. マルコフ連鎖で次の5年を当てる（後ろ向きの検証） ----------
s9 = stock[stock.no == 1].copy(); s9 = s9[s9["class"] != "total"]
s9["c"] = s9["class"].map(M9)
st20 = s9.groupby("c").n2020.sum().reindex(H9); st25 = s9.groupby("c").n2025.sum().reindex(H9)

# 2010-2015 の遷移で 2015→2020 を予測、2015-2020 の遷移で 2020→2025 を予測
P1015, c1015, ent1015, _, n2010 = matrix(nat("2010-2015"), h9, H9)
P1520, c1520, ent1520, _, n2015 = matrix(nat("2015-2020"), h9, H9)
act2015 = (c1015.sum(0) + ent1015).reindex(H9)
act2020 = (c1520.sum(0) + ent1520).reindex(H9)
pred = []
for lab, Pm, ent, start, act in (("2015→2020（2010-15の遷移）", P1015, ent1015, act2015, act2020),
                                  ("2020→2025（2015-20の遷移）", P1520, ent1520, act2020, st25),
                                  ("2020→2025（2010-15の遷移）", P1015, ent1015, act2020, st25)):
    for es in (1.0, "ratio"):
        base = n2010.sum() if Pm is P1015 else n2015.sum()
        e = ent.values if es == 1.0 else ent.values * (start.sum() / base)
        ph = start.values @ Pm[H9].values + e
        for c, p_, a_ in zip(H9, ph, act.values):
            pred.append(dict(case=lab, entry="同じ数" if es == 1.0 else "前回の数に比例", size=c, pred=p_, actual=a_))
pred = pd.DataFrame(pred); pred["err_pct"] = (pred.pred / pred.actual - 1) * 100
pred.to_csv(RES / "markov_backtest.csv", index=False)
summ = pred.groupby(["case", "entry"]).apply(lambda x: pd.Series(dict(
    total_pred=x.pred.sum(), total_act=x.actual.sum(), mape=np.mean(np.abs(x.err_pct)),
    big_pred=x[x["size"].isin(H9[4:])].pred.sum(), big_act=x[x["size"].isin(H9[4:])].actual.sum()))).reset_index()
summ["total_err_pct"] = (summ.total_pred / summ.total_act - 1) * 100
summ["big_err_pct"] = (summ.big_pred / summ.big_act - 1) * 100
summ.to_csv(RES / "markov_backtest_summary.csv", index=False)
res["backtest"] = summ.round(3).to_dict("records")
res["stock2025"] = st25.astype(int).to_dict(); res["stock2020"] = act2020.astype(int).to_dict()

# 同じ遷移が続いたら（2025→2030→2035、推測の目安）
fut = []
n = st25.values.astype(float)
for y in (2030, 2035):
    n = n @ P1520[H9].values + ent1520.values * (n.sum() / n2015.sum())
    fut.append(dict(year=y, total=n.sum(), **{c: v for c, v in zip(H9, n)}))
fut = pd.DataFrame(fut); fut.to_csv(RES / "projection_2030_2035.csv", index=False)
res["projection"] = fut.round(0).to_dict("records")

# ---------- D. シフトシェア（都道府県、2015→2020 の残った割合） ----------
gp = t[(t.period == "2015-2020") & (t.level == "都道府県")].copy()
gp["f"] = gp["from"].map(h9); gp["t"] = gp["to"].map(h9)
gn = nat("2015-2020").copy(); gn["f"] = gn["from"].map(h9); gn["t"] = gn["to"].map(h9)
def surv_by_class(g):
    x = g[g.f.isin(H9)]
    tot = x.groupby("f").n.sum(); sv = x[x.t.isin(H9)].groupby("f").n.sum()
    return tot.reindex(H9).fillna(0), sv.reindex(H9).fillna(0)
NT, NS = surv_by_class(gn); s_nat = NS / NT; s_all = NS.sum() / NT.sum()
REGION = {"北海道": "北海道", **{p: "東北" for p in ["青森", "岩手", "宮城", "秋田", "山形", "福島"]},
          **{p: "北陸" for p in ["新潟", "富山", "石川", "福井"]},
          **{p: "関東・東山" for p in ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "山梨", "長野"]},
          **{p: "東海" for p in ["岐阜", "静岡", "愛知", "三重"]},
          **{p: "近畿" for p in ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"]},
          **{p: "中国" for p in ["鳥取", "島根", "岡山", "広島", "山口"]},
          **{p: "四国" for p in ["徳島", "香川", "愛媛", "高知"]},
          **{p: "九州・沖縄" for p in ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]}}
ss = []
for p, g in gp.groupby("area"):
    T, S = surv_by_class(g)
    n0 = T.sum(); act = S.sum()
    nat_eff = n0 * s_all
    mix = (T * s_nat).sum() - nat_eff
    ss.append(dict(pref=p, region=REGION.get(p, "?"), n2015=n0, survivors=act, expected_nat=nat_eff, mix=mix,
                   regional=act - nat_eff - mix, surv_rate=act / n0, surv_rate_mix=(T * s_nat).sum() / n0,
                   share_10plus_2015=T[H9[4:]].sum() / n0))
ss = pd.DataFrame(ss)
w = ss.n2015
def wr2(y, x):
    xm = np.average(x, weights=w); ym = np.average(y, weights=w)
    b = np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2)
    e = y - (ym + b * (x - xm))
    return 1 - np.sum(w * e ** 2) / np.sum(w * (y - ym) ** 2), b
r2, b = wr2(ss.surv_rate.values, ss.surv_rate_mix.values)
vr = np.var(ss.surv_rate_mix - s_all) / np.var(ss.surv_rate - s_all)
ss.to_csv(RES / "shift_share_pref_2015_2020.csv", index=False)
reg = ss.groupby("region")[["n2015", "survivors", "expected_nat", "mix", "regional"]].sum()
reg["surv_rate"] = reg.survivors / reg.n2015
reg["mix_pt"] = reg.mix / reg.n2015 * 100; reg["regional_pt"] = reg.regional / reg.n2015 * 100
reg.to_csv(RES / "shift_share_region_2015_2020.csv")
res["shift_share"] = dict(national_survival=float(s_all), r2_mix=float(r2), slope=float(b),
                          sd_actual_pt=float(ss.surv_rate.std() * 100), sd_mix_pt=float(ss.surv_rate_mix.std() * 100),
                          sd_regional_pt=float((ss.regional / ss.n2015).std() * 100),
                          range_actual=[float(ss.surv_rate.quantile(.05)), float(ss.surv_rate.quantile(.95))],
                          region=reg[["surv_rate", "mix_pt", "regional_pt"]].round(3).to_dict("index"))
# 同じ分析を 2010→2015 でも（頑健性）
gp2 = t[(t.period == "2010-2015") & (t.level == "都道府県")].copy(); gp2["f"] = gp2["from"].map(h9); gp2["t"] = gp2["to"].map(h9)
gn2 = nat("2010-2015").copy(); gn2["f"] = gn2["from"].map(h9); gn2["t"] = gn2["to"].map(h9)
NT2, NS2 = surv_by_class(gn2); s_nat2 = NS2 / NT2; s_all2 = NS2.sum() / NT2.sum()
rows2 = []
for p, g in gp2.groupby("area"):
    T, S = surv_by_class(g); rows2.append((T.sum(), S.sum() / T.sum(), (T * s_nat2).sum() / T.sum()))
a2 = np.array(rows2); w = a2[:, 0]
r2b, bb = wr2(a2[:, 1], a2[:, 2])
res["shift_share_2010_2015"] = dict(national_survival=float(s_all2), r2_mix=float(r2b), slope=float(bb))

# ---------- E. 集計（周辺の数）だけで遷移を推定したら（設計の代替案の検証） ----------
def macro_markov(per):
    g = t[(t.period == per) & (t.level == "都道府県")].copy(); g["f"] = g["from"].map(h9); g["t"] = g["to"].map(h9)
    X, Y = [], []
    for p, x in g.groupby("area"):
        X.append(x[x.f.isin(H9)].groupby("f").n.sum().reindex(H9).fillna(0).values)
        Y.append(x[x.f.isin(H9) & x.t.isin(H9)].groupby("t").n.sum().reindex(H9).fillna(0).values)  # 継続した経営体の今回の規模別の数
    X = np.array(X); Y = np.array(Y); k = len(H9)
    # 上へも下へも「隣の区分まで」と「2つ先まで」を許す帯行列（真の遷移もほぼこの形）
    mask = np.array([[1 if abs(i - j) <= 2 else 0 for j in range(k)] for i in range(k)])
    idx = np.argwhere(mask == 1)
    sc = X.sum(1, keepdims=True)
    def f(v):
        P = np.zeros((k, k)); P[idx[:, 0], idx[:, 1]] = v
        return np.sum(((X @ P - Y) / sc) ** 2)
    v0 = np.array([0.8 if i == j else 0.02 for i, j in idx])
    cons = [{"type": "ineq", "fun": (lambda v, i=i: 1 - sum(v[m] for m in range(len(idx)) if idx[m][0] == i))} for i in range(k)]
    r = minimize(f, v0, bounds=[(0, 1)] * len(idx), constraints=cons, method="SLSQP", options=dict(maxiter=2000, ftol=1e-14))
    P = np.zeros((k, k)); P[idx[:, 0], idx[:, 1]] = r.x
    return P
Pm = macro_markov("2015-2020")
Ptrue = P1520[H9].values
mm = pd.DataFrame({"size": H9, "stay_true": np.diag(Ptrue), "stay_macro": np.diag(Pm),
                   "up_true": [Ptrue[i, i + 1:].sum() for i in range(9)], "up_macro": [Pm[i, i + 1:].sum() for i in range(9)],
                   "exit_true": P1520["exit"].values, "exit_macro": 1 - Pm.sum(1)})
mm.to_csv(RES / "macro_vs_micro_2015_2020.csv", index=False)
res["macro_vs_micro"] = mm.round(3).to_dict("records")

# ---------- F. 頑健性のまとめ ----------
rb = ud_all.copy()
def rbline(per, cl, ed):
    x = rb[(rb.period == per) & (rb.classes == cl) & (rb.exit_def == ed)].set_index("size")
    return dict(exit_small=float(x.exit.iloc[0]), up_small=float(x.up.iloc[0]),
                exit_top=float(x.exit.iloc[-1]), up_mid=x.up.round(3).to_dict(), exit=x.exit.round(3).to_dict())
res["robust"] = {f"{p}|{c}|{e}": rbline(p, c, e) for p, c, e in [
    ("2015-2020", "H9", "exit+unlinked"), ("2015-2020", "H9", "exit_only"), ("2010-2015", "H9", "exit+unlinked"),
    ("2010-2015", "H9", "exit_only"), ("2015-2020", "H5", "exit+unlinked"), ("2010-2015", "H5", "exit+unlinked"),
    ("2005-2010", "H5", "exit+unlinked")]}
# 北海道と都府県
for area in ["北海道", "都府県"]:
    g = t[(t.period == "2015-2020") & (t.area == area) & (t.level == "地域")]
    P, cont, ent, _, n0 = matrix(g, h9, H9)
    res[f"robust_{area}"] = updown(P, H9).round(3).to_dict()
json.dump(res, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: res[k] for k in ["overall_exit_2015_2020", "n2015", "n2020", "area_share", "shift_share", "shift_share_2010_2015"]}, ensure_ascii=False, indent=1, default=float))
print(main[["stay", "up", "down", "exit", "n_start"]].round(3))
print(flows)
print(dec[dec.period == "2015-2020"])
print(summ.round(2).to_string())
print(fut.round(0).to_string())
print(mm.round(3).to_string())
