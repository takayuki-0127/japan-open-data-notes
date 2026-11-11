"""239 専門学校に進む人は、どの分野で増えたのか
- 年次統計（参考資料）「専修学校の学校数、在籍者数、教職員数（昭和51年〜）」で1976〜2025年度の生徒数
- 各年度の「設置者別学科別生徒数」（2000〜2025年度、計＝高等課程・専門課程・一般課程の合計）で分野別に並べる。
  小分類は2005年度から今と同じ区分なので、小分類の比較は2005→2025年度"""
import json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RAW, RES, FIG, C, GRAY, find, note
import gakko_parse as g

MAJ = g.S_MAJ


def nenji():
    d = pd.read_excel(RAW / "nenji_K008_000031852321.xlsx", header=None)
    d = d[d[1].astype(str).str.fullmatch(r"\d{4}")]
    return pd.DataFrame({"year": d[1].astype(int), "学校数": d[2].astype(float), "在籍者": pd.to_numeric(d[6], errors="coerce"),
                         "男": pd.to_numeric(d[10], errors="coerce"), "女": pd.to_numeric(d[11], errors="coerce")})


def build():
    k = nenji(); k.to_csv(DATA / "senshu_nenji.csv", index=False)
    m, s = [], []
    for y in range(2000, 2026):
        df, sd = g.table_by_major(find(y, "S"), MAJ + ["__残り"], subs=True)
        df = df[df.分類 != "__残り"]; df["year"] = y; sd["year"] = y; m.append(df); s.append(sd)
    m, s = pd.concat(m, ignore_index=True), pd.concat(s, ignore_index=True)
    s["小分類"] = s.小分類.str.replace("･", "・").replace({"受験・補修": "受験・補習"})
    m.to_csv(DATA / "senshu_students_by_field.csv", index=False); s.to_csv(DATA / "senshu_students_by_subfield.csv", index=False)
    return k, m, s


def main():
    k, m, s = build()
    k = k.set_index("year")
    P = m.pivot(index="year", columns="分類", values="計"); P.to_csv(RES / "a239_students_by_field.csv")
    chk = (P[MAJ].sum(axis=1) - P["計"]).abs().max()
    q = s[s.year.isin([2005, 2015, 2025])].pivot_table(index=["分類", "小分類"], columns="year", values="計")
    q = q[~q.index.get_level_values(1).isin(["その他"])]
    q["増減"] = q[2025] - q[2005]; q["倍率"] = q[2025] / q[2005]
    q.sort_values("増減").to_csv(RES / "a239_subfields_2005_2025.csv")
    pk = int(k.在籍者.idxmax())
    S = {"peak": [pk, int(k.loc[pk, "在籍者"])], "y2000": int(k.loc[2000, "在籍者"]), "y2005": int(k.loc[2005, "在籍者"]), "y2025": int(k.loc[2025, "在籍者"]),
         "check_major_sum_eq_total": float(chk), "check_total_eq_nenji": float((P["計"] - k.在籍者.reindex(P.index)).abs().max()),
         "field": {f: [int(P.loc[2000, f]), int(P.loc[2005, f]), int(P.loc[2025, f]), round(P.loc[2025, f] / P["計"].loc[2025] * 100, 1), round(P.loc[2000, f] / P["計"].loc[2000] * 100, 1)] for f in MAJ},
         "field_peak": {f: [int(P[f].idxmax()), int(P[f].max())] for f in MAJ}}
    up = q.sort_values("増減", ascending=False).head(8); dn = q.sort_values("増減").head(8)
    S["sub_up"] = {f"{a}/{b}": [int(r[2005]), int(r[2025]), round(r["倍率"], 2)] for (a, b), r in up.iterrows()}
    S["sub_down"] = {f"{a}/{b}": [int(r[2005]), int(r[2025]), round(r["倍率"], 2)] for (a, b), r in dn.iterrows()}
    nk = s[(s.分類 == "医療関係") & (s.小分類 == "看護")].set_index("year").計
    S["kango_peak"] = [int(nk.idxmax()), int(nk.max()), int(nk.loc[2025])]
    S["female_share"] = [round(k.loc[2000, "女"] / k.loc[2000, "在籍者"] * 100, 1), round(k.loc[2025, "女"] / k.loc[2025, "在籍者"] * 100, 1)]
    json.dump(S, open(RES / "a239_summary.json", "w"), ensure_ascii=False, indent=1)

    # 図1 長期
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.plot(k.index, k.在籍者 / 1e4, color=C[0], lw=2.4)
    ax.annotate(f"{pk}年度 {k.loc[pk, '在籍者'] / 1e4:.1f}万人", (pk, k.loc[pk, "在籍者"] / 1e4), xytext=(10, 8), textcoords="offset points", fontsize=9)
    ax.annotate(f"2025年度 {k.loc[2025, '在籍者'] / 1e4:.1f}万人", (2025, k.loc[2025, "在籍者"] / 1e4), xytext=(-90, -26), textcoords="offset points", fontsize=9)
    ax.set_ylim(0, 95); ax.set_xlim(1976, 2026); ax.set_title("専修学校の生徒（万人）")
    note(ax, "出典：文部科学省「学校基本調査」年次統計（e-Stat）をもとに作成者が加工して作成"); fig.savefig(FIG / "a239_long_series.png"); plt.close(fig)
    # 図2 分野別
    fig, ax = plt.subplots(figsize=(8, 4.8))
    pos = {f: P.loc[2025, f] / 1e4 for f in MAJ}
    order = sorted(MAJ, key=lambda f: pos[f])
    for a, b in zip(order, order[1:]):
        if pos[b] - pos[a] < .75:
            pos[b] = pos[a] + .75
    for f, col in zip(MAJ, C):
        ax.plot(P.index, P[f] / 1e4, color=col, lw=2.0, label=f.replace("関係", ""))
        ax.text(2025.4, pos[f], f"{f.replace('関係', '')} {P.loc[2025, f] / 1e4:.1f}", va="center", color=col, fontsize=8.5)
    ax.set_title("専修学校の分野別の生徒（万人）"); ax.set_xlim(2000, 2030)
    note(ax); fig.savefig(FIG / "a239_by_field.png"); plt.close(fig)
    # 図3 小分類の増減（2005→2025年度）
    sel = pd.concat([up, dn.iloc[::-1]])
    lab = [f"{b}（{a.replace('関係', '')}）" for a, b in sel.index]
    fig, ax = plt.subplots(figsize=(8, 5.6))
    v = sel["増減"].values
    ax.barh(lab, v, color=[C[0] if x > 0 else C[1] for x in v])
    for i, (x, r) in enumerate(zip(v, sel["倍率"].values)):
        ax.text(x + (300 if x > 0 else -300), i, f"{x:+,.0f}（{r:.2f}倍）", va="center", ha="left" if x > 0 else "right", fontsize=8)
    ax.axvline(0, color="#888", lw=.8); ax.invert_yaxis(); ax.set_xlim(-38000, 30000)
    ax.set_title("学科ごとの生徒の増減（2005年度→2025年度、人）")
    note(ax, "「その他」の学科は除いた\n" + "出典：文部科学省「学校基本調査」（e-Stat）をもとに作成者が加工して作成"); fig.savefig(FIG / "a239_subfield_change.png"); plt.close(fig)
    print(json.dumps(S, ensure_ascii=False))


if __name__ == "__main__":
    main()
