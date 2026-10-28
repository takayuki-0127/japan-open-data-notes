"""03 分析：線形計画で「作るものを変えたら、カロリーの自給率はどこまで上がるか」を、前提を変えて計算する。
変数：6作物（米・小麦・大豆・ばれいしょ・かんしょ・野菜）の面積、各作物の国産熱量 u、
      飼料用の農地のうち食用作物に回す面積（飼料用米・WCS用稲・畑の飼料作物）
目的：国産の供給熱量（1人1日 kcal）を最大にする
制約：・u ≤ κ×（1ha あたり kcal）×面積　・u ≤ 食べられる量（食べ方の前提）
      ・6作物の面積の合計 ≤ 今の6作物の面積＋飼料から回した面積　・米 ≤ 田で作れる面積
      ・（作付けの上限ありのとき）米以外の作物 ≤ 今の面積×k
      ・飼料の農地を減らすと、畜産物の国産熱量（飼料自給率を反映）が減る
"""
import json
import numpy as np, pandas as pd
from scipy.optimize import linprog
from common import RES

P = pd.read_csv(RES / "crop_params.csv")
G = json.load(open(RES / "params.json", encoding="utf-8"))
NAMES = list(P["作物"]); n = len(NAMES)
LAND = G["land"]
PADDY_EXTRA = 190600 + 119400  # 田で作っている麦・大豆（2024年 延べ面積・田）：米に戻せる面積の目安

def solve(diet="D1", landopt="L0", cropcap="C1", yf=1.0, lf=1.0, use_kappa=None, k=2.0,
          rice_mult=1.3, imo_mult=2.0, loss_mult=1.0, total_cap=True, allowed=None, keep_veg_soy=True, lo_frac=0.5):
    if use_kappa is None:
        use_kappa = True
    a0 = P["面積_ha"].values; kph = P["kcal_人日_per_万ha"].values / 1e4 * yf
    kap = P["kappa"].values if use_kappa else np.ones(n)
    D = P["供給熱量_kcal人日"].values.copy()
    if diet == "D1":
        cap = D.copy()
    elif diet == "D2":
        cap = D.copy(); cap[NAMES.index("米")] *= rice_mult
        cap[NAMES.index("ばれいしょ")] *= imo_mult; cap[NAMES.index("かんしょ")] *= imo_mult
    else:
        cap = np.full(n, np.inf)
    lam_f = G["livestock_dom"] * G["feed_B"] / (G["feed_B"] + G["feed_C"]) / (G["feed_land_upland_ha"] + G["wcs_ha"]) * loss_mult
    lam_r = G["livestock_dom"] * G["TDN_feed_rice"] / (G["feed_B"] + G["feed_C"]) / G["feed_rice_ha"] * loss_mult
    # 変数: A(n), u(n), xr(飼料用米), xw(WCS), xu(畑の飼料作物)
    nv = 2 * n + 3; iA = range(n); iu = range(n, 2 * n); XR, XW, XU = 2 * n, 2 * n + 1, 2 * n + 2
    c = np.zeros(nv); c[list(iu)] = -1; c[XR] = lam_r; c[XW] = lam_f; c[XU] = lam_f
    Aub, bub, names = [], [], []
    for i in range(n):  # u_i - kap*kph*A_i <= 0
        r = np.zeros(nv); r[n + i] = 1; r[i] = -kap[i] * kph[i]; Aub.append(r); bub.append(0); names.append("prod_" + NAMES[i])
    r = np.zeros(nv); r[list(iA)] = 1; r[XR] = r[XW] = r[XU] = -1; Aub.append(r); bub.append(a0.sum() * lf); names.append("land")
    ir = NAMES.index("米"); r = np.zeros(nv); r[ir] = 1; r[XR] = r[XW] = -1; Aub.append(r); bub.append((a0[ir] + PADDY_EXTRA) * lf); names.append("paddy")
    if total_cap and diet != "D3":
        r = np.zeros(nv); r[list(iu)] = 1; r[XR] = r[XW] = r[XU] = 0
        r[XR] = -lam_r; r[XW] = -lam_f; r[XU] = -lam_f
        Aub.append(r); bub.append(G["total_kcal"] - G["other_fixed"] - G["livestock_dom"]); names.append("total")
    bounds = [(0, None)] * n + [(0, cap[i] if np.isfinite(cap[i]) else None) for i in range(n)]
    if cropcap == "C1":
        lo = [a0[i] * lf if (keep_veg_soy and NAMES[i] in ("野菜", "大豆")) else a0[i] * lo_frac * lf for i in range(n)]
        bounds = [(lo[i], None if NAMES[i] == "米" else a0[i] * k * lf) for i in range(n)] + bounds[n:]
    if allowed is not None:
        bounds = [(0, 0) if NAMES[i] not in allowed else bounds[i] for i in range(n)] + bounds[n:]
    xr = G["feed_rice_ha"] if landopt in ("L1", "L2") else 0
    xw = G["wcs_ha"] if landopt in ("L1", "L2") else 0
    xu = G["feed_land_upland_ha"] if landopt == "L2" else 0
    bounds += [(0, xr), (0, xw), (0, xu)]
    res = linprog(c, A_ub=np.array(Aub), b_ub=np.array(bub), bounds=bounds, method="highs")
    assert res.status == 0, res.message
    x = res.x
    live = G["livestock_dom"] - lam_r * x[XR] - lam_f * (x[XW] + x[XU])
    dom = x[n:2 * n].sum() + G["other_fixed"] + live
    duals = dict(zip(names, -res.ineqlin.marginals))
    out = dict(diet=diet, land=landopt, cropcap=cropcap, domestic_kcal=dom, ss=dom / G["total_kcal"] * 100,
               livestock=live, crops_kcal=x[n:2 * n].sum(), shadow_land_per_10kha=duals["land"] * 1e4,
               shadow_paddy_per_10kha=duals["paddy"] * 1e4, feed_rice_used=x[XR], wcs_used=x[XW], upland_feed_used=x[XU])
    for i, nm in enumerate(NAMES):
        out["面積_" + nm] = x[i]; out["kcal_" + nm] = x[n + i]
    return out

def potential_all_land(allowed, rice_paddy=True):
    """（参考）農林水産省の「食料自給力指標」に近い見方：延べ面積のすべて（3,861千ha）をこの6作物に回したら、作物だけで何 kcal か。
    米は田の延べ面積まで。食べ方の上限・補正係数なし。畜産・魚・果実などは入れない。"""
    kph = P["kcal_人日_per_万ha"].values / 1e4
    c = np.zeros(n)
    for i, nm in enumerate(NAMES):
        c[i] = -kph[i] if nm in allowed else 0
    A = [np.ones(n)]; b = [LAND["延べ_田畑計_作付（栽培）延べ面積"]]
    if rice_paddy:
        r = np.zeros(n); r[NAMES.index("米")] = 1; A.append(r); b.append(LAND["延べ_田_作付（栽培）延べ面積"])
    bounds = [(0, None) if nm in allowed else (0, 0) for nm in NAMES]
    res = linprog(c, A_ub=np.array(A), b_ub=np.array(b), bounds=bounds, method="highs")
    return -res.fun, dict(zip(NAMES, res.x))

if __name__ == "__main__":
    base = dict(domestic_kcal=G["domestic_official"], ss=G["domestic_official"] / G["total_kcal"] * 100)
    print("今（2024年度）", base)
    rows = []
    for d in ["D1", "D2", "D3"]:
        for L in ["L0", "L1", "L2"]:
            for C in ["C0", "C1"]:
                rows.append(solve(d, L, C))
    S = pd.DataFrame(rows); S.to_csv(RES / "scenarios.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(S[["diet", "land", "cropcap", "domestic_kcal", "ss", "livestock", "shadow_land_per_10kha", "shadow_paddy_per_10kha"] +
            [c for c in S.columns if c.startswith("面積_")]].round(1).to_string())
    # 今の面積で再現できるか（検算）：今の面積を固定して計算すると 860 kcal に戻るはず
    a0 = P["面積_ha"].values; kph = P["kcal_人日_per_万ha"].values / 1e4
    chk = np.minimum(P["kappa"].values * kph * a0, P["供給熱量_kcal人日"].values).sum() + G["other_fixed"] + G["livestock_dom"]
    print("検算：今の面積での国産熱量", round(chk, 1), "公表", G["domestic_official"])
    # 頑健性：中心の2つのシナリオで前提を1つずつ変える
    R = []
    for ref in [("D1", "L2", "C1"), ("D2", "L1", "C1")]:
        b = solve(*ref)
        tests = [("収量 −10%", dict(yf=0.9)), ("収量 +10%", dict(yf=1.1)), ("農地 −10%", dict(lf=0.9)),
                 ("補正係数κなし", dict(use_kappa=False)), ("作付けの上限 今の1.5倍", dict(k=1.5)),
                 ("作付けの上限 今の3倍", dict(k=3.0)), ("作付けの上限なし", dict(cropcap="C0")), ("減らす下限（今の半分）をなくす", dict(lo_frac=0.0)), ("野菜・大豆も減らしてよい", dict(keep_veg_soy=False)),
                 ("飼料の農地を減らしたときの畜産の減り ×2", dict(loss_mult=2.0)), ("同 ×0.5", dict(loss_mult=0.5))]
        if ref[0] == "D2":
            tests += [("米を食べる量 1.2倍まで", dict(rice_mult=1.2)), ("米を食べる量 1.5倍まで", dict(rice_mult=1.5)),
                      ("いもを食べる量 1.5倍まで", dict(imo_mult=1.5)), ("いもを食べる量 4倍まで", dict(imo_mult=4.0))]
        for lab, kw in tests:
            args = dict(diet=ref[0], landopt=ref[1], cropcap=ref[2]); args.update(kw)
            o = solve(**args); R.append(dict(ref="-".join(ref), test=lab, ss=o["ss"], diff=o["ss"] - b["ss"], base_ss=b["ss"]))
    R = pd.DataFrame(R)
    PT = []
    for lab, al in [("米・小麦・大豆・野菜だけ", ["米", "小麦", "大豆", "野菜"]), ("いもも使う", NAMES)]:
        v, a = potential_all_land(al); PT.append(dict(pattern=lab, kcal_crops=v, **{"面積_" + k: x for k, x in a.items()}))
    PT = pd.DataFrame(PT); PT.to_csv(RES / "potential_all_land.csv", index=False, encoding="utf-8-sig"); print(PT.round(0).to_string())
    R.to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig"); print(R.round(2).to_string())
