"""V2：どこで亡くなるか（病院・自宅・老人ホームなど）の割合は、いつ流れが変わったか。
年ごとの割合に、折れ線（区分線形）回帰を当てはめ、折れ目の数と位置を BIC で選ぶ（joinpoint 回帰の簡易版）"""
from common import *
from itertools import combinations

p = place_of_death()
cats = {"病院": "hospital", "診療所": "clinic", "介護医療院・老健": "roken", "老人ホーム": "nursing_home", "自宅": "home", "その他": "other"}
sh = pd.DataFrame({k: p[v] / p.total * 100 for k, v in cats.items()}); sh.index = p.year
sh.round(2).to_csv(RES / "v2_shares.csv", encoding="utf-8-sig")


def joinpoint(y, x, kmax=3, minseg=4):
    """折れ目 k 個（0〜kmax）の連続な区分線形回帰を全探索。BIC 最小のモデルを返す"""
    best = []
    for k in range(kmax + 1):
        cand = x[minseg:-minseg] if k else [None]
        bestk = None
        for bps in (combinations(cand, k) if k else [()]):
            if k and any(b2 - b1 < minseg for b1, b2 in zip(bps, bps[1:])): continue
            X = np.column_stack([np.ones_like(x), x] + [np.maximum(x - b, 0) for b in bps])
            beta, *_ = np.linalg.lstsq(X, y, rcond=None); rss = ((y - X @ beta) ** 2).sum()
            if bestk is None or rss < bestk[1]: bestk = (bps, rss, beta, X @ beta)
        n = len(y); bic = n * np.log(bestk[1] / n) + (2 + 2 * k) * np.log(n)  # 折れ目の位置も1パラメータと数える
        best.append(dict(k=k, bps=bestk[0], rss=bestk[1], bic=bic, beta=bestk[2], fit=bestk[3]))
    return min(best, key=lambda d: d["bic"]), best


rows, fits = [], {}
for col, start in [("病院", 1951), ("自宅", 1951), ("老人ホーム", 1995)]:
    s = sh.loc[start:, col]; x = s.index.values.astype(float); y = s.values
    b, allk = joinpoint(y, x)
    slopes = np.cumsum(b["beta"][1:])  # 各区間の傾き（%ポイント／年）
    edges = [int(x[0])] + [int(v) for v in b["bps"]] + [int(x[-1])]
    for i in range(len(slopes)):
        rows.append(dict(place=col, segment=f"{edges[i]}–{edges[i+1]}", slope_pt_per_year=slopes[i]))
    fits[col] = (x, b["fit"], b["bps"])
    print(col, "k=", b["k"], "breaks=", b["bps"], [round(d["bic"], 1) for d in allk])
seg = pd.DataFrame(rows); seg.round(3).to_csv(RES / "v2_joinpoint.csv", index=False, encoding="utf-8-sig"); print(seg.round(3).to_string())

s = {"hospital_1951": sh.loc[1951, "病院"], "home_1951": sh.loc[1951, "自宅"], "hospital_peak_year": int(sh["病院"].idxmax()), "hospital_peak": sh["病院"].max(),
     "hospital_2025": sh.loc[2025, "病院"], "home_min_year": int(sh["自宅"].idxmin()), "home_min": sh["自宅"].min(), "home_2025": sh.loc[2025, "自宅"],
     "home_2019": sh.loc[2019, "自宅"], "home_2022": sh.loc[2022, "自宅"], "nh_2005": sh.loc[2005, "老人ホーム"], "nh_2025": sh.loc[2025, "老人ホーム"],
     "roken_2025": sh.loc[2025, "介護医療院・老健"], "cross_year_hosp_home": int(sh.index[(sh["病院"] > sh["自宅"])][0]),
     "home_count_2025": p.set_index("year").loc[2025, "home"], "home_count_2005": p.set_index("year").loc[2005, "home"],
     "nh_count_2025": p.set_index("year").loc[2025, "nursing_home"], "nh_count_2005": p.set_index("year").loc[2005, "nursing_home"]}
pd.Series(s).to_csv(RES / "v2_summary.csv", header=["value"]); print(pd.Series(s).round(2))

note = "\n（死亡の場所別の割合。老人ホームは1995年から別掲。介護医療院・老健は2017年までは介護老人保健施設のみ）"
fig, ax = plt.subplots(figsize=(10, 4.8))
for col, c in [("病院", BLUE), ("自宅", ORANGE), ("老人ホーム", GREEN), ("介護医療院・老健", PURPLE), ("診療所", GRAY)]:
    ax.plot(sh.index, sh[col], color=c, lw=2, label=col)
ax.set_ylabel("死亡に占める割合（%）"); ax.legend(frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=9)
ax.set_title(f"病院で亡くなる人は{s['cross_year_hosp_home']}年に自宅を逆転し、{s['hospital_peak_year']}年がピーク")
fig.text(0.01, -0.12, SOURCE.replace("第5.4表・", "") + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "v2_shares.png"); plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, (col, c) in zip(axes, [("病院", BLUE), ("自宅", ORANGE), ("老人ホーム", GREEN)]):
    x, f, bps = fits[col]
    ax.scatter(sh.loc[int(x[0]):, col].index, sh.loc[int(x[0]):, col], s=8, color=c)
    ax.plot(x, f, color=INK, lw=1.4)
    for b in bps: ax.axvline(b, color=GRAY, ls="--", lw=0.8); ax.text(b, ax.get_ylim()[1] if False else f.max(), f" {int(b)}", fontsize=8.5, color=INK, va="top")
    ax.set_title(col); ax.set_ylabel("%")
fig.suptitle("折れ線回帰で見た「流れが変わった年」（破線）", y=1.03)
fig.text(0.01, -0.08, SOURCE.replace("第5.4表・", "") + "\n（連続な区分線形回帰。折れ目は0〜3個の全組み合わせからBICで選択（3つの上限で選ばれた）、区間は最低4年）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "v2_joinpoint.png"); plt.close(fig)
