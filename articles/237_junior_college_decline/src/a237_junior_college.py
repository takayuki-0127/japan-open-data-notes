"""237 短期大学の学生は、30年でどれだけ減ったのか
- 年次統計（参考資料）「短期大学の学校数、在籍者数、教職員数（昭和25年〜）」で1950〜2025年度の在籍者・学校数
- 各年度の「関係学科別 学生数」（本科、2000〜2025年度）で、どの学科から減ったか"""
import json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RAW, RES, FIG, C, GRAY, find, note
import gakko_parse as g

ORDER = ["教育", "家政", "社会", "保健", "人文", "芸術", "工業", "教養", "農業", "その他"]


def nenji():
    d = pd.read_excel(RAW / "nenji_K012_000031852325.xlsx", header=None)
    d = d[d[1].astype(str).str.fullmatch(r"\d{4}")]
    return pd.DataFrame({"year": d[1].astype(int), "学校数": d[2].astype(float), "在籍者": pd.to_numeric(d[6], errors="coerce"),
                         "男": pd.to_numeric(d[10], errors="coerce"), "女": pd.to_numeric(d[11], errors="coerce")})


def build():
    k = nenji(); k.to_csv(DATA / "jc_nenji.csv", index=False)
    m, s = [], []
    for y in range(2000, 2026):
        df, sd = g.table_by_major(find(y, "GJ"), g.GJ_MAJ, subs=True); df["year"] = y; sd["year"] = y; m.append(df); s.append(sd)
    m, s = pd.concat(m, ignore_index=True), pd.concat(s, ignore_index=True)
    m.to_csv(DATA / "jc_students_by_field.csv", index=False); s.to_csv(DATA / "jc_students_by_subfield.csv", index=False)
    return k, m, s


def main():
    k, m, s = build()
    k = k.set_index("year")
    P = m.pivot(index="year", columns="分類", values="計")
    SH = P.div(P["計"], axis=0) * 100
    P.to_csv(RES / "a237_students_by_field.csv"); SH.round(2).to_csv(RES / "a237_share_by_field.csv")
    pk = int(k.在籍者.idxmax())
    S = {"peak": [pk, int(k.loc[pk, "在籍者"])], "y1995": int(k.loc[1995, "在籍者"]), "y2025": int(k.loc[2025, "在籍者"]),
         "ratio_2025_to_peak": round(k.loc[2025, "在籍者"] / k.loc[pk, "在籍者"], 3),
         "decline_1995_2025": round((1 - k.loc[2025, "在籍者"] / k.loc[1995, "在籍者"]) * 100, 1),
         "schools": [int(k.学校数.max()), int(k.学校数.idxmax()), int(k.loc[2025, "学校数"])],
         "female_share": {int(y): round(k.loc[y, "女"] / k.loc[y, "在籍者"] * 100, 1) for y in (1970, 1993, 2000, 2025)},
         "students_per_school": [round(k.loc[pk, "在籍者"] / k.loc[pk, "学校数"]), round(k.loc[2025, "在籍者"] / k.loc[2025, "学校数"])],
         "honka_2000_2025": [int(P.loc[2000, "計"]), int(P.loc[2025, "計"])],
         "field_2000_2025": {c: [int(P.loc[2000, c]), int(P.loc[2025, c]), round(P.loc[2025, c] / P.loc[2000, c] * 100, 1), round(SH.loc[2000, c], 1), round(SH.loc[2025, c], 1)] for c in ORDER}}
    sub = s[s.year.isin([2000, 2025])].pivot_table(index=["分類", "小分類"], columns="year", values="計")
    sub.to_csv(RES / "a237_subfields_2000_2025.csv")
    S["kindergarten"] = [int(sub.loc[("教育", "幼稚園教育"), 2000]), int(sub.loc[("教育", "幼稚園教育"), 2025])]
    S["kindergarten_share_2025"] = round(sub.loc[("教育", "幼稚園教育"), 2025] / P.loc[2025, "計"] * 100, 1)
    S["kaseigaku"] = [int(sub.loc[("家政", "家政学"), 2000]), int(sub.loc[("家政", "家政学"), 2025])]
    S["kango"] = [int(sub.loc[("保健", "看護学"), 2000]), int(sub.loc[("保健", "看護学"), 2025])]
    S["bungaku"] = [int(sub.loc[("人文", "文学"), 2000]), int(sub.loc[("人文", "文学"), 2025])]
    # 減った人数のうちどの学科の分か（2000→2025）
    d = (P.loc[2025] - P.loc[2000]).drop("計"); S["decline_contrib"] = {c: round(d[c] / d.sum() * 100, 1) for c in ORDER}
    S["k012_vs_honka_2025"] = round(P.loc[2025, "計"] / k.loc[2025, "在籍者"] * 100, 1)
    json.dump(S, open(RES / "a237_summary.json", "w"), ensure_ascii=False, indent=1)

    # 図1 長期の在籍者
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.fill_between(k.index, 0, k.女 / 1e4, color=C[1], alpha=.75, label="女性")
    ax.fill_between(k.index, k.女 / 1e4, k.在籍者 / 1e4, color=C[0], alpha=.75, label="男性")
    ax.annotate(f"{pk}年度 {k.loc[pk, '在籍者'] / 1e4:.1f}万人", (pk, k.loc[pk, "在籍者"] / 1e4), xytext=(-110, 6), textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color="#888"))
    ax.annotate(f"2025年度 {k.loc[2025, '在籍者'] / 1e4:.1f}万人", (2025, k.loc[2025, "在籍者"] / 1e4), xytext=(-120, 40), textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color="#888"))
    ax.set_title("短期大学の在籍者（万人）"); ax.set_xlim(1950, 2025); ax.legend(frameon=False, fontsize=9, loc="upper left")
    note(ax, "出典：文部科学省「学校基本調査」年次統計（e-Stat）をもとに作成者が加工して作成"); fig.savefig(FIG / "a237_long_series.png"); plt.close(fig)
    # 図2 学科別の2000年度と2025年度
    fig, ax = plt.subplots(figsize=(8, 4.8))
    x = np.arange(len(ORDER)); w = .38
    ax.bar(x - w / 2, [P.loc[2000, c] / 1e4 for c in ORDER], w, color=GRAY, label="2000年度")
    ax.bar(x + w / 2, [P.loc[2025, c] / 1e4 for c in ORDER], w, color=C[0], label="2025年度")
    for i, c in enumerate(ORDER):
        ax.text(i + w / 2, P.loc[2025, c] / 1e4 + .1, f"{P.loc[2025, c] / P.loc[2000, c] * 100:.0f}%", ha="center", fontsize=8, color=C[0])
    ax.set_xticks(x); ax.set_xticklabels(ORDER, fontsize=9.5); ax.set_title("短期大学（本科）の関係学科別の学生（万人、数字は2000年度＝100%）")
    ax.legend(frameon=False, fontsize=9)
    note(ax); fig.savefig(FIG / "a237_by_field.png"); plt.close(fig)
    # 図3 構成比
    yrs = [2000, 2005, 2010, 2015, 2020, 2025]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    left = np.zeros(len(yrs))
    for c, col in zip(ORDER, C + ["#bbbbbb"]):
        v = np.array([SH.loc[y, c] for y in yrs])
        ax.barh([str(y) for y in yrs], v, left=left, color=col, label=c)
        for i, (l, vv) in enumerate(zip(left, v)):
            if vv >= 8:
                ax.text(l + vv / 2, i, f"{vv:.0f}", ha="center", va="center", fontsize=8, color="white")
        left += v
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_title("短期大学（本科）の学生の学科構成（%）")
    ax.legend(frameon=False, fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(.5, -.08))
    note(ax, y=-0.13); fig.savefig(FIG / "a237_field_mix.png"); plt.close(fig)
    print(json.dumps(S, ensure_ascii=False))


if __name__ == "__main__":
    main()
