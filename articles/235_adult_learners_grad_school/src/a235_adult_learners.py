"""235 大学・大学院に入る社会人は、どれだけいるのか
- 大学院：年齢別入学者数の表の「上記『計』のうち社会人」（修士 2000〜、博士・専門職学位 2003〜2025年度）
- 大学（学部）：年齢別入学者数（2015〜2025年度）の25歳以上・30歳以上の入学者（社会人の数そのものは表にないので年齢で近づける）"""
import json, re
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, FIG, C, GRAY, find, note
import gakko_parse as g

COURSES = ["修士", "博士", "専門職学位"]


def age_sum(ages, lo):
    s = 0
    for k, v in ages.items():
        m = re.match(r"(\d+)", k)
        if m and int(m.group(1)) >= lo and v == v:
            s += v
    return s


def build():
    rows, urows = [], []
    for y in range(2000, 2026):
        for c, v in g.entrants_by_age(find(y, "AG")).items():
            t, s = v["total"], v["social"]
            rows.append(dict(year=y, 課程=c, 入学者=t[0], 入学者_女=t[2], 社会人=s[0], 社会人_女=s[2],
                             入学者_30歳以上=age_sum(v["ages"], 30), 入学者_25歳以上=age_sum(v["ages"], 25)))
        f = find(y, "AU")
        if f:
            t, a = g.undergrad_by_age(f)
            ages = {k: v[0] for k, v in a.items()}
            urows.append(dict(year=y, 入学者=t[0], 入学者_女=t[2], 入学者_25歳以上=age_sum(ages, 25), 入学者_30歳以上=age_sum(ages, 30),
                              入学者_22歳以上=age_sum(ages, 22), 女_25歳以上=sum(a[k][2] for k in a if re.match(r"(\d+)", k) and int(re.match(r"(\d+)", k).group(1)) >= 25)))
    gdf, udf = pd.DataFrame(rows), pd.DataFrame(urows)
    gdf.to_csv(DATA / "grad_entrants_social.csv", index=False)
    udf.to_csv(DATA / "undergrad_entrants_age.csv", index=False)
    return gdf, udf


def main():
    gdf, udf = build()
    gdf["社会人の割合"] = gdf.社会人 / gdf.入学者 * 100
    gdf["社会人の女性割合"] = gdf.社会人_女 / gdf.社会人 * 100
    gdf["30歳以上の割合"] = gdf.入学者_30歳以上 / gdf.入学者 * 100
    tot = gdf[gdf.year >= 2003].groupby("year")[["社会人", "入学者"]].sum()
    tot["社会人の割合"] = tot.社会人 / tot.入学者 * 100
    udf["25歳以上の割合"] = udf.入学者_25歳以上 / udf.入学者 * 100
    udf["30歳以上の割合"] = udf.入学者_30歳以上 / udf.入学者 * 100
    gdf.round(2).to_csv(RES / "a235_grad_social_by_course.csv", index=False)
    tot.round(2).to_csv(RES / "a235_grad_social_total.csv")
    udf.round(3).to_csv(RES / "a235_undergrad_age.csv", index=False)

    p = gdf.pivot(index="year", columns="課程", values="社会人")
    r = gdf.pivot(index="year", columns="課程", values="社会人の割合")
    f = gdf.pivot(index="year", columns="課程", values="社会人の女性割合")
    o = gdf.pivot(index="year", columns="課程", values="30歳以上の割合")
    S = {}
    S["grad_social_2025"] = int(tot.loc[2025, "社会人"]); S["grad_entrants_2025"] = int(tot.loc[2025, "入学者"])
    S["grad_social_share_2025"] = round(tot.loc[2025, "社会人の割合"], 1)
    S["grad_social_2003"] = int(tot.loc[2003, "社会人"]); S["grad_social_2004"] = int(tot.loc[2004, "社会人"])
    S["grad_social_share_peak"] = [int(tot.社会人の割合.idxmax()), round(tot.社会人の割合.max(), 1)]
    for c in COURSES:
        S[f"{c}_social_2025"] = int(p.loc[2025, c]); S[f"{c}_share_2025"] = round(r.loc[2025, c], 1)
        S[f"{c}_share_peak"] = [int(r[c].idxmax()), round(r[c].max(), 1)]
        S[f"{c}_female_share_of_social_2025"] = round(f.loc[2025, c], 1)
        S[f"{c}_30plus_share_2025"] = round(o.loc[2025, c], 1)
    S["修士_social_2000"] = int(p.loc[2000, "修士"]); S["修士_share_2000"] = round(r.loc[2000, "修士"], 1)
    S["修士_social_peak"] = [int(p["修士"].idxmax()), int(p["修士"].max())]
    S["修士_30plus_share_2000"] = round(o.loc[2000, "修士"], 1)
    S["博士_social_2003"] = int(p.loc[2003, "博士"]); S["博士_share_2003"] = round(r.loc[2003, "博士"], 1)
    S["博士_share_2010"] = round(r.loc[2010, "博士"], 1)
    S["博士_entrants_2003_2025"] = [int(gdf[(gdf.課程 == "博士") & (gdf.year == 2003)].入学者.iloc[0]), int(gdf[(gdf.課程 == "博士") & (gdf.year == 2025)].入学者.iloc[0])]
    S["博士_nonsocial_2003_2025"] = [S["博士_entrants_2003_2025"][0] - S["博士_social_2003"], S["博士_entrants_2003_2025"][1] - S["博士_social_2025"]]
    s1, s2 = S["博士_social_2003"], S["博士_social_2025"]; n1, n2 = S["博士_nonsocial_2003_2025"]
    rr = lambda a, b: a / (a + b) * 100
    S["博士_share_decomp_pt"] = {"社会人の増加": round((rr(s2, n1) - rr(s1, n1) + rr(s2, n2) - rr(s1, n2)) / 2, 1),
                                "社会人以外の減少": round((rr(s1, n2) - rr(s1, n1) + rr(s2, n2) - rr(s2, n1)) / 2, 1)}
    S["専門職_social_2005"] = int(p.loc[2005, "専門職学位"])
    u = udf.set_index("year")
    S["ug_25plus"] = {int(y): [int(u.loc[y, "入学者_25歳以上"]), round(u.loc[y, "25歳以上の割合"], 2)] for y in u.index}
    S["ug_30plus_2015_2025"] = [int(u.loc[2015, "入学者_30歳以上"]), int(u.loc[2025, "入学者_30歳以上"])]
    S["ug_female_share_25plus_2025"] = round(u.loc[2025, "女_25歳以上"] / u.loc[2025, "入学者_25歳以上"] * 100, 1)
    S["ratio_grad_vs_ug_2025"] = round(S["grad_social_2025"] / u.loc[2025, "入学者_25歳以上"], 1)
    json.dump(S, open(RES / "a235_summary.json", "w"), ensure_ascii=False, indent=1)

    # 図1 社会人入学者の数（課程別、積み上げ）
    fig, ax = plt.subplots(figsize=(8, 4.6))
    yrs = p.index
    ax.stackplot(yrs, [p[c].fillna(0) for c in COURSES], labels=["修士課程", "博士課程", "専門職学位課程"], colors=C[:3], alpha=.85)
    ax.set_title("大学院の社会人入学者（人）")
    ax.set_xlim(2000, 2025); ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.text(2001, 1500, "2000〜02年度は\n修士課程のみ", fontsize=8, color="#555")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    note(ax); fig.savefig(FIG / "a235_grad_social_count.png"); plt.close(fig)
    # 図2 入学者に占める社会人の割合
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for c, col in zip(COURSES, C):
        ax.plot(r.index, r[c], color=col, lw=2.2, label=c + "課程")
        ax.annotate(f"{r.loc[2025, c]:.1f}%", (2025, r.loc[2025, c]), xytext=(4, 0), textcoords="offset points", va="center", color=col, fontsize=9)
    ax.plot(tot.index, tot.社会人の割合, color=GRAY, lw=1.6, ls="--", label="大学院計（2003年度〜）")
    ax.set_title("大学院の入学者に占める社会人の割合（%）"); ax.set_xlim(2000, 2027); ax.set_ylim(0, 90)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    note(ax); fig.savefig(FIG / "a235_grad_social_share.png"); plt.close(fig)
    # 図3 学部の25歳以上の入学者
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(u.index, u.入学者_25歳以上, color=C[0], alpha=.8, label="25歳以上の入学者（人）")
    ax.bar(u.index, u.入学者_30歳以上, color=C[1], alpha=.9, label="うち30歳以上")
    for y in u.index:
        ax.text(y, u.loc[y, "入学者_25歳以上"] + 60, f"{u.loc[y, '25歳以上の割合']:.2f}%", ha="center", fontsize=8, color="#333")
    ax.set_title("大学（学部）の25歳以上の入学者（数字は入学者全体に占める割合）")
    ax.set_xticks(u.index); ax.tick_params(axis="x", labelsize=9); ax.legend(frameon=False, fontsize=9)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    note(ax); fig.savefig(FIG / "a235_undergrad_25plus.png"); plt.close(fig)
    print(json.dumps(S, ensure_ascii=False))


if __name__ == "__main__":
    main()
