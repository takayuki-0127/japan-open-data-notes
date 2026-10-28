"""03 分析：北陸新幹線（2015年3月 長野―金沢）の効果が、隣の県（福井・岐阜など）にこぼれたかを推定し、F29 の直接効果と比べる。
- 隣の県それぞれを「処置」とみなした SCM・SDID・ASCM・単純な差の差（対照からは隣の県と石川・富山を外す）
- 対照の県すべてを順に「処置」とみなしたプラセボで、隣の県の推定値がどれくらい珍しいか
- 二元固定効果の差の差（石川・富山／隣／隣の隣 をまとめて1本の回帰で）と、距離帯ごとの効果
- F29 の直接効果が、対照に隣の県（岐阜）を入れていたことで変わったか
- 頑健性：隣の定義・期間・対照の選び方・総数と外国人・時点のプラセボ"""
import json
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from common import *

np.random.seed(SEED)
W = {c: load_panel(c) for c in ["japanese", "total", "foreign"]}
PREFS = list(W["japanese"].columns)
ADJ = adjacency()
D_KZ, D_TY = dist_from("石川"), dist_from("富山")
DMIN = pd.concat([D_KZ, D_TY], axis=1).min(axis=1)
RING2 = sorted((set().union(*[ADJ[p] for p in RING1_BORDER + RING1_LINE]) - set(TREATED + RING1_BORDER + RING1_LINE + EXCL_HOKKAIDO + EXCL_KYUSHU + EXCL_QUAKE)))
F29_DONORS = [p for p in PREFS if p not in TREATED + BASE_EXCL]                       # F29 の33県（岐阜を含む）
OTHER_EXCL = EXCL_HOKKAIDO + EXCL_KYUSHU + EXCL_QUAKE                                  # 波及とは別の理由で外す県
BASE = [p for p in PREFS if p not in TREATED + RING1_BORDER + RING1_LINE + OTHER_EXCL]  # 基本の対照：32県
STRICT = [p for p in BASE if p not in RING2]                                           # 隣の隣も外す
METRO = ["東京", "神奈川", "千葉", "埼玉", "大阪", "愛知", "京都", "兵庫"]
NOMETRO = [p for p in BASE if p not in METRO]
print("隣の隣", RING2); print("基本の対照", len(BASE), "厳しい対照", len(STRICT))
out = dict(ring2=RING2, base_donors=BASE, strict_donors=STRICT,
           dist_km={p: round(float(DMIN[p]), 1) for p in RING1_BORDER + RING1_LINE + RING2})


def pct(x): return float(np.expm1(x) * 100)


def est(y, tr, donors, open_=OPEN, methods=("SCM", "SDID", "ASCM", "DID")):
    if isinstance(tr, list):   # まとめるときは、SDID 以外は県の平均（対数）を1つの単位にする
        y = y.assign(_pool=y[tr].mean(axis=1)); trs, tr = tr, "_pool"
    else:
        trs = tr
    f = dict(SCM=lambda: scm(y, tr, donors, open_), SDID=lambda: sdid(y, trs, donors, open_),
             ASCM=lambda: ascm(y, tr, donors, open_, alpha=100.0), DID=lambda: did(y, tr, donors, open_))
    return {m: f[m]() for m in methods}


def placebo(y, donors, method="SDID", open_=OPEN):
    """対照の県を1つずつ「処置」とみなし、残りの対照で推定した値の分布"""
    vals = {}
    for p in donors:
        rest = [q for q in donors if q != p]
        r = sdid(y, p, rest, open_) if method == "SDID" else scm(y, p, rest, open_)
        vals[p] = float(r["att"])
    return pd.Series(vals)


def infer(att, plc):
    """プラセボの標準偏差で95%区間、絶対値の順位で両側の p 値"""
    sd = plc.std(ddof=1)
    rank = int((plc.abs() >= abs(att)).sum()) + 1
    return dict(lo=pct(att - 1.96 * sd), hi=pct(att + 1.96 * sd), rank=rank, n=len(plc) + 1, p=rank / (len(plc) + 1))


# ---- 1. 基本：隣の県ごとの効果（日本人）
y = prep(W["japanese"])
plc = {m: placebo(y, BASE, m) for m in ["SDID", "SCM"]}
pd.DataFrame(plc).to_csv(RES / "placebo_in_space.csv")
rows, main = [], {}
units = RING1_BORDER + RING1_LINE
for tr in units + ["福井＋岐阜"]:
    t = RING1_BORDER if tr == "福井＋岐阜" else tr
    R = est(y, t, BASE, methods=("SDID", "DID") if tr == "福井＋岐阜" else ("SCM", "SDID", "ASCM", "DID"))
    main[tr] = R
    for m, r in R.items():
        row = dict(unit=tr, group="隣（駅なし）" if tr in RING1_BORDER + ["福井＋岐阜"] else "隣（駅あり）",
                   method=m, att_pct=pct(r["att"]), dist_km=float(DMIN.get(tr, np.nan)))
        if m in plc: row.update(infer(r["att"], plc[m]))
        if "gap" in r and m != "DID":
            g = r["gap"]; row["pre_rmse"] = float(np.sqrt((g[g.index < OPEN] ** 2).mean()))
        rows.append(row)
# 直接効果（F29 の再現と、隣を対照から外した版）
for tr in TREATED:
    for lab, dn in [("F29の対照（岐阜を含む33県）", F29_DONORS), ("隣を外した対照（32県）", BASE), ("隣の隣も外した対照", STRICT)]:
        for m in ["SCM", "SDID"]:
            r = scm(y, tr, dn) if m == "SCM" else sdid(y, tr, dn)
            row = dict(unit=tr, group="直接：" + lab, method=m, att_pct=pct(r["att"]), dist_km=float(DMIN[tr]))
            if dn is BASE: row.update(infer(r["att"], plc[m]))
            rows.append(row)
E = pd.DataFrame(rows); E.to_csv(RES / "estimates_main.csv", index=False)
print(E.round(2).to_string())

# 年ごとの効果と系列（図用）
yr = []
ser = {}
for tr in units + ["福井＋岐阜"]:
    r = main[tr]["SDID"]; g = r["gap"]
    for Y, v in g.loc[OPEN:POST1].groupby(g.loc[OPEN:POST1].index.year).mean().items():
        yr.append(dict(unit=tr, year=Y, pct=pct(v)))
    if tr in RING1_BORDER:
        ser[tr + "_actual"] = y[tr]; ser[tr + "_SDID"] = r["synth"]; ser[tr + "_SCM"] = main[tr]["SCM"]["synth"]
pd.DataFrame(yr).to_csv(RES / "effect_by_year.csv", index=False)
pd.DataFrame(ser).to_csv(RES / "series_neighbors.csv")

# 全ての県の SDID の推定値と距離（距離による減衰の図）
dd = []
for p in BASE:
    dd.append(dict(pref=p, role="対照（プラセボ）", dist_km=float(DMIN[p]), att_pct=pct(plc["SDID"][p])))
for p in units:
    dd.append(dict(pref=p, role="隣（駅なし）" if p in RING1_BORDER else "隣（駅あり）", dist_km=float(DMIN[p]),
                   att_pct=float(E.query("unit==@p and method=='SDID'").att_pct.iloc[0])))
for p in TREATED:
    dd.append(dict(pref=p, role="処置", dist_km=0.0,
                   att_pct=float(E.query("unit==@p and method=='SDID' and group=='直接：隣を外した対照（32県）'").att_pct.iloc[0])))
pd.DataFrame(dd).to_csv(RES / "effect_vs_distance.csv", index=False)

# ---- 2. 二元固定効果の差の差（まとめて1本の回帰）
def twfe(y, groups, open_=OPEN, cluster=True):
    keep = [p for g in groups.values() for p in g]
    L = y[keep].stack().rename("y").reset_index(); L.columns = ["date", "pref", "y"]
    L["post"] = (L.date >= open_).astype(int)
    terms = []
    for k, g in groups.items():
        if k == "対照": continue
        c = "g_" + str(len(terms)); L[c] = L.pref.isin(g).astype(int) * L.post; terms.append((k, c))
    fml = "y ~ " + " + ".join(c for _, c in terms) + " + C(pref) + C(date)"
    m = smf.ols(fml, L).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(L.pref)[0]})
    return {k: dict(b=pct(m.params[c]), lo=pct(m.params[c] - 1.96 * m.bse[c]), hi=pct(m.params[c] + 1.96 * m.bse[c]),
                    p=float(m.pvalues[c])) for k, c in terms}

reg = {}
reg["基本（処置・隣・隣の隣）"] = twfe(y, {"処置": TREATED, "隣（駅なし）": RING1_BORDER, "隣（駅あり）": RING1_LINE,
                                    "隣の隣": RING2, "対照": STRICT})
# 距離帯（石川・富山の県庁所在地からの近い方の距離）
bands = {"0–150km": [p for p in BASE + RING1_BORDER if DMIN[p] <= 150],
         "150–250km": [p for p in BASE + RING1_BORDER if 150 < DMIN[p] <= 250],
         "250–400km": [p for p in BASE + RING1_BORDER if 250 < DMIN[p] <= 400]}
far = [p for p in BASE if DMIN[p] > 400]
reg["距離帯"] = twfe(y, {"処置": TREATED, **bands, "対照": far})
out["bands"] = bands
print(json.dumps(reg, ensure_ascii=False, indent=1))

# ---- 3. 頑健性：福井＋岐阜（または定義した「隣」）をまとめた SDID と、回帰の係数
# プラセボ区間（まとめた場合）：対照から同じ数の県をランダムに選んで「処置」とみなす
def pooled_ci(y, nb, donors, open_=OPEN, reps=60, seed=SEED):
    rng = np.random.default_rng(seed); k = len(nb); vals = []
    for _ in range(reps):
        fake = list(rng.choice(donors, k, replace=False)); rest = [q for q in donors if q not in fake]
        vals.append(sdid(y, fake if k > 1 else fake[0], rest, open_)["att"])
    att = sdid(y, nb if k > 1 else nb[0], donors, open_)["att"]; sd = np.std(vals, ddof=1)
    return dict(att_pct=pct(att), lo=pct(att - 1.96 * sd), hi=pct(att + 1.96 * sd))

dist_ring = [p for p in PREFS if DMIN[p] <= 160 and p not in TREATED + RING1_LINE + OTHER_EXCL]
chubu_ring = [p for p in CHUBU if p not in TREATED + RING1_LINE]
out["dist_ring"], out["chubu_ring"] = dist_ring, chubu_ring
rob = []
def add(kind, label, nb, donors, yy=None, open_=OPEN):
    yy = y if yy is None else yy
    r = pooled_ci(yy, nb, donors, open_); r.update(kind=kind, label=label, neighbors="・".join(nb), n_donors=len(donors))
    rob.append(r); print(kind, label, round(r["att_pct"], 2), round(r["lo"], 1), round(r["hi"], 1))

add("基本", "福井＋岐阜（県境・駅なし）", RING1_BORDER, BASE)
# 隣の定義
add("隣の定義", "福井だけ", ["福井"], BASE)
add("隣の定義", "岐阜だけ", ["岐阜"], BASE)
add("隣の定義", "県境を接する4県（新潟・長野を含む）", RING1_BORDER + RING1_LINE, BASE)
add("隣の定義", f"距離160km以内（{'・'.join(dist_ring)}）", dist_ring, [p for p in BASE if p not in dist_ring])
add("隣の定義", f"中部地方（{'・'.join(chubu_ring)}）", chubu_ring, [p for p in BASE if p not in chubu_ring])
add("隣の定義", "隣の隣（" + "・".join(RING2) + "）", RING2, STRICT)
# 期間
for lab, p0, p1 in [("事後を開業1年目まで（〜2016/2）", PRE0, pd.Timestamp("2016-02-01")),
                    ("事後を2017年末まで", PRE0, pd.Timestamp("2017-12-01")),
                    ("事前を2013年1月から", pd.Timestamp("2013-01-01"), POST1)]:
    add("期間", lab, RING1_BORDER, BASE, yy=prep(W["japanese"], pre0=p0, post1=p1))
# 対照の選び方
add("対照", "隣の隣も外す（" + str(len(STRICT)) + "県）", RING1_BORDER, STRICT)
add("対照", "大都市圏8都府県を外す", RING1_BORDER, NOMETRO)
# 系列
add("系列", "延べ宿泊者数の総数（日本人＋外国人）", RING1_BORDER, BASE, yy=prep(W["total"]))
add("系列", "外国人", RING1_BORDER, BASE, yy=prep(W["foreign"]))
# 時点のプラセボ：開業を2013年9月とみなす（事後は2015年2月まで）
add("時点のプラセボ", "開業を2013年9月とみなす", RING1_BORDER, BASE,
    yy=prep(W["japanese"], pre0=PRE0, post1=pd.Timestamp("2015-02-01"), open_=pd.Timestamp("2013-09-01")),
    open_=pd.Timestamp("2013-09-01"))
R = pd.DataFrame(rob); R.to_csv(RES / "robustness.csv", index=False)

# 回帰の頑健性：隣の定義ごと
regrob = []
for lab, nb in [("福井＋岐阜", RING1_BORDER), ("距離160km以内", dist_ring), ("中部地方", chubu_ring)]:
    g = {"処置": TREATED, "隣": nb, "対照": [p for p in STRICT if p not in nb]}
    r = twfe(y, g)["隣"]; r["label"] = lab; regrob.append(r)
reg["回帰・隣の定義"] = regrob
json.dump(reg, open(RES / "twfe.json", "w"), ensure_ascii=False, indent=1)

# 人泊数への換算（福井・岐阜、SDID、事後58か月の合計）
conv = {}
for tr in RING1_BORDER:
    act = W["japanese"].loc[OPEN:POST1, tr]; g = main[tr]["SDID"]["gap"].loc[OPEN:POST1]
    conv[tr] = dict(add_nights=float((act - act * np.exp(-g)).sum()), act_nights=float(act.sum()))
out["nights"] = conv
out["main"] = E.to_dict("records"); out["robustness"] = R.to_dict("records"); out["twfe"] = reg
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print("done")
