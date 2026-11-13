"""570 進展の途中で打ち切ったチェインラダーは、テールファクターを省くと最終損害をどれだけ少なく見るか（架空の支払データ）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "架空の支払データ（作成者が乱数で作成、seed 570）。記事570"
NA = 10                  # 事故年10年、最大10年分の進展が見える
SHAPE = 0.8              # 支払までの年数：ワイブル分布の形
MAXT = 40                # 40年目までに全額払う
REPS = 300

def scale_for(p10):
    """10年目までに p10 を払い終える尺度"""
    return 10 / (-np.log(1 - p10)) ** (1 / SHAPE)

def true_cdf(t, theta):
    return np.where(t >= MAXT, 1.0, 1 - np.exp(-(t / theta) ** SHAPE))

def simulate(rng, theta):
    tri = np.full((NA, NA), np.nan); ult = np.zeros(NA)
    for i in range(NA):
        n = rng.poisson(400)
        sev = rng.lognormal(np.log(100) - .5, 1.0, n)
        t = np.minimum(rng.weibull(SHAPE, n) * theta, MAXT)
        ult[i] = sev.sum()
        for d in range(NA - i):
            tri[i, d] = sev[t <= d + 1].sum()
    return tri, ult

def ldf(tri):
    return np.array([tri[~np.isnan(tri[:, d + 1]), d + 1].sum() / tri[~np.isnan(tri[:, d + 1]), d].sum() for d in range(NA - 1)])

def fit_tail(f, kind, first=3):
    """進展係数の (f−1) を年数に当てはめて、10年目より先を外挿する。first 年目以降の係数を使う"""
    age = np.arange(1, NA)                       # f[d] は d 年目→d+1 年目
    m = (age >= first) & (f > 1)
    y = np.log(f[m] - 1)
    x = age[m] if kind == "exp" else np.log(age[m])
    b, a = np.polyfit(x, y, 1)
    fut = np.arange(NA, MAXT)                     # 40年目まで外挿する
    xf = fut if kind == "exp" else np.log(fut)
    g = np.exp(a + b * xf)
    tail = float(np.exp(np.log1p(g).sum())) if b < 0 else np.nan
    return tail, a, b

def estimate(tri):
    f = ldf(tri); lat = np.array([tri[i, NA - 1 - i] for i in range(NA)])
    cdf = np.array([np.prod(f[NA - 1 - i:]) for i in range(NA)])
    out = {}
    for name, tail in (("none", 1.0), ("exp", fit_tail(f, "exp")[0]), ("power", fit_tail(f, "power")[0])):
        out[name] = (lat * cdf * tail, tail)
    return out, f

def main():
    rows = []; keep = {}
    for p10 in (0.95, 0.85, 0.75):
        theta = scale_for(p10); true_tail = 1 / float(true_cdf(np.array(10.0), theta))
        rng = np.random.default_rng(570)
        res = []
        for _ in range(REPS):
            tri, ult = simulate(rng, theta)
            est, f = estimate(tri)
            r = dict(true_tail=true_tail)
            for k, (u, tl) in est.items():
                r[k] = u.sum() / ult.sum() - 1; r[k + "_tail"] = tl
                r[k + "_ay"] = (u / ult - 1).tolist()
            r["true_tail_ult"] = None
            res.append(r)
        D = pd.DataFrame(res); keep[p10] = D
        rows.append(dict(p10=p10, theta=theta, true_tail=true_tail,
                         none=D["none"].median(), exp=D["exp"].median(), power=D["power"].median(),
                         none_mean=D["none"].mean(), exp_mean=D["exp"].mean(), power_mean=D["power"].mean(),
                         exp_p10=D["exp"].quantile(.1), exp_p90=D["exp"].quantile(.9), power_p10=D["power"].quantile(.1), power_p90=D["power"].quantile(.9),
                         exp_sd=D["exp"].std(), power_sd=D["power"].std(), none_sd=D["none"].std(),
                         exp_tail=D.exp_tail.median(), power_tail=D.power_tail.median(),
                         power_tail_p10=D.power_tail.quantile(.1), power_tail_p90=D.power_tail.quantile(.9)))
    T = pd.DataFrame(rows); T.to_csv(RES / "summary.csv", index=False)
    D = keep[0.85]
    by_ay = pd.DataFrame(dict(ay=np.arange(2016, 2026), none=np.median(np.stack(D.none_ay), 0),
                              exp=np.median(np.stack(D.exp_ay), 0), power=np.median(np.stack(D.power_ay), 0)))
    by_ay.to_csv(RES / "by_accident_year_p85.csv", index=False)

    # 1回分の三角形と、本当の進展係数・あてはめた曲線（p10=0.85）
    theta = scale_for(.85); rng = np.random.default_rng(5701)
    tri, ult = simulate(rng, theta); f = ldf(tri)
    pd.DataFrame([dict(ay=2016 + i, dev=d + 1, paid=tri[i, d]) for i in range(NA) for d in range(NA - i)]).to_csv(RES / "example_triangle_long.csv", index=False)
    te, ae, be = fit_tail(f, "exp"); tp, ap, bp = fit_tail(f, "power")
    ages = np.arange(1, 31)
    true_f = true_cdf(ages + 1.0, theta) / true_cdf(ages * 1.0, theta)

    # SQL：進展係数と (f−1) の対数の直線（指数の当てはめ）を DuckDB で
    con = duckdb.connect(); con.execute("SET threads=1")
    con.register("tri", pd.read_csv(RES / "example_triangle_long.csv"))
    q = con.execute((SQL / "a570_tail.sql").read_text()).df(); q.to_csv(RES / "sql_example.csv", index=False)
    match = bool(np.isclose(q.slope.iloc[0], be, rtol=1e-9) and np.isclose(q.intercept.iloc[0], ae, rtol=1e-9))

    J = dict(reps=REPS, summary=T.round(5).to_dict("records"), by_ay_p85=by_ay.round(5).to_dict("records"),
             example=dict(ldf=f.round(6).tolist(), exp_tail=te, power_tail=tp, true_tail=1 / float(true_cdf(np.array(10.0), theta)),
                          exp_fit=dict(a=ae, b=be), power_fit=dict(a=ap, b=bp)),
             sql_check=dict(sql=q.round(10).to_dict("records")[0], match=match))
    json.dump(J, open(RES / "a570_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：テールなし・指数・べき の最終損害のずれ
    fig, ax = plt.subplots(figsize=(8, 4.3)); xs = np.arange(len(T)); w = .26
    for j, (k, c, lab) in enumerate((("none", GRAY, "テールなし"), ("exp", ORANGE, "指数で外挿"), ("power", BLUE, "べき（逆べき）で外挿"))):
        b = ax.bar(xs + (j - 1) * w, T[k] * 100, w, color=c, label=lab); ax.bar_label(b, fmt="%+.1f%%", fontsize=8.5)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(xs, [f"10年で{p*100:.0f}%払う\n（本当のテール {t:.3f}）" for p, t in zip(T.p10, T.true_tail)])
    ax.set_ylabel("最終損害の合計の見込みのずれ（%）"); ax.legend(fontsize=9, loc="lower left")
    ax.set_title("テールを省くと少なく、外挿の形しだいで多くも少なくもなる（300回の中央値）")
    save(fig, "a570_by_tail.png", SRC)

    # 図2：進展係数と当てはめた曲線
    fig, ax = plt.subplots(figsize=(8, 4.3))
    ax.plot(ages, true_f - 1, color=INK, lw=1.2, label="本当の (係数−1)")
    ax.plot(np.arange(1, NA), f - 1, "o", color=GREEN, label="三角形から計算（1回分）")
    ax.plot(ages, np.exp(ae + be * ages), "--", color=ORANGE, label=f"指数で外挿（テール {te:.3f}）")
    ax.plot(ages, np.exp(ap + bp * np.log(ages)), "--", color=BLUE, label=f"べきで外挿（テール {tp:.3f}）")
    ax.axvline(NA - .5, color=GRAY, lw=.8); ax.text(NA - .3, .5, "← 見えている  見えていない →", fontsize=9, color=GRAY)
    ax.set_yscale("log"); ax.set_xlabel("経過年数"); ax.set_ylabel("進展係数 − 1（対数目盛）")
    ax.set_title(f"10年で85%払う場合（本当のテール {J['example']['true_tail']:.3f}）"); ax.legend(fontsize=8.5)
    save(fig, "a570_curves.png", SRC)

    # 図3：事故年ごと（p10=0.85）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for k, c, lab in (("none", GRAY, "テールなし"), ("exp", ORANGE, "指数で外挿"), ("power", BLUE, "べきで外挿")):
        ax.plot(by_ay.ay, by_ay[k] * 100, "o-", color=c, label=lab)
    ax.axhline(0, color=INK, lw=.8); ax.set_xlabel("事故年"); ax.set_ylabel("最終損害の見込みのずれ（%）")
    ax.set_title("10年で85%払う場合の事故年ごとのずれ（300回の中央値）"); ax.legend(fontsize=9)
    save(fig, "a570_by_ay.png", SRC)
    print(T.round(4).to_string()); print(by_ay.round(4).to_string()); print(J["example"], match)

if __name__ == "__main__":
    main()
