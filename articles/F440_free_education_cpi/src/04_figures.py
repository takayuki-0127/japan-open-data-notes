"""04 図（オフライン）：PNG 4枚。日付が入らないよう metadata を消す。"""
import csv, json, pathlib
import figstyle
from figstyle import plt, C, INK2, style, save

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
SRC = "出典：総務省「消費者物価指数」2015年・2020年・2025年基準（全国、月次）をもとに作成者が加工して作成"


def xpos(p):
    return int(p[:4]) + (int(p[4:]) - 1) / 12


def fig1(rows):
    x = [xpos(r["period"]) for r in rows]
    pre = [float(r["c_preschool"]) for r in rows]; hs = [float(r["c_hs"]) for r in rows]; lu = [float(r["c_lunch"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8.4, 5))
    wd = 1 / 12 * 0.85
    ax.bar(x, pre, width=wd, color=C[0], label="幼稚園・保育所の保育料", align="edge")
    ax.bar(x, hs, width=wd, bottom=[min(p, 0) for p in pre], color=C[1], label="高校の授業料（公立・私立）", align="edge")
    ax.bar(x, lu, width=wd, bottom=[min(p, 0) + min(h, 0) for p, h in zip(pre, hs)], color=C[3], label="学校給食（参考）", align="edge")
    ax.axhline(0, color=INK2, lw=0.8)
    for xv in [2021, 2026]:
        ax.axvline(xv, color="#c9c8c3", lw=0.8, ls=":")
    ax.text(2019.05, 0.06, "2015年基準", fontsize=8, color=INK2); ax.text(2021.05, 0.06, "2020年基準", fontsize=8, color=INK2); ax.text(2026.05, 0.06, "2025年基準", fontsize=8, color=INK2)
    ax.set_ylim(-0.75, 0.1)
    ax.set_xlim(2019, 2026.8); ax.set_xticks(range(2019, 2027))
    ax.set_ylabel("総合の前年同月比への寄与（ポイント）")
    ax.set_title("幼保の無償化は1年間、総合の前年比を約0.58ポイント押し下げた", loc="left", fontsize=12)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    style(ax)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.9, bottom=0.14)
    save(fig, FIG / "fig1_contrib_monthly.png", SRC, "注：寄与＝ウエイト×（今月−前年同月の指数）÷（総ウエイト×前年同月の総合）。月ごとにその時期の基準の表を使った")


def fig2(rows):
    x = [xpos(r["period"]) for r in rows]
    t = [float(r["total_yoy"]) for r in rows]; e = [float(r["total_ex_free5"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8.4, 5))
    ax.plot(x, t, color="#0b0b0b", lw=2, label="総合の前年同月比")
    ax.plot(x, e, color=C[0], lw=2, ls="--", label="幼稚園・保育所・高校の5品目の寄与を除いた値")
    ax.fill_between(x, t, e, color=C[0], alpha=0.12, lw=0)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlim(2019, 2026.8); ax.set_xticks(range(2019, 2027))
    ax.set_ylabel("%")
    ax.set_title("無償化の月から1年間は、総合の前年比がその分だけ低く出る", loc="left", fontsize=12)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    style(ax)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.14)
    save(fig, FIG / "fig2_total_vs_ex.png", SRC, "注：前年同月比は公表の指数（小数1桁）から計算。5品目は幼稚園保育料（公立・私立）・保育所保育料・高等学校授業料（公立・私立）")


def fig3(m):
    ev = m["events"]
    items = [("2019年10月\n幼稚園・保育所", ev["E1_2019_10_preschool"]["mean_12m"], C[0]),
             ("2020年4月\n高校（私立）", ev["E2_2020_04_private_hs"]["mean_12m"], C[1]),
             ("2020年4月\n大学など（参考）", ev["E2b_2020_04_higher_ed"]["mean_12m"], C[5]),
             ("2025年4月\n高校（公立・私立）", ev["E3_2025_04_hs"]["mean_12m"], C[1]),
             ("2026年4月\n高校（2025年基準）", ev["E4_2026_04_hs"]["first6_mean"], C[1]),
             ("2026年4月\n高校（2020年基準）", m["rob_E4_basis2020_first6"], C[1])]
    fig, ax = plt.subplots(figsize=(8.4, 5))
    xs = range(len(items))
    ax.bar(xs, [v for _, v, _ in items], color=[c for _, _, c in items], width=0.6)
    for i, (_, v, _) in enumerate(items):
        ax.text(i, v - 0.015, f"{v:.3f}", ha="center", va="top", fontsize=9, color=INK2)
    ax.set_xticks(list(xs)); ax.set_xticklabels([n for n, _, _ in items], fontsize=8.5)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylim(-0.7, 0.05)
    ax.set_ylabel("総合の前年同月比への寄与（ポイント、平均）")
    ax.set_title("押し下げの大きさは、幼保が高校の約3倍", loc="left", fontsize=12)
    style(ax)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.9, bottom=0.2)
    save(fig, FIG / "fig3_event_compare.png", SRC, "注：無償化の月から12か月の平均。2026年4月は9月までの6か月の平均。基準はその時期のもの（2026年4月は2つの基準で計算）")


def fig4():
    rows = list(csv.DictReader(open(DATA / "cpi_items_monthly.csv", encoding="utf-8")))
    d = {}
    for r in rows:
        d.setdefault((r["basis"], r["code"]), {})[r["period"]] = float(r["value"])

    def shift(p, k):
        y, mth = int(p[:4]), int(p[4:]); t = y * 12 + mth - 1 + k
        return f"{t // 12}{t % 12 + 1:02d}"
    lines = [("2015", "8080", "201910", "幼稚園保育料（公立）2019年10月", C[0], "-"), ("2015", "8090", "201910", "幼稚園保育料（私立）2019年10月", C[0], "--"),
             ("2015", "9921", "201910", "保育所保育料 2019年10月", C[2], "-"), ("2020", "8020", "202504", "高校授業料（公立）2025年4月", C[1], "-"),
             ("2025", "8030", "202604", "高校授業料（私立）2026年4月", C[1], "--")]
    fig, ax = plt.subplots(figsize=(8.4, 5))
    for b, c, st, lab, col, ls in lines:
        s = d[(b, c)]; base = s[shift(st, -1)]
        ks = [k for k in range(-6, 13) if shift(st, k) in s]
        ax.plot(ks, [100 * s[shift(st, k)] / base for k in ks], color=col, ls=ls, lw=2, label=lab)
    ax.axvline(0, color=INK2, lw=0.8, ls=":")
    ax.set_xlabel("無償化の月からの月数（0＝無償化の月）")
    ax.set_ylabel("前の月＝100")
    ax.set_ylim(-5, 110)
    ax.set_title("品目の指数は、その月に一度に下がり、あとは横ばい", loc="left", fontsize=12)
    ax.legend(loc="upper right", frameon=False, fontsize=8.5)
    ax.set_xticks(range(-6, 13, 2))
    style(ax)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    save(fig, FIG / "fig4_item_levels.png", SRC, "注：その時期の基準の月次の指数。2026年4月の私立は2026年9月まで")


def main():
    rows = list(csv.DictReader(open(RES / "requestion_ex_free.csv", encoding="utf-8")))
    m = json.load(open(RES / "main.json", encoding="utf-8"))
    fig1(rows); fig2(rows); fig3(m); fig4()


if __name__ == "__main__":
    main()
