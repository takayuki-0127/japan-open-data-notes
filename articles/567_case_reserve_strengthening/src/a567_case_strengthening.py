"""567 個別見積を途中から厚く積むと、発生ベースのチェインラダーはどれだけ多く見込むか（架空のデータ）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "架空の支払と個別見積（作成者が乱数で作成、seed 567）。記事567"
NA = 10                      # 事故年 2016〜2025、2025年末で評価
Y0 = 2016
SETTLE = np.array([.25, .25, .18, .12, .08, .05, .03, .02, .01, .01])   # 何年目に支払って終わるか
REPS = 300

def simulate(rng, a_old, a_new, cy0):
    """三角形（累計の支払・発生）と本当の最終損害を返す。cy0 以降の年末は個別見積を a_new 倍で積む"""
    paid = np.full((NA, NA), np.nan); inc = np.full((NA, NA), np.nan); ult = np.zeros(NA)
    paid_adj = None
    inc_adj = np.full((NA, NA), np.nan)
    for i in range(NA):
        n = rng.poisson(500)
        sev = rng.lognormal(np.log(100) - .5, 1.0, n)          # 平均100万円
        s = rng.choice(NA, n, p=SETTLE)
        noise = rng.lognormal(-.045, .3, n)                     # 見積のぶれ（平均1）
        ult[i] = sev.sum()
        for d in range(NA - i):
            cy = Y0 + i + d
            a = a_new if cy >= cy0 else a_old
            closed = s <= d
            pd_ = sev[closed].sum(); case_true = (sev[~closed] * noise[~closed]).sum()
            paid[i, d] = pd_; inc[i, d] = pd_ + a * case_true; inc_adj[i, d] = pd_ + a_new * case_true
    return paid, inc, inc_adj, ult

def ldf(tri):
    f = []
    for d in range(NA - 1):
        rows = ~np.isnan(tri[:, d + 1])
        f.append(tri[rows, d + 1].sum() / tri[rows, d].sum())
    return np.array(f)

def cl_ult(tri):
    f = ldf(tri); u = np.zeros(NA)
    for i in range(NA):
        d = NA - 1 - i; u[i] = tri[i, d] * np.prod(f[d:])
    return u

def run(a_old, a_new, cy0, seed):
    rng = np.random.default_rng(seed); out = []
    for _ in range(REPS):
        paid, inc, inc_adj, ult = simulate(rng, a_old, a_new, cy0)
        pd_now = np.array([paid[i, NA - 1 - i] for i in range(NA)])
        res_true = (ult - pd_now).sum()
        r = dict(true_res=res_true)
        for k, t in (("paid", paid), ("inc", inc), ("inc_adj", inc_adj)):
            u = cl_ult(t); r[k] = (u - pd_now).sum() / res_true - 1
            r[k + "_ult"] = u.sum() / ult.sum() - 1
        r["by_ay_inc"] = (cl_ult(inc) / ult).tolist(); r["by_ay_paid"] = (cl_ult(paid) / ult).tolist()
        out.append(r)
    return out

def summ(out):
    return {k: float(np.mean([o[k] for o in out])) for k in ("paid", "inc", "inc_adj", "paid_ult", "inc_ult", "inc_adj_ult")} | \
           {k + "_sd": float(np.std([o[k] for o in out])) for k in ("paid", "inc")}

def main():
    rows = []
    for a_new in (0.8, 0.9, 1.0, 1.1):
        for cy0 in (2025, 2023, 2021):
            o = run(.8, a_new, cy0, 567)
            rows.append(dict(a_old=.8, a_new=a_new, cy0=cy0, n_diag=2026 - cy0, **summ(o)))
            if a_new == 1.0 and cy0 == 2023:
                base = o
    T = pd.DataFrame(rows); T.to_csv(RES / "bias_by_scenario.csv", index=False)
    by_ay = pd.DataFrame(dict(ay=np.arange(Y0, Y0 + NA),
                              inc=np.mean([o["by_ay_inc"] for o in base], 0) - 1,
                              paid=np.mean([o["by_ay_paid"] for o in base], 0) - 1))
    by_ay.to_csv(RES / "by_accident_year_base.csv", index=False)

    # SQL：1回分の発生の三角形から、出来高で重み付けた進展係数を DuckDB で計算
    rng = np.random.default_rng(5670)
    paid, inc, inc_adj, ult = simulate(rng, .8, 1.0, 2023)
    long = pd.DataFrame([dict(ay=Y0 + i, dev=d + 1, incurred=inc[i, d]) for i in range(NA) for d in range(NA - i)])
    long.to_csv(RES / "example_incurred_triangle_long.csv", index=False)
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("tri", long)
    s = con.execute((SQL / "a567_chain_ladder.sql").read_text()).df()
    s.to_csv(RES / "sql_ldf_example.csv", index=False)
    py = ldf(inc); match = bool(np.allclose(s.sort_values("dev").ldf.values, py, rtol=0, atol=1e-12))
    ex = dict(ldf_python=py.round(6).tolist(), ldf_sql=s.sort_values("dev").ldf.round(6).tolist(), match=match,
              ldf_adj=ldf(inc_adj).round(6).tolist())

    J = dict(reps=REPS, base=summ(base), scenarios=T.round(5).to_dict("records"), sql_check=ex,
             by_ay=by_ay.round(5).to_dict("records"))
    json.dump(J, open(RES / "a567_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：積み方の変化の大きさごとの、支払備金の見込みのずれ（直近3年の年末から）
    t = T[T.cy0 == 2023]
    fig, ax = plt.subplots(figsize=(8, 4.3)); xs = np.arange(len(t)); w = .26
    for j, (k, c, lab) in enumerate((("paid", GRAY, "支払ベース"), ("inc", ORANGE, "発生ベース"), ("inc_adj", BLUE, "発生ベース（過去の見積を今の積み方に直す）"))):
        b = ax.bar(xs + (j - 1) * w, t[k] * 100, w, color=c, label=lab); ax.bar_label(b, fmt="%+.0f%%", fontsize=8)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(xs, [f"0.8→{a:.1f}" for a in t.a_new]); ax.set_xlabel("個別見積の積み方（本当の残りに対する倍率、2023年末から）")
    ax.set_ylabel("未払い分の見込みのずれ（%）"); ax.legend(fontsize=8, loc="upper left")
    ax.set_title("個別見積を厚くすると、発生ベースだけが多く見込む（300回の平均）")
    save(fig, "a567_by_level.png", SRC)

    # 図2：事故年ごと（0.8→1.0、2023年末から）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(by_ay.ay, by_ay.inc * 100, "o-", color=ORANGE, label="発生ベース")
    ax.plot(by_ay.ay, by_ay.paid * 100, "o-", color=GRAY, label="支払ベース")
    ax.axhline(0, color=INK, lw=.8); ax.set_xlabel("事故年"); ax.set_ylabel("最終損害の見込みのずれ（%）")
    ax.set_title("ずれは新しい事故年ほど大きい（0.8→1.0、2023年末から）"); ax.legend()
    save(fig, "a567_by_ay.png", SRC)

    # 図3：変えた時期ごと（発生ベース）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for cy0, c in ((2025, LIGHT), (2023, ORANGE), (2021, INK)):
        tt = T[T.cy0 == cy0]
        ax.plot(tt.a_new, tt.inc * 100, "o-", color=c, label=f"{cy0}年末から（直近{2026 - cy0}年）")
    ax.axhline(0, color=GRAY, lw=.8); ax.set_xlabel("新しい積み方の倍率（前は0.8）"); ax.set_ylabel("未払い分の見込みのずれ（%）")
    ax.set_title("発生ベースのずれは、変えた時期でも変わる"); ax.legend(fontsize=9)
    save(fig, "a567_by_timing.png", SRC)
    print(T.round(4).to_string()); print(by_ay.round(4).to_string()); print(ex)

if __name__ == "__main__":
    main()
