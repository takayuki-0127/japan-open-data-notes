"""238 大学院に進む人は、どの分野で増えて、どこで減ったのか
各年度の「専攻分野別 大学院入学状況」（2000〜2025年度）の入学者（修士課程・博士課程）を分野別に並べる"""
import json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, FIG, C, GRAY, find, note
import gakko_parse as g

F = ["工学", "その他", "社会科学", "理学", "保健", "人文科学", "農学", "教育", "芸術", "家政", "商船"]


def build():
    out = []
    for y in range(2000, 2026):
        for sh, c in [(0, "修士"), (1, "博士")]:
            df, _ = g.table_by_major(find(y, "N"), g.GU_MAJ, sheet=sh, which=1)
            df["year"] = y; df["課程"] = c; out.append(df)
    d = pd.concat(out, ignore_index=True); d.to_csv(DATA / "grad_entrants_by_field.csv", index=False)
    return d


def main():
    d = build()
    S = {}
    for c in ["修士", "博士"]:
        p = d[d.課程 == c].pivot(index="year", columns="分類", values="計")
        p.to_csv(RES / f"a238_{c}_entrants.csv")
        ch = (p.loc[2025] - p.loc[2000]).drop("計")
        S[c] = {"total": [int(p.loc[2000, "計"]), int(p.loc[2025, "計"])], "peak": [int(p["計"].idxmax()), int(p["計"].max())],
                "min": [int(p["計"].idxmin()), int(p["計"].min())],
                "by_field": {f: [int(p.loc[2000, f]), int(p.loc[2025, f]), round((p.loc[2025, f] / p.loc[2000, f] - 1) * 100, 1) if p.loc[2000, f] else None] for f in F},
                "share_2025": {f: round(p.loc[2025, f] / p.loc[2025, "計"] * 100, 1) for f in F},
                "share_2000": {f: round(p.loc[2000, f] / p.loc[2000, "計"] * 100, 1) for f in F}}
        S[c]["change"] = {f: int(ch[f]) for f in F}
        S[c]["female_share"] = [round(d[(d.課程 == c) & (d.分類 == "計") & (d.year == y)].女.iloc[0] / d[(d.課程 == c) & (d.分類 == "計") & (d.year == y)].計.iloc[0] * 100, 1) for y in (2000, 2025)]
        S[c]["kogaku_2010_2015"] = [int(p.loc[2010, "工学"]), int(p.loc[2015, "工学"])]
    p = d[d.課程 == "修士"].pivot(index="year", columns="分類", values="計")
    S["修士"]["kyoiku_2007_2008_2010_2025"] = [int(p.loc[y, "教育"]) for y in (2007, 2008, 2010, 2020, 2025)]
    json.dump(S, open(RES / "a238_summary.json", "w"), ensure_ascii=False, indent=1)

    # 図1 修士の分野別入学者
    p = d[d.課程 == "修士"].pivot(index="year", columns="分類", values="計")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    fl = ["工学", "その他", "社会科学", "理学", "保健", "人文科学", "教育"]
    pos = {f: np.log10(p.loc[2025, f] / 1e3) for f in fl}
    order = sorted(fl, key=lambda f: pos[f])
    for a, b in zip(order, order[1:]):
        if pos[b] - pos[a] < .045:
            pos[b] = pos[a] + .045
    for f, col in zip(fl, C):
        ax.plot(p.index, p[f] / 1e3, color=col, lw=2.2 if f in ("工学", "その他") else 1.7, label=f)
        ax.text(2025.4, 10 ** pos[f], f"{f} {p.loc[2025, f] / 1e3:.1f}", va="center", color=col, fontsize=8.5)
    ax.set_title("修士課程の入学者（千人、専攻分野別）"); ax.set_xlim(2000, 2029.5); ax.set_yscale("log")
    ax.set_yticks([1, 2, 5, 10, 20, 35]); ax.set_yticklabels(["1", "2", "5", "10", "20", "35"])
    note(ax, "縦軸は対数目盛。「その他」は複数の分野にまたがる研究科など\n" + "出典：文部科学省「学校基本調査」（e-Stat）をもとに作成者が加工して作成")
    fig.savefig(FIG / "a238_master_by_field.png"); plt.close(fig)
    # 図2 2000→2025年度の増減（人）
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), sharey=True)
    for ax, c in zip(axs, ["修士", "博士"]):
        v = [S[c]["change"][f] for f in F[:-1]]
        ax.barh(F[:-1], v, color=[C[0] if x > 0 else C[1] for x in v])
        for i, x in enumerate(v):
            ax.text(x + (60 if x >= 0 else -60), i, f"{x:+,}", va="center", ha="left" if x >= 0 else "right", fontsize=8)
        ax.axvline(0, color="#888", lw=.8); ax.set_title(f"{c}課程（計 {S[c]['change'] and sum(S[c]['change'].values()):+,}人）", fontsize=11)
        lim = max(abs(min(v)), max(v)) * 1.45; ax.set_xlim(-lim, lim)
    axs[0].invert_yaxis(); fig.suptitle("大学院の入学者の増減（2000年度→2025年度、人）")
    note(axs[0]); fig.savefig(FIG / "a238_change.png"); plt.close(fig)
    # 図3 博士の分野別（2000年度＝100）
    q = d[d.課程 == "博士"].pivot(index="year", columns="分類", values="計")
    idx = q.div(q.loc[2000]) * 100
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for f, col in zip(["保健", "工学", "その他", "理学", "社会科学", "人文科学", "農学"], C):
        ax.plot(idx.index, idx[f], color=col, lw=1.9, label=f)
        ax.annotate(f"{f} {idx.loc[2025, f]:.0f}", (2025, idx.loc[2025, f]), xytext=(4, 0), textcoords="offset points", va="center", color=col, fontsize=8.5)
    ax.plot(idx.index, idx["計"], color=INK if False else "#222", lw=2.4, ls="--", label="計")
    ax.axhline(100, color="#bbb", lw=.8)
    ax.annotate(f"計 {idx.loc[2025, '計']:.0f}", (2025, idx.loc[2025, "計"]), xytext=(4, 6), textcoords="offset points", va="center", color="#222", fontsize=8.5)
    ax.set_title("博士課程の入学者（2000年度＝100、専攻分野別）"); ax.set_xlim(2000, 2029.5)
    note(ax); fig.savefig(FIG / "a238_doctor_index.png"); plt.close(fig)
    print(json.dumps(S, ensure_ascii=False))


if __name__ == "__main__":
    main()
