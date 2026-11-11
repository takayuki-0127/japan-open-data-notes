"""236 理系の学部に進む女子は、どれだけ増えたのか
大学（学部）の関係学科別学生数（2000〜2025年度、男女別）から、分野ごとの女子学生の割合を出す。
頑健性：1年次の学生だけで同じ割合を出す（入ってくる学生の変化に近い）"""
import json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, FIG, C, GRAY, find, note
import gakko_parse as g

STEM = ["理学", "工学", "農学", "保健"]
SUBS = {"理学": ["数学", "物理学", "化学", "生物学", "地学"],
        "工学": ["機械工学", "電気通信工学", "土木建築工学", "応用化学", "経営工学"],
        "保健": ["医学", "歯学", "薬学", "看護学"]}


def build():
    m, s, f1 = [], [], []
    for y in range(2000, 2026):
        df, sd = g.table_by_major(find(y, "GU"), g.GU_MAJ, subs=True)
        df["year"] = y; sd["year"] = y; m.append(df); s.append(sd)
        d1, _ = g.table_by_major(find(y, "GU"), g.GU_MAJ, which=1)      # 2組目の計男女＝1年次
        d1["year"] = y; f1.append(d1)
    m, s, f1 = (pd.concat(x, ignore_index=True) for x in (m, s, f1))
    m.to_csv(DATA / "univ_students_by_field.csv", index=False)
    s.to_csv(DATA / "univ_students_by_subfield.csv", index=False)
    f1.to_csv(DATA / "univ_first_year_by_field.csv", index=False)
    return m, s, f1


def main():
    m, s, f1 = build()
    for d in (m, s, f1):
        d["女子の割合"] = d.女 / d.計 * 100
    P = m.pivot(index="year", columns="分類", values="女子の割合")
    N = m.pivot(index="year", columns="分類", values="女")
    P1 = f1.pivot(index="year", columns="分類", values="女子の割合")
    P.round(2).to_csv(RES / "a236_female_share_by_field.csv")
    P1.round(2).to_csv(RES / "a236_female_share_first_year.csv")
    rs = m[m.分類.isin(["理学", "工学"])].groupby("year")[["女", "計"]].sum(); rs["女子の割合"] = rs.女 / rs.計 * 100
    rs1 = f1[f1.分類.isin(["理学", "工学"])].groupby("year")[["女", "計"]].sum(); rs1["女子の割合"] = rs1.女 / rs1.計 * 100
    rs.round(2).to_csv(RES / "a236_rigaku_kogaku_total.csv")
    sub = s[s.apply(lambda r: r.小分類 in SUBS.get(r.分類, []), axis=1)]
    sub = sub[sub.year.isin([2000, 2025])].pivot_table(index=["分類", "小分類"], columns="year", values=["女子の割合", "計", "女"])
    sub.round(2).to_csv(RES / "a236_subfields_2000_2025.csv")
    S = {"female_share": {k: [round(P.loc[2000, k], 1), round(P.loc[2025, k], 1)] for k in STEM + ["計", "社会科学", "人文科学"]},
         "female_share_first_year": {k: [round(P1.loc[2000, k], 1), round(P1.loc[2025, k], 1)] for k in STEM + ["計"]},
         "rigaku_kogaku_women": [int(rs.loc[2000, "女"]), int(rs.loc[2025, "女"])],
         "rigaku_kogaku_share": [round(rs.loc[2000, "女子の割合"], 1), round(rs.loc[2010, "女子の割合"], 1), round(rs.loc[2025, "女子の割合"], 1)],
         "rigaku_kogaku_share_first_year": [round(rs1.loc[2000, "女子の割合"], 1), round(rs1.loc[2025, "女子の割合"], 1)],
         "rigaku_kogaku_total": [int(rs.loc[2000, "計"]), int(rs.loc[2025, "計"])],
         "kogaku_women": [int(N.loc[2000, "工学"]), int(N.loc[2025, "工学"])],
         "kogaku_share_2010_2015_2020": [round(P.loc[y, "工学"], 1) for y in (2010, 2015, 2020)],
         "hoken_women": [int(N.loc[2000, "保健"]), int(N.loc[2025, "保健"])],
         "subfields": {f"{a}/{b}": [round(sub.loc[(a, b), ("女子の割合", 2000)], 1), round(sub.loc[(a, b), ("女子の割合", 2025)], 1),
                                    int(sub.loc[(a, b), ("計", 2000)]), int(sub.loc[(a, b), ("計", 2025)])] for a, b in sub.index}}
    # 女子学生の増え方のうち、工学の学生全体が増えた分と女子の割合が上がった分（2000→2025）
    t0, t1 = m[(m.year == 2000) & (m.分類 == "工学")].iloc[0], m[(m.year == 2025) & (m.分類 == "工学")].iloc[0]
    S["kogaku_decomp"] = {"total_change": int(t1.女 - t0.女), "due_to_share": round((t1.女 / t1.計 - t0.女 / t0.計) * t1.計), "due_to_size": round((t1.計 - t0.計) * t0.女 / t0.計)}
    json.dump(S, open(RES / "a236_summary.json", "w"), ensure_ascii=False, indent=1)

    # 図1 分野別の女子の割合
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for k, col in zip(["保健", "農学", "理学", "工学"], C):
        ax.plot(P.index, P[k], color=col, lw=2.3, label=k)
        ax.annotate(f"{P.loc[2025, k]:.1f}%", (2025, P.loc[2025, k]), xytext=(4, 0), textcoords="offset points", va="center", color=col, fontsize=9)
    ax.plot(P.index, P["計"], color=GRAY, lw=1.6, ls="--", label="学部全体")
    ax.set_title("大学（学部）の学生に占める女子の割合（%）"); ax.set_xlim(2000, 2027.5); ax.set_ylim(0, 70)
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper left")
    note(ax); fig.savefig(FIG / "a236_female_share_by_field.png"); plt.close(fig)
    # 図2 小分類の2000年度と2025年度
    lab, a0, a1 = [], [], []
    for a in ["理学", "工学", "保健"]:
        for b in SUBS[a]:
            if (a, b) in sub.index:
                lab.append(f"{a}：{b}"); a0.append(sub.loc[(a, b), ("女子の割合", 2000)]); a1.append(sub.loc[(a, b), ("女子の割合", 2025)])
    yy = np.arange(len(lab))[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.6))
    for yv, x0, x1 in zip(yy, a0, a1):
        ax.plot([x0, x1], [yv, yv], color="#cccccc", lw=2)
    ax.scatter(a0, yy, color=GRAY, s=40, label="2000年度", zorder=3)
    ax.scatter(a1, yy, color=C[1], s=46, label="2025年度", zorder=3)
    for yv, x1 in zip(yy, a1):
        ax.text(x1 + (2 if x1 < 85 else -9), yv, f"{x1:.0f}%", va="center", fontsize=8.5, color=C[1])
    ax.set_yticks(yy); ax.set_yticklabels(lab, fontsize=9.5); ax.set_xlim(0, 100)
    ax.set_title("学科ごとの女子学生の割合（%）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
    note(ax); fig.savefig(FIG / "a236_subfields.png"); plt.close(fig)
    # 図3 理学＋工学の女子学生の数と割合（全学年・1年次）
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(rs.index, rs.女 / 1e4, color=C[0], alpha=.75, label="理学＋工学の女子学生（万人、左）")
    ax.set_ylabel("万人"); ax2 = ax.twinx()
    ax2.plot(rs.index, rs.女子の割合, color=C[1], lw=2.3, label="女子の割合（全学年、右）")
    ax2.plot(rs1.index, rs1.女子の割合, color=C[1], lw=1.6, ls=":", label="女子の割合（1年次、右）")
    ax2.set_ylim(0, 25); ax2.set_ylabel("%"); ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8.5, loc="upper left")
    ax.set_ylim(0, 12); ax.set_title("理学・工学の女子学生")
    note(ax); fig.savefig(FIG / "a236_rigaku_kogaku.png"); plt.close(fig)
    print(json.dumps(S, ensure_ascii=False))


if __name__ == "__main__":
    main()
